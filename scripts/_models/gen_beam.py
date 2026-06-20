#!/usr/bin/env python3
"""BEAM — Beam Therapeutics (NASDAQ) · YOUNG memo intake builder.
Numbers locked via /tmp/young/model.py (model_dcf); prose conviction-neutral.
Finding: weighted $39.38 vs spot $30 = +31.3% — asymmetric, cash-cushioned base-editing."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from gen_young import build_young

def sc(p, rev, opm, wacc, tg, s2c, pf, dist, raises, rprices, dil, fs, tam, comp, hl, narr, pr):
    return dict(p=p, rev=rev, opm=opm, wacc=wacc, tg=tg, s2c=s2c, pf=pf, dist=dist, raises=raises,
                rprices=rprices, dil=dil, fs=fs, tam=tam, comp=comp, hl=hl, narr=narr, pr=pr)

SPEC = dict(
 ticker="BEAM", company="Beam Therapeutics", exch="NASDAQ", spot=30.0,
 cap=3.09, sh=103.0, cash=1.21, net_debt=0.10, last_rev=0.10,
 extras=["$1.21B cash (Q1'26) vs ~$0.10B debt → net cash ~$11.75/share; runway to mid-2029",
         "Pre-product base editing; FY25 collaboration revenue $139.7M; R&D burn ~$400M/yr",
         "risto-cel SCD BLA as early as YE2026; BEAM-302 (AATD) pivotal cohort H2 2026"],
 wl="asymmetrical-moonshots", tier="Med-Low", themes=["precision-medicine-oncology"],
 cq="At ~$30 with ~$11.75/share of net cash, do the de-risked BEAM-302 (AATD) and risto-cel SCD programs make base editing a cheap option, or is clinical failure the likelier outcome?",
 thesis=(
   "Beam is a pre-product, clinical-stage base-editing biotech — it precisely rewrites a single DNA base with no "
   "double-strand cut. Revenue is lumpy collaboration income ($139.7M FY25); the op loss runs ~$400M/yr. The asset "
   "that matters is $1.21B cash (~$11.75/share, runway to mid-2029) plus a pipeline: risto-cel SCD (BLA as early as "
   "YE2026) and BEAM-302, the first in-vivo corrective editor, on an FDA-aligned accelerated path. The DCF asks "
   "whether the leads reach market before dilution erodes the equity. Weighted fair value is $39.38 vs $30 spot, "
   "+31% — asymmetric: the cash raises the floor, the de-risked data builds the right tail, clinical failure is the risk."),
 tam_billion=30, hist_years=[2023, 2024, 2025], hist_rev=[0.028, 0.0635, 0.1397], hist_fleet=[0, 0, 0],
 p3cfg=[("peer_y", 35), ("peer_text", "Commercial biotech op margin ~30-45%"), ("fleet_anchor", 0),
        ("fleet_title", "Product-revenue ramp (log)"), ("fleet_reference", None), ("valn_anchor_y", 5),
        ("valn_anchor_text", "Commercial biotech P/S ~4-6x"),
        ("valn_caption", "Pre-product: the ~$3.1B cap is pipeline value plus a $1.21B cash floor, not revenue."),
        ("tam_title", "$30B genetic-disease therapeutics — BEAM share"),
        ("tam_legend", ["BEAM", "Gene-editing rivals", "Other genetic medicine"])],
 subtitle="FY23-FY25 history + FY26-FY35 scenario projections  ·  fiscal years end Dec 31  ·  Q1'26 (May 2026) release",
 sources="Sources: BEAM FY2025 10-K + Q1'26 10-Q (CIK 1745999), company runway guidance, BEAM-302 AATD Phase 1 data (Mar 2026), risto-cel BEACON (NEJM Apr 2026). Revenue is lumpy collaboration income; product revenue is modeled post-approval. FCF is NOL-shielded pre-tax over the explicit window. TAM: a serviceable slice of genetic-disease therapeutics, ~$30B.",
 ipo="IPO Feb '20", xmin=-6.3,
 points=[[-6.0, 17.0], [-5.0, 80.0], [-4.5, 120.0], [-4.0, 40.0], [-3.0, 30.0], [-2.0, 25.0], [-1.0, 28.0], [-0.4, 36.0], [-0.05, 30.0]],
 wr=[
   ("Ultra Bear 16%", "Leads fail; reverts to the ~$8 cash floor."),
   ("Bear 29%", "Risto-cel ships, slow vs Casgevy; one franchise."),
   ("Base 32%", "Both leads reach market; partial validation."),
   ("Bull 15%", "Both win; in-vivo platform scales to franchises."),
   ("Ultra Bull 8%", "Dominant in-vivo platform; several blockbusters."),
 ],
 pb=[
   ("Cash floor is real", "$1.21B cash (~$11.75/share) and runway to mid-2029 bound the downside — even the ultra-bear expected value is $5.77."),
   ("BEAM-302 is de-risked", "The AATD Phase 1 data showed a working in-vivo corrective edit on the AAT biomarker, with an FDA-aligned accelerated path."),
   ("Two independent shots", "Risto-cel (SCD) and BEAM-302 (AATD) fail or succeed on different biology, so partial success beats an all-or-nothing wipeout."),
   ("No-cut mechanism", "Base editing avoids CRISPR's double-strand cut; Casgevy needs myeloablative chemo and carries a malignancy black-box — a differentiation lane."),
   ("Self-funded to inflection", "Burn is heavy but funded; raises are dilutive, not existential — the risk is clinical, not insolvency."),
 ],
 tr=[
   ("Bull validation", "BEAM-302 pivotal cohort shows durable AAT correction with clean safety; risto-cel BLA accepted and a differentiated SCD launch lands vs Casgevy."),
   ("Bear validation", "BEAM-302 durability fades or an in-vivo LNP safety signal emerges; risto-cel launch stalls against the incumbent; raises come faster and larger than ~$0.95B."),
   ("Reframe needed", "If cash falls toward the floor without a pivotal win, or a platform-wide safety class effect appears, the option re-rates toward the distress case."),
 ],
 gloss=[
   ("base editing", "A precise single-base DNA rewrite that corrects a mutation without cutting both strands, avoiding the genotoxicity of a CRISPR double-strand cut."),
   ("risto-cel / BEAM-101", "Beam's ex-vivo base-editing therapy for sickle cell disease; durably induces protective fetal hemoglobin; BLA possible as early as YE2026."),
   ("BEAM-302", "An in-vivo LNP base editor for AATD that corrects the PiZ→PiM mutation — the first in-vivo corrective editor and the biggest swing factor."),
   ("AATD", "Alpha-1 antitrypsin deficiency — a genetic disorder; the AAT protein level is the FDA-accepted accelerated-approval biomarker."),
   ("Casgevy", "The Vertex/CRISPR Therapeutics approved SCD therapy — the incumbent — burdened by myeloablative chemo conditioning and a malignancy black-box warning."),
   ("p_fail", "Modeled probability the scenario's programs fail to reach commercial value — the clinical/regulatory risk weight, high for a pre-product editing platform."),
 ],
 competitive=dict(
   arena="In-vivo and ex-vivo gene editing for genetic disease, where Beam competes with Vertex/CRISPR, Intellia, CRISPR Therapeutics, and Editas.",
   powers=[
     ("scale_economies", 1, "Manufacturing and trial scale matter, but Beam is pre-product and sub-scale versus the SCD incumbent today."),
     ("network_economies", 0, "No network effect in therapeutics; demand does not compound with an installed base."),
     ("counter_positioning", 2, "No-cut base editing is positioned against CRISPR's genotoxic double-strand cut; incumbents cannot easily abandon their cutting approach."),
     ("switching_costs", 1, "One-time curative dosing creates patient lock-in per franchise, but does not bind the next indication or prescriber."),
     ("branding", 1, "NEJM data and platform reputation help, but prescribing follows clinical evidence, not brand."),
     ("cornered_resource", 2, "Foundational base-editing IP and the in-vivo LNP delivery toolkit are the resource Beam is trying to corner."),
     ("process_power", 2, "A repeatable single-base correction process across targets is the Power being originated — unproven until durability replicates."),
   ],
   dom="cornered_resource", window="open",
   rivals=[
     ("Vertex / CRISPR Therapeutics", "public", "Casgevy: approved SCD incumbent, chemo conditioning, slow uptake", 0.60, 0.35, "Well-capitalized, marketed product"),
     ("Intellia / NTLA", "public", "In-vivo CRISPR editor; direct competitor for the in-vivo category", 0.15, 0.25, "Funded, clinical-stage"),
     ("CRISPR Therapeutics / CRSP", "public", "CRISPR platform breadth beyond Casgevy across multiple indications", 0.10, 0.15, "Strong balance sheet"),
     ("Editas", "public", "Gene-editing peer, repositioning; smaller and earlier", 0.05, 0.05, "Smaller cap, clinical-stage"),
   ],
   lead_lag=[
     ("In-vivo corrective editing", "First in-vivo corrective Phase 1 readout (BEAM-302)", "Intellia in-vivo programs", "leading"),
     ("SCD commercialization", "BLA-stage, not yet launched", "Vertex/CRISPR (Casgevy approved)", "lagging"),
     ("Editing precision / safety", "No double-strand cut, durable HbF induction", "CRISPR cut-based platforms", "leading"),
   ],
   take=(
     "Beam is trying to originate a cornered-resource and process Power in precise in-vivo editing — foundational "
     "base-editing IP plus a repeatable LNP correction process that, if it replicates, turns each genetic target "
     "into a shot on goal. The window is open: no rival has shown a durable in-vivo corrective edit. The falsifier "
     "the bull must clear is concrete — BEAM-302 must show durable AAT correction with a clean in-vivo safety "
     "profile, and risto-cel must launch differentiated against Casgevy. Without durability the resource is not yet cornered."),
 ),
 scn={
  "ultra_bear": sc(0.16, [0.12,0.13,0.14,0.15,0.16,0.17,0.18,0.19,0.20,0.21],
    [-3.6,-3.2,-2.6,-2.0,-1.5,-1.1,-0.8,-0.5,-0.3,-0.15], (0.135,0.11), 0.03, 1.5, 80, 8.0,
    [0.0,0.0,0.30,0.35,0.30,0.20,0.10,0.0,0.0,0.0], 16.0, 76, 181, 0.70, 18.0,
    "Leads fail; cash floor holds",
    ["The lead programs fail in pivotal trials or a serious safety signal halts the in-vivo platform. FY35 product "
     "revenue is just $0.21B at a −15% op margin; p_fail is 80%. The company burns down toward its cash, and the "
     "going-concern value collapses to the operating business.",
     "The standalone DCF is −$3.15/share, but the expected value is $5.77 because the rich $1.21B cash translates "
     "into an ~$8.00 distress floor — the cushion, not the pipeline, is what the holder recovers. This is the "
     "structural reason the downside is bounded rather than zero."],
    "High clinical risk is real for a pre-product editing platform — in-vivo LNP safety and BEAM-302 durability "
    "are unproven. Weighted at 16%: a credible but not modal path, given two independent lead programs and a deep early pipeline."),
  "bear": sc(0.29, [0.12,0.14,0.17,0.24,0.36,0.48,0.58,0.65,0.70,0.74],
    [-3.4,-2.9,-2.2,-1.3,-0.5,0.0,0.14,0.22,0.27,0.30], (0.125,0.105), 0.035, 1.6, 55, 8.0,
    [0.0,0.0,0.30,0.30,0.20,0.10,0.0,0.0,0.0,0.0], 22.0, 40, 144, 2.47, 18.0,
    "One franchise; slow vs Casgevy",
    ["Risto-cel reaches the SCD market but uptake is slow against an already-approved incumbent, and the in-vivo "
     "programs disappoint. FY35 product revenue is $0.74B at a 30% op margin; p_fail is 55%. A single franchise "
     "carries the company.",
     "Reaching market requires ~$0.9B of dilutive raises before revenue scales, capping the equity return. The DCF "
     "is $6.04/share and the expected value $7.12 — better than the cash floor, but the platform thesis is unproven "
     "and the upside is one product deep."],
    "Weighted at 29%: partial success is plausible given risto-cel's durable fetal-hemoglobin data and NEJM "
    "publication, but slow launch economics against Casgevy and stalled in-vivo programs keep this a meaningful, near-modal outcome."),
  "base": sc(0.32, [0.12,0.15,0.20,0.32,0.55,0.85,1.10,1.30,1.42,1.50],
    [-3.5,-3.0,-2.2,-1.0,-0.2,0.16,0.28,0.34,0.37,0.40], (0.115,0.10), 0.04, 1.8, 35, 8.0,
    [0.0,0.0,0.30,0.35,0.20,0.10,0.0,0.0,0.0,0.0], 31.0, 30, 134, 5.0, 18.0,
    "Both leads ship; partial validation",
    ["Risto-cel and BEAM-302 (AATD) both reach market, partially validating in-vivo base editing. FY35 product "
     "revenue is $1.50B at a 40% op margin; p_fail is 35%. The AATD accelerated-approval path on the AAT biomarker "
     "pays off, and a second modality proves the platform travels.",
     "About $0.95B of pre-product raises land before revenue inflects around 2031, diluting the path but funding it "
     "through commercialization. The DCF is $27.46/share and the expected value $20.65 — the modal case sits near, "
     "then below, spot, so the value lives in the tails."],
    "Weighted at 32% — the modal outcome. It needs two independent programs to clear pivotal data and the first "
    "in-vivo corrective editor to commercialize, both plausible after the BEAM-302 Phase 1 readout but each individually uncertain."),
  "bull": sc(0.15, [0.12,0.16,0.26,0.50,0.95,1.45,1.95,2.30,2.50,2.60],
    [-3.3,-2.6,-1.6,-0.4,0.10,0.25,0.33,0.38,0.41,0.43], (0.11,0.095), 0.05, 2.0, 18, 8.0,
    [0.0,0.0,0.25,0.30,0.25,0.0,0.0,0.0,0.0,0.0], 40.0, 19, 123, 8.67, 18.0,
    "Both win; platform scales",
    ["Both lead programs succeed and the in-vivo LNP platform scales into multiple franchises beyond AATD — GSD1a "
     "(BEAM-301), PKU (BEAM-304), and partnered cardio programs. FY35 product revenue is $2.60B at a 43% op margin; "
     "p_fail drops to 18% as the platform de-risks across targets.",
     "Demonstrated durability and a clean safety profile turn each new target into a repeatable shot rather than a "
     "one-off bet. The DCF is $85.37/share and the expected value $71.44 — this is where the editing-platform "
     "optionality starts to dominate the weighted value."],
    "Weighted at 15%: requires the platform to generalize across several in-vivo targets with durable correction "
    "and acceptable safety. A real path given the corrective mechanism and Pfizer/Lilly/Apellis partners, but it asks for sustained multi-program execution."),
  "ultra_bull": sc(0.08, [0.12,0.18,0.32,0.65,1.25,2.05,2.95,3.65,3.95,4.10],
    [-3.0,-2.0,-0.8,0.0,0.18,0.30,0.38,0.42,0.44,0.46], (0.105,0.09), 0.06, 2.2, 8, 8.0,
    [0.0,0.0,0.20,0.0,0.0,0.0,0.0,0.0,0.0,0.0], 40.0, 5, 108, 13.67, 18.0,
    "Dominant platform; blockbusters",
    ["Base editing becomes the dominant in-vivo gene-editing modality, with several blockbuster franchises across "
     "genetic disease. FY35 product revenue is $4.10B at a 46% op margin; p_fail is 8% as the platform proves "
     "broadly safe and durable, and the precise no-cut mechanism becomes the standard.",
     "At this scale the company is a platform, not a product — repeatable single-base correction across a large "
     "target set with strong margins. The DCF is $258.43/share and the expected value $238.40, the franchise-platform "
     "tail that makes the overall distribution asymmetric-positive."],
    "Weighted at 8%: the low-probability, high-magnitude outcome requiring base editing to win the in-vivo category "
    "outright over CRISPR-based rivals. Bounded by competition and the long durability record a category standard demands."),
 })
build_young(SPEC)
