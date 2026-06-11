# CLAUDE.md — operating guide for ar2eb

Context for any Claude session on this repo. Threads here hit length limits and
get restarted often, so the durable context lives in the repo, not the thread:
this file + `spec/memo-spec__v023__2026-05-23_21-30.md` (the methodology spec,
changelog-driven — currently at logical **v033**) are the source of truth.

## What this is

`ar2eb` generates single-investor **investment memos**: 5–6 landscape pages per
ticker, authored as `data/<ticker>.yml`, rendered through a JSX → Playwright
(headless Chromium) print harness that produces **both** the website and the PDF
from one component set. Live at **ar2eb.com**.

- **Source of truth:** `data/<ticker>.yml` (one file per ticker).
- **Layout source of truth:** `public/memo_pdf.jsx` (one ~3,500-line file; page +
  chart components, dispatch on `dcf_type`).
- **Methodology source of truth:** the `spec/memo-spec__*.md` (read it before
  changing how memos are built; update its changelog when you change the product).

Four archetypes (`dcf_type`): `young_company` (Damodaran), `mature_company`,
`mature_company_sotp`, `private_prevaluation`. Page 4 is the **competitive
landscape** (§6d, Helmer's 7 Powers; gated on a `competitive:` block).

## Build / run (verified working in the web environment)

One-time toolchain (the container ships Chromium 1194 at `/opt/pw-browsers/`):
```
npm install                  # esbuild + react (for the bundle)
pip install playwright       # python playwright (Chromium binary already present)
```
Pipeline (in order):
```
python scripts/validate.py [<ticker>...]        # Math QC; ERROR fails, WARN informs
python scripts/build_site_data.py               # data/*.yml → public/data.js
node build.js                                    # esbuild → public/assets/bundle/{site,print}.js
python scripts/render_memo_pdf.py <ticker>       # → out/<ticker>-memo__*.pdf
python scripts/rebuild_all.py [--strict-layout]  # bump-aware full rebuild → public/memos/
```
- **After editing `public/memo_pdf.jsx`, run `node build.js` before rendering** —
  the harness loads the pre-compiled bundle, not the raw JSX. (Babel-in-browser
  was retired; see spec §5.)
- Always render with `STRICT_LAYOUT=1` before merging (fails on page overflow /
  footer-band intrusion). `MEMO_FORCE=1` overwrites committed PDFs in place.
- New PDFs are immutable per stamp version — bump via `scripts/bump_pdf_version.py`.

## How to frame decisions for me (Arthur's standing preference)

Present decisions as a **table** so I can approve in bulk. Columns:
`# | Question | Recommendation | Confidence | Rationale`.
- If every row is high-confidence, drop the Confidence column and say
  "Confidence: high across the table."
- Low-confidence recommendations are fine and **preferred over declining to
  recommend** — just label them (e.g. "Low — depends on X").
- I'll reply `go` (adopt all), `go on rows 1 and 3`, or `go but swap row 2`.
- **Use the table even for a single decision.** Always make an actual
  recommendation — don't just present options.

## Working style

- Work in **large autonomous chunks**; pause only on genuine decisions. Surface
  critical questions; make the call on minor ones.
- Commit at clean, working checkpoints (the branch should never be left broken).
- **Conviction-neutrality (spec §3.5 B):** analysis is fundamentals-only. My
  conviction ranking never feeds the central question, scenario probabilities, or
  the headline expected value — that lives only in §12 position sizing.
- Governing build principle (spec §3.5): all axis limits / page bounds / layout
  containers compute from data; never hardcoded.

## Git & deploy

- **GitHub Flow:** `main` + short-lived feature branches → PR → merge. No
  long-lived dev branch. Repo: `arthurculang/ar2eb`.
- **Deploy:** GitHub Actions (`.github/workflows/pages.yml`) → GitHub Pages,
  custom domain via `public/CNAME` (ar2eb.com). `netlify.toml` deleted (was vestigial).
  **Live host confirmed (2026-05-31):** apex `ar2eb.com` is a *proxied Cloudflare
  CNAME → `arthurculang.github.io`* (GitHub Pages). *History (resolved): host churned
  Cloudflare Worker → Cloudflare Pages → GitHub Pages; the Worker and the Cloudflare
  Pages "ar2eb-site" project are dead/parked — GitHub Pages is the one true deployer.*
- **DNS** is managed at **Cloudflare**. Mail is on **@culang.co**, so `ar2eb.com`
  sends no email. **Anti-spoof lockdown is LIVE (2026-05-31):** null-MX (`0 .`),
  SPF `v=spf1 -all`, DMARC `p=reject; sp=reject; adkim=s; aspf=s`, plus a
  `www → apex` 301 redirect (proxied CNAME + Redirect Rule). Re-enabling mail on
  `ar2eb.com` would require revisiting that DMARC/SPF/MX lockdown first.

## Status / open items

- **DNS housekeeping — DONE (2026-05-31).** `www → apex` 301 redirect live; null-MX +
  SPF `-all` + DMARC `p=reject` live; Cloudflare DNS panel clean. (Posture recorded
  under Git & deploy above.)
- **Competitive page (§6d) — DONE.** Rolled out to all 9 tickers, 6-page PDFs shipped
  to `public/memos/`, `tests/visual_baseline.json` regenerated (9×6), spec Page-4/5
  cross-refs swept. Origination lens: AUR/JOBY/NAUT/IONQ/Anthropic; audit: LTH/ZM/COIN/ISRG.
- **Wave 1 — Batch A DONE (2026-05-31): RKLB, OKLO, ACHR, GRAL, TXG shipped & live.**
  All 6-page, conviction-neutral, §6d competitive page baked in; `visual_baseline.json` now
  **14 tickers / 84 pages** (`--check` clean). The authoring pattern that held: research (web
  subagent) → **model the DCF in python for internal consistency** (a reusable engine —
  `/tmp/model_dcf.py` young + `/tmp/model_mature.py` — reproduces the validator's
  equity-bridge + cash-runway/Gordon math to the cent, killing the AUR sign-flip class) →
  *generate* the intake from locked inputs (no transcription drift) → scaffold → validate →
  render under `STRICT_LAYOUT`. **Page-1 overflow on the 5-scenario layout is prose-driven
  (thesis length) or card-headline-driven, NOT structural** — trim the ticker's own copy to
  ~RKLB length (+10–15px clearance), never the shared layout, so the other tickers stay
  byte-identical and the baseline stays green.
  - **Findings (entry price vs the scenario distribution drives the sign):** RKLB **−63%**,
    OKLO **−53%** (richly-priced pre/early-revenue moonshots; *post-v030 second-act retrofit* —
    were −85%/−64% on the old linear-ultra method, and even a Starlink-style constellation
    (RKLB) / HALEU-fuel-monopoly (OKLO) ultra-bull leaves them deeply negative, because the
    modal base sits 90%+ below spot — the market prices near-certain success); GRAL **+9%**
    (fairly valued — the modal FDA+Medicare
    success ≈ spot, post-NHS-miss; tiny ~43M float amplifies both tails); ACHR **+18%**
    (Joby's eVTOL fundamentals at ~half the price → the 15% cert-success+defense tail goes
    positive-EV, vs Joby −20%); TXG **−49%**.
  - **TXG reclassified young → MATURE (user-approved).** Revenue ~$600M flat-declining,
    cash-generative, net-cash (p_fail≈0), razor/blade consumables, public peer comps → a
    mature-company DCF (Power **Audit** lens, Gordon terminal, no dilution). The mature engine
    is verified against ZM's shipped numbers and is in the toolkit for Batch B.
- **Spec v030 — `ultra_bull` as a Power-gated second-act (DONE; §6c.11.1).** Fixed a structural
  short-vol bias: the ultra-bulls were linear lifts (`base × bigger TAM share`), not exponential
  second acts (AWS/Starlink/NVIDIA-datacenter). New rule: the upper scenarios may carry a
  second-act revenue stream (not in base TAM) + a platform terminal, **gated on the §6d Power
  Origination** (durable Power ≥2 + named falsifier), analog-anchored (sanity-checked vs the
  analog's *realized* financials, not a TAM %). **Retrofitted RKLB + OKLO** (the two where a
  Power is genuinely being originated; ACHR/GRAL are cheap-options, left alone). The `/tmp`
  retrofit scripts (`retrofit_rklb.py`, `retrofit_oklo.py`) patch only `bull`/`ultra_bull` +
  thesis. *Watch-out:* a second-act ultra makes the ultra card / forward-chart taller — re-trim
  Page-1 prose; OKLO lands at −1px (within the 2px STRICT tolerance, passes; chart-bound, not
  prose-trimmable without touching the shared layout).
- **Wave 1 — Batch B (mature) SHIPPED & LIVE (2026-06-03): LULU, ABNB, UBER, YETI, DASH, ILMN.**
  All 6 researched (web subagents) + modeled through the mature engine (preserved in
  `scripts/_models/`, verified vs ZM) + authored via the reusable builder (`gen_b1.py build()`,
  driven by `gen_b2.py`/`gen_b3.py`) → shipped 6-page memos, audit lens. **`visual_baseline.json`
  now 20 tickers / 120 pages (`--check` clean); validator green.** **Findings (same
  entry-price-vs-distribution logic as Batch A —
  beaten-down quality screens cheap, rallied names expensive):** **LULU +65%** (de-rated ~60% to
  ~10× FCF; modal stabilization overshoots the decline the market prices — even a real
  brand-impairment ultra_bear is −34%); **UBER +48%** (~14× EV/FCF; market over-discounts the AV
  threat, but the AV-disruption ultra_bear is −44%); **ABNB +38%** (~15× EV/FCF FCF-machine,
  decelerating but cheap); **YETI +4%** and **DASH −1%** (fair — DASH down 40% but still ~33× FCF
  + SBC dilution offsets 20%+ growth); **ILMN −30%** (rallied ~80% to near highs, priced for a
  re-acceleration the base doesn't deliver — the TXG mirror). **Watchlist:** UBER → `fcf-megacap`;
  ILMN → `fcf-megacap` (debatable vs ++growth); ABNB/DASH/LULU/YETI → `fcf-plus-plus-growth`.
  **Watchlist (shipped):** UBER → `fcf-megacap` (tier-less); ILMN/ABNB/DASH/LULU/YETI →
  `fcf-plus-plus-growth`. *Layout note:* the 5-scenario mature Page 1 lands at −1px clearance
  (within STRICT's 2px tolerance → passes; cards/chart-bound, not prose-trimmable) — acceptable,
  like OKLO. **Wave 1 MERGED to main via PR #22** (2026-06-03): 11 new/retrofit memos (RKLB, OKLO,
  ACHR, GRAL, TXG + the 6 mature) + spec v030, live on ar2eb.com.
- **SHAK — Shake Shack added (2026-06-11; 21st ticker, mature_company, `fcf-plus-plus-growth` /
  `premium-consumer-brands`, tier Med — Arthur to confirm).** Authored via the reusable mature toolkit
  (`gen_shak.py` → `gen_b1.build` → `model_mature` → scaffold → STRICT render); op-margin history GAAP
  from SEC XBRL (CIK 1620533). **Finding: −10%** (weighted $49.2 vs spot $54.70) — *fairly-valued-to-
  modestly-rich*: down ~55% YoY to ~13× EV/EBITDA after the Jun-2026 guide cut, net cash (p_fail≈0), but
  thin **capital-intensive FCF** (~4% margin, capex ~11–12% funding a 4× unit runway) caps even the modal
  case at ~fair (−9%); upside needs a Lynch-driven FCF inflection (bull +56%, ultra-bull +121%) vs a
  capital-intensity bear (−54%). The ILMN/TXG "de-rated but not cheap" family. 6pp (no POCD yet);
  `visual_baseline.json` **now 21 tickers**; `--check` clean; validator green. *Layout note:* page-1 5-scenario
  overflow was the usual prose-driven trim (thesis/CQ/extras → ~LULU length), never the shared layout.
- **Arthur Indicator — AI 1.0 LIVE, AI 2.0 DRAFT (2026-06-04; spec §13).** Lightweight
  valuation-efficiency *screen* complementing the DCF: `AI_1.0 = EV/(Rev×(GM+RevGrowth))` — "am I
  paying a fair price for the *quality* of this business?" (product-economics EV/Rev ÷ gross-margin
  Rule-of-40). Zones (META-anchored): green <6 buy · fair ~6–15 · red >15. `scripts/arthur_indicator.py`
  (snapshot: LULU 1.95 cheapest → IONQ 154 / RKLB 197 richest) + `scripts/arthur_indicator_history.py`
  (sourced 2016–2025 small-multiples — META 2022=3.1, NVDA FY23 31→FY25 12, LULU 3.0, ISRG ~15–25).
  Cross-validates the DCF (agree at extremes; **divergences are the signal** — TXG/ILMN screen "fair"
  on GM+growth but DCF-negative, GM-flattered + decelerating). **AI 2.0** (adds op/FCF-margin + Δ
  rate-of-change terms, weights `w1…w8`) captured from `AI.pdf`; **backtested on a sourced 104-name
  universe (v035) — does NOT calibrate; no enrichment beats AI 1.0 out-of-sample (see next bullet).
  AI 1.0 itself is now OOS-validated on the broad universe.** N/A for pre-revenue / gross-loss names
  (the young DCF's domain).
- **AI 2.0 backtest — DONE (2026-06-05, branch `claude/ecstatic-newton-YKOJJ`, spec v034→v035): AI 2.0
  does NOT calibrate; AI 1.0 *validated* out-of-sample.** Sourced the panel end-to-end (SEC XBRL + Yahoo
  FYE prices). A cap **sanity-gate** caught + fixed two `source_ai2_panel.py` bugs (both self-tested):
  (i) Yahoo's `quote.close` is split-adjusted *not* raw → rebuilt the unadjusted close from the split
  events (NVDA FY2024 $152B→$1526B); (ii) dual-class names expose no consolidated share count in
  companyfacts → weighted-avg-share fallback (META 0 caps → $1.48T). **v034 (26 names):** 8-weight fit
  overfits (LOYO-OOS −0.063/−0.068, sign-flipping); regularized `ai2_backtest.py` (nested ladder + Δ≥0
  sampler + ridge + 1-param `--fcfm` + exhaustive `--grid`) → only AI 1.0 + an FCF-margin term beat AI 1.0
  OOS at both horizons, but modest/1y-concentrated, flagged as possibly small-sample. **v035 (expanded → 104
  in-domain tickers, winners+busts; CIKs ticker-verified vs `data.sec.gov/submissions`; ~85 names/cross-section,
  ~1000 rows/97 tickers all-8 features): the FCF-margin signal does NOT survive — NO enrichment (fcfm/opm/any
  Δ/full-8) beats AI 1.0 OOS at both horizons (L3 fcfm → −0.041/3y); the 26-name win was a small-sample
  artifact. A belt-and-suspenders exhaustive `--grid` (15,625 fixed combos, no sampler) confirms it: ~2,500
  beat AI 1.0 in-sample with backwards (negative-margin) weights, but nested OOS the best wins only 3y
  (+0.084)/loses 1y (+0.032) — the sampler missed nothing.** Conversely **AI 1.0
  (gm+growth) is validated: OOS +0.044/3y, +0.063/1y on the broad universe** (narrow-panel 3y was ≈0).
  AI 1.0 (`scripts/arthur_indicator.py`) stays the live screen — now with broad-universe OOS support;
  AI 2.0 earns none of its 8 weights. *Data limit (documented):* ~14 compounders (ORCL/V/MA/INTU/CDNS/TMO/
  SBUX…) stopped tagging consolidated gross profit in companyfacts post-2018 → partly drop; faking a margin
  would break conviction-neutrality. **MERGED to main via PR #24 (2026-06-06): v032 + v033 (POCD) + v034 +
  v035 + the AI 2.0 tooling (harness `--select`/`--fcfm`/`--grid`, sourcing script, 104-name panel). AI 1.0
  (`scripts/arthur_indicator.py`) stays the live screen.**
- **Website rendering-parity — DONE (2026-06-04, merged to main).** (1) Embedded site memo now renders
  the §6d competitive page (`EmbeddedMemo` had mounted only 5 of 6 page components; PDF showed 6) — JS
  sizes the wrap height so 5- and 6-page memos both fit. (2) Site memo re-creates the `.memo-page` print
  box (1in/0.55in white frame + white card + beige inter-page gap); that box lived only in `print.html`,
  so the site had been butting black text against the white edge. PDF untouched.
- **Chart label clipping — Page-1 forward chart FIXED (landed 2026-06-07, salvage merge of
  `focused-ramanujan`); other charts TRACKED.** Root cause: in a viewBox'd `<svg>`, a `pt` font-size
  resolves to px (×96/72) and that px value is treated as *user units*, so every `pt` chart font renders
  **1.333× larger** than its number in the plot's coordinate system; the forward chart's hardcoded right
  margin (`widthPt−60`) clipped the right-edge series labels + title on every ticker. **Fix:**
  `estSvgTextWidth()` + a baked Inter-SemiBold em-table in `memo_pdf.jsx` (folds in the 1.333×; ignores
  kerning → safe upper bound); `ForwardValueChart` sizes its right margin to the widest end label (floored
  at 60 so short-label charts stay byte-identical) and compresses the title via `textLength` only on
  overflow. A **WARN-ONLY horizontal-clip guard** is in `render_memo_pdf.py` (flags chart `<text>` past its
  SVG viewBox; **promote to STRICT once the tracked items clear**). **TRACKED (pre-existing, unfixed — fix
  by sizing each margin from data via `estSvgTextWidth`):** (a) young-company **valuation caption** overflow
  (OKLO ~+138px in a 280 box; ACHR/GRAL similar — needs wrap or YAML trim); (b) GRAL **TAM `$70B` bar
  labels** + young TAM title poke right; (c) mature **equity-build** (`UltBear/UltBull`) + **FCF** axis
  labels poke left ~3–5px; (d) forward-chart **`-5y` x-tick** drawn off-plot on recent IPOs (OKLO/GRAL —
  filter xTicks to `t ≥ X_MIN`). *(The branch also tracked IONQ page-6 vertical overflow — already fixed
  by #27's trigger drop.)*
- **Spec §12 portfolio construction** — draft; **§15 (v036) operationalizes it** as a deterministic
  auto-weighting rule (decision D1 — rec: EV-tilted with caps) feeding the monthly rebuild.
- **POCD underwriting lens (§14) — People-leg foundation BUILT (v036).** Framework: Ackman's *underwrite
  SpaceX like any venture investment* applied across the **whole** book via **People · Opportunity · Context ·
  Deal** (origin **Sahlman / HBS**, building on Poorvu & Stevenson; Ackman cited, didn't originate). O/C/D
  already map onto §6c/§6d/§13/§12; the build item was **People**. **Shipped:** a `pocd:` YAML schema
  (observable People inputs — realized capital-allocation track record, insider ownership, incentive
  alignment, governance flags, key-person risk, 1–5 score, takeaway) + a `validate.py` hook (`_pocd_warnings`,
  WARN-only, gated, with a **conviction-neutrality guard** rejecting belief/preference fields — §3.5 B:
  observable only, never "I believe in the founder"). **Rendered back-matter scorecard page BUILT + rolled
  out to 9 tickers** (founder-led RKLB/COIN/ABNB/ZM/DASH + mature UBER/ISRG/LULU/ILMN; 7pp each,
  STRICT_LAYOUT clean, observable/sourced People data, baselines green; observable scores discriminate —
  ILMN 2 post-GRAIL → ISRG/UBER/RKLB/ABNB/ZM 4). `PagePOCD` in `memo_pdf.jsx` (+ site parity in `pages.jsx`),
  gated on a `pocd:` block, placed last so it never renumbers existing pages. Extend to more tickers as People data is sourced.
- **Spec §15 (v036, DRAFT) — operating cadence & automation + 1 July 2026 "launch" (Arthur's ask).**
  **Monthly (22nd):** archive prior month → mechanically re-price + re-render all memos → update §12 weights →
  deploy. **Daily (after close):** track the weighted portfolio vs. a wide multi-asset benchmark set
  (VT · SPY/QQQ/IWM · EFA/EEM · AGG · SHY/IEF/TLT · TIP · BIL · GLD · DBC · VNQ · opt. BTC). **Mechanism
  (v037 re-platform): Claude Code Routines (cloud), NOT GitHub Actions and NOT `/loop`** — per Arthur's
  "max Claude, min GitHub" preference. Routines (`claude.ai/code/routines`) are native cron triggers that run
  unattended on Anthropic's cloud (no machine, no live session; `/loop` can't — session-scoped, 7-day expiry).
  **The win:** Routines run on the Claude **subscription**, so the two old owner chores EVAPORATE — no
  `ANTHROPIC_API_KEY` repo secret and no "Actions → Read and write" toggle (the Routine commits via its own
  GitHub connection). **Launch = "start fresh":** hide all pre-launch memos from public view (internal archive,
  unlinked), publish the first official set, begin performance tracking from t₀ (1 Jul 2026). **Decisions adopted
  2026-06-06 ("go on all"):** D1 EV-tilted caps · D2 monthly = AGENTIC · D3 truly-private archive · D4 benchmark
  sleeve. **BUILT:** `portfolio/build_weights.py` + `weights.yml` (10 tradeable holdings, EV-tilted, private/
  anthropic excluded), `portfolio/track_performance.py` (validated live). Execution = **two Routines** —
  *ar2eb daily performance* (thin/Haiku, `0 22 * * 1-5`, just runs the script + commits) and *ar2eb monthly
  rebuild* (agentic/Opus, `0 13 22 * *`, opens a PR) — defined in the copy-paste runbook **`portfolio/ROUTINES.md`**
  (the two `.github/workflows/*.yml` jobs were DELETED in the re-platform; `pages.yml` stays). **Routines
  CREATED by Arthur (2026-06-07) — owner setup DONE**; `ROUTINES.md` stays the reference config (edit in the
  UI → mirror there). **Launch tooling (D3) BUILT (v038, 2026-06-11): `scripts/launch_archive.py` + root
  `LAUNCH.md`.** Design fact that shaped it: the site renders a "Prior versions (N)" panel from
  `stamp.prior_versions` and 41 PDF versions have accumulated in `public/memos/` — so "hide pre-launch memos"
  = clear every `prior_versions` block + remove ALL accumulated PDFs, not just swap the current set.
  `--export` = safe gitignored snapshot (`archive-export/`, MANIFEST w/ sha256s) for the private repo;
  `--flip --yes` = guarded start-fresh (stamps → v+1 @ one shared launch timestamp, history cleared, 41 PDFs
  rm'd, STRICT re-render + baseline regen, staged-not-committed; mechanical only — optional re-price happens
  BEFORE it per LAUNCH.md). Stamp transform self-tested green on all 20 live YMLs; export exercised for real;
  flip verified dry-run-safe. *D3 facts (verified 2026-06-07): repo is PUBLIC → truly-private = separate
  PRIVATE repo `ar2eb-archive` (owner creates, ~1 min; Claude's GitHub scope is ar2eb-only — launch session
  can `add_repo` it); pre-launch memos stay in public git history regardless (no rewrite — decided).*
  **Remaining: owner creates `ar2eb-archive` (any time) + the 1-July day-of run (LAUNCH.md).** Live epoch
  t₀ = 2026-07-01 (the daily routine no-ops until then). *(POCD scorecard page §14 is DONE — 9 tickers.)*
- **Cleanup backlog (recorded 2026-06-07; updated 2026-06-10 — owner actions; Claude gets 403 on remote
  branch deletion).** (1) **Safe deletes:** the dead probe `claude/_probe-workflows`; all merged `claude/*`
  branches (`git branch -r --merged origin/main` is authoritative); `claude/ionq-ultra-bull-pressure-test-6GEnv`
  (landed via the #21 squash — `git cherry` shows its patch in main); and — **NEW (landed via #33, 2026-06-10)** —
  the three salvaged branches `claude/focused-ramanujan-RK6qV` (forward-chart clip fix), `claude/happy-wozniak-S2CTV`
  (About wording), `claude/pensive-franklin-DEtCF` (hero logo), now contained in main. (2) **Still to triage:**
  `claude/sweet-noether-80vbp` (IONQ page-6 trim) looks superseded by #27's trigger-drop fix — verify, then
  delete. No open PRs exist for any of these (checked 2026-06-10).
