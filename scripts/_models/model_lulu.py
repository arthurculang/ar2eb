import sys; sys.path.insert(0, __import__("os").path.dirname(__file__))
from model_mature import report_m, model_m
SPOT, CASH = 127.0, 1.8
def scn(prob,g,fcfm,wacc,tg,fs):
    return dict(probability=prob, rev_b=11.1, rev_path=g, fcf_margin=fcfm, wacc_path=[wacc]*5, term_g=tg, final_shares=fs)
S = {
 # brand impairment (Under Armour-like): revenue declines, margins crater, terminal de-rates
 "ultra_bear": scn(0.15,[-0.05,-0.05,-0.04,-0.03,-0.02],[0.10,0.09,0.08,0.08,0.08],0.115,0.0,102),
 # share loss continues; US shrinks, intl decelerates; thin margins
 "bear":       scn(0.32,[0.0,0.0,0.01,0.02,0.02],       [0.11,0.11,0.12,0.12,0.12],0.105,0.015,103),
 # US stabilizes; international/China compounds; margins ~hold
 "base":       scn(0.33,[0.03,0.04,0.04,0.05,0.05],     [0.13,0.13,0.14,0.14,0.14],0.095,0.02,105),
 # new-CEO turnaround: US re-accelerates + intl + categories; margin recovery
 "bull":       scn(0.15,[0.05,0.07,0.07,0.07,0.07],     [0.14,0.15,0.15,0.16,0.16],0.09,0.025,107),
 # full turnaround + China + footwear + re-rating
 "ultra_bull": scn(0.05,[0.07,0.10,0.10,0.10,0.09],     [0.15,0.16,0.16,0.17,0.17],0.085,0.025,108),
}
print("=== LULU 2nd pass (harsher downside) ===")
report_m(SPOT, S, CASH)
for k in S:
    r=S[k]["_d"]; print(f"    {k:<11} rev30 ${r['rev'][-1]:.1f}B fcf30 ${r['fcf'][-1]:.2f}B termX {r['term_mult']:.1f} dcf ${r['dcf_ps']:.2f} eq ${r['total_equity']:.1f}B")
