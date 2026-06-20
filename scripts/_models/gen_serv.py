#!/usr/bin/env python3
"""SERV — Serve Robotics (NASDAQ) · YOUNG memo intake builder.
Numbers locked via /tmp/moon/model.py (auto-diluted); prose conviction-neutral.
Finding: weighted $9.33 vs spot $7.22 = +29.2% — tail-driven autonomous-delivery moonshot."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from gen_young import build_young

def sc(p, rev, opm, wacc, tg, s2c, pf, dist, raises, rprices, dil, fs, tam, comp, hl, narr, pr):
    return dict(p=p, rev=rev, opm=opm, wacc=wacc, tg=tg, s2c=s2c, pf=pf, dist=dist, raises=raises,
                rprices=rprices, dil=dil, fs=fs, tam=tam, comp=comp, hl=hl, narr=narr, pr=pr)

SPEC = dict(
 ticker="SERV", company="Serve Robotics", exch="NASDAQ", spot=7.22,
 cap=0.56, sh=77.0, cash=0.197, net_debt=0.0, last_rev=0.0027,
 extras=["~$197M liquidity (~$47M cash + securities); ~1.2yr runway; burn ~$41M/qtr",
         "~2,000 robots deployed across 44 cities but only ~812 daily-active (<half utilized)",
         "FY26 guide $26M (~9x FY25); heavy dilution (24.8M -> 77.4M shares in 2yr; $150M ATM)"],
 wl="asymmetrical-moonshots", tier="Low", themes=["autonomous-vehicles-systems"],
 cq="With a fleet of ~2,000 robots already built but fewer than half daily-active, is SERV a cheap option on utilization inflecting to profitable unit economics, or a dilutive grind where the modal case loses money?",
 thesis=(
   "Serve Robotics runs autonomous sidewalk delivery robots, spun out of Uber/Postmates and Nvidia-backed. It trades "
   "at $7.22 (~$540M cap), down ~23% YTD, on FY25 revenue of just $2.7M against a ~$41M/quarter operating burn — a "
   "pre-scale company with ~$197M of liquidity and roughly 1.2 years of runway. The build is done: ~2,000 robots sit "
   "across 44 cities, but only ~812 are daily-active, so the central question is utilization, not fleet size. Anchor "
   "demand from Uber Eats (up-to-2,000-robot deal) and DoorDash exists to fill it. The DCF weighted fair value is "
   "$9.33, +29% above spot — but the modal base sits ~63% below the price, so the answer rides the right tail and is "
   "paid for with relentless dilution."),
 tam_billion=50, hist_years=[2023, 2024, 2025], hist_rev=[0.0002, 0.0018, 0.0027], hist_fleet=[0, 0, 0],
 p3cfg=[("peer_y", 13), ("peer_text", "Profitable logistics/delivery op margin ~10-15%"), ("fleet_anchor", 0),
        ("fleet_title", "Revenue ramp (log)"), ("fleet_reference", None), ("valn_anchor_y", 2),
        ("valn_anchor_text", "Mature logistics P/S ~1-3x"),
        ("valn_caption", "At ~200x sales on a pre-scale fleet, the price is utilization optionality, not fundamentals."),
        ("tam_title", "$50B last-mile delivery automation — SERV share"),
        ("tam_legend", ["SERV", "Competitors", "Other last-mile delivery"])],
 subtitle="FY23-FY25 history + FY26-FY35 scenario projections  ·  fiscal years end Dec 31  ·  Q1'26 (May 2026) release",
 sources="Sources: SERV FY2025 10-K + Q1'26 results (CIK 1832483), FY26 revenue guidance, fleet/utilization disclosures. Revenue is pre-scale (delivery fees + software); FCF is NOL-shielded pre-tax over the explicit window; raises auto-sized to fund the burn (the model's dilution path). TAM: the serviceable last-mile / sidewalk delivery automation market, ~$50B.",
 ipo="Uplisted '24", xmin=-2.6,
 points=[[-2.4, 4.0], [-2.0, 3.0], [-1.6, 5.0], [-1.2, 20.0], [-0.9, 14.0], [-0.6, 10.0], [-0.3, 8.5], [-0.05, 7.22]],
 wr=[
   ("Ultra Bear 15%", "Utilization never improves; unit economics fail; dilutive grind toward the distress floor."),
   ("Bear 30%", "Modest scaling but stays sub-scale; heavy dilution offsets the operating progress."),
   ("Base 30%", "Fleet utilization inflects and unit economics work; ~$0.70B revenue, but dilution caps per-share value below spot."),
   ("Bull 17%", "Delivery automation scales regionally; operating leverage on the already-built fleet."),
   ("Ultra Bull 8%", "Becomes a DoorDash-scale autonomous delivery network at ~7M deliveries/day."),
 ],
 pb=[
   ("The fleet is already built", "~2,000 robots across 44 cities are deployed; the spend is largely sunk, so utilization rising to profitability is operating leverage, not new capex."),
   ("Anchor demand is contracted", "Uber Eats (up-to-2,000-robot multi-year deal) plus DoorDash give committed volume to fill the fleet — the demand side is signed, not speculative."),
   ("Hyper-growth off a tiny base", "Revenue grew +578% YoY in Q1'26 and FY26 is guided to ~$26M (~9x FY25); management now reports utilization, not fleet size."),
   ("De-rated price, fat right tail", "Down ~23% YTD, the equity is a cheap option — roughly 89% of the expected value sits in the bull and ultra-bull, priced lightly versus spot."),
   ("A vertically-integrated stack", "Magna manufacturing, Nvidia compute, and the Diligent Robotics acquisition build a hardware-and-autonomy stack rivals must assemble from scratch."),
 ],
 tr=[
   ("Bull validation", "Daily-active robots climb toward the ~2,000 deployed; cost-per-delivery falls through $1; Uber Eats scales toward the 2,000-robot commitment; raises shrink as revenue funds the burn."),
   ("Bear validation", "Utilization stays stuck below half the fleet; the FY26 ~$26M guide slips; an equity raise on weak terms confirms dilutive stagnation; unit economics stay above $1/delivery."),
   ("Reframe needed", "Utilized-fleet unit economics turn durably profitable and self-funding, shifting the story from option-on-fleet to cash-flow; or the cash and ATM exhaust before that, breaking the thesis."),
 ],
 gloss=[
   ("Daily-active vs deployed fleet", "Robots actually running paid deliveries each day (~812) versus the total fielded (~2,000). The gap — under half utilized — is the central operational fact."),
   ("Unit economics / cost-per-delivery", "The profit on a single delivery after labor, energy, hardware depreciation and operations. SERV targets sub-$1/delivery; clearing it is what makes the model work."),
   ("Operating leverage", "Because the ~2,000-robot fleet is already built, additional deliveries on the same hardware drop largely to profit — so the model's value is highly sensitive to utilization."),
   ("Sales-to-capital (s2c)", "How much new revenue each dollar of reinvested capital produces; it sets how fast revenue can grow before the company must raise fresh capital."),
   ("ATM dilution", "An at-the-market equity program (here a live $150M ATM plus a $100M registered-direct) that funds the burn by selling new shares — the source of the modeled share-count growth."),
   ("p_fail", "The modeled probability the scenario ends in failure (utilization and unit economics never clear), driving the equity toward the $1.50 distress floor."),
 ],
 competitive=dict(
   arena="Autonomous last-mile delivery — sidewalk robots and small autonomous vehicles fulfilling food and goods orders — where SERV competes with platform in-house autonomy, venture-backed robot fleets, and logistics incumbents.",
   powers=[
     ("scale_economies", 1, "A first-mover fleet could earn route density and hardware-cost scale, but unit economics at scale are unproven."),
     ("network_economies", 1, "Density helps reliability and cost, but value does not yet compound two-sidedly across users the way a marketplace does."),
     ("counter_positioning", 1, "A robotics-native model the platforms are slower to build, but Uber and DoorDash are funding their own autonomy in parallel."),
     ("switching_costs", 1, "Multi-year platform deals create some stickiness, but Uber and DoorDash multi-source delivery and can shift volume."),
     ("branding", 0, "No consumer brand power; the order rides on Uber Eats or DoorDash, not the Serve name."),
     ("cornered_resource", 2, "The Magna exclusive-manufacturing and Nvidia compute stack plus the contracted Uber/DoorDash demand are the strongest candidate, but each is contractual, not owned."),
     ("process_power", 1, "An integrated build-and-operate workflow is distinctive but not yet shown to deliver profitably at scale."),
   ],
   dom="cornered_resource", window="open",
   rivals=[
     ("DoorDash (in-house / Wolt)", "incumbent-division", "A core customer building its own autonomy and robots — partner and potential substitute", 0.0, 0.0, "DoorDash balance sheet"),
     ("Coco Robotics", "private", "Venture-backed sidewalk delivery robots in overlapping US cities", 0.0, 0.0, "Private (VC-backed)"),
     ("Nuro", "private", "Well-funded autonomous delivery vehicles; deep capital and AV stack", 0.0, 0.0, "Private (heavily funded)"),
     ("Avride / Amazon logistics", "incumbent-division", "Platform and retail-scale autonomy efforts with vast balance sheets", 0.0, 0.0, "Corporate balance sheets"),
   ],
   lead_lag=[
     ("Robots deployed in commercial service", "~2,000 across 44 cities", "Smaller commercial fleets (Coco/Nuro)", "leading"),
     ("Profitable utilized-fleet unit economics", "Unproven; targeting sub-$1/delivery", "Also unproven across the field", "even"),
     ("Capital and balance-sheet depth", "~$197M liquidity, dilution-funded", "Deeper (DoorDash, Amazon, Nuro)", "lagging"),
   ],
   take=(
     "SERV is trying to originate a scale-economies plus cornered-resource Power — a first-mover commercial fleet, "
     "contracted Uber and DoorDash demand, and an exclusive Magna/Nvidia build stack — but no durable Power exists "
     "yet, because under half the fleet is utilized and unit economics at scale are unproven. The demand and the "
     "stack are contractual, not owned, and the platforms are funding their own autonomy, so the moat is contestable. "
     "The falsifier the bull must clear is utilized-fleet unit economics turning durably profitable — sub-$1/delivery "
     "on a high-utilization fleet — before dilution exhausts holders. Until that prints, the fleet is a built option, "
     "not a won Power, and the window stays open."),
 ),
 scn={
  "ultra_bear": sc(0.15, [0.026,0.05,0.08,0.10,0.12,0.14,0.15,0.16,0.17,0.18],
    [-6.0,-3.0,-1.7,-1.0,-0.6,-0.35,-0.18,-0.05,0.02,0.06], (0.145,0.115), 0.03, 2.0, 85, 1.50,
    [0.0,0.164,0.151,0.11,0.082,0.059,0.032,0.0,0.0,0.0], 4.0, 194, 226.5, 0.36, 25.0,
    "Utilization stalls; dilutive grind",
    ["Daily-active robots stay stuck below half the deployed fleet, unit economics never clear the sub-$1/delivery "
     "bar, and Uber Eats and DoorDash volume fails to fill the built capacity. Revenue reaches only about $0.18B by "
     "FY35 at a 6% operating margin — sub-scale logistics economics that never earn their cost of capital.",
     "With nothing to fund the burn, the auto-sized raises push the share count from ~77M toward ~227M, nearly "
     "tripling the float. The DCF lands at −$1.32; the $1.50 distress floor and residual liquidity drag the expected "
     "value to $1.08. The fleet exists, but the equity is diluted toward salvage."],
    "A 15% read. An 85% p_fail reflects that thin-margin delivery economics at sub-half fleet utilization rarely turn profitable before the cash and a live $150M ATM plus $100M registered-direct are exhausted."),
  "bear": sc(0.30, [0.026,0.06,0.11,0.17,0.24,0.30,0.35,0.38,0.40,0.42],
    [-6.0,-2.6,-1.1,-0.45,-0.05,0.04,0.08,0.10,0.11,0.12], (0.14,0.11), 0.035, 2.2, 55, 1.50,
    [0.0,0.172,0.144,0.104,0.044,0.0,0.0,0.0,0.0,0.0], 6.0, 100, 154.3, 0.84, 25.0,
    "Modest scaling; dilution offsets",
    ["Utilization improves somewhat and a few markets reach reasonable density, but the network never becomes a "
     "self-sustaining engine. Revenue reaches about $0.42B by FY35 at a 12% operating margin — better than today, "
     "yet far short of the scale and cost-per-delivery needed to justify a platform valuation.",
     "Continued burn forces heavy raises, lifting shares toward ~154M and offsetting most of the operating "
     "progress. The DCF is −$0.39 and the expected value $0.65, both below spot. Real volume growth, but the "
     "per-share economics never outrun the dilution."],
    "A 30% read. A 55% p_fail captures partial commercial traction — Uber Eats and DoorDash contracts are signed and FY26 revenue is guided to ~$26M (~9x FY25) — against the risk that scaling stalls short of durable profitability."),
  "base": sc(0.30, [0.026,0.07,0.14,0.25,0.38,0.50,0.58,0.64,0.68,0.70],
    [-6.0,-2.2,-0.7,-0.1,0.04,0.08,0.11,0.13,0.14,0.15], (0.135,0.105), 0.04, 2.3, 35, 1.50,
    [0.0,0.173,0.129,0.073,0.041,0.0,0.0,0.0,0.0,0.0], 8.0, 68, 129.0, 1.4, 25.0,
    "Utilization inflects; still dilutive",
    ["Fleet utilization inflects — daily-active robots climb toward the deployed total, Uber Eats and DoorDash "
     "demand fills the built capacity, and cost-per-delivery falls toward the sub-$1 target so unit economics work. "
     "Revenue reaches about $0.70B by FY35 at a 15% operating margin as the network earns operating leverage on "
     "hardware that is already in the ground.",
     "Growth still outpaces internal funding, so the company raises through the decade and shares drift toward "
     "~129M. The DCF is $2.64 and the expected value $2.24 — both well under spot. The modal outcome validates the "
     "operating model yet leaves the equity worth roughly a third of today's price, because the dilution caps the "
     "per-share value."],
    "A 35% p_fail assumes the operating model works within the decade — supported by the demonstrated +578% revenue growth and the shift to utilization metrics — but still a coin-flip-plus that profitable unit economics arrive before dilution does the damage."),
  "bull": sc(0.17, [0.026,0.09,0.20,0.40,0.65,0.92,1.15,1.32,1.43,1.50],
    [-5.5,-1.8,-0.3,0.05,0.10,0.14,0.16,0.18,0.19,0.20], (0.13,0.10), 0.05, 2.5, 15, 1.50,
    [0.0,0.174,0.104,0.06,0.035,0.0,0.0,0.0,0.0,0.0], 12.0, 40, 108.1, 3.0, 25.0,
    "Delivery automation scales regionally",
    ["Autonomous delivery scales across whole regions — utilization runs high on a much larger fleet, the Magna "
     "manufacturing and Nvidia compute stack drives hardware cost down, and the Uber Eats and DoorDash channels "
     "compound volume. Revenue reaches about $1.50B by FY35 at a 20% operating margin as operating leverage on the "
     "built network finally shows.",
     "Internal cash funds more of the growth, so dilution eases and shares settle near ~108M. The DCF is $18.50 and "
     "the expected value $15.95 — roughly two and a half times spot. This is the first scenario where the value of "
     "the network clearly exceeds the price paid plus the dilution to get there."],
    "A 15% p_fail. Requires utilized-fleet unit economics to turn durably profitable and the deployment to broaden regionally — anchored to the FY26 utilization and cost-per-delivery targets, which would be the first hard evidence the model scales."),
  "ultra_bull": sc(0.08, [0.026,0.11,0.28,0.58,0.95,1.45,1.95,2.35,2.65,2.80],
    [-5.0,-1.3,0.0,0.08,0.14,0.18,0.21,0.22,0.23,0.24], (0.125,0.095), 0.06, 2.7, 8, 1.50,
    [0.0,0.147,0.063,0.064,0.0,0.0,0.0,0.0,0.0,0.0], 16.0, 22, 94.1, 5.6, 25.0,
    "DoorDash-scale delivery network",
    ["Serve becomes a DoorDash-scale autonomous delivery network — on the order of ~7M deliveries per day — the "
     "default last-mile robotics layer for the food and goods platforms. Revenue reaches about $2.80B by FY35 at a "
     "24% operating margin as network density and a first-mover fleet originate genuine scale economies.",
     "Self-funding largely replaces dilution and shares settle near ~94M. The DCF is $75.77 and the expected value "
     "$69.83 — roughly ten times spot. This tail is where the bulk of the weighted value lives, and it depends on "
     "the fleet cornering last-mile delivery before rivals or the platforms' own autonomy close in."],
    "An 8% read. The lowest-probability, highest-payoff outcome: an 8% p_fail and a winner-take-most network result, assuming the first-mover fleet plus Uber/DoorDash demand harden into a scale-economies Power that later entrants cannot match."),
 })
build_young(SPEC)
