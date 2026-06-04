import sys; sys.path.insert(0, __import__("os").path.dirname(__file__))
from model_mature import report_m
def scn(prob,g,fcfm,wacc,tg,fs):
    return dict(probability=prob,rev_b=52.0,rev_path=g,fcf_margin=fcfm,wacc_path=[wacc]*5,term_g=tg,final_shares=fs)
S={ # harsher AV-disruption downside; FCF margins closer to current 19%
 "ultra_bear":scn(0.15,[0.02,0.02,0.01,0.0,0.0],   [0.15,0.15,0.14,0.14,0.14],0.11,0.01,1950),
 "bear":      scn(0.27,[0.06,0.06,0.05,0.05,0.04], [0.18,0.18,0.18,0.19,0.19],0.10,0.02,1950),
 "base":      scn(0.33,[0.10,0.10,0.09,0.08,0.08], [0.19,0.20,0.20,0.21,0.21],0.095,0.025,1930),
 "bull":      scn(0.18,[0.13,0.13,0.11,0.10,0.10], [0.21,0.22,0.22,0.23,0.23],0.09,0.03,1900),
 "ultra_bull":scn(0.07,[0.16,0.15,0.13,0.12,0.11], [0.22,0.24,0.24,0.25,0.25],0.085,0.03,1880),
}
print("=== UBER 2nd pass (harsher AV downside) ===")
report_m(70.40,S,2.7,0.0)
