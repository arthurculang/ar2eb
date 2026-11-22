#!/usr/bin/env python3
"""RDDT re-underwrite (Nov-2026 out-of-cycle, after the Q3-2026 print and the -44% month).

Reproducible record of the re-model. Numerics through model_mature (the same engine
gen_RDDT.py used via gen_b1.build); written surgically into data/rddt.yml with the
stock_comp.py line writer. final_shares is left as authored: the stock-comp rule's
shares-only reset to today's diluted count (201.9M, 10-Q 2026-09-30) is applied
AFTERWARDS with `scripts/stock_comp.py rddt --shares 201.9 --mark`-style tooling.

Evidence (all dated, observable):
- 10-Q 2026-09-30 (filed 2026-10-30), SEC XBRL: 9M-2026 revenue $2.363B; Q3 $895M (+53%);
  9M GAAP op income $676M (28.6%); 9M OCF $938M, capex $3.5M; 9M stock comp $301M (12.7%);
  cash $1.358B + available-for-sale securities $1.676B = $3.033B; no debt.
- Q3-2026 release (2026-10-29): Q4 revenue guide $1.00-1.03B, adj. EBITDA $480-510M;
  DAUq 130.3M (+12% y/y, flat q/q; US -2%, international +24%); ARPU $6.87 (+36%).
- Q3 call (2026-10-29): Google search referrals fell >1M/week in October; Q4 DAUq could fall
  a low-double-digit % if the trend persists. Stock -29% on 2026-10-30 (CNBC).
- Similarweb via Business Insider (Nov-2026): global visits -13% Oct-2025 -> Oct-2026.
- WSJ (Jul-2026): Google data-licensing renewal (~$60M/yr, due early 2027) in turbulence.
FY2026 revenue is therefore ~known: $2.363B + guide $1.00-1.03B = $3.36-3.39B (+52.7..+54.1%).
"""
import sys, os, re
from pathlib import Path
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from model_mature import model_m
import yaml
from stock_comp import _set, _block_end, SCN_RE

REPO = Path(__file__).resolve().parents[2]
PATH = REPO / "data" / "rddt.yml"
CASH = 3.033          # cash $1.358B + marketable securities $1.676B at 2026-09-30; no debt
TODAY_DILUTED = 201.9  # 10-Q Q3-2026 diluted weighted average (applied by stock_comp.py)

S = {  # g = revenue growth off FY25 $2.203B; fcfm = owner FCF margin (after stock comp at FY25 15.6%)
 "ultra_bear": dict(p=0.20, g=[0.525, 0.00, -0.05, 0.00, 0.03], fcfm=[0.24, 0.18, 0.15, 0.16, 0.17],
                    opm=[0.285, 0.20, 0.16, 0.17, 0.18]),
 "bear":       dict(p=0.30, g=[0.53, 0.12, 0.08, 0.07, 0.06], fcfm=[0.24, 0.23, 0.24, 0.24, 0.24],
                    opm=[0.29, 0.26, 0.25, 0.25, 0.25]),
 "base":       dict(p=0.30, g=[0.535, 0.22, 0.16, 0.12, 0.10], fcfm=[0.24, 0.26, 0.28, 0.29, 0.30],
                    opm=[0.29, 0.29, 0.30, 0.31, 0.31]),
 "bull":       dict(p=0.14, g=[0.54, 0.30, 0.22, 0.16, 0.13], fcfm=[0.245, 0.28, 0.30, 0.32, 0.33],
                    opm=[0.29, 0.31, 0.33, 0.34, 0.35]),
 "ultra_bull": dict(p=0.06, g=[0.545, 0.38, 0.28, 0.21, 0.16], fcfm=[0.25, 0.30, 0.33, 0.35, 0.36],
                    opm=[0.295, 0.32, 0.35, 0.36, 0.37]),
}


def fmt(v):
    return "[" + ", ".join(f"{x:g}" for x in v) + "]" if isinstance(v, list) else f"{v:g}"


def main(dry=False):
    raw = PATH.read_text(encoding="utf-8")
    d = yaml.safe_load(raw)
    spot = float(d["spot"])
    lines = raw.split("\n")
    top = next(i for i, l in enumerate(lines) if l.startswith("scenarios:"))
    end = _block_end(lines, top, 0, len(lines))
    starts = [(m.group(1), i) for i in range(top + 1, end) if (m := SCN_RE.match(lines[i]))]
    bounds = [(k, s, starts[n + 1][1] if n + 1 < len(starts) else end) for n, (k, s) in enumerate(starts)]
    wt = wt_today = 0.0
    for k, s, e in reversed(bounds):
        sc, spec = d["scenarios"][k], S[k]
        dp = sc["dcf_path"]
        fs = dp["final_shares"]
        r = model_m(dict(rev_b=dp["rev_b"], rev_path=spec["g"], fcf_margin=spec["fcfm"],
                         wacc_path=dp["wacc_path"], term_g=dp["term_g"], final_shares=fs), CASH)
        r_today = model_m(dict(rev_b=dp["rev_b"], rev_path=spec["g"], fcf_margin=spec["fcfm"],
                               wacc_path=dp["wacc_path"], term_g=dp["term_g"],
                               final_shares=TODAY_DILUTED), CASH)
        wt += spec["p"] * r["dcf_ps"]; wt_today += spec["p"] * r_today["dcf_ps"]
        print(f"{k:11s} p={spec['p']:.2f} FY26 ${r['rev'][0]:.3f}B FY30 ${r['rev'][-1]:.3f}B "
              f"termX {r['term_mult']:>5} ${r['dcf_ps']:>7.2f} (at {TODAY_DILUTED}M: "
              f"${r_today['dcf_ps']:.2f}, {r_today['dcf_ps']/spot-1:+.1%})")
        dpl = next(i for i in range(s, e) if re.match(r"^    dcf_path:\s*(#.*)?$", lines[i]))
        dpe = _block_end(lines, dpl, 4, e)
        vals = [("rev_path", spec["g"]), ("op_margin", spec["opm"]), ("fcf", r["fcf"]),
                ("cash", CASH), ("pv_fcf", [round(r["fcf"][i] / ((1 + dp["wacc_path"][0]) ** (i + 1)), 3)
                                             for i in range(5)]),
                ("sum_pv_fcf", r["sum_pv_fcf"]), ("terminal_value", r["terminal_value"]),
                ("pv_terminal", r["pv_terminal"]), ("op_ev", r["op_ev"]),
                ("total_equity", r["total_equity"]), ("dcf_per_share", r["dcf_ps"])]
        for key, v in vals:
            delta = _set(lines, dpl, dpe, key, fmt(v), 6, keep_comment=False)
            dpe += delta; e += delta
        _set(lines, s, e, "expected_per_share", fmt(r["dcf_ps"]), 4, False)
        _set(lines, s, e, "probability", fmt(spec["p"]), 4, False)
        dml = next(i for i in range(s, e) if re.match(r"^    dcf_metrics:", lines[i]))
        _set(lines, dml, _block_end(lines, dml, 4, e), "cagr_5y", fmt(r["cagr5"]), 6, False)
    mk = next(i for i, l in enumerate(lines) if l.startswith("market:"))
    _set(lines, mk, _block_end(lines, mk, 0, len(lines)), "cash_billion", fmt(CASH), 2, False)
    print(f"weighted (authored shares) ${wt:.2f} {wt/spot-1:+.1%}; at {TODAY_DILUTED}M "
          f"${wt_today:.2f} {wt_today/spot-1:+.1%}")
    if not dry:
        PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main(dry="--dry-run" in sys.argv)
