#!/usr/bin/env python3
"""Reusable young-company (Damodaran) DCF modeler for ar2eb Wave-1 authoring.

Mirrors scripts/scaffold_ticker.py (equity bridge) AND scripts/validate.py
(cash-runway ERROR with prev_rev=0 at year 0) EXACTLY, so a scenario set that
prints clean here will pass `validate.py` after scaffolding. Lets me iterate
the 5-scenario DCF to internal consistency before authoring any YAML — the
discipline that avoids the AUR sign-flip class of error.

Usage: import and call model(ticker_inputs), or run a ticker module that
defines SPOT, SHARES_M, CASH_B, LAST_HIST_REV_B, SCENARIOS and calls report().
"""
from functools import reduce


def _cumdisc(wacc, i):
    return reduce(lambda a, w: a * (1 + w), wacc[: i + 1], 1.0)


def model_scenario(s, cash_b, last_hist_rev_b):
    """s: dict with rev_path, op_margin, wacc_path, term_g, s2c, p_fail,
    distress, raises, raise_prices, final_shares, net_debt(0), special_assets(0).
    Returns a dict of derived arrays + scalars + the validator cash-runway path."""
    rev = s["rev_path"]; opm = s["op_margin"]; wacc = s["wacc_path"]
    n = len(rev)
    assert len(opm) == n and len(wacc) == n, "rev/opm/wacc length mismatch"
    s2c = s["s2c"]

    # FCF for the DCF (reinvest[0] uses last historical revenue as prior).
    nopat, reinvest, fcf = [], [], []
    prev = last_hist_rev_b
    for i in range(n):
        np_ = rev[i] * opm[i]
        rein = (rev[i] - prev) / s2c if s2c else 0.0
        nopat.append(round(np_, 3)); reinvest.append(round(rein, 3))
        fcf.append(round(np_ - rein, 3))
        prev = rev[i]

    # PV of FCF.
    pv_fcf = [round(fcf[i] / _cumdisc(wacc, i), 3) for i in range(n)]
    sum_pv_fcf = round(sum(pv_fcf), 2)

    # Terminal (Gordon perpetuity on last FCF).
    tg = s["term_g"]
    assert wacc[-1] > tg, "wacc[-1] must exceed term_g"
    tv = fcf[-1] * (1 + tg) / (wacc[-1] - tg)
    pv_term = round(tv / _cumdisc(wacc, n - 1), 2)
    op_ev = round(sum_pv_fcf + pv_term, 2)

    cash = s.get("cash", cash_b); nd = s.get("net_debt", 0.0); sa = s.get("special_assets", 0.0)
    total_equity = round(op_ev + cash - nd + sa, 2)
    shares = s["final_shares"]
    dcf_ps = round(total_equity * 1000 / shares, 2)
    pf = s["p_fail"] / 100
    expected = round(max((1 - pf) * dcf_ps + pf * s["distress"], 0.0), 2)

    # Validator cash-runway (prev_rev = 0 at year 0 — the harsher basis).
    raises = s["raises"]
    cumcash = [cash_b]; prev = 0.0; cur = cash_b
    for i in range(n):
        f = rev[i] * opm[i] - (rev[i] - prev) / s2c
        cur = cur + (raises[i] if i < len(raises) else 0) + f
        cumcash.append(round(cur, 3)); prev = rev[i]
    min_cash = min(cumcash)

    # final_shares cross-check.
    new_sh = sum((r * 1000 / p) for r, p in zip(raises, s["raise_prices"]) if p > 0)
    return dict(nopat=nopat, reinvest=reinvest, fcf=fcf, pv_fcf=pv_fcf,
                sum_pv_fcf=sum_pv_fcf, terminal_value=round(tv, 2), pv_terminal=pv_term,
                op_ev=op_ev, total_equity=total_equity, dcf_ps=dcf_ps, expected=expected,
                min_cash=min_cash, cumcash=cumcash, raise_total=round(sum(raises), 3),
                implied_shares=round(s.get("shares0", 0) + new_sh, 1))


def report(spot, shares_m, cash_b, last_hist_rev_b, scenarios, shares0_m=None):
    print(f"  spot ${spot}  shares {shares_m}M  cash ${cash_b}B  last_hist_rev ${last_hist_rev_b}B")
    print(f"  {'scn':<10}{'prob':>6}{'dcf_ps':>9}{'exp_ps':>9}{'minCash':>9}{'raiseTot':>9}{'rev35':>8}{'opm35':>7}")
    psum = 0.0; weighted = 0.0; bad = []
    for k in ["ultra_bear", "bear", "base", "bull", "ultra_bull"]:
        if k not in scenarios:
            continue
        s = scenarios[k]
        if shares0_m is not None:
            s.setdefault("shares0", shares0_m)
        r = model_scenario(s, cash_b, last_hist_rev_b)
        p = s["probability"]; psum += p; weighted += p * r["expected"]
        flag = "  <-- CASH<0" if r["min_cash"] < -0.05 else ""
        print(f"  {k:<10}{p:>6.2f}{r['dcf_ps']:>9.2f}{r['expected']:>9.2f}"
              f"{r['min_cash']:>9.3f}{r['raise_total']:>9.2f}{s['rev_path'][-1]:>8.2f}{s['op_margin'][-1]:>7.2f}{flag}")
        if r["min_cash"] < -0.05:
            bad.append(k)
        s["_derived"] = r
    print(f"  prob sum = {psum:.3f}   WEIGHTED EXPECTED = ${weighted:.2f}   "
          f"vs spot ${spot} = {(weighted/spot-1)*100:+.1f}%")
    if bad:
        print(f"  !! cash-runway violations: {bad}")
    return weighted
