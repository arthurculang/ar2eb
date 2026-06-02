"""Mature-company DCF engine. Mirrors scaffold derive_dcf_path + validate (mature).
expected_per_share = dcf_per_share (no p_fail). fcf provided OR = rev*fcf_margin."""
from functools import reduce
def _cd(w,i): return reduce(lambda a,x:a*(1+x), w[:i+1], 1.0)
def model_m(s, cash, nd=0.0, sa=0.0):
    rb=s["rev_b"]; g=s["rev_path"]; w=s["wacc_path"]; n=len(g)
    rev=[]; r=rb
    for i in range(n): r*= (1+g[i]); rev.append(round(r,3))
    if "fcf" in s: fcf=s["fcf"]
    else: fcf=[round(rev[i]*s["fcf_margin"][i],3) for i in range(n)]
    pv=[round(fcf[i]/_cd(w,i),3) for i in range(n)]; spv=round(sum(pv),2)
    tg=s["term_g"]; assert w[-1]>tg
    tv=fcf[-1]*(1+tg)/(w[-1]-tg); pvt=round(tv/_cd(w,n-1),2)
    opev=round(spv+pvt,2); eq=round(opev+cash-nd+sa,2); ps=round(eq*1000/s["final_shares"],2)
    mult=tv/fcf[-1] if fcf[-1] else 0
    return dict(rev=rev,fcf=fcf,sum_pv_fcf=spv,terminal_value=round(tv,2),pv_terminal=pvt,
                op_ev=opev,total_equity=eq,dcf_ps=ps,expected=ps,term_mult=round(mult,1),
                cagr5=round((reduce(lambda a,x:a*(1+x),g,1.0)**(1/n)-1)*100,1))
def report_m(spot, scen, cash, nd=0.0, sa_by=None):
    print(f"  {'scn':<11}{'prob':>6}{'cagr':>7}{'fcf30':>8}{'termX':>7}{'dcf_ps':>9}{'vs_spot':>9}")
    psum=0; wt=0
    for k in ["ultra_bear","bear","base","bull","ultra_bull"]:
        if k not in scen: continue
        s=scen[k]; sa=(sa_by or {}).get(k,0.0); r=model_m(s,cash,nd,sa)
        p=s["probability"]; psum+=p; wt+=p*r["expected"]
        print(f"  {k:<11}{p:>6.2f}{r['cagr5']:>7.1f}{r['fcf'][-1]:>8.3f}{r['term_mult']:>7.1f}{r['dcf_ps']:>9.2f}{(r['dcf_ps']/spot-1)*100:>+8.1f}%")
        s["_d"]=r
    print(f"  prob {psum:.3f}  WEIGHTED ${wt:.2f}  vs spot ${spot} = {(wt/spot-1)*100:+.1f}%")
    return wt
