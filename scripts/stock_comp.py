#!/usr/bin/env python3
"""Stock-comp rule (spec §4): value every mature memo on owner FCF and today's
diluted share count.

Reported FCF adds stock comp back as non-cash, so a DCF on it divided by today's
share count ignores the cost entirely. The rule charges it exactly once:
  - OWNER FCF: FCF − (latest-FY stock comp ÷ revenue) × revenue, every year and
    every scenario, divided by TODAY's diluted share count with no credit for
    future buybacks (buybacks are paid from FCF already in the value; a buyback
    at fair value creates none); or
  - EXPLICIT DILUTION: reported FCF with the share count grown at the observed
    net issuance rate (DASH).
Never both. v048 applied it above ~8% of revenue; v049 extends it to every
mature memo. Young-company DCFs comply by construction.

Operations (each re-derives the bridge bottom-up — pv_fcf → Σ → terminal → op EV
→ equity → per-share → expected — edits ONLY those lines, and verifies by reload
that nothing else in the file changed):
  --sbc-pct X        charge stock comp at X (decimal share of revenue). Only for
                     a memo still on REPORTED FCF — the tool refuses a memo whose
                     marker or margins say it is already charged.
  --shares N         set every scenario's final_shares (and the masthead count +
                     market cap) to today's diluted count, N million.
  --shift-op-margin  with --sbc-pct: move projected op margins to the same
                     after-stock-comp basis as the history chart (display only).
  --mark --basis B   record a memo already compliant (owner_fcf | explicit_dilution).
  --allow-formula-reset  proceed when a scenario's stored DCF doesn't reproduce with
                     the standard bridge (a hand-tuned value), replacing it with the
                     formula value; recorded in the marker.
Every write upserts a `stock_comp:` block in the yml (basis, inputs, source,
date); that marker is what stops a later run from charging stock comp twice.

Usage:
  python scripts/stock_comp.py --audit [tickers]       # basis of every mature memo
  python scripts/stock_comp.py --fetch <ticker>        # SEC-sourced inputs (fresh)
  python scripts/stock_comp.py <ticker> --sbc-pct 0.062 --shares 12088 \\
      --source "10-K FY2025; 10-Q Q2-2026 diluted WASO" [--shift-op-margin] [--dry-run]
  python scripts/stock_comp.py <ticker> --shares 433 --source "..."   # shares only
  python scripts/stock_comp.py <ticker> --mark --basis owner_fcf --sbc-pct 0.094 --source "..."
  python scripts/stock_comp.py --selftest              # reproduces v048's re-model

Loss quarters: the reported diluted count equals basic (anti-dilutive awards are
excluded). --fetch flags it; add unvested awards and in-the-money options by the
treasury method from the 10-Q EPS note before passing --shares. Convertibles
already carried as debt stay out of the count.
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import os
import re
import subprocess
import sys
from functools import reduce
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
SURVEY = REPO / "scripts" / "_models" / "stock_comp_survey.json"
MATURE = ("mature_company", "mature_company_sotp")
SCN_RE = re.compile(r"^  (ultra_bear|bear|base|bull|ultra_bull):\s*(#.*)?$")
DERIVED = ("pv_fcf", "sum_pv_fcf", "terminal_value", "pv_terminal", "op_ev",
           "total_equity")
# Stock-comp cash-flow tags, in priority order (the cash-flow statement add-back).
SBC_TAGS = ["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense",
            "ShareBasedCompensationArrangementByShareBasedPaymentAwardCompensationCost1"]
# CIKs for mature memos missing from source_mega7.CIK (entity names verified
# against SEC companyfacts, 2026-10).
EXTRA_CIK = {"CAI": 2019410, "COIN": 1679788, "HHH": 1981792, "LTH": 1869198,
             "NVCR": 1645113, "SHAK": 1620533, "SYM": 1837240, "TEM": 1717115,
             "TWST": 1581280}


# ── model ─────────────────────────────────────────────────────────────────
def _cum(w: list[float], i: int) -> float:
    return reduce(lambda a, x: a * (1 + x), w[:i + 1], 1.0)


def revenues(dp: dict) -> list[float]:
    """Absolute revenue path: mature rev_path holds growth rates off rev_b."""
    out, r = [], dp["rev_b"]
    for g in dp["rev_path"]:
        r *= 1 + g
        out.append(r)
    return out


def bridge(dp: dict, fcf: list[float], shares: float, exit_mult) -> dict:
    """The mature bridge exactly as validate.py checks it (spec §5)."""
    w, n = dp["wacc_path"], len(fcf)
    pv = [round(fcf[i] / _cum(w, i), 3) for i in range(n)]
    spv = round(sum(pv), 2)
    if exit_mult:
        tv = round(fcf[-1] * exit_mult, 2)
    else:
        tv = round(fcf[-1] * (1 + dp["term_g"]) / (w[-1] - dp["term_g"]), 2)
    pvt = round(tv / _cum(w, n - 1), 2)
    opev = round(spv + pvt, 2)
    eq = round(opev + dp.get("cash", 0) - dp.get("net_debt", 0)
               + dp.get("special_assets", 0), 2)
    return dict(pv_fcf=pv, sum_pv_fcf=spv, terminal_value=tv, pv_terminal=pvt,
                op_ev=opev, total_equity=eq, dcf_per_share=round(eq * 1000 / shares, 2))


def plan(d: dict, sbc_pct=None, shares=None, shift=False, allow_reset=False) -> dict:
    """Per-scenario new values. Standard mature memos carry expected =
    max(0, dcf); a memo with its own expected/DCF relationship (HHH's NAV
    discount) keeps that ratio."""
    scn = d["scenarios"]
    standard = all(abs(s["expected_per_share"] - max(0.0, s["dcf_path"]["dcf_per_share"]))
                   <= max(0.10, 0.005 * abs(s["dcf_path"]["dcf_per_share"]))   # hand-rounding
                   for s in scn.values())
    out = {}
    for k, sc in scn.items():
        dp = sc["dcf_path"]
        em = (sc.get("dcf_metrics") or {}).get("exit_fcf_multiple")
        sh = float(shares) if shares is not None else dp["final_shares"]
        new = {}
        if sbc_pct is not None:
            repro = bridge(dp, dp["fcf"], dp["final_shares"], em)["dcf_per_share"]
            # engines round intermediate fields differently: tolerate rounding, catch hand-tuning
            if abs(repro - dp["dcf_per_share"]) > max(0.25, 0.01 * abs(dp["dcf_per_share"])) and not allow_reset:
                raise SystemExit(f"{k}: the standard bridge gives ${repro} vs the memo's "
                                 f"${dp['dcf_per_share']} (a hand-tuned or non-standard value). Re-model "
                                 "through its own engine, or pass --allow-formula-reset to replace it "
                                 "with the formula value (recorded in the marker)")
            fcf = [round(f - sbc_pct * r, 3) for f, r in zip(dp["fcf"], revenues(dp))]
            new["fcf"] = fcf
            new.update(bridge(dp, fcf, sh, em))
            if shift:
                new["op_margin"] = [round(m - sbc_pct, 3) for m in dp["op_margin"]]
        else:
            new["dcf_per_share"] = round(dp["total_equity"] * 1000 / sh, 2)
        if shares is not None:
            new["final_shares"] = sh
        if standard:
            new["expected_per_share"] = round(max(0.0, new["dcf_per_share"]), 2)
        elif dp["dcf_per_share"]:
            new["expected_per_share"] = round(
                sc["expected_per_share"] * new["dcf_per_share"] / dp["dcf_per_share"], 2)
        out[k] = new
    return {"scenarios": out, "standard_expected": standard}


# ── surgical YAML writer ──────────────────────────────────────────────────
def _fmt(key: str, v) -> str:
    if isinstance(v, list):
        return "[" + ", ".join(f"{x:.3f}" for x in v) + "]"
    if key == "final_shares":
        return f"{v:g}"
    return f"{v:.2f}"


def _set(lines: list[str], lo: int, hi: int, key: str, text: str, indent: int,
         keep_comment: bool) -> int:
    """Replace `key:` (at exactly `indent`) inside [lo, hi); a block-style list
    below it is consumed. Returns the net change in line count."""
    for i in range(lo, hi):
        m = re.match(rf"^( {{{indent}}}){re.escape(key)}:(\s*)([^#\n]*?)(\s*#.*)?$", lines[i])
        if not m:
            continue
        removed = 0
        if m.group(3).strip() == "":                      # block-style list follows
            j = i + 1
            while j < hi and re.match(rf"^ {{{indent},}}- [-0-9.eE]+\s*(#.*)?$", lines[j]):
                j += 1
            removed = j - i - 1
            del lines[i + 1:j]
        tail = (m.group(4) or "") if keep_comment else ""
        lines[i] = f"{m.group(1)}{key}: {text}{tail}"
        return -removed
    raise KeyError(f"{key} not found at indent {indent}")


def _block_end(lines: list[str], start: int, indent: int, hi: int) -> int:
    for j in range(start + 1, hi):
        s = lines[j]
        if s.strip() and not s.lstrip().startswith("#") and len(s) - len(s.lstrip()) <= indent:
            return j
    return hi


def write(raw: str, d: dict, p: dict, shares, marker: dict | None) -> str:
    lines = raw.split("\n")
    top = next(i for i, l in enumerate(lines) if l.startswith("scenarios:"))
    end = _block_end(lines, top, 0, len(lines))
    starts = [(m.group(1), i) for i in range(top + 1, end) if (m := SCN_RE.match(lines[i]))]
    bounds = [(k, s, starts[n + 1][1] if n + 1 < len(starts) else end)
              for n, (k, s) in enumerate(starts)]
    for k, s, e in reversed(bounds):                       # bottom-up: no index drift
        new = p["scenarios"][k]
        if not new:
            continue
        dpl = next(i for i in range(s, e) if re.match(r"^    dcf_path:\s*(#.*)?$", lines[i]))
        dpe = _block_end(lines, dpl, 4, e)
        for key in ("fcf", "op_margin", *DERIVED, "final_shares", "dcf_per_share"):
            if key in new:
                delta = _set(lines, dpl, dpe, key, _fmt(key, new[key]), 6,
                             keep_comment=key in ("fcf", "op_margin"))
                dpe += delta
                e += delta
        if "expected_per_share" in new:
            _set(lines, s, e, "expected_per_share", _fmt("x", new["expected_per_share"]), 4, False)
    if shares is not None:
        spot = float(d["spot"])
        mk = next(i for i, l in enumerate(lines) if l.startswith("market:"))
        mke = _block_end(lines, mk, 0, len(lines))
        _set(lines, mk, mke, "shares_outstanding_million", f"{float(shares):g}", 2, True)
        _set(lines, mk, mke, "market_cap_billion", f"{float(shares) * spot / 1000:.2f}", 2, True)
    text = "\n".join(lines)
    if marker is not None:
        block = yaml.dump({"stock_comp": marker}, sort_keys=False, allow_unicode=True,
                          width=110).rstrip("\n")
        m = re.search(r"^stock_comp:.*?(?=^\S|\Z)", text, re.M | re.S)
        if m:
            text = text[:m.start()] + block + "\n" + text[m.end():]
        else:
            text = text.rstrip("\n") + "\n\n" + block + "\n"
    return text


def verify(before: dict, after: dict, p: dict, shares, marker) -> None:
    """Only the planned fields changed, and they hold the planned values."""
    b, a = copy.deepcopy(before), copy.deepcopy(after)
    for doc in (b, a):
        doc.pop("stock_comp", None)
        if shares is not None:
            doc["market"].pop("shares_outstanding_million", None)
            doc["market"].pop("market_cap_billion", None)
        for k, sc in doc["scenarios"].items():
            sc.pop("expected_per_share", None)
            for key in p["scenarios"][k]:
                sc["dcf_path"].pop(key, None)
    if a != b:
        raise SystemExit("verification failed: a field outside the plan changed")
    for k, new in p["scenarios"].items():
        got = {**after["scenarios"][k]["dcf_path"],
               "expected_per_share": after["scenarios"][k]["expected_per_share"]}
        for key, v in new.items():
            g = got[key]
            ok = (all(abs(x - y) < 1e-9 for x, y in zip(g, v)) and len(g) == len(v)) \
                if isinstance(v, list) else abs(float(g) - float(v)) < 1e-9
            if not ok:
                raise SystemExit(f"verification failed: {k}.{key} wrote {g!r}, planned {v!r}")
        dp = after["scenarios"][k]["dcf_path"]                  # validator identities
        assert abs(dp["op_ev"] + dp["cash"] - dp.get("net_debt", 0)
                   + dp.get("special_assets", 0) - dp["total_equity"]) < 0.02, k
        assert abs(dp["sum_pv_fcf"] + dp["pv_terminal"] - dp["op_ev"]) < 0.02, k
        assert abs(dp["total_equity"] * 1000 / dp["final_shares"] - dp["dcf_per_share"]) < 0.02, k
    if marker is not None and after.get("stock_comp") != marker:
        raise SystemExit("verification failed: stock_comp marker did not round-trip")


# ── helpers ───────────────────────────────────────────────────────────────
def weighted(d: dict, p: dict | None = None) -> float:
    return sum(s["probability"] * (p["scenarios"][k]["expected_per_share"] if p else s["expected_per_share"])
               for k, s in d["scenarios"].items())


def survey() -> dict:
    return json.loads(SURVEY.read_text()) if SURVEY.exists() else {}


def margin_hint(d: dict, pct) -> tuple[str, float | None]:
    """Is the modeled FCF already after stock comp? Compares the base case's
    first-year FCF margin with the last reported FCF margin."""
    cr = d.get("chart_reference") or {}
    hf, hr = cr.get("history_fcf"), cr.get("history_revenue")
    b = d["scenarios"]["base"]["dcf_path"]
    fy1 = b["fcf"][0] / revenues(b)[0]
    try:
        rep = hf[-1] / hr[-1]
    except (TypeError, IndexError, ZeroDivisionError):
        return "no FCF history", None
    if pct is None:
        return "no stock-comp data", None
    if rep <= 0.02:
        return "reported FCF near zero — read the generator notes", rep - fy1
    gap = rep - fy1
    if gap >= 0.75 * pct:
        return "already after stock comp (likely)", gap
    if gap <= 0.25 * pct:
        return "before stock comp (likely)", gap
    return "ambiguous — read the generator notes", gap


def generator_says_owner(t: str) -> bool:
    """The memo's generator (scripts/_models/gen_<T>.py) documents an ex-SBC basis."""
    for name in (f"gen_{t.upper()}.py", f"gen_{t}.py"):
        f = REPO / "scripts" / "_models" / name
        if f.exists() and re.search(r"ex-SBC|SBC-adjusted|owner[- ]FCF", f.read_text(), re.I):
            return True
    return False


def evidence(t: str, d: dict, pct) -> tuple[str, str]:
    """(verdict, detail) on whether the memo's FCF is already after stock comp.
    Ranked: marker > authored basis (survey, from the build log) > generator
    notes > margins (only when stock comp is large enough to see — below ~2% of
    revenue the margin gap is model noise)."""
    mk = d.get("stock_comp") or {}
    if mk:
        return mk.get("basis", "owner_fcf"), f"marker ({mk.get('applied')})"
    ab = (survey().get(t) or {}).get("authored_basis")
    if ab in ("owner_fcf", "reported_fcf", "explicit_dilution"):
        return ab, "authored basis (build log)"
    if generator_says_owner(t):
        return "owner_fcf", "generator notes say ex-SBC"
    hint, gap = margin_hint(d, pct)
    g = f" ({gap:+.1%} gap)" if gap is not None else ""
    if pct is None or gap is None or hint.startswith("reported FCF near zero"):
        return "unclear", hint
    if pct < 0.02:
        return "reported_fcf", f"assumed — stock comp too small to see in margins{g}"
    if hint.startswith("already"):
        return "owner_fcf", "margins" + g
    if hint.startswith("before"):
        return "reported_fcf", "margins" + g
    return "unclear", "margins ambiguous" + g


def mature_tickers() -> list[str]:
    out = []
    for f in sorted(DATA.glob("*.yml")):
        if f.stem.startswith("_") or f.stem == "taxonomy":
            continue
        if yaml.safe_load(f.read_text()).get("dcf_type") in MATURE:
            out.append(f.stem)
    return out


# ── commands ──────────────────────────────────────────────────────────────
def audit(tickers: list[str]) -> None:
    sv = survey()
    print(f"{'memo':6} {'stock comp':>10}  {'FCF basis (evidence)':<58} {'shares vs today':<26} action")
    for t in tickers:
        d = yaml.safe_load((DATA / f"{t}.yml").read_text())
        mk = d.get("stock_comp") or {}
        pct = (sv.get(t) or {}).get("pct")
        verdict, detail = evidence(t, d, pct)
        mast = d["market"]["shares_outstanding_million"]
        fs = [s["dcf_path"]["final_shares"] for s in d["scenarios"].values()]
        lo, hi = min(fs) / mast - 1, max(fs) / mast - 1
        sh = ("≈ today's" if max(abs(lo), abs(hi)) <= 0.02 else
              f"credits buybacks ({lo:+.0%}..{hi:+.0%})" if hi <= 0.02 else
              f"adds dilution ({lo:+.0%}..{hi:+.0%})" if lo >= -0.02 else
              f"mixed ({lo:+.0%}..{hi:+.0%})")
        if mk:
            action = "done" if sh.startswith("≈") else "done (shares differ from masthead — check)"
        elif verdict == "owner_fcf":
            action = "--mark --basis owner_fcf" if sh.startswith("≈") else "--shares N + --mark"
        elif verdict == "reported_fcf":
            authored = detail.startswith("authored")
            action = ("explicit dilution? confirm vs net issuance, else --sbc-pct + --shares"
                      if sh.startswith("adds") and not authored else "--sbc-pct + --shares")
            try:                                                # will the standard bridge reproduce it?
                plan(d, pct or 0.0, None)
            except SystemExit:
                action += " (+ --allow-formula-reset: a hand-set value)"
        elif verdict == "explicit_dilution":
            action = "leave as authored unless decision #12 retires explicit dilution (CLAUDE.md)"
        else:
            action = "judge from the generator notes / filings"
        print(f"{t:6} {(f'{pct:.1%}' if pct is not None else 'n/a'):>10}  "
              f"{(verdict + ': ' + detail)[:58]:<58} {sh:<26} {action}")


def _quarterly(facts: dict, tag: str, unit: str) -> dict:
    out = {}
    for e in facts.get("facts", {}).get("us-gaap", {}).get(tag, {}).get("units", {}).get(unit, []):
        s, en = e.get("start"), e.get("end")
        if not s or not en:
            continue
        days = (dt.date.fromisoformat(en) - dt.date.fromisoformat(s)).days
        if 80 <= days <= 100:
            cur = out.get((s, en))
            if cur is None or e.get("filed", "") > cur[1]:
                out[(s, en)] = (float(e["val"]), e.get("filed", ""), e.get("form", ""))
    return out


def fetch(ticker: str, cik: int | None) -> None:
    sys.path.insert(0, str(REPO / "scripts" / "_models"))
    os.environ["AI2_NO_CACHE"] = "1"                         # always fresh filings
    import source_ai2_panel as S
    if cik is None:
        import source_mega7 as M
        cik = {**M.CIK, **EXTRA_CIK}.get(ticker.upper())
    if cik is None:
        raise SystemExit(f"no CIK for {ticker}; pass --cik")
    facts = S.companyfacts(int(cik))
    sbc, rev = S.flow_series(facts, SBC_TAGS), S.flow_series(facts, S.CONCEPTS["revenue"])
    fy = max(set(sbc) & set(rev))
    print(f"{facts.get('entityName')} (CIK {cik})")
    print(f"  FY{fy} stock comp ${sbc[fy] / 1e9:.3f}B / revenue ${rev[fy] / 1e9:.3f}B = {sbc[fy] / rev[fy]:.4f}")
    dil = _quarterly(facts, "WeightedAverageNumberOfDilutedSharesOutstanding", "shares")
    bas = _quarterly(facts, "WeightedAverageNumberOfSharesOutstandingBasic", "shares")
    ni = _quarterly(facts, "NetIncomeLoss", "USD")
    if not dil:
        print("  no quarterly diluted share count tagged — read the latest 10-Q")
        return
    key = max(dil, key=lambda k: k[1])
    d_m, b_m = dil[key][0] / 1e6, (bas.get(key, (None,))[0] or 0) / 1e6
    loss = ni.get(key, (0,))[0] < 0
    print(f"  quarter {key[0]}..{key[1]} ({dil[key][2]} filed {dil[key][1]}): diluted {d_m:.1f}M, basic {b_m:.1f}M"
          f"{', net LOSS' if loss else ''}")
    if loss or abs(d_m - b_m) < 1e-6:
        print("  LOSS QUARTER: diluted = basic. Add unvested awards + in-the-money options (treasury method,"
              " 10-Q EPS note) before --shares; converts carried as debt stay out.")
    print(f"  suggested: python scripts/stock_comp.py {ticker.lower()} --sbc-pct {sbc[fy] / rev[fy]:.4f} "
          f"--shares {d_m:.1f} --source \"10-K FY{fy}; {dil[key][2]} {key[1]} diluted WASO\"")


def apply(ticker: str, sbc_pct, shares, shift: bool, source: str, dry: bool,
          mark: bool, basis: str | None, raw_override: str | None = None,
          check_validator: bool = True, allow_reset: bool = False) -> tuple[str, dict]:
    path = DATA / f"{ticker}.yml"
    raw = raw_override if raw_override is not None else path.read_text(encoding="utf-8")
    d = yaml.safe_load(raw)
    if d.get("dcf_type") not in MATURE:
        raise SystemExit(f"{ticker}: {d.get('dcf_type')} — the rule is for mature memos "
                         "(young-company DCFs comply by construction)")
    prior = d.get("stock_comp") or {}
    if sbc_pct is not None and prior.get("basis") == "owner_fcf":
        raise SystemExit(f"{ticker}: stock comp was already charged ({prior.get('applied')}); "
                         "charging again would count it twice")
    explicit = prior.get("basis") == "explicit_dilution" or (
        not prior and evidence(ticker, d, sbc_pct)[0] == "explicit_dilution")
    if sbc_pct is not None and explicit and shares is None:
        raise SystemExit(f"{ticker}: on explicit dilution — switching to owner FCF needs --shares too")
    if sbc_pct is not None and not prior and not mark and raw_override is None:
        verdict, detail = evidence(ticker, d, sbc_pct)
        if verdict == "owner_fcf" and not os.environ.get("STOCK_COMP_OVERRIDE_HINT"):
            raise SystemExit(f"{ticker}: evidence says the FCF is already after stock comp ({detail}); "
                             "charging again would count it twice. Use --shares / --mark, or set "
                             "STOCK_COMP_OVERRIDE_HINT=1 if you have checked it isn't.")
    if shift and sbc_pct is None:
        raise SystemExit("--shift-op-margin needs --sbc-pct")
    if mark:
        p = {"scenarios": {k: {} for k in d["scenarios"]}, "standard_expected": True}
    else:
        p = plan(d, sbc_pct, shares, shift, allow_reset)
    marker = {"basis": basis or ("owner_fcf" if (sbc_pct is not None or prior.get("basis") == "owner_fcf")
                                 else prior.get("basis") or "owner_fcf")}
    sp = sbc_pct if sbc_pct is not None else prior.get("sbc_pct_of_revenue")
    if sp is not None:
        marker["sbc_pct_of_revenue"] = round(float(sp), 4)
    sh = shares if shares is not None else prior.get("diluted_shares_million")
    if sh is not None:
        marker["diluted_shares_million"] = float(sh)
    steps = [s for s, on in (("charge_stock_comp", sbc_pct is not None and not mark),
                             ("set_diluted_shares", shares is not None and not mark),
                             ("shift_op_margin", shift), ("formula_reset", allow_reset and not mark),
                             ("mark", mark)) if on]
    marker["steps"] = ", ".join(([prior["steps"]] if prior.get("steps") else []) + steps)
    marker["source"] = source
    marker["applied"] = dt.date.today().isoformat()
    new_raw = write(raw, d, p, None if mark else shares, marker)
    after = yaml.safe_load(new_raw)
    verify(d, after, p, None if mark else shares, marker)
    spot = float(d["spot"])
    w0 = weighted(d)
    w1 = w0 if mark else weighted(d, p)
    if raw_override is None:
        print(f"{ticker.upper()}: weighted ${w0:.2f} -> ${w1:.2f} at spot ${spot:.2f}: "
              f"{w0 / spot - 1:+.1%} -> {w1 / spot - 1:+.1%}"
              + ("" if p["standard_expected"] else "  (expected/DCF ratio preserved — review)"))
        for k, sc in d["scenarios"].items():
            if mark:
                break
            print(f"   {k:11s} p={sc['probability']:.2f}  ${sc['expected_per_share']:>9.2f} -> "
                  f"${p['scenarios'][k]['expected_per_share']:>9.2f}")
    if not dry and raw_override is None:
        path.write_text(new_raw, encoding="utf-8")
        if check_validator:
            r = subprocess.run([sys.executable, "scripts/validate.py", ticker], cwd=REPO,
                               capture_output=True, text=True)
            print("   validate:", (r.stdout.strip().splitlines() or ["?"])[-1])
            if r.returncode:
                raise SystemExit(r.stdout + r.stderr)
    return new_raw, p


def selftest() -> int:
    """Reproduce v048's re-model of ZM/ABNB/COIN/META from their pre-v048
    files (git 5e3166a): every model field must match the shipped memo."""
    sv = survey()
    cases = {"zm": (299.7, True), "abnb": (597.0, False), "coin": (263.4, True),
             "meta": (2566.0, False)}
    fields = ("fcf", "op_margin", *DERIVED, "final_shares", "dcf_per_share")
    bad = 0
    for t, (sh, shift) in cases.items():
        old = subprocess.run(["git", "show", f"5e3166a:data/{t}.yml"], cwd=REPO,
                             capture_output=True, text=True, check=True).stdout
        new_raw, _ = apply(t, sv[t]["pct"], sh, shift, "selftest", True, False, None,
                           raw_override=old, check_validator=False, allow_reset=True)
        got, ref = yaml.safe_load(new_raw), yaml.safe_load((DATA / f"{t}.yml").read_text())
        diffs = []
        for k in ref["scenarios"]:
            a, b = got["scenarios"][k], ref["scenarios"][k]
            for f in fields:
                if a["dcf_path"][f] != b["dcf_path"][f]:
                    diffs.append(f"{k}.{f}")
            if a["expected_per_share"] != b["expected_per_share"]:
                diffs.append(f"{k}.expected_per_share")
        for f in ("shares_outstanding_million", "market_cap_billion"):
            if got["market"][f] != ref["market"][f]:
                diffs.append(f"market.{f}")
        bad += bool(diffs)
        print(f"{t.upper():5s} {'reproduces the shipped v048 model' if not diffs else 'MISMATCH: ' + ', '.join(diffs[:6])}")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("tickers", nargs="*")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--cik", type=int)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--sbc-pct", type=float)
    ap.add_argument("--shares", type=float)
    ap.add_argument("--shift-op-margin", action="store_true")
    ap.add_argument("--mark", action="store_true")
    ap.add_argument("--basis", choices=["owner_fcf", "explicit_dilution"])
    ap.add_argument("--source", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-formula-reset", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.audit:
        audit(a.tickers or mature_tickers())
        return 0
    if len(a.tickers) != 1:
        ap.error("give exactly one ticker (or --audit / --selftest)")
    t = a.tickers[0].lower()
    if a.fetch:
        fetch(t, a.cik)
        return 0
    if not (a.sbc_pct is not None or a.shares is not None or a.mark):
        ap.error("nothing to do: pass --sbc-pct, --shares and/or --mark")
    if not a.source and not a.dry_run:
        ap.error("--source is required (cite the filings the inputs come from)")
    if a.mark and not a.basis:
        ap.error("--mark needs --basis")
    apply(t, a.sbc_pct, a.shares, a.shift_op_margin, a.source, a.dry_run, a.mark, a.basis,
          allow_reset=a.allow_formula_reset)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
