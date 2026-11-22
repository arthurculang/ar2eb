#!/usr/bin/env python3
"""COIN re-underwrite, Nov 2026 (out-of-cycle, after the −42% month).

Reproducible record of the re-model. Two steps:

  1. THIS SCRIPT rewrites data/coin.yml onto the REPORTED (before stock comp)
     basis with the new scenario inputs, removes the `stock_comp:` marker, and
     re-derives every bridge field with the standard mature exit-multiple bridge
     (stock_comp.bridge — the identity validate.py checks), still on 263.4M shares.
  2. Then the stock-comp rule is re-applied with the tool, LAST:
       python scripts/stock_comp.py coin --sbc-pct 0.1687 --shares 277.1 --shift-op-margin \
         --source "..."
     which charges owner FCF at the new ratio, moves op margins to the
     after-stock-comp basis, and resets the share count.

Inputs (all sourced; see the PR audit record):
  * FY26 revenue re-anchored to actuals: 9M26 revenue $3,848.6M (10-Q filed
    2026-10-29); Q4 from the Q3 deck outlook (S&S $550-630M; transaction revenue
    ~$165M QTD through Oct 25) -> FY26 ~$5.0B (-28% to -32% by scenario, vs the
    old -20% ... +10%).
  * FY26 owner-FCF margin ~0 (scenario spread -2pp ... +2pp): 9M26 OCF $786M vs
    stock comp $719M; 9M26 GAAP op margin -1.9%. The FY26 interim "reported"
    margin is set to that owner margin + the 11.69% the tool charges, so FY26
    owner FCF matches the observed year (actual FY26 stock comp ~$0.96B exceeds
    11.69% of FY26 revenue; the out-years carry 11.69%, which at the base FY30
    revenue (~$8.0B) charges ~$0.94B, about today's ~$0.95B TTM dollar run-rate).
  * FY27-FY30 owner margins: operating leverage off the post-restructuring Q3-26
    run-rate (GAAP op income $61.7M x4 on $1,215.6M x4 revenue), incremental
    margin 0.70 (observed: FY25->FY26 decremental ~69%, FY23->FY24 incremental
    ~71%), capped at each scenario's prior (mature-state) margin; in years where
    revenue sits below the Q3 run-rate, min(prior margin, Q3 run-rate margin).
  * FY27 growth: a cyclical rebound per scenario off the trough; FY28-FY30 keep
    each scenario's prior growth rates.
  * Special assets (BTC + other crypto + CRCL, scenario-scaled by the prior
    author's convention) re-marked x0.70: (BTC 17,954 x ~$64K + CRCL <=8.4M x
    $51.88) = ~$1.59B vs the ~$2.3B mark the Sep memo used (17.2K x ~$87K +
    8.4M x ~$92).
  * Probabilities: bear 22 -> 28, base 47 -> 43, bull 18 -> 16 (the memo's own
    bear-validation trigger "transaction rev < $700M/qtr" fired in Q2 and Q3 2026).
  * Stock comp re-applied LAST with the tool at the unchanged FY2025 ratio
    (0.1169) and the Q3-2026 diluted count ex-converts (277.1M).
"""
from __future__ import annotations

import re
import sys
from functools import reduce
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
from stock_comp import bridge, revenues  # noqa: E402

OLD_SBC = 0.1169          # the v048 charge being removed (pre-SBC = after-SBC + 0.1169)
SHARES0 = 263.4           # interim; the tool resets to 277.1

K = 0.70                  # incremental GAAP (after-stock-comp) margin
RA = 1.215582 * 4         # Q3-2026 annualized revenue, $B (10-Q)
AA = 0.061669 * 4         # Q3-2026 annualized GAAP operating income, $B (10-Q)

NEW = {
    #             FY26   FY27   FY26 owner margin  probability special
    "ultra_bear": (-0.32, -0.20, -0.02, 0.08, 1.05),
    "bear":       (-0.31,  0.00, -0.01, 0.28, 2.10),
    "base":       (-0.30,  0.20,  0.00, 0.43, 3.50),
    "bull":       (-0.29,  0.45,  0.01, 0.16, 5.60),
    "ultra_bull": (-0.28,  0.60,  0.02, 0.05, 10.50),
}


def main(dry: bool) -> None:
    path = REPO / "data" / "coin.yml"
    raw = path.read_text(encoding="utf-8")
    d = yaml.safe_load(raw)
    assert (d.get("stock_comp") or {}).get("basis") == "owner_fcf" or "--force" in sys.argv
    lines = raw.split("\n")
    out_rows = []
    for k, (g1, g2, m1, p, sa) in NEW.items():
        sc = d["scenarios"][k]
        dp = sc["dcf_path"]
        rp = [g1, g2] + dp["rev_path"][2:]
        tmp = dict(dp, rev_path=rp)
        rev = revenues(tmp)
        own = [m1]
        for t in range(1, 5):
            lev = (AA + K * (rev[t] - RA)) / rev[t] if rev[t] >= RA else AA / RA
            own.append(round(min(dp["op_margin"][t], lev), 3))
        pre = [round(m + OLD_SBC, 4) for m in own]       # interim reported basis
        fcf = [round(r * m, 3) for r, m in zip(rev, pre)]
        em = sc["dcf_metrics"]["exit_fcf_multiple"]
        tmp.update(special_assets=sa)
        b = bridge(tmp, fcf, SHARES0, em)
        cagr = round(((reduce(lambda a, x: a * (1 + x), rp, 1.0)) ** (1 / 5) - 1) * 100, 1)
        new = dict(rev_path=rp, op_margin=pre, fcf=fcf, special_assets=sa, **b)
        out_rows.append((k, p, b["dcf_per_share"], rev[0], rev[-1], fcf[-1]))
        lines = _patch(lines, k, new, p, cagr)
    new_raw = "\n".join(lines)
    new_raw = re.sub(r"\nstock_comp:\n(?:  .*\n?)+", "\n", new_raw)   # drop the marker; re-applied by the tool
    chk = yaml.safe_load(new_raw)
    assert "stock_comp" not in chk
    assert abs(sum(s["probability"] for s in chk["scenarios"].values()) - 1) < 1e-9
    w = sum(s["probability"] * s["expected_per_share"] for s in chk["scenarios"].values())
    for r in out_rows:
        print(f"  {r[0]:11s} p={r[1]:.2f} dcf ${r[2]:8.2f}  FY26 rev {r[3]:.2f}  FY30 rev {r[4]:.2f}  FY30 FCF(pre-SBC) {r[5]:.3f}")
    print(f"  interim weighted (reported basis, 263.4M) ${w:.2f}")
    if not dry:
        path.write_text(new_raw, encoding="utf-8")


def _patch(lines, scen, new, prob, cagr):
    start = next(i for i, l in enumerate(lines) if re.match(rf"^  {scen}:\s*$", l))
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"^  \S", lines[i]) or re.match(r"^\S", lines[i])), len(lines))
    i = start
    while i < end:
        l = lines[i]
        m = re.match(r"^(\s+)(\w+):(.*)$", l)
        if m:
            ind, key = m.group(1), m.group(2)
            if key == "probability" and len(ind) == 4:
                lines[i] = f"{ind}probability: {prob:.2f}"
            elif key == "expected_per_share" and len(ind) == 4:
                lines[i] = f"{ind}expected_per_share: {max(0.0, new['dcf_per_share']):.2f}"
            elif key == "cagr_5y":
                lines[i] = f"{ind}cagr_5y: {cagr}"
            elif len(ind) == 6 and key in ("rev_path", "op_margin") and m.group(3).strip() == "":
                j = i + 1
                vals = new[key]
                for v in vals:
                    lines[j] = re.sub(r"-\s.*$", f"- {v:g}", lines[j])
                    j += 1
            elif len(ind) == 6 and key in ("fcf", "pv_fcf"):
                lines[i] = f"{ind}{key}: [" + ", ".join(f"{x:.3f}" for x in new[key]) + "]"
            elif len(ind) == 6 and key in ("special_assets", "sum_pv_fcf", "terminal_value", "pv_terminal",
                                           "op_ev", "total_equity", "dcf_per_share"):
                lines[i] = f"{ind}{key}: {new[key]:.2f}" if key != "special_assets" else f"{ind}{key}: {new[key]}"
        i += 1
    return lines


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
