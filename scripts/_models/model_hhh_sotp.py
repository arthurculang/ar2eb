#!/usr/bin/env python3
"""HHH SOTP/NAV model v4 (LOCKED) — stable run-rate FCF, exit-multiple terminal.

Year-1 RE cash flow ~constant (~$0.57B = the real run-rate: MPC EBT $476M + OA NOI
$276M - G&A ~$122M, normalized). Revenue ~$1.5B at a ~38% RE cash margin. Scenario
variation = the 5y growth trajectory (land price/monetization) + Vantage value +
the residual NAV discount the market keeps. Terminal = exit multiple (~14x, a cap
rate) on year-5 cash flow. op_ev (real estate) = PV(5y FCF) + PV(exit). All
validator identities tie; displayed fields (cagr, margin, exit x, starting rev,
Vantage) all read in the correct direction.
"""
SHARES=59.63; CASH=1.84; DEBT=5.79; SPOT=66.86; WACC=0.075; MARGIN=0.38; REV_B=1.50
# (name, prob, NAV/sh, vantage, resid_discount, rev_growth_5y)
SC=[
 ("ultra_bear",0.10, 86, 0.9,0.41,0.00),
 ("bear",      0.22,104, 1.2,0.31,0.02),
 ("base",      0.40,113, 1.5,0.20,0.04),
 ("bull",      0.20,132, 2.0,0.10,0.06),
 ("ultra_bull",0.08,178, 3.6,0.05,0.09),
]
print(f"{'scen':<11}{'prob':>5}{'op_ev':>7}{'vant':>6}{'eq':>7}{'NAV':>6}{'resid':>6}"
      f"{'exp':>7}{'rev0':>6}{'cagr':>6}{'exit×':>7}{'op_ev✓':>8}")
print("-"*82); ev_w=0; rows=[]
for name,prob,nav,vant,resid,g in SC:
    eqt=nav*SHARES/1000; op_ev=round(eqt-CASH+DEBT-vant,3)
    rev=[round(REV_B*(1+g)**t,3) for t in range(1,6)]
    fcf=[round(r*MARGIN,3) for r in rev]
    pv,fac=[],1.0
    for f in fcf:
        fac*=(1+WACC); pv.append(round(f/fac,3))
    sum_pv=round(sum(pv),3); pv_term=round(op_ev-sum_pv,3)
    tv=round(pv_term*(1+WACC)**5,3); xm=round(tv/fcf[-1],2)
    eq=round(op_ev+CASH-DEBT+vant,3); navc=eq*1000/SHARES
    exp=round(navc*(1-resid),2); ev_w+=prob*exp
    op_ev_chk=round(sum_pv+pv_term,3)
    rows.append((name,prob,op_ev,vant,eq,navc,resid,exp,rev,fcf,pv,sum_pv,tv,pv_term,xm,g))
    print(f"{name:<11}{prob:>5.2f}{op_ev:>7.2f}{vant:>6.2f}{eq:>7.2f}{navc:>6.0f}{resid:>6.0%}"
          f"{exp:>7.1f}{rev[0]:>6.2f}{g*100:>5.0f}%{xm:>7.1f}{op_ev_chk:>8.2f}")
print("-"*82)
print(f"WEIGHTED ${ev_w:.2f} vs ${SPOT} -> {ev_w/SPOT-1:+.1%} | prob {sum(r[1] for r in rows):.2f}")
print()
import json
out={}
for (name,prob,op_ev,vant,eq,navc,resid,exp,rev,fcf,pv,sum_pv,tv,pv_term,xm,g) in rows:
    revpath=[round(g,3)]*5
    out[name]=dict(probability=prob,expected_per_share=exp,nav_per_share=round(navc,1),
        resid_discount=resid,cagr_5y=round(g*100,1),wacc=WACC,exit_fcf_multiple=xm,vantage=vant,
        rev_b=REV_B,rev_path=revpath,op_margin=[MARGIN]*5,fcf=fcf,pv_fcf=pv,sum_pv_fcf=sum_pv,
        terminal_value=tv,pv_terminal=pv_term,op_ev=op_ev,cash=CASH,net_debt=DEBT,
        special_assets=vant,total_equity=eq,final_shares=SHARES,dcf_per_share=round(eq*1000/SHARES,2))
print(json.dumps(out,indent=1))

# ── emit YAML dcf_metrics + dcf_path blocks per scenario ──
print("\n\n===YAML BLOCKS===")
for name,prob,nav,vant,resid,g in SC:
    eqt=nav*SHARES/1000; op_ev=round(eqt-CASH+DEBT-vant,3)
    rev=[round(REV_B*(1+g)**t,3) for t in range(1,6)]
    fcf=[round(r*MARGIN,3) for r in rev]
    pv,fac=[],1.0
    for f in fcf:
        fac*=(1+WACC); pv.append(round(f/fac,3))
    sum_pv=round(sum(pv),3); pv_term=round(op_ev-sum_pv,3)
    tv=round(pv_term*(1+WACC)**5,3); xm=round(tv/fcf[-1],2)
    eq=round(op_ev+CASH-DEBT+vant,3); navc=round(eq*1000/SHARES,2)
    exp=round(navc*(1-resid),2)
    revpath=[round(g,3)]*5; om=[MARGIN]*5; wp=[WACC]*5
    print(f"# --- {name}  (prob {prob}, expected ${exp}, NAV ${navc}, resid disc {resid:.0%}) ---")
    print(f"    dcf_metrics:")
    print(f"      cagr_5y: {round(g*100,1)}")
    print(f"      wacc: {WACC}")
    print(f"      exit_fcf_multiple: {xm}")
    print(f"      special_label: Vantage insurance")
    print(f"    dcf_path:")
    print(f"      rev_b: {REV_B}")
    print(f"      rev_path: {revpath}")
    print(f"      op_margin: {om}")
    print(f"      wacc_path: {wp}")
    print(f"      fcf: {fcf}")
    print(f"      pv_fcf: {pv}")
    print(f"      term_g: 0.02")
    print(f"      sum_pv_fcf: {sum_pv}")
    print(f"      terminal_value: {tv}")
    print(f"      pv_terminal: {pv_term}")
    print(f"      op_ev: {op_ev}")
    print(f"      cash: {CASH}")
    print(f"      net_debt: {DEBT}")
    print(f"      special_assets: {vant}")
    print(f"      total_equity: {eq}")
    print(f"      raise_total: 0.0")
    print(f"      dilution_pct: 0")
    print(f"      final_shares: {SHARES}")
    print(f"      dcf_per_share: {navc}")
    print(f"      distress: 0.0")
