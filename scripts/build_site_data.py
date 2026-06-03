#!/usr/bin/env python3
"""Generate public/data.js from data/{ticker}.yml — the site's data module.

The Claude Design export ships data.js as placeholder content. This makes
data/{ticker}.yml the single source of truth for the website too: numbers,
scenarios, and the PDF link all flow from the same YAML the memo PDF uses.
The probability-weighted math mirrors memo.py exactly so the site's
"expected fair value" + forward table match the PDF's Page 1.

Run after editing any data/{ticker}.yml or bumping a PDF version; it is
wired into scripts/rebuild_all.py.
"""
import datetime
import json
import os
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
MEMOS_DIR = REPO / "public" / "memos"
OUT = REPO / "public" / "data.js"

TICKERS = ["joby", "aur", "lth", "zm", "naut", "isrg", "ionq", "coin", "anthropic", "rklb", "oklo", "achr", "gral", "txg", "lulu", "abnb", "uber"]
# Canonical scenario order — worst to best. Each ticker subsets this list
# based on which keys appear in scenarios.* (e.g. ZM has all five, JOBY/AUR/
# LTH/NAUT have the standard four). The order here drives display order
# everywhere (Page 1 cards, Page 4 quant grid, Page 2 narratives) so adding
# ultra_bear at the front meant updating the visual layouts to render from
# left-to-right in the same order.
SCEN_ORDER = ["ultra_bear", "bear", "base", "bull", "ultra_bull"]
SITE_KEY = {
    "ultra_bear": "ultra_bear",
    "bear": "bear",
    "base": "base",
    "bull": "bull",
    "ultra_bull": "ultra",
}

DCF_DISPLAY = {
    "young_company": ("Young-Company DCF (Damodaran)", "asymmetrical-moonshots"),
    "mature_company": ("Mature-Company DCF", "fcf-plus-plus-growth"),
    "mature_company_sotp": ("Mature-Company DCF · SOTP", "fcf-plus-plus-growth"),
    "private_prevaluation": ("Private Pre-Valuation (exit-scenario)", "private-wishlist"),
}

# Canonical Helm taxonomy — source of truth for watchlists, umbrellas, themes,
# and conviction tiers. Loaded once; per-ticker taxonomy blocks are validated
# against this. The site emits memo.taxonomy (with display names resolved) so
# the JSX side can render chips, filters, and the future Matrix view without
# carrying the taxonomy mapping in JS.
TAXONOMY = yaml.safe_load((REPO / "data" / "taxonomy.yml").read_text())


def _theme_to_umbrella() -> dict:
    """Build reverse lookup: theme slug → umbrella slug. The taxonomy nests
    themes under umbrellas; this flattens for fast resolution."""
    out = {}
    for u_slug, u in TAXONOMY["umbrellas"].items():
        for t_slug in u.get("themes", {}):
            out[t_slug] = u_slug
    return out


THEME_TO_UMBRELLA = _theme_to_umbrella()


def resolve_taxonomy(tax: dict, ticker: str) -> dict:
    """Validate per-ticker taxonomy fields against TAXONOMY and resolve
    display names for the site. Raises ValueError on invalid values so a
    typo (e.g. wrong theme slug) fails the build instead of shipping silently."""
    if not tax:
        raise ValueError(f"{ticker}: missing top-level `taxonomy:` block")
    wl = tax.get("watchlist")
    if wl not in TAXONOMY["watchlists"]:
        raise ValueError(f"{ticker}: taxonomy.watchlist={wl!r} not in {list(TAXONOMY['watchlists'])}")
    tier = tax.get("tier")
    if TAXONOMY["watchlists"][wl].get("allows_tiers", True):
        if tier not in TAXONOMY["tiers"]:
            raise ValueError(f"{ticker}: taxonomy.tier={tier!r} not in {TAXONOMY['tiers']}")
    elif tier is not None:
        raise ValueError(f"{ticker}: watchlist {wl!r} is tier-less; remove taxonomy.tier")
    themes = tax.get("themes") or []
    if not themes:
        raise ValueError(f"{ticker}: taxonomy.themes must have at least one entry")
    for t in themes:
        if t not in THEME_TO_UMBRELLA:
            raise ValueError(f"{ticker}: taxonomy.themes entry {t!r} not in any umbrella")
    primary = tax.get("primary_theme") or themes[0]
    if primary not in themes:
        raise ValueError(f"{ticker}: taxonomy.primary_theme={primary!r} not in themes")
    umbrella = THEME_TO_UMBRELLA[primary]
    return {
        "watchlist": wl,
        "watchlistName": TAXONOMY["watchlists"][wl]["name"],
        "tier": tier,
        "themes": list(themes),
        "themeNames": [TAXONOMY["umbrellas"][THEME_TO_UMBRELLA[t]]["themes"][t] for t in themes],
        "primaryTheme": primary,
        "primaryThemeName": TAXONOMY["umbrellas"][umbrella]["themes"][primary],
        "umbrella": umbrella,
        "umbrellaName": TAXONOMY["umbrellas"][umbrella]["name"],
    }


def collapse(s: str) -> str:
    return " ".join(str(s).split())


def _pick_rev_per_unit(chart_data: dict) -> list | None:
    # rev_per_unit's YAML key is ticker-specific. Probe known names, then
    # fall back to anything that starts with "rev_per_" so a new ticker can
    # name its unit naturally (e.g. rev_per_system for IONQ) without needing
    # a JSX/Python sync.
    for key in ("rev_per_aircraft", "rev_per_truck", "rev_per_instrument", "rev_per_system"):
        if key in chart_data:
            return list(chart_data[key])
    for key in chart_data:
        if key.startswith("rev_per_"):
            return list(chart_data[key])
    return None


def _camelize(d: dict) -> dict:
    """snake_case → camelCase for top-level keys (recursive on dict values).
    The JSX side uses camelCase; YAML uses snake_case. Keep the line crossing
    here so JSX doesn't carry the mapping."""
    out = {}
    for k, v in d.items():
        parts = k.split("_")
        new_k = parts[0] + "".join(p.title() for p in parts[1:])
        if isinstance(v, dict):
            v = _camelize(v)
        out[new_k] = v
    return out


def _camel_deep(v):
    """Like _camelize but also recurses into lists (the competitive block
    carries lists of dicts — rivals, lead_lag, threats)."""
    if isinstance(v, dict):
        out = {}
        for k, val in v.items():
            parts = k.split("_")
            out[parts[0] + "".join(p.title() for p in parts[1:])] = _camel_deep(val)
        return out
    if isinstance(v, list):
        return [_camel_deep(x) for x in v]
    return v


def fmt_shares(m: float) -> str:
    return f"{m / 1000:.2f}B" if m >= 1000 else f"{m:.0f}M"


def _fmt_b(b: float) -> str:
    return f"${b:g}B" if b >= 1 else f"${b * 1000:.0f}M"

def fmt_cash(mk: dict) -> str:
    cash = mk["cash_billion"]
    nd = mk["net_debt_billion"]
    s = f"{_fmt_b(cash)} cash, " + ("zero debt" if nd == 0 else f"{_fmt_b(nd)} net debt")
    extras = [e for e in mk.get("extras", []) if e]
    if extras:
        s += " · " + "; ".join(extras)
    return s


def human_size(p: Path) -> str:
    n = p.stat().st_size
    return f"{n / 1048576:.1f} MB" if n >= 1048576 else f"{n / 1024:.0f} KB"


def label_date(d) -> tuple[str, str]:
    if isinstance(d, (datetime.date, datetime.datetime)):
        iso = d.strftime("%Y-%m-%d")
        lbl = d.strftime("%B %-d, %Y")
    else:
        iso = str(d)
        dt = datetime.datetime.strptime(iso, "%Y-%m-%d")
        lbl = dt.strftime("%B %-d, %Y")
    return iso, lbl


def _scn_print_payload(s: dict, is_private: bool) -> dict:
    """Per-scenario PDF payload. Public scenarios carry dcf_metrics/dcf_path;
    private scenarios carry an exit_terms block instead (the renderer
    dispatches on dcfType)."""
    base = {
        "probability": float(s["probability"]),
        "expectedPerShare": float(s["expected_per_share"]),
        "label": s["label"],
        "shortLabel": s["short_label"],
    }
    if is_private:
        base["exitTerms"] = _camelize(dict(s["exit_terms"]))
        base["dcfMetrics"] = {}
        base["dcfPath"] = {}
        base["chartData"] = {}
        base["revPerUnit"] = None
    else:
        base["dcfMetrics"] = dict(s["dcf_metrics"])
        base["dcfPath"] = dict(s["dcf_path"])
        base["chartData"] = dict(s.get("chart_data", {}))
        base["revPerUnit"] = _pick_rev_per_unit(s.get("chart_data", {}))
    return base


def build_memo(ticker: str) -> dict:
    d = yaml.safe_load((DATA / f"{ticker}.yml").read_text())
    st = d["stamp"]
    spot = float(d["spot"])
    dcf_type = d["dcf_type"]
    dcf_display, fallback_category = DCF_DISPLAY[dcf_type]
    # Taxonomy is now the source of truth for category. The DCF-type fallback
    # remains for any ticker not yet tagged (back-compat during rollout).
    tax = resolve_taxonomy(d.get("taxonomy"), ticker) if d.get("taxonomy") else None
    category = tax["watchlist"] if tax else fallback_category
    iso, lbl = label_date(d["date"])

    is_private = dcf_type == "private_prevaluation"
    scn = d["scenarios"]
    # Probability-weighted math — identical to memo.py. For private companies
    # expected_per_share is already a present-value (discounted at a venture
    # WACC per scenario), so the weighted is a present value too.
    pw_expected = sum(s["probability"] * s["expected_per_share"]
                      for s in scn.values())

    # Forward-compounded value table is a public-equity construct (compound the
    # weighted value at the terminal WACC out to +20y). It's meaningless for a
    # private pre-exit company whose value crystallizes at a discrete exit, so
    # we emit an empty compound for private and the Page 1 forward table is
    # suppressed in the renderer.
    if is_private:
        compound = []
    else:
        def pw_at(T: int) -> float:
            return sum(s["probability"] * s["expected_per_share"]
                       * (1 + s["dcf_path"]["wacc_path"][-1]) ** T
                       for s in scn.values())
        compound = [{"y": T, "value": round(pw_at(T), 2),
                     "mult": round(pw_at(T) / spot, 2)} for T in (5, 10, 15, 20)]

    # Each ticker subsets SCEN_ORDER based on which keys exist in its YAML.
    # ZM has 5 (with ultra_bear); JOBY/AUR/LTH/NAUT have the standard 4.
    ticker_scens = [k for k in SCEN_ORDER if k in scn]

    scenarios = []
    for k in ticker_scens:
        s = scn[k]
        paras = s["narrative"]
        what = paras[:-1] if len(paras) > 2 else paras  # drop math-summary para (memo.py P2)
        scenarios.append({
            "key": SITE_KEY[k],
            "label": s["label"].upper(),
            "prob": round(s["probability"] * 100),
            "price": round(float(s["expected_per_share"]), 2),
            "headline": collapse(s["headline"]),
            "why": collapse(s["probability_rationale"]),
            "what": [collapse(p) for p in what],
        })

    probs = {k: round(scn[k]["probability"] * 100) for k in ticker_scens}
    pdf_file = f"{ticker}-memo__v{st['pdf_version']}__{st['pdf_timestamp']}.pdf"
    pdf_path = MEMOS_DIR / pdf_file
    # The target PDF may not be rendered yet — rebuild_all runs build_site_data
    # (which render needs for content + footer stamp) *before* the render step,
    # and a freshly bumped stamp names a file that doesn't exist until render.
    # Size is display-only, so emit a placeholder and continue rather than
    # hard-failing; it's corrected on the post-render rebuild.
    pdf_size = human_size(pdf_path) if pdf_path.exists() else "—"
    if not pdf_path.exists():
        print(f"  note: {pdf_file} not yet rendered — size placeholder")

    # Prior versions — the same shape we accept in the YAML (stamp.prior_versions).
    # We resolve each entry's PDF filename + size against public/memos/. If a
    # historical PDF is missing on disk we drop the entry from the site
    # listing (file would 404). Most recent first.
    prior = []
    for pv in (st.get("prior_versions") or []):
        pv_file = f"{ticker}-memo__v{pv['version']}__{pv['timestamp']}.pdf"
        pv_path = MEMOS_DIR / pv_file
        if not pv_path.exists():
            continue
        prior.append({
            "version": pv["version"],
            "file": pv_file,
            "size": human_size(pv_path),
            "asOfDate": pv["asOfDate"],
            "spotPrice": float(pv["spotPrice"]),
        })

    mk = d["market"]
    return {
        "ticker": d["ticker"],
        "slug": ticker,
        "company": d["company"],
        "exchange": d["exchange"],
        "category": category,
        "dcfType": dcf_display,
        "publishedISO": iso,
        "publishedLabel": lbl,
        "pdf": {"file": pdf_file, "size": pdf_size, "priorVersions": prior},
        "metrics": {
            "mktCap": _fmt_b(mk['market_cap_billion']),
            "shares": fmt_shares(mk["shares_outstanding_million"]),
            "cash": fmt_cash(mk),
        },
        "spot": {"price": spot, "asOf": f"{lbl} close"},
        "expected": {"fair": round(pw_expected, 2),
                      "deltaPct": round((pw_expected / spot - 1) * 100, 1)},
        "compound": compound,
        "taxonomy": tax,
        "question": collapse(d["central_question"]),
        "scenarios": scenarios,
        "methodology": (
            f"DCF framework: {dcf_display}. Probability weighting: "
            + (f"Ultra Bear {probs['ultra_bear']} / " if "ultra_bear" in probs else "")
            + f"Bear {probs['bear']} / Base {probs['base']} / "
            f"Bull {probs['bull']} / Ultra Bull {probs['ultra_bull']}. "
            f"Spot price reference: {lbl} close."),
        "thesis": collapse(d["thesis"]),
        # Public-equity price history. Private companies have no price history
        # (funding_history is emitted under print.fundingHistory instead).
        "historicalPrices": ({
            "xMin": float(d["historical_prices"]["x_min"]),
            "ipoMarker": d["historical_prices"]["ipo_marker"],
            "points": [[float(p[0]), float(p[1])]
                       for p in d["historical_prices"]["points"]],
        } if "historical_prices" in d else None),
        "weightingRationale": [
            {"label": r["label"], "body": collapse(r["body"])}
            for r in d["weighting_rationale"]
        ],
        # Page 3 (business snapshot) data — historical anchors for charts +
        # page subtitle/sources strings.
        "page3": {
            "subtitle": collapse(d["page3"]["subtitle"]),
            "sources": collapse(d["page3"]["sources"]),
            "chartReference": _camelize(d.get("chart_reference", {})),
            # Phase 4: chart-aesthetic config (titles, peer copy, captions,
            # legend strings) lives in YAML so per-ticker layout strings
            # ship with the data, not the JSX.
            "chartConfig": _camelize(d.get("page3_chart_config", {})),
        },
        # PDF-only payload — fields the print harness (public/print.html +
        # public/memo_pdf.jsx) needs that the site doesn't. Per-scenario data
        # is dumped raw so the JSX can compute display rows itself (no
        # parallel "what to display" logic in Python).
        "print": {
            "dcfType": dcf_type,
            "dcfPeriodYears": 10 if dcf_type == "young_company" else 5,  # n/a for private
            "tamBillion": d.get("chart_reference", {}).get("tam_billion"),
            "weighted": {
                "expected": round(pw_expected, 2),
                "upsidePct": round((pw_expected / spot - 1) * 100, 1),
            },
            "market": {
                "marketCapBillion": float(mk["market_cap_billion"]),
                "sharesOutstandingMillion": float(mk["shares_outstanding_million"]),
                "cashBillion": float(mk["cash_billion"]),
                "netDebtBillion": float(mk["net_debt_billion"]),
            },
            "scenarios": {
                k: _scn_print_payload(scn[k], is_private)
                for k in ticker_scens
            },
            # Private-company extras. Funding-round history replaces public
            # price history; the renderer uses it for the Page-1/Page-3 charts.
            **({
                "private": {
                    "spotKind": d.get("spot_kind"),
                    "spotAsOf": d.get("spot_as_of"),
                    "spotRound": d.get("spot_round"),
                    "spotCaveat": collapse(d.get("spot_caveat", "")),
                    "lastPostMoneyBillion": float(mk["market_cap_billion"]),
                    "fdsMillion": float(mk["shares_outstanding_million"]),
                },
                "fundingHistory": {
                    "firstRoundMarker": d["funding_history"]["first_round_marker"],
                    "xMin": float(d["funding_history"]["x_min"]),
                    "rounds": [
                        {"x": float(r["x"]), "ps": float(r["ps"]), "name": r["name"],
                         "pm": float(r["pm"]), "lead": r.get("lead", "")}
                        for r in d["funding_history"]["rounds"]
                    ],
                },
            } if is_private else {}),
            # Page 4 — Competitive landscape (§6d). Optional: emitted only when
            # the ticker carries a `competitive` block; the renderer adds the
            # 6th page only when present (else the memo stays 5 pages).
            **({"competitive": _camel_deep(d["competitive"])}
               if "competitive" in d else {}),
            "appendix": {
                "pushback": [{"label": p["label"], "body": collapse(p["body"])}
                             for p in d["appendix"]["pushback"]],
                "triggers": [{"label": t["label"], "body": collapse(t["body"])}
                             for t in d["appendix"]["triggers"]],
            },
            "glossary": [{"term": g["term"], "definition": collapse(g["definition"])}
                         for g in d["glossary"]],
            "stamp": {
                "footerVersion": st["footer_version"],
                "footerTimestamp": st["footer_timestamp"],
                "canonicalJsx": st["canonical_jsx"],
            },
        },
    }


# Categories derive from the taxonomy watchlists. Built dynamically and
# filtered to watchlists that have ≥1 published memo (no empty cards on
# the home page). Adding a memo in a new watchlist (e.g. private-wishlist,
# fcf-megacap) makes the category appear automatically — no hand-wiring.
def build_categories(memos: list) -> dict:
    present = {m["category"] for m in memos}
    out = {}
    for slug, w in TAXONOMY["watchlists"].items():
        if slug not in present:
            continue
        out[slug] = {
            "slug": slug,
            "name": w["name"],
            "sub": collapse(w.get("sub", "")),
            "short": collapse(w.get("sub", "")),
            "long": collapse(w.get("long", "")),
        }
    return out

DISCLAIMER_BLOCKS = [
    {"h": "Not investment advice.",
     "p": "This research is published for educational and informational "
          "purposes only by an individual not registered as an investment "
          "advisor. Nothing on this site constitutes a recommendation to buy, "
          "sell, or hold any security, or a solicitation to make any "
          "investment decision."},
    {"h": "AI-assisted analysis.",
     "p": "Research is produced with assistance from large language models "
          "(Claude, primarily). Numbers, scenarios, and probability weights "
          "reflect the author’s independent judgment; LLM-generated "
          "content is reviewed and edited before publication. Errors and "
          "omissions remain the author’s responsibility."},
    {"h": "Author may hold positions.",
     "p": "The author may hold long or short positions in any security "
          "discussed, and may transact in those securities at any time, "
          "without notice. Position disclosures are not provided."},
    {"h": "No warranties.",
     "p": "Information is provided on an “as is” basis. The author "
          "makes no representations as to accuracy, completeness, or fitness "
          "for any particular purpose. Past performance is not indicative of "
          "future results. Probability-weighted expected values are model "
          "outputs, not predictions."},
    {"h": "Do your own research.",
     "p": "Consult a registered investment advisor before making any "
          "investment decision."},
]

# Disclaimers rendered on PDF Page 5. These mirror memo.py's hardcoded
# DISCLAIMERS_FULL list (6 items, fuller treatment than the site's
# DISCLAIMER_BLOCKS). Kept here so the JSX print harness has a single
# source of truth.
PDF_DISCLAIMERS = [
    {"h": "Not investment advice.",
     "p": "This document is produced for entertainment and educational "
          "purposes only by an individual amateur investor. "
          "\"Alameda Research 2: Electric Boogaloo\" is the unincorporated "
          "personal concept of one person and is not a registered investment "
          "management entity. Nothing herein constitutes investment advice, "
          "a recommendation, or a solicitation to buy or sell any security."},
    {"h": "Not a professional.",
     "p": "The author is not a registered investment advisor, broker-dealer, "
          "CFA charterholder, certified financial planner, or licensed "
          "financial professional of any kind. The author has no formal "
          "training in equity research or capital markets. No fiduciary "
          "relationship is created by reading this document."},
    {"h": "AI-assisted analysis.",
     "p": "Substantial portions of this analysis were produced with the "
          "assistance of large language models. LLMs are known to fabricate "
          "facts, miscalculate numbers, hallucinate sources, and present "
          "incorrect information with high apparent confidence. Every figure, "
          "claim, and projection in this document should be independently "
          "verified before acting on it."},
    {"h": "Forward-looking statements.",
     "p": "Scenarios, valuations, projections, and any forward-looking "
          "statements involve substantial assumptions and uncertainty. Actual "
          "results may differ materially from those projected. Past "
          "performance is not indicative of future results. The model is a "
          "model; reality is not."},
    {"h": "Author may hold positions.",
     # Ticker token replaced at render time so the JSX can swap per memo.
     "p": "The author may own, intend to acquire, or hold short exposure to "
          "${TICKER} or related securities at any time. Positions may change "
          "without notice and without an update to this document. Do not "
          "assume the author's positions match the tone of the analysis."},
    {"h": "Do your own research.",
     "p": "Do not make investment decisions on the basis of this document. "
          "Consult a licensed financial professional and read the company's "
          "official SEC filings (10-K, 10-Q, 8-K, proxy) before forming any "
          "investment view. If you wouldn't trust your retirement to a "
          "chatbot, don't trust this either."},
]


def main() -> None:
    memos = [build_memo(t) for t in TICKERS]
    categories = build_categories(memos)
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=2)
    js = (
        "/* AR2EB — memo data.\n"
        " * GENERATED by scripts/build_site_data.py from data/{ticker}.yml.\n"
        " * Do not edit by hand — edit the YAML and rerun the generator. */\n\n"
        f"const MEMOS = {dump(memos)};\n\n"
        f"const CATEGORIES = {dump(categories)};\n\n"
        f"const DISCLAIMER_BLOCKS = {dump(DISCLAIMER_BLOCKS)};\n\n"
        f"const PDF_DISCLAIMERS = {dump(PDF_DISCLAIMERS)};\n\n"
        "window.AR2EB_DATA = { MEMOS, CATEGORIES, DISCLAIMER_BLOCKS, PDF_DISCLAIMERS };\n"
    )
    OUT.write_text(js, encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}  ({len(memos)} memos, {OUT.stat().st_size:,} bytes)")
    for m in memos:
        print(f"  {m['ticker']:4} spot ${m['spot']['price']:>7.2f}  "
              f"expected ${m['expected']['fair']:>8.2f} "
              f"({m['expected']['deltaPct']:+.1f}%)  -> {m['pdf']['file']}")


if __name__ == "__main__":
    main()
