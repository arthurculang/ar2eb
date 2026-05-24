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

TICKERS = ["joby", "aur", "lth", "zm", "naut"]
SCEN_ORDER = ["bear", "base", "bull", "ultra_bull"]
SITE_KEY = {"bear": "bear", "base": "base", "bull": "bull", "ultra_bull": "ultra"}

DCF_DISPLAY = {
    "young_company": ("Young-Company DCF (Damodaran)", "asymmetrical-moonshots"),
    "mature_company": ("Mature-Company DCF", "fcf-plus-plus-growth"),
    "mature_company_sotp": ("Mature-Company DCF · SOTP", "fcf-plus-plus-growth"),
}


def collapse(s: str) -> str:
    return " ".join(str(s).split())


def _pick_rev_per_unit(chart_data: dict) -> list | None:
    # rev_per_unit's YAML key is ticker-specific. Probe known names.
    for key in ("rev_per_aircraft", "rev_per_truck", "rev_per_instrument"):
        if key in chart_data:
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


def build_memo(ticker: str) -> dict:
    d = yaml.safe_load((DATA / f"{ticker}.yml").read_text())
    st = d["stamp"]
    spot = float(d["spot"])
    dcf_type = d["dcf_type"]
    dcf_display, category = DCF_DISPLAY[dcf_type]
    iso, lbl = label_date(d["date"])

    scn = d["scenarios"]
    # Probability-weighted math — identical to memo.py.
    pw_expected = sum(s["probability"] * s["expected_per_share"]
                      for s in scn.values())

    def pw_at(T: int) -> float:
        return sum(s["probability"] * s["expected_per_share"]
                   * (1 + s["dcf_path"]["wacc_path"][-1]) ** T
                   for s in scn.values())

    compound = [{"y": T, "value": round(pw_at(T), 2),
                 "mult": round(pw_at(T) / spot, 2)} for T in (5, 10, 15, 20)]

    scenarios = []
    for k in SCEN_ORDER:
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

    probs = {k: round(scn[k]["probability"] * 100) for k in SCEN_ORDER}
    pdf_file = f"{ticker}-memo__v{st['pdf_version']}__{st['pdf_timestamp']}.pdf"
    pdf_path = MEMOS_DIR / pdf_file
    if not pdf_path.exists():
        raise FileNotFoundError(
            f"{ticker}: {pdf_file} not in public/memos/ — regenerate the PDF "
            f"(scripts/rebuild_all.py) before building site data")

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
        "pdf": {"file": pdf_file, "size": human_size(pdf_path)},
        "metrics": {
            "mktCap": _fmt_b(mk['market_cap_billion']),
            "shares": fmt_shares(mk["shares_outstanding_million"]),
            "cash": fmt_cash(mk),
        },
        "spot": {"price": spot, "asOf": f"{lbl} close"},
        "expected": {"fair": round(pw_expected, 2),
                      "deltaPct": round((pw_expected / spot - 1) * 100, 1)},
        "compound": compound,
        "question": collapse(d["central_question"]),
        "scenarios": scenarios,
        "methodology": (
            f"DCF framework: {dcf_display}. Probability weighting: "
            f"Bear {probs['bear']} / Base {probs['base']} / "
            f"Bull {probs['bull']} / Ultra Bull {probs['ultra_bull']}. "
            f"Spot price reference: {lbl} close."),
        "thesis": collapse(d["thesis"]),
        "historicalPrices": {
            "xMin": float(d["historical_prices"]["x_min"]),
            "ipoMarker": d["historical_prices"]["ipo_marker"],
            "points": [[float(p[0]), float(p[1])]
                       for p in d["historical_prices"]["points"]],
        },
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
            "dcfPeriodYears": 10 if dcf_type == "young_company" else 5,
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
                k: {
                    "probability": float(scn[k]["probability"]),
                    "expectedPerShare": float(scn[k]["expected_per_share"]),
                    "label": scn[k]["label"],
                    "shortLabel": scn[k]["short_label"],
                    "dcfMetrics": dict(scn[k]["dcf_metrics"]),
                    "dcfPath": dict(scn[k]["dcf_path"]),
                    "chartData": dict(scn[k].get("chart_data", {})),
                    # rev_per_unit's YAML key differs per ticker
                    # (rev_per_aircraft/rev_per_truck/rev_per_instrument);
                    # normalize for the JSX charts.
                    "revPerUnit": _pick_rev_per_unit(scn[k].get("chart_data", {})),
                }
                for k in SCEN_ORDER
            },
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


# Static blocks — verbatim from the design spec (prompt-for-claude-design
# §disclaimer); content-stable, not derived from YAML.
CATEGORIES = {
    "asymmetrical-moonshots": {
        "slug": "asymmetrical-moonshots",
        "name": "Asymmetrical Moonshots",
        "sub": "Young-company DCFs. Compound conditional tails. Show your work.",
        "short": "Young-company DCFs. Compound conditional tails. Show your work.",
        "long": ("Pre-revenue or pre-profitability category-defining companies "
                 "where the standard 5-year DCF generates nonsense. The "
                 "young-company framework asks what mature TAM share is "
                 "plausible, what terminal margins look like at scale, and what "
                 "probability of outright failure. Three scenarios plus an "
                 "ultra-bull tail, weighted; show your work."),
    },
    "fcf-plus-plus-growth": {
        "slug": "fcf-plus-plus-growth",
        "name": "FCF++Growth",
        "sub": "Mature-company DCFs. Cash machines with optionality.",
        "short": "Mature-company DCFs. Cash machines with optionality.",
        "long": ("Established businesses generating real free cash flow today, "
                 "with credible paths to growth-rate inflection. The "
                 "mature-company framework uses 5-year explicit DCFs with "
                 "terminal-value treatment, and prices in the bull case where "
                 "the company gets re-rated AS WELL AS executes operationally."),
    },
}

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
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=2)
    js = (
        "/* AR2EB — memo data.\n"
        " * GENERATED by scripts/build_site_data.py from data/{ticker}.yml.\n"
        " * Do not edit by hand — edit the YAML and rerun the generator. */\n\n"
        f"const MEMOS = {dump(memos)};\n\n"
        f"const CATEGORIES = {dump(CATEGORIES)};\n\n"
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
