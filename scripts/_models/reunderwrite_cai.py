#!/usr/bin/env python3
"""CAI out-of-cycle re-underwrite (Nov-2026 batch 1) — reproducible record.

Evidence (SEC companyfacts, CIK 2019410, Q3-2026 10-Q filed 2026-11-04; Q3 8-K 2026-11-04):
  9M-2026 revenue $755.2M (Q3 $275.4M, +27%); FY26 guide raised to $1.04-1.05B.
  9M OCF $39.1M - capex $49.9M - stock comp $56.6M = owner FCF -$67.4M (incl. a $78.5M
  supplies/inventory build for Caris Detect capacity). 9M GAAP op margin 6.8% (Q3 7.0%).
  Cash + investments $769.2M at 2026-09-30; term loan $400M face (gross-debt convention).

Changes (inputs only; every derived field re-derived by the standard mature bridge):
  * year-1 revenue growth re-anchored to nine booked months (Q4 is the only open quarter);
  * year-1 owner FCF set to the evidenced FY26 run-rate (negative, inventory build);
    years 2-5 keep each scenario's prior owner-FCF margin on the new revenue base;
  * year-1 op margin aligned to the 9M GAAP 6.8%;
  * cash 0.80 -> 0.769; probabilities: ultra_bull 9 -> 8, base 36 -> 37.
Then, LAST:  python scripts/stock_comp.py cai --shares 295.1 --mark ... (today's diluted count).
Usage: python scripts/_models/reunderwrite_cai.py [--write]   (run once, on the pre-re-underwrite yml at HEAD 0a0cc44)
"""
import sys, re
from pathlib import Path
import yaml
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
import stock_comp as SC  # noqa: E402  (surgical writer + validator-identical bridge)

YML = REPO / "data" / "cai.yml"
CASH = 0.769
G1 = dict(ultra_bear=0.24, bear=0.265, base=0.287, bull=0.30, ultra_bull=0.32)
FCF1 = dict(ultra_bear=-0.09, bear=-0.085, base=-0.075, bull=-0.07, ultra_bull=-0.065)
OPM1 = dict(ultra_bear=0.05, bear=0.06, base=0.07, bull=0.07, ultra_bull=0.075)
PROB = dict(ultra_bear=0.10, bear=0.27, base=0.37, bull=0.18, ultra_bull=0.08)


def main(write: bool) -> None:
    raw = YML.read_text()
    d = yaml.safe_load(raw)
    spot = float(d["spot"])
    out, wt = {}, 0.0
    for k, sc in d["scenarios"].items():
        dp = sc["dcf_path"]
        old_rev = SC.revenues(dp)
        margins = [f / r for f, r in zip(dp["fcf"], old_rev)]
        g = [G1[k]] + list(dp["rev_path"][1:])
        dp2 = dict(dp, rev_path=g, cash=CASH)
        rev = SC.revenues(dp2)
        fcf = [FCF1[k]] + [round(rev[i] * margins[i], 3) for i in range(1, len(rev))]
        opm = [OPM1[k]] + list(dp["op_margin"][1:])
        b = SC.bridge(dp2, fcf, dp["final_shares"], None)
        cagr = round(((rev[-1] / dp["rev_b"]) ** (1 / len(rev)) - 1) * 100, 1)
        out[k] = dict(rev_path=g, fcf=fcf, op_margin=opm, cagr=cagr, **b)
        wt += PROB[k] * b["dcf_per_share"]
        print(f"{k:<11} p={PROB[k]:.2f} cagr={cagr:5.1f} rev30={rev[-1]:.3f} fcf={fcf} "
              f"dcf={b['dcf_per_share']:7.2f} (was {dp['dcf_per_share']:.2f}) {b['dcf_per_share']/spot-1:+.1%}")
    print(f"weighted ${wt:.2f} vs ${spot} = {wt/spot-1:+.1%}  (pre stock_comp share reset)")
    if not write:
        return
    lines = raw.split("\n")
    top = next(i for i, l in enumerate(lines) if l.startswith("scenarios:"))
    end = SC._block_end(lines, top, 0, len(lines))
    starts = [(m.group(1), i) for i in range(top + 1, end) if (m := SC.SCN_RE.match(lines[i]))]
    bounds = [(k, s, starts[n + 1][1] if n + 1 < len(starts) else end) for n, (k, s) in enumerate(starts)]
    for k, s, e in reversed(bounds):
        o = out[k]
        dpl = next(i for i in range(s, e) if re.match(r"^    dcf_path:\s*$", lines[i]))
        dpe = SC._block_end(lines, dpl, 4, e)
        vals = dict(rev_path=SC._fmt("l", o["rev_path"]), op_margin=SC._fmt("l", o["op_margin"]),
                    fcf=SC._fmt("l", o["fcf"]), cash=f"{CASH}",
                    pv_fcf=SC._fmt("l", o["pv_fcf"]), sum_pv_fcf=f"{o['sum_pv_fcf']:.2f}",
                    terminal_value=f"{o['terminal_value']:.2f}", pv_terminal=f"{o['pv_terminal']:.2f}",
                    op_ev=f"{o['op_ev']:.2f}", total_equity=f"{o['total_equity']:.2f}",
                    dcf_per_share=f"{o['dcf_per_share']:.2f}")
        for key, text in vals.items():
            delta = SC._set(lines, dpl, dpe, key, text, 6, keep_comment=False)
            dpe += delta; e += delta
        SC._set(lines, s, e, "expected_per_share", f"{o['dcf_per_share']:.2f}", 4, False)
        SC._set(lines, s, e, "probability", f"{PROB[k]}", 4, False)
        SC._set(lines, s, e, "cagr_5y", f"{o['cagr']}", 6, False)
    YML.write_text("\n".join(lines))
    print("written", YML)


if __name__ == "__main__":
    main("--write" in sys.argv)
