#!/usr/bin/env python3
"""Reusable mature-company memo builder + Batch-B specs (group 1: LULU, ABNB, UBER).
Emits data/_intake/<ticker>.yml from a compact content spec; numerics via model_mature."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from model_mature import model_m
import yaml
from collections import OrderedDict
yaml.add_representer(type(None), lambda d,_: d.represent_scalar('tag:yaml.org,2002:null',''))
yaml.add_representer(OrderedDict, lambda d,data: d.represent_dict(data.items()))
def rnd(xs): return [round(float(x),3) for x in xs]
SK=["ultra_bear","bear","base","bull","ultra_bull"]
LAB={"ultra_bear":("Ultra Bear","UltBear"),"bear":("Bear","Bear"),"base":("Base","Base"),"bull":("Bull","Bull"),"ultra_bull":("Ultra Bull","UltBull")}

def build(s):
    cash=s["cash"]; nd=s.get("net_debt",0.0); REVB=s["rev_b"]; TICK=s["ticker"].lower()
    scen=OrderedDict()
    for k in SK:
        n=s["scn"][k]
        r=model_m(dict(rev_b=REVB,rev_path=n["g"],fcf_margin=n["fcfm"],wacc_path=[n["wacc"]]*5,term_g=n["tg"],final_shares=n["fs"]),cash,nd)
        lab,slab=LAB[k]
        scen[k]=OrderedDict([("label",lab),("short_label",slab),("probability",n["p"]),
            ("expected_per_share",r["expected"]),("headline",n["hl"]),("narrative",n["narr"]),
            ("probability_rationale",n["pr"]),
            ("dcf_metrics",OrderedDict([("cagr_5y",r["cagr5"]),("wacc",n["wacc"])])),
            ("dcf_path",OrderedDict([("rev_b",REVB),("rev_path",rnd(n["g"])),("op_margin",rnd(n["opm"])),
                ("wacc_path",[n["wacc"]]*5),("term_g",n["tg"]),("fcf",r["fcf"]),("cash",cash),("net_debt",nd),
                ("raise_total",0.0),("dilution_pct",0),("final_shares",n["fs"]),("distress",0.0)])),
            ("chart_data",OrderedDict([("ev_rev_multiple",rnd(n["evr"])),("ev_fcf_multiple",rnd(n["evf"]))]))])
    intake=OrderedDict([("ticker",s["ticker"]),("company",s["company"]),("exchange",s["exch"]),
        ("dcf_type","mature_company"),("date","2026-06-01"),("spot",s["spot"]),
        ("market",OrderedDict([("market_cap_billion",s["cap"]),("shares_outstanding_million",s["sh"]),
            ("cash_billion",cash),("net_debt_billion",nd),("extras",s["extras"])])),
        ("taxonomy",OrderedDict([("watchlist",s["wl"]),("tier",s.get("tier")),("themes",s["themes"]),("primary_theme",s["themes"][0])])),
        ("central_question",s["cq"]),("thesis",s["thesis"]),
        ("chart_reference",OrderedDict(s["chartref"])),
        ("page3_chart_config",OrderedDict(s["p3cfg"])),
        ("page3",OrderedDict([("subtitle",s["subtitle"]),("sources",s["sources"])])),
        ("scenarios",scen),
        ("historical_prices",OrderedDict([("ipo_marker",s["ipo"]),("x_min",s["xmin"]),("points",s["points"])])),
        ("weighting_rationale",[OrderedDict([("label",l),("body",b)]) for l,b in s["wr"]]),
        ("appendix",OrderedDict([("pushback",[OrderedDict([("label",l),("body",b)]) for l,b in s["pb"]]),
            ("triggers",[OrderedDict([("label",l),("body",b)]) for l,b in s["tr"]])])),
        ("glossary",[OrderedDict([("term",t),("definition",d)]) for t,d in s["gloss"]]),
        ("competitive",OrderedDict([("arena",s["arena"]),("lens","power_audit"),
            ("powers",OrderedDict([(p,OrderedDict([("score",sc),("note",nt)])) for p,sc,nt in s["powers"]])),
            ("dominant_power",s["dom"]),("durability",s["dur"]),
            ("rivals",[OrderedDict([("name",nm),("kind",kd),("note",nt),("growth",gr),("margin",mg),("multiple",ml)]) for nm,kd,nt,gr,mg,ml in s["rivals"]]),
            ("threats",[OrderedDict([("vector",v),("who",w),("falsifier",f)]) for v,w,f in s["threats"]]),
            ("takeaway",s["take"])]))])
    out=f"/home/user/ar2eb/data/_intake/{TICK}.yml"
    open(out,"w").write(f"# {s['ticker']} — {s['company']} ({s['exch']}) · INTAKE (MATURE; python-modeled; scaffold-ready)\n"+
        yaml.dump(intake,sort_keys=False,default_flow_style=False,width=120,allow_unicode=True))
    w=sum(scen[k]["probability"]*scen[k]["expected_per_share"] for k in SK)
    print(f"  {s['ticker']}: weighted ${w:.2f} vs spot ${s['spot']} = {(w/s['spot']-1)*100:+.1f}%  -> {out}")

SPECS=[
# ============================== LULU ==============================
dict(ticker="LULU",company="Lululemon Athletica",exch="NASDAQ",spot=127.0,cap=15.2,sh=114.0,cash=1.8,rev_b=11.1,
 wl="fcf-plus-plus-growth",tier="Med-High",themes=["premium-consumer-brands"],
 extras=["$1.8B cash, no debt; ~114M shares; heavy buyback, no dividend","Revenue $11.1B FY25 (+5%, decelerating from +42%); ~22% op margin, ~$1.58B FCF","Down ~60% from the $340 high; US declining, China/international +20-29%"],
 cq="Is lululemon's ~60% de-rating to ~10x FCF an overshoot on a still-profitable premium brand — or the early innings of structural brand impairment (US decline, Alo/Vuori share loss)?",
 thesis="Lululemon trades at ~$15B (≈$127/sh, down ~60% from $340) — ~10x FCF on $11.1B revenue, ~22% operating margins, net cash and a heavy buyback. Growth has decelerated hard (+42%→+5%, guided +2-4%): the US is shrinking (-1 to -3%) while China/international compound +20-29%. The mature DCF asks whether the brand stabilizes and defends margins, or whether dupes (Alo, Vuori) and stale product structurally impair it. The finding: even pricing real brand-impairment downside (ultra-bear -34%), the modal stabilization case at 10x FCF implies the de-rating overshot.",
 chartref=[("history_years",[2021,2022,2023,2024,2025]),("history_revenue",[6.25,8.11,9.62,10.59,11.1]),("history_op_margin",[21.3,16.4,22.2,23.7,19.9]),("history_fcf",[0.7,0.9,1.3,1.64,1.58]),("history_ev_rev",[6.0,5.0,3.5,2.5,1.2])],
 p3cfg=[("segment_a","Americas"),("segment_b","International"),("hist_ent_split",[0.86,0.84,0.82,0.80,0.78]),("chart6_title","Equity build (Op EV + net cash)"),("chart6_type","matureEquityBuild")],
 subtitle="FY21-FY25 history + FY26-FY30 scenario projections  ·  fiscal years end late Jan  ·  FY2025 (Feb'26) results",
 sources="Sources: lululemon FY2025 results (year ended Feb 1, 2026; revenue $11.1B, FCF ~$1.58B, net cash ~$1.8B), FY2026 guidance, Earnest/Retail Dive share data. Revenue as a growth-rate path off FY25; FCF = revenue x FCF margin; Gordon terminal at scenario WACC. EV/sales vs premium-apparel peers.",
 ipo="IPO Jul '07",xmin=-6.5,points=[[-6.0,200.0],[-5.0,350.0],[-4.0,485.0],[-3.5,300.0],[-3.0,380.0],[-2.0,400.0],[-1.5,340.0],[-1.0,300.0],[-0.5,200.0],[-0.25,150.0],[-0.05,127.0]],
 scn={
  "ultra_bear":dict(p=0.15,g=[-0.05,-0.05,-0.04,-0.03,-0.02],fcfm=[0.10,0.09,0.08,0.08,0.08],opm=[0.16,0.14,0.12,0.12,0.12],wacc=0.115,tg=0.0,fs=102,evr=[1.0,0.8,0.6,0.5,0.4],evf=[9,8,7,7,7],
    hl="Brand impairment; US decline; margins crater.",
    narr=["Brand heat fades like Under Armour's: US revenue keeps declining, Alo/Vuori and dupes take share, and the full-price model erodes into promotions. Revenue falls ~4%/yr; operating margins compress toward single digits.","A shrinking premium brand earns a distressed multiple — DCF ~$85, ~33% below spot. The net cash and buyback cushion the floor but can't offset structural impairment."],
    pr="The genuine bear: the founder himself called the product stale, US (50%+ of sales) is already declining, and DTC share fell 30%->24% in a year. 15% weight on real brand impairment."),
  "bear":dict(p=0.32,g=[0.0,0.0,0.01,0.02,0.02],fcfm=[0.11,0.11,0.12,0.12,0.12],opm=[0.18,0.18,0.19,0.19,0.20],wacc=0.105,tg=0.015,fs=103,evr=[1.4,1.3,1.2,1.1,1.1],evf=[12,11,11,11,11],
    hl="Share loss continues; US shrinks; capped.",
    narr=["The US stays soft and international decelerates; lululemon holds its position but doesn't grow, and tariffs/promotions keep margins below the historical peak. Revenue roughly flat, low-teens FCF margin.","DCF ~$158 (+24%) — even a 'dominant but ex-growth' brand at ~11x FCF is worth more than today's price; the de-rating already prices worse."],
    pr="Share loss continues and the dupe pressure caps the multiple, but the brand doesn't break. 32% weight as the plausible 'stalls but survives' path given the bearish US momentum."),
  "base":dict(p=0.33,g=[0.03,0.04,0.04,0.05,0.05],fcfm=[0.13,0.13,0.14,0.14,0.14],opm=[0.21,0.21,0.22,0.22,0.22],wacc=0.095,tg=0.02,fs=105,evr=[2.0,1.9,1.8,1.7,1.7],evf=[15,14,14,14,14],
    hl="US stabilizes; China/international compounds.",
    narr=["The modal path: the US stabilizes under new CEO Heidi O'Neill (ex-Nike) while China/international keep compounding ~20%, blending to ~4% total growth at a defended ~22% operating margin.","DCF ~$236 (+85%). A stabilizing premium brand at 10x FCF with a long international runway is simply mispriced if the modal case plays out — the core of the thesis."],
    pr="Requires US stabilization (not re-acceleration) plus continued international compounding — consistent with FY26 guidance. 33% as the central outcome; the brand's cornered-resource fabrics + community don't vanish."),
  "bull":dict(p=0.15,g=[0.05,0.07,0.07,0.07,0.07],fcfm=[0.14,0.15,0.15,0.16,0.16],opm=[0.22,0.23,0.23,0.24,0.24],wacc=0.09,tg=0.025,fs=107,evr=[2.6,2.5,2.4,2.3,2.3],evf=[17,16,16,16,16],
    hl="New-CEO turnaround; margin recovery.",
    narr=["The turnaround lands: product newness re-accelerates the US, international/China stay hot, footwear/men's scale, and margins recover toward 24%. Revenue compounds ~7%.","DCF ~$324 (+155%) — back toward the old growth-compounder valuation as the brand re-rates with the fundamentals."],
    pr="O'Neill's product fix works and the US re-accelerates while international compounds — a real turnaround. ~15% weight; lululemon has done it before."),
  "ultra_bull":dict(p=0.05,g=[0.07,0.10,0.10,0.10,0.09],fcfm=[0.15,0.16,0.16,0.17,0.17],opm=[0.23,0.24,0.24,0.25,0.25],wacc=0.085,tg=0.025,fs=108,evr=[3.2,3.1,3.0,2.9,2.9],evf=[19,18,18,18,18],
    hl="Full re-rate; China + footwear scale.",
    narr=["The full turnaround: China becomes a second home market, footwear/men's/international all compound, and lululemon re-rates to a premium growth multiple. Revenue ~10% CAGR at peak margins.","DCF ~$409 (+222%) — the brand reclaims its compounder status; ~5% probability."],
    pr="Everything works — US turnaround AND China AND categories AND a multiple re-rating. ~5%, the asymmetric upside the depressed entry is buying.")},
 wr=[("Ultra Bear 15%","Brand impairment; US decline; ~$85 (-34%)."),("Bear 32%","Share loss; US shrinks; ex-growth; ~$158 (+24%)."),("Base 33%","US stabilizes + China/intl; ~$236 (+85%)."),("Bull 15%","New-CEO turnaround; ~$324 (+155%)."),("Ultra Bull 5%","Full re-rate + China; ~$409 (+222%).")],
 pb=[("~10x FCF for a 22%-margin brand.","Net-cash, $1.58B FCF, ~22% operating margin — priced like a terminal-decline retailer, not a premium brand."),
     ("Cornered-resource fabrics.","Proprietary Nulu/Luxtreme/Everlux blends + fit/quality are the hardest thing for Alo/Vuori/dupes to replicate."),
     ("Huge international runway.","China +29%, international +22%, only ~16% of revenue — a multi-year growth engine the US weakness masks."),
     ("Heavy buyback at the lows.","No dividend; ~$1.6B authorization remaining, retiring shares at ~10x FCF — accretive."),
     ("New CEO from Nike.","Heidi O'Neill (ex-Nike) + a settled founder proxy fight = fresh product/turnaround optionality.")],
 tr=[("Bull validation","US/Americas revenue returns to growth  ·  international stays >20%  ·  gross margin re-expands above 58%  ·  footwear/men's scale"),
     ("Bear validation","Americas declines for 2+ years  ·  DTC share falls below 22%  ·  gross margin compresses below 55% on sustained promotions"),
     ("Reframe needed","if the brand goes structurally cold (Under-Armour path) the cornered-resource Power erodes — re-rate the terminal toward a commodity-apparel multiple")],
 gloss=[("DTC / wholesale","Direct-to-consumer (stores + digital, ~60% of sales, higher margin) vs wholesale; the channel mix that supports the brand premium."),
        ("Dupes","Lower-priced look-alikes (and premium challengers Alo/Vuori) eroding lululemon's US share — the central bear mechanism."),
        ("Power of Three x2","Management's plan to double men's + digital and quadruple international vs 2021 — now at risk on the FY26 guide."),
        ("Cornered resource","Helmer Power: proprietary fabrics + fit/quality that rivals can't easily copy — lululemon's most durable moat."),
        ("FCF margin","Free cash flow / revenue (~14% in FY25); the mature-DCF lever the 22% operating margin converts to.")],
 arena="Premium athleisure — lululemon (brand + proprietary fabrics, ~60% DTC) vs Nike, Alo Yoga, Vuori, Athleta, On, fast-fashion dupes; defending a premium brand Power as US share erodes.",
 powers=[("scale_economies",2,"Sourcing/marketing leverage at $11B revenue, but apparel scale is limited vs Nike."),
         ("network_economies",1,"Community/ambassadors are brand affinity, not a hard network."),
         ("counter_positioning",1,"Was the women's-first disruptor; now the incumbent being counter-positioned by Alo/Vuori."),
         ("switching_costs",1,"Weak — apparel is promiscuous; this is why dupes bite."),
         ("branding",3,"The dominant Power: premium pricing, cult community, ~58% gross margin — but eroding in US (DTC share 30%->24%)."),
         ("cornered_resource",2,"Proprietary fabrics (Nulu/Luxtreme/Everlux) + fit/quality + patents — durable, the hardest piece to dupe."),
         ("process_power",1,"Design/supply learning curve; modest.")],
 dom="branding",dur="medium",
 rivals=[("Nike","public","Scale leader, mid-cycle reset; women's/DTC is lululemon's edge vs Nike.",0.02,0.11,"~25x P/E"),
         ("Alo Yoga","private","Influencer-led, fashion-forward; ~88% growth, taking US share at higher tickets.",None,None,"private"),
         ("Vuori","private","Workout-to-everyday; ~33%+ growth, premium-priced, gaining share.",None,None,"private"),
         ("On Holding","public","Premium performance, fast-growing; adjacency pressure.",0.30,0.10,"~45x P/E")],
 threats=[("branding","Alo Yoga + Vuori (US share)","Americas revenue declines for 2+ years while DTC share falls below 22%."),
          ("counter_positioning","Fast-fashion dupes","Gross margin compresses below 55% on sustained promotions/markdowns."),
          ("scale_economies","Nike / macro down-trade","International growth decelerates below 10% while the US keeps shrinking.")],
 take="lululemon's brand Power is genuinely durable internationally (China +29%, only 16% of revenue) and underpinned by cornered-resource fabrics, but it is eroding in the saturated US where Alo/Vuori and dupes are taking DTC share and the founder calls the product stale. The ~60% de-rating to ~10x FCF prices structural impairment; the DCF tests whether the brand stabilizes — and even a real-impairment ultra-bear is only -34%, while the modal stabilization implies the sell-off overshot."),
]
if __name__ == "__main__":   # don't regenerate stale intakes on `from gen_b1 import build`
    for sp in SPECS: build(sp)
