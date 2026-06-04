#!/usr/bin/env python3
"""Arthur Indicator v1.0 over time (the "dip into green = buy" view).

    AI_1.0 = EV / ( Revenue x (GrossMargin + RevGrowth) )    EV = MktCap - NetCash

SOURCED annual fiscal-year-end fundamentals (SEC 10-K/8-K for revenue/GM/cash/debt;
FYE share-price x shares for market cap). Market caps carry ~+/-2-5% (FYE daily closes
were search-sourced, not pulled cell-by-cell). Per-name notes:
  - GROWTH for each series' first year is the known actual YoY (no prior row in the table).
  - UBER FY2020 revenue ROSE +6.8% on an as-filed total-revenue basis (Delivery offset the
    Mobility COVID drop) — NOT -21% (that was Mobility-only). UBER 2019 (IPO year, revenue
    restated) omitted. UBER gross margin steps 54%->~40% post-2021 as low-margin Freight/
    grocery consolidate into revenue (accounting artifact; the take-rate model makes GM fuzzy).
    Net cash is the strict cash+ST-inv - total-debt (UBER is net-DEBT 2020+; its reported
    "net cash" counts ~$6B of long-term equity stakes).
  - TXG FY2025 uses CORE revenue ($598.7M, -2.0%, ~67% GM) ex the one-time $44.1M patent
    settlement (the reported $642.8M/+5.2% overstates both) — matches the TXG memo's rev_b.
Refine the market caps to exact FYE closes if trading off these specific values.
"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# (year, mktcap$B, netcash$B [+=cash, -=debt], revenue$B, gross_margin, yoy_growth)
D = {
 "META": [(2016,332,29.4,27.64,.863,.542),(2017,519,41.7,40.65,.866,.471),(2018,377,41.1,55.84,.832,.374),
          (2019,584,54.9,70.70,.819,.266),(2020,773,62.0,85.97,.806,.216),(2021,919,48.0,117.93,.808,.372),
          (2022,311,30.8,116.61,.783,-.011),(2023,906,47.0,134.90,.808,.157),(2024,1473,49.0,164.50,.816,.219),
          (2025,1650,22.9,200.97,.820,.222)],
 "NVDA": [(2016,17,5.3,5.01,.561,.070),(2017,65,4.8,6.91,.588,.379),(2018,148,5.1,9.71,.599,.406),
          (2019,87,5.4,11.72,.612,.206),(2020,143,8.9,10.92,.620,-.068),(2021,321,4.6,16.68,.623,.527),
          (2022,610,10.3,26.91,.649,.614),(2023,481,2.4,26.97,.569,.002),(2024,1516,16.3,60.92,.727,1.259),
          (2025,2940,21.7,130.50,.750,1.142)],
 "LULU": [(2016,9.0,0.9,2.344,.508,.140),(2017,10.6,1.0,2.649,.528,.130),(2018,19.6,1.1,3.288,.550,.241),
          (2019,31.3,1.1,3.979,.559,.210),(2020,41.7,1.2,4.402,.560,.106),(2021,39.3,1.3,6.257,.577,.421),
          (2022,39.1,1.2,8.111,.553,.296),(2023,61.4,2.2,9.619,.583,.186),(2024,47.4,1.3,10.588,.592,.101),
          (2025,22.4,1.8,11.090,.566,.047)],
 "UBER": [(2020,94,-0.7,11.139,.537,.068),(2021,82,-5.0,17.455,.464,.567),(2022,49,-5.0,31.877,.383,.826),
          (2023,127,-3.9,37.281,.398,.170),(2024,128,-1.3,43.978,.394,.180),(2025,173,-2.9,52.017,.398,.183)],
 "ISRG": [(2016,25.4,4.80,2.704,.699,.134),(2017,42.7,3.80,3.129,.704,.157),(2018,54.9,4.83,3.724,.699,.190),
          (2019,68.5,5.85,4.479,.694,.203),(2020,96.3,6.87,4.358,.656,-.027),(2021,132.0,8.62,5.710,.693,.310),
          (2022,92.9,6.74,6.222,.692,.090),(2023,120.8,7.34,7.124,.664,.145),(2024,189.9,8.83,8.352,.687,.172),
          (2025,201.0,9.03,10.065,.660,.205)],
 "TXG":  [(2019,8.1,0.424,0.2459,.752,.680),(2020,16.1,0.664,0.2988,.797,.215),(2021,16.7,0.587,0.4905,.849,.642),
          (2022,4.2,0.430,0.5164,.767,.053),(2023,6.6,0.389,0.6187,.659,.198),(2024,1.8,0.393,0.6108,.680,-.013),
          (2025,2.07,0.523,0.5987,.670,-.020)],
}
def ai(cap,nc,rev,gm,g):
    den=rev*(gm+g); return (cap-nc)/den if den>0 else None

fig,axes=plt.subplots(2,3,figsize=(15,8.5)); axes=axes.flatten()
fig.suptitle("Arthur Indicator v1.0 over time   —   EV / (Revenue × (Gross Margin + Revenue Growth))\n"
             "sourced annual fiscal-year-end fundamentals (market caps ±~2–5%)",
             fontsize=12.5,fontweight="bold")
for ax,(name,rows) in zip(axes,D.items()):
    yrs=[r[0] for r in rows]; vals=[ai(*r[1:]) for r in rows]
    ax.axhspan(0,6,color="#16a34a",alpha=.13); ax.axhspan(6,11,color="#eab308",alpha=.12)
    ax.axhspan(11,200,color="#dc2626",alpha=.09)
    ax.plot(yrs,vals,"-o",color="#0f172a",lw=2,ms=5,zorder=5)
    lo=min(vals);
    for x,v in zip(yrs,vals):
        if v==lo or x==yrs[-1] or v==max(vals):
            ax.annotate(f"{v:.1f}",(x,v),textcoords="offset points",
                        xytext=(0,7 if v<max(vals)*.8 else -13),ha="center",fontsize=8,fontweight="bold")
    ax.set_title(name,fontsize=12,fontweight="bold",loc="left")
    ax.set_ylim(0,max(13,max(v for v in vals if v)*1.12)); ax.set_xticks(yrs[::2])
    ax.grid(alpha=.25,axis="y"); ax.tick_params(labelsize=8)
axes[0].annotate("2022 = 3.1\nthe doc's 'screaming buy'",(2022,3.11),xytext=(2017.5,6.0),fontsize=8,
                 color="#15803d",fontweight="bold",arrowprops=dict(arrowstyle="->",color="#15803d"))
axes[1].annotate("FY23: rich at 31\n(zero-growth year)",(2023,31.1),xytext=(2018.2,24),fontsize=8,color="#b91c1c",
                 arrowprops=dict(arrowstyle="->",color="#b91c1c"))
axes[1].annotate("FY25: ~12 'fair' at $3T\n(growth justifies it)",(2025,11.8),xytext=(2021.5,4),fontsize=8,
                 color="#15803d",arrowprops=dict(arrowstyle="->",color="#15803d"))
axes[2].annotate("2025 = 3.0 (green)\n→ ~2 now",(2025,3.03),xytext=(2020.5,9),fontsize=8,color="#15803d",
                 fontweight="bold",arrowprops=dict(arrowstyle="->",color="#15803d"))
fig.legend(handles=[Patch(facecolor="#16a34a",alpha=.3,label="GREEN <6 (cheap-for-quality)"),
                    Patch(facecolor="#eab308",alpha=.3,label="fair 6–11"),
                    Patch(facecolor="#dc2626",alpha=.3,label="RED >11 (rich)")],
           loc="lower center",ncol=3,fontsize=9,frameon=False,bbox_to_anchor=(.5,-.005))
fig.tight_layout(rect=[0,.04,1,.93])
out="scripts/_models/arthur_indicator_history.png"
fig.savefig(out,dpi=130,bbox_inches="tight"); print("wrote",out)
for name,rows in D.items():
    print(f"{name:<5}", " ".join(f"{r[0]}:{ai(*r[1:]):.1f}" for r in rows))
