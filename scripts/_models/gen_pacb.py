#!/usr/bin/env python3
"""PACB — Pacific Biosciences (NASDAQ) · YOUNG memo intake builder.
Numbers locked via /tmp/young/model.py (model_dcf); prose conviction-neutral.
Finding: weighted $1.29 vs spot $1.32 = -2.3% — fair; distressed, financially-levered option."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from gen_young import build_young

def sc(p, rev, opm, wacc, tg, s2c, pf, dist, raises, rprices, dil, fs, tam, comp, hl, narr, pr):
    return dict(p=p, rev=rev, opm=opm, wacc=wacc, tg=tg, s2c=s2c, pf=pf, dist=dist, raises=raises,
                rprices=rprices, dil=dil, fs=fs, tam=tam, comp=comp, hl=hl, narr=narr, pr=pr)

SPEC = dict(
 ticker="PACB", company="Pacific Biosciences", exch="NASDAQ", spot=1.32,
 cap=0.41, sh=310.5, cash=0.276, net_debt=0.644, last_rev=0.16,
 extras=["$0.276B cash vs ~$0.644B convertible notes (due 2029/2030) → ~$0.368B net debt > the equity cap",
         "FY25 revenue $160M (+4%): consumables $82M (+16%), instruments $53.8M (-18%)",
         "Cash-flow-positive targeted 2027; FY26 opex guided $220-225M; ~310M shares, no reverse split"],
 wl="asymmetrical-moonshots", tier="Low", themes=["omics-life-science-infrastructure"],
 cq="At $1.32, can long-read consumables reach cash-flow breakeven before the ~$644M of converts mature in 2029/2030 — or does the net debt swamp the equity first?",
 thesis=(
   "Pacific Biosciences sells long-read HiFi DNA sequencers (Revio, Vega) and the high-margin consumables that run "
   "on them — the #3 behind Illumina's short-read scale and Oxford Nanopore in long-read. The $1.32 sticker hides "
   "the setup: $0.276B cash against ~$0.644B of convertible notes is ~$0.368B net debt, larger than the $410M "
   "equity cap — a financially-levered option, not a cheap value stock. The DCF asks whether ~16%-growing consumable "
   "pull-through reaches cash-flow positive (targeted 2027) before the converts mature. Roughly half the probability "
   "mass is worth ~$0 because the debt outranks the equity; a fat long-read-wins tail offsets it. Weighted $1.29 vs "
   "spot $1.32, modestly negative."),
 tam_billion=8, hist_years=[2023, 2024, 2025], hist_rev=[0.200, 0.154, 0.160], hist_fleet=[0, 0, 0],
 p3cfg=[("peer_y", 20), ("peer_text", "Illumina-scale sequencing op margin ~20%"), ("fleet_anchor", 0),
        ("fleet_title", "Revenue ramp (log)"), ("fleet_reference", None), ("valn_anchor_y", 4),
        ("valn_anchor_text", "Profitable sequencing EV/sales ~4-6x"),
        ("valn_caption", "At $1.32 the equity looks cheap, but ~$368M net debt means the converts, not revenue, set the value."),
        ("tam_title", "$8B long-read sequencing — PACB share"),
        ("tam_legend", ["PACB", "Illumina / Oxford Nanopore", "Other sequencing"])],
 subtitle="FY23-FY25 history + FY26-FY35 scenario projections  ·  fiscal years end Dec 31  ·  Q1'26 (May 2026) release",
 sources="Sources: PACB FY2025 + Q1'26 results (CIK 1299130), convertible-note terms (1.375% 2030 ~$441M + 1.50% 2029 ~$200M), FY26 opex/breakeven guidance. Equity bridge carries the ~$644M converts as net debt. FCF is NOL-shielded pre-tax over the explicit window. TAM: the long-read serviceable slice of the sequencing market, ~$8B.",
 ipo="IPO '10", xmin=-5.2,
 points=[[-5.0, 22.0], [-4.5, 15.0], [-4.0, 8.0], [-3.0, 5.0], [-2.5, 3.0], [-2.0, 2.0], [-1.0, 1.5], [-0.5, 1.8], [-0.05, 1.32]],
 wr=[
   ("Ultra Bear 18%", "Long-read stalls; converts wipe out equity."),
   ("Bear 32%", "Growth too slow to clear the debt in time."),
   ("Base 30%", "Breakeven ~2027; equity just clears converts."),
   ("Bull 13%", "Long-read inflects; consumables beat the debt."),
   ("Ultra Bull 7%", "Long-read wins big WGS share; a re-rating."),
 ],
 pb=[
   ("Converts were already refinanced", "The 2028 SoftBank wall was pushed to 2029/2030, buying runway — but ~$644M still outranks a $410M equity cap and must be cleared."),
   ("Consumables are inflecting now", "Consumables grew +16% to $82M while instruments fell -18% — the razor/blade pivot is visibly underway, the bull's required first step."),
   ("Restructuring de-risks the burn", "FY26 opex guided down to $220-225M with headcount -16% targets cash-flow-positive in 2027 — if hit, base-case equity survives."),
   ("Long-read accuracy is a real edge", "HiFi reads solve problems short-read can't; if whole-genome sequencing shifts to long-read, the #3 still captures a growing consumables annuity."),
   ("It is a barbell, not sticker-cheap", "The $1.32 looks cheap, but net debt above the equity cap means ~half the mass is ~$0 — the price reflects leverage, not a bargain."),
 ],
 tr=[
   ("Bull validation", "Consumable pull-through accelerates above ~$229K/Revio; adj-EBITDA turns positive; the FY27 cash-flow-positive target is reaffirmed; converts refinanced non-dilutively."),
   ("Bear validation", "Instrument declines persist; pull-through flattens; burn stays ~$45M/qtr; a dilutive equity or convert refinancing before 2029."),
   ("Reframe needed", "A larger-than-expected raise, a covenant or maturity event, or a credible buyer for the long-read franchise — any of which resets the equity thesis."),
 ],
 gloss=[
   ("long-read / HiFi sequencing", "DNA sequencing that reads long, highly accurate fragments (HiFi), resolving regions short-read instruments struggle with."),
   ("consumable pull-through", "Recurring high-margin reagent/kit revenue each installed instrument generates per year — the 'blade' in the razor/blade model."),
   ("Revio", "PACB's high-throughput long-read sequencer (346 installed); the main pull-through driver at ~$229K annualized."),
   ("convertible notes", "Debt that can convert to equity; ~$644M here (due 2029/2030) that outranks common holders until repaid or converted."),
   ("razor/blade model", "Selling instruments (razor) to drive recurring consumable sales (blade); the pivot underway as consumables grow and instruments shrink."),
   ("p_fail", "Modeled probability the equity is wiped out (distress ~$0.30/share) before the scenario's terminal year — elevated here by net debt above the equity cap."),
 ],
 competitive=dict(
   arena="Long-read DNA sequencing within the broader sequencing market — PACB (HiFi/SMRT) versus Illumina's dominant short-read scale and Oxford Nanopore in direct long-read.",
   powers=[
     ("scale_economies", 1, "Sub-scale #3 at ~$160M revenue; Illumina's ~$4.5B base buys cost and R&D advantages PACB can't match."),
     ("network_economies", 1, "Some ecosystem pull from published HiFi methods and installed-base data, but no strong cross-side network."),
     ("counter_positioning", 1, "Long-read is structurally different from short-read, but Illumina can and does add long-read offerings, blunting the wedge."),
     ("switching_costs", 2, "Installed Revio/Vega plus validated lab workflows create real stickiness, anchoring recurring consumable pull-through."),
     ("branding", 1, "Credible accuracy reputation in long-read, but no pricing-power brand against the incumbent."),
     ("cornered_resource", 2, "HiFi/SMRT IP and accuracy are the asset PACB is trying to turn into Power, but contested by Nanopore and Illumina."),
     ("process_power", 1, "Manufacturing and chemistry know-how exist; not yet a durable, hard-to-replicate process advantage at scale."),
   ],
   dom="cornered_resource", window="closing",
   rivals=[
     ("Illumina", "public", "Short-read scale leader, ~$4.5B revenue; dominant economics, adding long-read", 0.85, 0.70, "strong cash flow, self-funded"),
     ("Oxford Nanopore", "public", "Direct long-read rival (LSE); portable, real-time reads", 0.05, 0.12, "public, funded but pre-profit"),
     ("Pacific Biosciences", "public", "The #3; HiFi accuracy edge, net-debt-constrained", 0.10, 0.18, "net debt ~$368M; burning cash"),
   ],
   lead_lag=[
     ("Long-read accuracy (HiFi)", "Leading on accuracy", "Oxford Nanopore", "leading"),
     ("Scale / cost per genome", "Sub-scale", "Illumina", "lagging"),
     ("Balance-sheet strength", "Net debt above equity cap", "Illumina", "lagging"),
   ],
   take=(
     "A Power is being attempted, not yet originated. PACB is trying to convert HiFi/SMRT accuracy into a "
     "cornered-resource and process Power in long-read, but it lags Illumina's scale economies badly and shares "
     "the long-read field with Oxford Nanopore. The falsifier the bull must clear is observable and singular — "
     "consumable pull-through compounding fast enough to reach cash-flow breakeven and clear the ~$644M convert "
     "wall before 2029/2030. Miss it and the leverage, not the technology, decides the outcome."),
 ),
 scn={
  "ultra_bear": sc(0.18, [0.16,0.16,0.17,0.18,0.19,0.20,0.21,0.22,0.23,0.24],
    [-0.45,-0.30,-0.20,-0.12,-0.06,-0.02,0.01,0.03,0.05,0.06], (0.14,0.115), 0.03, 1.4, 50, 0.30,
    [0.0,0.0,0.10,0.15,0.15,0.10,0.0,0.0,0.0,0.0], 1.2, 134, 727, 3.0, 5.0,
    "Long-read stalls; equity wiped",
    ["Long-read adoption stalls and instrument placements keep shrinking, leaving FY35 revenue near $0.24B at a thin "
     "6% operating margin. Pull-through never funds the cost base, and burn forces small dilutive raises that add "
     "shares at a low price while the value migrates to the noteholders.",
     "With a 50% failure probability the ~$0.644B of converts outrank a tiny equity stub, so common is worth ~$0 in "
     "restructuring (distress $0.30/share). DCF -$1.06; probability-weighted contribution rounds to $0. The debt, "
     "not the business, sets the floor."],
    "The razor/blade pivot is real but unproven at scale, and a 50% p_fail reflects a sub-scale #3 carrying net "
    "debt above its equity cap into a 2029/2030 maturity wall — plausible but not the modal path."),
  "bear": sc(0.32, [0.17,0.18,0.20,0.23,0.27,0.32,0.37,0.42,0.46,0.49],
    [-0.35,-0.22,-0.12,-0.04,0.03,0.08,0.12,0.15,0.17,0.19], (0.13,0.11), 0.035, 1.5, 35, 0.30,
    [0.0,0.0,0.0,0.10,0.10,0.0,0.0,0.0,0.0,0.0], 1.4, 46, 453, 6.125, 5.0,
    "Growth too slow for the debt",
    ["Consumables grow modestly to ~$0.49B FY35 revenue at a 19% margin, but the ramp is too slow to cover the "
     "converts before they mature. The business limps toward breakeven while the installed base compounds only "
     "gradually and instruments stay soft.",
     "At 35% p_fail the equity barely exists once ~$0.644B of debt is serviced or refinanced into dilution; DCF "
     "-$0.35, weighted contribution ~$0. A workable product that simply can't out-run its own balance sheet in time."],
    "The largest single bucket. Reflects the central tension — real but unspectacular long-read uptake against a "
    "fixed debt wall — where survival is likely but equity value is not, given how little cushion sits above the converts."),
  "base": sc(0.30, [0.17,0.19,0.22,0.27,0.33,0.40,0.47,0.54,0.59,0.62],
    [-0.30,-0.16,-0.06,0.02,0.07,0.11,0.14,0.17,0.19,0.21], (0.12,0.105), 0.04, 1.6, 22, 0.30,
    [0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0], 0.0, 0, 311, 7.75, 5.0,
    "Breakeven ~2027; equity clears",
    ["Steady long-read adoption plus the FY26 cost cuts (opex $220-225M, headcount -16%) reach cash-flow breakeven "
     "around 2027. FY35 revenue ~$0.62B at a 21% margin as Revio pull-through (~$229K annualized) and a growing "
     "Vega base compound high-margin consumables.",
     "At 22% p_fail the equity barely clears the ~$0.644B of converts rather than being consumed by them; DCF $0.62, "
     "weighted contribution $0.55. The modal case is survival with thin positive equity — close to today's price, "
     "which is why the headline lands near fair."],
    "Requires the consumables flywheel to fund operations on roughly the guided timeline and the converts to be "
    "covered or refinanced cleanly. A demanding but reachable path given the restructuring already underway and the 2027 breakeven target."),
  "bull": sc(0.13, [0.18,0.21,0.25,0.31,0.39,0.48,0.57,0.65,0.72,0.78],
    [-0.25,-0.10,0.02,0.09,0.14,0.18,0.21,0.23,0.25,0.26], (0.115,0.10), 0.05, 1.8, 12, 0.30,
    [0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0], 0.0, 0, 311, 9.75, 5.0,
    "Long-read inflects; debt covered",
    ["Long-read genuinely inflects: the Revio and Vega base compounds high-margin consumables to ~$0.78B FY35 "
     "revenue at a 26% margin. Operating leverage turns the razor/blade model cash-generative well ahead of the "
     "maturity wall.",
     "At 12% p_fail the converts are comfortably covered and the equity captures the upside above them; DCF $3.25, "
     "weighted contribution $2.90. This is the first scenario where financial leverage works for the common holder "
     "rather than against it."],
    "Needs durable consumable pull-through growth and a clinical/research shift toward long-read accuracy that PACB "
    "captures as the #3 — a real but lower-probability inflection, hence 13%."),
  "ultra_bull": sc(0.07, [0.19,0.23,0.29,0.38,0.50,0.64,0.78,0.90,0.99,1.05],
    [-0.18,0.0,0.09,0.16,0.21,0.25,0.28,0.30,0.31,0.31], (0.11,0.095), 0.06, 2.0, 6, 0.30,
    [0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0], 0.0, 0, 311, 13.125, 5.0,
    "Long-read wins WGS; re-rating",
    ["Long-read takes a large share of whole-genome sequencing and PACB rides ~6x revenue growth to ~$1.05B FY35 at "
     "a 31% margin. The installed base becomes a consumables annuity and the equity re-rates as the debt shrinks to "
     "a rounding error against cash flow.",
     "At 6% p_fail the converts are trivially covered; DCF $10.83, weighted contribution $10.20. The fat tail that, "
     "alongside the bull, carries the distribution and offsets the ~50% of mass worth ~$0."],
    "The lowest-probability outcome: long-read displacing short-read at population scale against Illumina's "
    "entrenched economics. Low odds, but the operating and financial leverage make the payoff large enough to matter to the weighted value."),
 })
build_young(SPEC)
