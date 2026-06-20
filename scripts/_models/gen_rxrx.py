#!/usr/bin/env python3
"""RXRX — Recursion Pharmaceuticals (NASDAQ) · YOUNG memo intake builder.
Numbers locked via /tmp/young/model.py (model_dcf); prose conviction-neutral.
Finding: weighted $3.85 vs spot $3.15 = +22.3% — tail-driven AI-discovery moonshot."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from gen_young import build_young

def sc(p, rev, opm, wacc, tg, s2c, pf, dist, raises, rprices, dil, fs, tam, comp, hl, narr, pr):
    return dict(p=p, rev=rev, opm=opm, wacc=wacc, tg=tg, s2c=s2c, pf=pf, dist=dist, raises=raises,
                rprices=rprices, dil=dil, fs=fs, tam=tam, comp=comp, hl=hl, narr=narr, pr=pr)

SPEC = dict(
 ticker="RXRX", company="Recursion Pharmaceuticals", exch="NASDAQ", spot=3.15,
 cap=1.61, sh=510.0, cash=0.665, net_debt=0.0, last_rev=0.075,
 extras=["$0.665B cash (Q1'26); runway into early 2028; burn ~$340M/yr",
         "FY25 revenue $74.7M (+27%) — all collaboration/milestone, no product sales",
         "Down ~37% YTD to ~$3.15; ~510M shares post-Exscientia merger + ATM"],
 wl="asymmetrical-moonshots", tier="Low", themes=["precision-medicine-oncology"],
 cq="At a ~37%-de-rated $3.15 with ~$1.3/share of net cash, is RXRX a cheap option on AI-drug-discovery validation, or a platform that funds itself toward dilutive stagnation?",
 thesis=(
   "Recursion runs an AI-drug-discovery platform — automated wet-lab Phenomaps plus an NVIDIA supercomputer — that "
   "maps cellular phenotypes to find drug candidates. After the Exscientia merger doubled the share count, it trades "
   "at $3.15 (~$1.6B cap), down ~37% YTD, on FY25 revenue of $74.7M that is entirely collaboration income — no "
   "approved drug. Funded into early 2028, the near-term risk is dilution, not insolvency. The DCF asks whether the "
   "platform ever yields an economically-meaningful approved drug. Weighted fair value is $3.85, +22% above spot — "
   "but the modal base sits below the price, so the answer rides the right tail."),
 tam_billion=50, hist_years=[2023, 2024, 2025], hist_rev=[0.045, 0.0588, 0.0747], hist_fleet=[0, 0, 0],
 p3cfg=[("peer_y", 25), ("peer_text", "Profitable biopharma op margin ~25-35%"), ("fleet_anchor", 0),
        ("fleet_title", "Revenue ramp (log)"), ("fleet_reference", None), ("valn_anchor_y", 5),
        ("valn_anchor_text", "Mature biopharma P/S ~4-6x"),
        ("valn_caption", "At ~21x sales on milestone-only revenue, the price is platform optionality, not fundamentals."),
        ("tam_title", "$50B AI-enabled drug-discovery value — RXRX share"),
        ("tam_legend", ["RXRX", "Competitors", "Other AI-bio / pharma R&D"])],
 subtitle="FY23-FY25 history + FY26-FY35 scenario projections  ·  fiscal years end Dec 31  ·  Q1'26 (May 2026) release",
 sources="Sources: RXRX FY2025 results + Q1'26 8-K (CIK 1601830), company runway/burn guidance. Revenue is collaboration/milestone income (no product sales). FCF is NOL-shielded pre-tax over the explicit window (documented simplification). TAM: a serviceable slice of AI-enabled drug-discovery value, ~$50B.",
 ipo="IPO Apr '21", xmin=-5.2,
 points=[[-5.0, 18.0], [-4.5, 12.0], [-4.0, 7.0], [-3.0, 9.0], [-2.5, 15.0], [-2.0, 8.0], [-1.0, 6.0], [-0.5, 5.0], [-0.05, 3.15]],
 wr=[
   ("Ultra Bear 15%", "Platform never delivers; milestone-only revenue, heavy dilution toward the cash floor."),
   ("Bear 30%", "One or two small partnered wins; revenue stays sub-scale and dilution offsets it."),
   ("Base 32%", "Modest validation — a few wins plus broader partnerships; ~$0.9B revenue, still dilutive."),
   ("Bull 15%", "AI discovery becomes a real engine — multiple approvals, royalty and licensing income."),
   ("Ultra Bull 8%", "Recursion OS becomes a dominant tech-bio platform; a pharma-scale outcome."),
 ],
 pb=[
   ("Cash cushion is real", "~$1.3/share of net cash and runway to early 2028 mean the near-term risk is dilution, not insolvency — the floor is firm."),
   ("Three pharma partners paying", "Roche/Genentech ($213M received), Sanofi ($134M, fifth milestone Feb 2026) and Bayer validate that pharma will pay for the platform."),
   ("De-rated price, fat right tail", "Down ~37% YTD, the equity is a cheap option — ~88% of the expected value sits in the bull and ultra-bull, priced lightly."),
   ("Compute-scale advantage", "BioHive-2 plus automated Phenomaps generate proprietary phenotypic data at a scale rivals cannot easily match — the raw material of a cornered resource."),
   ("Milestones could self-fund", "If readouts hit, milestone and royalty income reduce future raises, shrinking the dilution that drags the base and bear."),
 ],
 tr=[
   ("Bull validation", "REC-617 combo data (1H27) and REC-4881 registrational path (2H26) read out positive; new or expanded pharma deals with upfront and royalty terms; raises shrink as milestones fund spend."),
   ("Bear validation", "Pipeline readouts slip or disappoint; milestone revenue stays lumpy (Q1'26 was only $6.5M); an equity raise on weak terms confirms dilutive stagnation; partners do not expand."),
   ("Reframe needed", "A drug actually reaches approval and royalty economics, shifting the story from option-on-platform to cash-flow; or a partner walks and the platform thesis breaks."),
 ],
 gloss=[
   ("Recursion OS", "Recursion's integrated platform — automated wet-lab biology plus AI/supercomputing — for finding and advancing drug candidates."),
   ("Phenomap", "A large map of how cells change appearance (phenotype) under genetic or chemical perturbations, used to spot disease-relevant drug effects."),
   ("Milestone / collaboration revenue", "Payments from pharma partners (Roche, Sanofi, Bayer) for upfronts and progress, not from selling an approved product — RXRX's only revenue today."),
   ("p_fail", "The modeled probability the scenario ends in failure (no economically-meaningful drug), driving the equity toward the distress floor."),
   ("Sales-to-capital (s2c)", "How much new revenue each dollar of reinvested capital produces; sets how fast revenue can grow before fresh capital is needed."),
   ("Distress floor", "The ~$0.80/share residual value (cash and salvage) the equity defaults to in a failure outcome, setting a floor under the expected value."),
 ],
 competitive=dict(
   arena="AI-driven drug discovery — turning proprietary biological data into approved drugs — where RXRX competes with private AI-bio labs, one public peer, and big-pharma in-house AI.",
   powers=[
     ("scale_economies", 1, "Compute and wet-lab automation scale, but no fixed-cost moat until products generate revenue."),
     ("network_economies", 0, "No two-sided network; more partners help data, but value does not compound across users."),
     ("counter_positioning", 1, "Tech-bio model big pharma is slow to copy, but pharma is building its own AI in parallel."),
     ("switching_costs", 1, "Multi-year collaborations create some stickiness, but partners run several AI vendors at once."),
     ("branding", 0, "No brand power pre-approval; credibility rests on data, not name."),
     ("cornered_resource", 2, "The Phenomap dataset and BioHive-2 are the strongest candidate — proprietary, hard to replicate at scale, but unproven as a drug-output advantage."),
     ("process_power", 1, "Integrated discovery workflow is distinctive but not yet shown to produce approved drugs repeatably."),
   ],
   dom="cornered_resource", window="open",
   rivals=[
     ("Insilico Medicine", "private", "Generative-AI discovery, clinical-stage pipeline; well-funded private rival", 0.0, 0.0, "Private (VC-backed)"),
     ("Isomorphic Labs", "private", "Alphabet/DeepMind spinout; AlphaFold lineage and deep capital", 0.0, 0.0, "Alphabet-funded"),
     ("Schrodinger", "public", "Physics-based computational platform plus owned pipeline; the listed comp", 0.0, 0.0, "Public equity"),
     ("Big-pharma in-house AI", "incumbent-division", "Roche, Sanofi, Novartis building internal AI — partners and potential substitutes", 0.0, 0.0, "Pharma balance sheets"),
   ],
   lead_lag=[
     ("Approved drugs from AI discovery", "Zero", "Zero (Insilico/Isomorphic/Schrodinger)", "even"),
     ("Proprietary phenotypic data scale", "Industry-leading Phenomap library", "Smaller / model-based", "leading"),
     ("Capital and balance-sheet depth", "~$0.665B cash, dilution-funded", "Deeper (Alphabet, big pharma)", "lagging"),
   ],
   take=(
     "No durable Power is originated yet — like all AI-bio, RXRX has zero approved drugs, so switching costs, "
     "branding and scale economies are still latent. The one candidate is a cornered resource: the Phenomap "
     "dataset and BioHive-2 compute generate proprietary phenotypic data at a scale rivals cannot easily match. "
     "The bet is whether that data-and-Phenomap flywheel converts into repeatable approved drugs before "
     "well-capitalized private labs (Insilico, Isomorphic) or pharma's own AI close the gap. The falsifier the "
     "bull must clear is the 2026-2027 readouts producing real clinical and royalty economics — until a drug "
     "ships, the resource is unproven and the Power window stays open, not won."),
 ),
 scn={
  "ultra_bear": sc(0.15, [0.06,0.07,0.08,0.09,0.10,0.11,0.12,0.13,0.14,0.15],
    [-5.5,-3.8,-2.6,-1.7,-1.1,-0.7,-0.4,-0.2,-0.05,0.03], (0.145,0.115), 0.03, 1.0, 85, 0.80,
    [0.0,0.30,0.30,0.25,0.20,0.10,0.0,0.0,0.0,0.0], 2.5, 90, 970, 0.30, 30.0,
    "Platform never delivers; dilutive grind to the floor",
    ["The Recursion OS produces no approved, economically-meaningful drug. Revenue stays milestone-only and "
     "sub-scale — about $0.15B by FY35 at a 3% operating margin — as partnered programs stall and pharma "
     "interest in the platform fades. The discovery engine is real but never converts into product royalties.",
     "With nothing to fund itself, the company raises roughly $1.15B over the decade, pushing the share count "
     "toward 970M. The DCF lands at −$0.24; the $0.80 distress floor and residual cash drive the expected "
     "value to $0.64. The bet expires worthless except for the balance sheet."],
    "A 15% read. The platform has zero approved drugs and NVIDIA fully exited its equity in Feb 2026 — a "
    "negative external signal. An 85% p_fail reflects that AI-bio has, industry-wide, not yet produced an approved drug."),
  "bear": sc(0.30, [0.08,0.11,0.15,0.20,0.26,0.32,0.38,0.43,0.47,0.50],
    [-5.0,-3.2,-2.0,-1.1,-0.5,-0.05,0.10,0.16,0.20,0.22], (0.14,0.11), 0.035, 1.05, 55, 0.80,
    [0.20,0.30,0.30,0.20,0.10,0.0,0.0,0.0,0.0,0.0], 3.0, 72, 877, 1.0, 30.0,
    "A couple small partnered wins; revenue stays sub-scale",
    ["One or two partnered programs reach approval or meaningful royalty, but the platform never becomes a "
     "self-sustaining engine. Revenue reaches about $0.50B by FY35 at a 22% operating margin — better than "
     "milestone-only, yet far short of the scale needed to justify a platform multiple.",
     "Continued spending forces roughly $1.1B of raises, lifting shares toward 877M and offsetting much of the "
     "operating progress. The DCF is −$0.14 and the expected value $0.38. Real science, but the economics never "
     "outrun the dilution."],
    "A 30% read — the heaviest single weight. Reflects partial platform validation: Roche, Sanofi, and Bayer "
    "deals exist and Sanofi paid a fifth milestone in Feb 2026, but a 55% p_fail captures how rarely partnered candidates clear."),
  "base": sc(0.32, [0.10,0.14,0.20,0.30,0.42,0.55,0.68,0.78,0.85,0.90],
    [-4.2,-2.6,-1.5,-0.75,-0.25,0.06,0.15,0.21,0.25,0.28], (0.135,0.105), 0.04, 1.1, 35, 0.80,
    [0.25,0.35,0.30,0.20,0.10,0.0,0.0,0.0,0.0,0.0], 4.0, 59, 810, 1.8, 30.0,
    "Platform validates modestly; still dilutive",
    ["Recursion OS proves itself in a limited way — a couple of pipeline or royalty wins plus expanding pharma "
     "partnerships. Revenue reaches about $0.90B by FY35 at a 28% operating margin as collaboration income "
     "broadens into early product and royalty streams. The platform earns credibility without becoming dominant.",
     "Growth still outpaces internal funding, so roughly $1.2B is raised and shares drift toward 810M. The DCF "
     "is $0.72 and the expected value $0.75 — both below spot. The modal outcome validates the science yet "
     "leaves the equity worth less than today's price."],
    "A 32% read, the modal case. A 35% p_fail assumes the platform delivers at least modest product or royalty "
    "economics within the decade — consistent with three named pharma partners but no approved drug yet."),
  "bull": sc(0.15, [0.12,0.20,0.32,0.50,0.75,1.05,1.40,1.80,2.15,2.50],
    [-3.5,-1.8,-0.7,-0.05,0.12,0.20,0.26,0.30,0.33,0.35], (0.13,0.10), 0.05, 1.3, 15, 0.80,
    [0.20,0.25,0.25,0.15,0.10,0.0,0.0,0.0,0.0,0.0], 9.0, 21, 616, 5.0, 30.0,
    "AI discovery becomes a real engine",
    ["The platform converts into a genuine discovery engine — multiple approvals across the pipeline (REC-617, "
     "REC-4881, REC-1245 and successors), plus royalty and platform-licensing income. Revenue reaches about "
     "$2.50B by FY35 at a 35% operating margin as the Phenomap flywheel compounds into repeatable output.",
     "Milestones and royalties fund more of the spend, so dilution eases and shares settle near 616M. The DCF is "
     "$7.03 and the expected value $6.10 — more than double spot. This is the first scenario where platform "
     "value clearly exceeds the price paid."],
    "A 15% read. Requires the data flywheel to translate into repeated approvals — a 15% p_fail. Anchored to "
    "the combo and registrational readouts due 2026-2027, which would be the first hard evidence the engine produces drugs."),
  "ultra_bull": sc(0.08, [0.14,0.26,0.46,0.78,1.25,1.95,2.85,3.80,4.55,5.20],
    [-2.8,-1.0,0.0,0.10,0.20,0.27,0.32,0.36,0.38,0.40], (0.125,0.095), 0.06, 1.5, 8, 0.80,
    [0.15,0.20,0.15,0.0,0.0,0.0,0.0,0.0,0.0,0.0], 10.0, 10, 560, 10.4, 30.0,
    "A dominant tech-bio platform",
    ["Recursion OS becomes a dominant tech-bio platform — the standard layer for AI-driven discovery, licensed "
     "broadly and generating a major pharma-scale outcome. Revenue reaches about $5.20B by FY35 at a 40% "
     "operating margin as platform economics, not single drugs, drive the model.",
     "Self-funding largely replaces dilution and the equity compounds toward roughly $19B. The DCF is $33.75 and "
     "the expected value $31.11 — roughly ten times spot. This tail is where the bulk of the weighted value "
     "lives, and it depends on the platform cornering the discovery resource."],
    "An 8% read. The lowest-probability, highest-payoff outcome: an 8% p_fail and a winner-take-most platform "
    "result. It assumes the Phenomap data advantage becomes a durable cornered resource the rest of AI-bio cannot replicate."),
 })
build_young(SPEC)
