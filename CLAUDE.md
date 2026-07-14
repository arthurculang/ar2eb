# CLAUDE.md — operating guide for ar2eb

Context for any Claude session on this repo. Threads here hit length limits and
get restarted often, so the durable context lives in the repo, not the thread:
this file + `spec/memo-spec__v023__2026-05-23_21-30.md` (the methodology spec,
changelog-driven — currently at logical **v045**) are the source of truth.
(The `__v023` filename is a **frozen fossil**; the top of the spec's in-file
changelog is the version of record. There is exactly one spec file — the old
`__v020` was removed 2026-07-05. Renaming to a stable name is open decision #6.)

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

**Clear but minimal — keep the table; plain words in every cell, no padding.**
Each cell needs exactly enough plain words to make the question and the
recommendation clear — no more. The failure to avoid is the *cryptic* cell:
abbreviations, undefined jargon, or `A → B` chains I have to decode. The opposite
failure is a wall of prose. So: plain-language cells, define a term inline only
if it's load-bearing, cut every word that isn't doing work.

Present decisions as a **table** so I can approve in bulk. Columns:
`# | Question | Recommendation | Confidence | Rationale`.
- If every row is high-confidence, drop the Confidence column and say
  "Confidence: high across the table."
- Low-confidence recommendations are fine and **preferred over declining to
  recommend** — just label them (e.g. "Low — depends on X").
- I'll reply `go` (adopt all), `go on rows 1 and 3`, or `go but swap row 2`.
- **Use the table even for a single decision.** Always make an actual
  recommendation — don't just present options.
- **Always frame next steps / open items as a recommendation**, never a neutral
  menu — say what you'd do next and why, even when the final call is mine. A
  labeled low-confidence rec ("Low — your conviction call") beats "here are the
  options." End turns with a recommended next action, not an open question.

## Working style

- Work in **large autonomous chunks**; pause only on genuine decisions. Surface
  critical questions; make the call on minor ones.
- Commit at clean, working checkpoints (the branch should never be left broken).
- **Conviction-neutrality (spec §3.5 B):** analysis is fundamentals-only. My
  conviction ranking never feeds the central question, scenario probabilities, or
  the headline expected value — that lives only in §12 position sizing.
- Governing build principle (spec §3.5): all axis limits / page bounds / layout
  containers compute from data; never hardcoded.
- **The site is EXTERNAL — ar2eb.com is public-facing.** Rendered copy must read
  for an outside reader. **Never expose internal-spec jargon** (`§6d`, `§12`,
  `§16`, `spec §X`, bare section numbers, internal file/anchor names like
  `...-draft`) in anything that renders: the site pages (`pages.jsx`,
  `components.jsx`, `ai2_report.jsx`) or memo fields that show on the page
  (thesis, narratives, takeaways, the POCD O/C/D legs incl. `deal`, `sources`,
  captions). Source-code `//`/`#` comments may keep `§`-refs (not rendered).
  Hold all site/memo prose to a **PhD-level editorial bar** — accurate (e.g. don't
  say "three words" for a three-*idea* tagline), economical, no mixed metaphors.

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

> **Read this header first; everything under "Build log" below is dated history (newest first), not live state.**

### Current state (2026-07-05)
- **LAUNCHED** — ar2eb.com live on the official set (t₀ = 2026-07-01). Both Routines verified live: *daily perf* commits nightly; *monthly rebuild* = the July re-price (PR #78). Site deploy-gated by CI (validate + data.js-in-sync, PR #81).
- **poppler IS installable here** (`apt-get update && apt-get install -y poppler-utils`) — the June "no-poppler → site-only, can't touch the baseline" caveat class is **DEAD**. Every PDF + `visual_baseline.json` was regenerated at the July-1 flip and in each fix wave since; the on-disk set is current. **Ignore the "site-only / poppler caveat" phrasing in the older build-log bullets below.**
- **Memo/ticker count: derive from `ls data/*.yml`** (currently 56 memos) — the TICKERS lists in validate/rebuild_all/visual_hash derive from it (PR #81); never hardcode a count.
- Newest waves: **PR #81** (22-defect full-review fix wave), **Wave B** (TXG second-act re-model → −54.5%; NAUT a16z/dilution flags), **Wave C** (site design system + this restructure).

### Open decisions (awaiting Arthur)
| # | Question | Recommendation |
|---|---|---|
| 1 | Ratify **GROSS total debt** as the single `net_debt_billion` convention book-wide? | **Yes** — 18/21 non-zero memos already gross + the validator equity bridge assumes it. Then normalize the 4 masthead non-conformers (HHH, COIN, +2) + the CROX/LTH dcf_path. |
| 2 | **CROX / LTH dcf_path double-count cash** (net_debt is net but the bridge re-adds cash) — equity overstated ~3% / $0.23B | Fix to gross. CROX finding +56.8% → ~+54%; LTH ~unchanged. A correctness fix that moves CROX's finding — your sign-off. |
| 3 | **BTC discount rate/horizon (30%/7yr)** + **ZRO conviction tier** | The biggest §16 lever; confirm before wiring crypto into the *tracked* book (BTC-USD feed ready). |
| 4 | **NAUT downside is a null partition** — ultra_bear & bear both floor at $0 EV | Collapse to one bear (sub-partition in prose), or model a small survival stub in the bear. |
| 5 | **LULU probability skew** — base (33%) ≈ bear (32%), upside-skewed off a non-modal base | Re-examine the base-rate for a decelerating premium brand; likely raise base toward ~45–50%. |
| 6 | **Spec filename convention** — `__v023` frozen while content is logical v045 | Rename to stable `spec/memo-spec.md`; declare "in-file changelog top = version of record"; cap the in-file changelog at ~5, older → `spec/CHANGELOG.md`. |
| 7 | **Tail-EV companion statistic** (e.g. P(≤spot)) on Page 1 for tail-driven names (NAUT/PACB) | Add to §6b — a required companion line when the top scenario's EV share ≥ ~2.5× its probability. |
| 8 | **SYM as the first POCD "1"** tier | Your call (control entrenchment + a 2024 restatement/material-weakness integrity flag). |

### Authoring gotchas (durable — promoted from scattered batch bullets; do NOT re-derive)
- **Page-1 5-scenario overflow is prose-driven** — trim the ticker's OWN central_question / thesis / scenario-card headlines toward ~RKLB length, never the shared layout. Diagnose by which trim moves the px (STRICT reports the overflow px).
- **`tam_competitor_share` is absolute $B (must be < `tam_billion`), NOT a %** — the GRAL/IONQ/PACB TAM-chart clip class. `validate.py` now WARNs on `≥ tam`.
- **Never write `Capitalizedword: ` in an unquoted YAML value** (the CROX `Bull:` bug → `build_site_data` aborts → renderer runs on stale `data.js`). Build POCD/pocd blocks via `yaml.dump`.
- **Back-matter (Page 6/7) and Page-1 are stretched-row CSS grids** — row height = tallest cell; trim the TALLEST cell in the binding row, not a short one.
- **A mechanical re-price leaves prose STALE** — after any `spot`/`market_cap` change, grep the memo's `thesis` / `weighting_rationale` / `pocd.deal` for hardcoded `$`/`%` and sync them (the recurring "stale thesis vs re-priced finding" bug — hit on PACB #74, TXG Wave B).
- **`final_shares` must reconcile with `shares0 + Σ(raise/price)`** or the validator WARNs — use scalar avg raise-prices and set `final_shares` to the implied diluted count.

### Build log (historical — newest first; superseded phrasing above wins)

- **LAUNCHED 2026-07-02 (t₀ epoch 2026-07-01) + both Routines VERIFIED LIVE.** The 1-July "start fresh" ran a day late, end-to-end from a
  web session — **poppler IS installable in these containers** (`apt-get update && apt-get install -y poppler-utils`), so the "no poppler →
  site-only" caveat class that governed June is dead; PDFs + `visual_baseline.json` are maintainable again. Sequence: (1) **Routines
  root-cause found by Arthur — the repo was never BOUND to either routine** (every daily run Jun-17→30 red-X'd; monthly's Jun-22 ✗; the stale
  pre-v042 prompt was a second, latent bug — also fixed by re-pasting from `ROUTINES.md`). **Daily verified live:** t₀ row committed to main
  (`c40a615`, 2026-07-01 all-zeros baseline); writes nightly from 07-02. **Monthly verified live:** its first real run opened **PR #78
  "Monthly rebuild 2026-07"** — 52 bumps + re-price to the 07-01 close + re-weight (**22 holdings**; GRAL/PACB/NVCR/PRME dropped, upside ≤ 0)
  + two real `bump_pdf_version.py` fixes (single-quoted `date:` leaked quotes into `prior_versions.asOfDate`; inline-empty
  `prior_versions: []` got a duplicate key YAML silently drops) + a CAI page-1 precision fix + 9 judgment flags. **#78 was MERGED as the
  launch re-price** (LAUNCH.md step 1) — the earlier close-unmerged plan was reversed on inspection: the flip erases the extra bump anyway,
  and merging the re-weighted book *before* nonzero perf rows accrue is the clean moment for tracking integrity. (2) `--export` →
  `archive-export/prelaunch-2026-07-02/` (238 files / 44 MB / 56 tickers / 129 PDFs; MANIFEST @ `63facb0`). (3) `--flip --yes`: all 56
  stamps → v+1 @ shared `2026-07-02_15-17`, `prior_versions` cleared, 129 pre-launch PDFs removed, official set re-rendered
  STRICT + baseline regenerated. **OWNER ITEM — private-archive push (D3) still pending:** the launch session had no `add_repo`
  (claude-code-remote MCP absent), and the export is byte-reconstructible from public git (`git checkout 63facb0 &&
  python scripts/launch_archive.py --export`); push from a session scoped to both repos, or locally per LAUNCH.md step 3 Path B.
  **Re-research queue from #78 (pure entry-price moves; theses untouched):** first **TXG** (−49→−63% after a +39%/mo rally — smells like
  news), **PACB** (+31→−1% sign flip; the levered stub is hyper-price-sensitive), **NAUT** (+174→+258% at $1.84 — a 15%-cap holding on a
  stale thesis); then RKLB / ACHR / PRME (moonshot news risk); then TEM / ILMN / ZM (valuation-only). **Routine drift to sync in the UI
  (low):** daily prompt omits `risk_stats.csv` staging; schedule is daily-2PM-PDT vs the spec'd weekdays-22:00-UTC (weekend runs no-op).
- **Full-codebase adversarial review + fix wave SHIPPED (2026-07-02; day-1 post-launch hotfix).** 65-agent review (10 code units → findings →
  1-2 skeptics each → completeness critic): **26 confirmed · 10 refuted · 13 low-sev deferred**; every confirmed HIGH fixed same-day. **Rendering
  (PDFs hot-fixed IN PLACE at the launch stamp — no bump, findings/copy untouched):** (1) MatureBalanceChart all-negative FCF domain (`max×1.2`
  flips sign → TEM/TWST/NVCR page-3 FCF chart drew one full-column bar + invisible bars since they shipped; STRICT gates can't see vertical
  in-chart overflow); (2) YoungValuationChart hardcoded `[0,2,4,6,8]` ticks vs ultra_bear P/S 50–126× (OKLO/ACHR/IONQ/RKLB axis ~90% unscaled —
  exposed by the 5-scenario ship); (3) lthClubs fan endpoints were hardcoded AND wrong (50/80/130/180 vs authored 77/97/107/117) and NaN-dropped
  ultra_bear — now reads `scenarios[k].chartData.luxury_club_count_fy30`; (4) tick-above-domain-top gridlines through titles (~10 mature memos;
  revenue/segments/balance domains now snap to a round top tick); (5) EvMultiples fixed tick ladder → `niceStep` (SHOP had ~25 touching labels).
  **Site:** Math table/exports/method text now show the 4th (category) multiplier the score always used; BLGFF excluded from the site allocation
  via the same `dcf_type` predicate as `build_weights.py` (watchlist test had site book ≠ tracked book); `Link` keeps cmd/ctrl/shift/middle-click
  native; matrix columns auto-extend to new watchlists; `build.js` now `?v=`-stamps **styles.css + data.js** (were unversioned → stale-cache class).
  **Masthead:** `market.net_debt_billion` is GROSS on some ymls (AAPL 90.7 self-contradicted its own extras on the live card) and NET on others
  (CROX) → `fmt_cash` says plain "debt"; **normalizing that field book-wide is an open data audit.** **Pipeline:** `validate.py` CLI honored only
  argv[1] (the "all 1 ticker(s)" tell — multi-ticker runs silently validated one), now all + unknown-flag/ticker rejection + a
  `tam_competitor_share ≥ tam` unit WARN; TICKERS lists derive from `data/*.yml` (validate/rebuild_all/visual_hash; build_site_data keeps curated
  order but hard-fails on drift); `rebuild_all` runs `node build.js` (stale-bundle class killed), re-runs `build_site_data` AFTER renders (**fixes
  the `size: "—"` the flip shipped on every live Download card**), then restamps; `render_memo_pdf` dumps console/pageerror on mount-timeout;
  `track_performance` **refuses to write a partial perf row when a weighted holding's fetch fails** (the CSV is the permanent record), skips
  Sortino gracefully on a failed benchmark fetch (was a KeyError crash), preserves legacy CSV columns on upsert; `gen_b1` import no longer
  regenerates stale intakes; `gen_young` docstring had tam_competitor_share as % (the PACB-clip recipe) → $B; `requirements.txt` added;
  **pages.yml CI now gates deploys on validate.py + data.js-in-sync** (a stale/invalid data.js could previously deploy silently); 2 dead
  `oneoff_*.py` removed. **Notable refutations:** the Indicator's 12-name GM table is documented neutral-where-undefined behavior (NOT a bug);
  the Sortino common-window intersection is the intended fair-comparison design. **Deferred (low):** scenario color map in triplicate (1 hex
  drifted); dup CAGR row in the mature assumptions fallback; YoungTamChart x-tick buckets (PACB shows a single $0B tick); dead CSS cluster;
  crypto-yml QC bypass; `ai2_panel(_sourced).csv` name consolidation; the net_debt field normalization audit above.
- **Portfolio-tab overhaul SHIPPED (2026-06-22; spec v043, §16 NEW).** (1) **Two new watchlist categories** — `competitors`
  (ACHR, PACB moved here — rivals to core holdings) and `crypto`. (2) **Category sizing tilt** = a 4th §12 weight factor
  `× category_mult` (fun-speculative 0.5 · competitors 0.3 · crypto 0.5 · core 1.0), in both `build_weights.py` and
  `pages.jsx` `computePortfolio`; conviction-neutral. (3) **Crypto valuation (§16) — non-DCF, NOT manual:** BTC = gold-anchored
  store-of-value TAM-penetration, ZRO = fee/network multiple; each scenario target **discounted to a PV** (BTC 30%/7yr → **+105%**;
  ZRO 35%/4yr → **−55%**) so upside is comparable to the DCF book, then run through the identical §12 rule (Indicator neutral 1.0,
  crypto category 0.5). Source = `data/_crypto.yml` → `build_site_data.build_crypto()` → a separate `CRYPTO` array (no PDF/memo
  page) merged into the matrix + portfolio. **BTC sizes to ~5%; ZRO earns no weight** (rich risk-adjusted, shows red in the matrix).
  Crypto is **site-only** — NOT in the tracked book (`weights.yml`/daily perf) yet; needs a price feed (BTC-USD Yahoo; **ZRO TBD**).
  (4) **Conviction tiers (Arthur):** SHAK Med-Low, TEM **High** (DCF −28% → still 0 weight in the long-only book — conviction ≠ DCF),
  BEAM Low, RXRX/PACB Low. **Crypto tiers:** BTC **High** (Arthur), ZRO Low (confirm). (5) **Colored legends** on all 3 Portfolio graphics (allocation = indigo ramp for any count; Math-table
  key; matrix cheap/fair/rich key). Validator green (53 pass); site-only (no memo PDF/baseline change). *Open: confirm ZRO
  conviction tier + the BTC discount rate/horizon (the biggest lever); wire crypto into the tracked book before launch (ZRO feed);
  PACB resolved to `competitors` (you'd named it both Fun/Spec and Competitors).* Research subagent sourced the crypto numbers (web).
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
- **Mega-7 mega-caps SHIPPED (2026-06-14; tickers 22–28): META, AMZN, GOOGL, AAPL, NVDA, TSLA, DIS.** First
  `fcf-megacap` batch beyond UBER/ILMN — all mature_company, **tier-less** (allows_tiers:false). Sourced
  end-to-end from SEC XBRL (`scripts/_models/source_mega7.py`; DIS CIK 1744489 added to the dict), modeled
  through the mature engine, authored from a **locked numeric skeleton** (`/tmp/mega7/numbers.py` → per-ticker
  `scripts/_models/gen_<T>.py`; prose drafted by 7 parallel subagents, **numbers mine + verified**) → scaffold
  → STRICT. **Findings (entry price vs the distribution — same logic as every wave):** META **+14.6%** (cheapest
  mega-cap on normalized FCF, −18% TTM while ads accelerate +33%), DIS **+10.3%** (beaten-down turnaround;
  streaming margin past the linear-TV decline), AMZN **−6.9%** (fair; FY25 FCF crushed to ~$7.7B by ~$200B AI
  capex, recovers as AWS reaccelerates), GOOGL **−21.4%** (rich after the +28% YTD run; priced for the AI-stack
  win), NVDA **−25.2%** (priced for perfection at ~50× FCF, China=$0, enormous distribution), AAPL **−34.5%**
  (richest — mid-single grower at ~43× FCF, AI outsourced to Gemini, ~$20B/yr search cliff), TSLA **−75.0%**
  (the **RKLB/OKLO pattern** — the DCF underwrites only auto+energy; the robotaxi/FSD/Optimus optionality lives
  entirely in the ultra-bull second act and even that lands −6%; what you pay above ~$100 IS the optionality,
  priced explicitly). **Caught a systematic net-cash framing bug** (the builder's `net_debt` field is GROSS
  debt; true net = cash − net_debt) and corrected all 7 gen files. `visual_baseline.json` **now 28 tickers**;
  validator green; all 28 STRICT-clean. *Page-1 5-scenario + Page-6 back-matter overflow = the usual prose
  trim (thesis/CQ/weighting + pushback/triggers/glossary → ~SHAK length), never the shared layout — a sequential
  subagent drove all 7 to STRICT-clean. Key mechanism: the back-matter/Page-1 are CSS grids with **stretched
  rows** (row height = tallest cell), so trim the LONGEST cell in a row, not a short one.*
- **Wave-2c chart-layout hardening — DONE (2026-06-14); clip-guard promoted WARN→STRICT.** Every tracked chart
  clip fixed *from data* (spec §3.5): (a) young **valuation caption** word-wraps to ≤2 lines (`wrapSvgText`);
  (b) **mature equity-build** left margin sized to the widest scenario label (`eqL` — kills the `UltBear` −5px
  clip on every mature ticker) AND made **net-debt-aware** (byte-identical for net-cash names; a red −net-debt
  bar + correct equity for AAPL/DIS, the first material-net-debt mature memos); (c) a magnitude-aware **`niceStep`**
  axis tick replaces the fixed `yMax>6?2` logic that exploded into hundreds of gridlines at mega-cap $100B–$1T
  scale (Mature Revenue + FCF charts), with the left margin sized from the widest `$…B` label (`monoTextWidth`);
  (d) **`ChartTitle`** compresses via `textLength` when a title would overrun (ACHR TAM title +59px); (e)
  **GRAL/IONQ `tam_competitor_share`** corrected (was > TAM — a copy-paste from OKLO; competitor bars ran
  off-axis). With every chart margin/title now data-sized, the horizontal SVG-clip guard in `render_memo_pdf.py`
  is **promoted from WARN-only to a STRICT gate** (2px tol, like the page-overflow check). All 28 render
  STRICT-clean (overflow + clips); baseline regenerated + `--check` green; rendering deterministic (no pollution).
- **FCF+ medium batch SHIPPED (2026-06-14; tickers 29–36): CMG, DAL, HOOD, DE, ALGN, ADSK, CART, U.** Second
  `fcf-plus-plus-growth` wave, all mature_company, **conviction tiers set by Arthur** (CART/DAL/CMG/HOOD/DE = Med;
  ALGN/U/ADSK = Low; U placed here at Low, not fun-speculative). Sourced end-to-end from SEC XBRL (`source_mega7.py`
  extended: DAL 27904, DE 315189, U 1810806, CART/Maplebear 1579091), modeled through the mature engine, authored
  from a locked numeric skeleton (`/tmp/fcf8/numbers.py` → per-ticker `gen_<T>.py`; prose by 8 parallel subagents,
  numbers mine). **Key calibration vs the Mega-7: SBC-adjusted the high-stock-comp names** (CART/ADSK/HOOD/U →
  ex-SBC owner FCF margins + share dilution, NOT the SBC-inflated headline FCF) — first pass gave ADSK +86% / CART
  +134%; ex-SBC lands them at the honest +54%/+58%. **Findings:** CART **+57.7%** (cheap ~11× FCF + an ~80%-margin
  ad flywheel + a buyback ~35% of cap) and ADSK **+53.6%** (de-rated −31% YTD to ~17× FCF + Starboard forcing
  margins toward ~45% — the LULU/UBER de-rated-quality family) are the two cheap ones; ALGN **−1.5%** / CMG
  **−4.8%** / DAL **−8.1%** the fair cluster (de-rated-not-cheap / premium-QSR-still-rich / cheap-but-cyclical-
  airline); DE **−21.8%** (cyclical at the ag trough at a full multiple); HOOD **−57.7%** (priced for perfection
  ~52× FCF, crypto/rate-cyclical) and U **−56.5%** (a dilutive GAAP-loss Vector turnaround, +56% share dilution/5y —
  the most speculative). Each carries its honest caveat (DAL refinery-grossed GAAP revenue, **DE's ~$45B captive-
  finance debt EXCLUDED** from the modeled bridge, HOOD broker-op-margin estimated since XBRL doesn't tag it, U
  convertibles + dilution, ADSK/CART billing-shift/SBC). `visual_baseline.json` **now 36 tickers**; validator green;
  all 8 STRICT-clean (overflow + clips); baseline `--check` green (no drift in the existing 28). *Layout note: the
  usual Page-1 (5-scenario) + Page-6 (back-matter) prose trims — the binding elements are the scenario-card headlines
  (Page 1) and the pushback-row bodies in the stretched 3-col grid (Page 6); DE's captive-finance caveat got
  consolidated from 4 places to 2.* Shipped on `claude/fcf-medium-batch` (stacked on the Mega-7 `conviction-bluf`).
- **Fun-Speculative mature slice SHIPPED (2026-06-15; tickers 37–42): CROX, RDDT, TOST, WRBY, YOU, SHOP.** First
  `fun-speculative` batch, all mature_company; conviction tiers (Arthur, via screenshot): CROX **High**; RDDT/TOST/
  WRBY/SHOP Med; YOU Low. Sourced from SEC XBRL (`source_mega7.py` extended: RDDT 1713445, TOST 1650164, WRBY
  1504776, YOU 1856314; CROX/SHOP already in the panel dict), modeled through the mature engine, authored from a
  locked skeleton (`/tmp/funspec/numbers.py` → per-ticker `gen_<T>.py`; prose by 6 parallel subagents, numbers mine).
  SBC-adjusted RDDT/TOST/SHOP ex-SBC. **Findings:** CROX **+56.8%** (cheapest — ~9× EV/FCF + heavy buyback; market
  hates the HEYDUDE drag + flat revenue; FY25 GAAP op margin is the non-cash impairment, modeled normalized ~22%;
  net debt $1.2B), YOU **+38.8%** (cheap net-cash FCF machine ~13× FCF, ~30% FCF margin, capital return; dual-class
  governance + estimated ~95M share count are flags), TOST **+25.5%** (de-rated −40% TTM + a real margin inflection;
  FCF modeled on payments-heavy total revenue), SHOP **−15.1%** (rich ~30× fwd FCF on 34% growth; GAAP loss is a
  non-cash equity mark), RDDT **−20.2%** (priced for perfection, +69% growth ~43× FCF, existential Google-AI-traffic
  risk), WRBY **−42.1%** (expensive ~3× sales, priced for a not-yet-shown margin inflection + the Google-glasses
  call-option). `visual_baseline.json` **now 42 tickers**; validator green; all 6 STRICT-clean; no drift on the
  existing 36. *Recovery lesson: a trim subagent hand-edited CROX's thesis with `Bull:`/`Bear:` (a `Word: ` colon-space
  in an unquoted YAML scalar → YAML read it as a mapping key → `build_site_data` aborted → the renderer ran on a stale
  `data.js`, making all the trims unreliable). The gen source was always valid; re-scaffolding restored it; a
  YAML-safety rule ("never write `Capitalizedword: ` in a value; confirm build_site_data succeeds after each edit")
  is now in the trim brief.* Deferred to framework-specific waves: **HHH** (real-estate SOTP), **SYM** + the rest of the
  **moonshot tier** (SERV/NVCR/TWST/PRME/CAI…, young_company DCF), **BLGFF** (a Baillie Gifford closed-end fund — NAV/
  discount, no operating DCF). Shipped on `claude/fun-speculative-batch`.
- **Young AI-bio/genomics sub-batch SHIPPED (2026-06-16; tickers 43–46): RXRX, BEAM, PACB (young_company) + TEM (mature).**
  First wave through the NEW reusable **young builder `scripts/_models/gen_young.py`** (the young analog of `gen_b1`: a
  compact content spec → `data/_intake/<t>.yml`, numerics via `model_dcf.model_scenario` — 10-yr explicit + Gordon + p_fail/
  distress + raise/dilution + cash-runway check). Authored from locked numbers (`/tmp/young/model.py`; conviction tiers RXRX/PACB/
  TEM **Low**, BEAM **Med-Low** — Arthur to confirm) + prose by 4 parallel subagents. **Findings (entry-price-vs-distribution,
  same logic as every wave; the four span the spectrum):** **BEAM +31.3%** (pre-product base editing; **$1.21B cash ≈ $11.75/sh
  cushion** makes the ultra-bear *expected* $5.77 despite a negative DCF — the cash IS the distress floor — plus a de-risked
  BEAM-302/AATD platform tail; clinical failure is the risk, not insolvency); **RXRX +22.3%** (pre-product AI-discovery platform
  −37% YTD; modal base *below* spot, ~88% of value in the bull/ultra-bull tail — a cheap option on platform validation);
  **PACB −2.3%** (long-read sequencer; $1.32 sticker hides **~$644M converts vs $276M cash = ~$368M net debt > the equity cap**
  → ~50% of the mass worth ~0, offset by a long-read-wins tail — a distressed, financially-**levered** option, the leverage
  is the story); **TEM −28.5%** (rich/priced-for-perfection, the ILMN/RDDT family — $1.3B rev near adj-EBITDA breakeven, but
  **SBC ~$136M/yr swamps the +$65M adj-EBITDA → owner-FCF still negative**; only the bull clears spot; Lefkofsky ~60% vote).
  **TEM reclassified young→mature (TXG precedent):** the young cash-runway check uses `prev_rev=0`, which fabricates a phantom
  ~$0.97B year-1 reinvestment at $1.3B revenue — so a $1.3B-revenue near-breakeven name is a mature_company, not a moonshot.
  `visual_baseline.json` **now 46 tickers**; validator green; all 4 STRICT-clean (overflow + clips); no drift on the existing 42.
  *Lessons: (1) **`tam_competitor_share` is $B (absolute, < tam_billion), NOT a %** — set it as 80(%) on PACB's $8B TAM and it
  plotted as $80B, clipping +823px (the GRAL/IONQ wave-2c class). (2) Young **Page-1 5-scenario** binding when the left column is
  short is the **scenario-card headlines** below the fixed-height forward chart (trim headlines, not thesis); when the left column
  is tall it's thesis/weighting — diagnose by which trim moves the px. (3) `final_shares` must reconcile with `shares0 + Σ
  raise/price` or the validator WARNs — use scalar avg raise-prices and set fs to the implied count.* **MERGED to main via PR #54**
  (2026-06-16, with the Schwager-Sortino tracker below).
- **Portfolio tracker — Schwager modified Sortino vs S&P/NASDAQ (2026-06-16; merged PR #54).** `portfolio/track_performance.py`
  now reconstructs the buy-and-hold (drifting-weight) portfolio's daily returns and computes **Schwager's modified Sortino ratio**
  (from *Unknown Market Wizards*): `(annualized return − MAR) / (√2 × annualized downside deviation)` — the **√2 makes it directly
  Sharpe-comparable** (equal for a symmetric distribution, above Sharpe only with positive skew). MAR = realized risk-free (BIL);
  vs SPY (S&P 500) + QQQ (NASDAQ-100); snapshot persisted to `risk_stats.csv`; runs in the daily routine + via `AI_EPOCH=<date>
  --sortino` for a trailing-window backtest. Trailing-12mo backtest (today's weights × trailing prices, NOT the live book):
  Portfolio Sortino **0.55** vs SPY **1.71** / QQQ **1.88** — the concentrated book's ~3× downside deviation drags its
  downside-risk-adjusted return well below the indices. Lower Sortino = worse (return per unit of downside risk). README/ROUTINES updated.
- **Moonshot-tier batch SHIPPED (2026-06-20; tickers 47–50): SERV, PRME (young_company) + TWST, SYM (mature).** Second wave through
  the reusable young builder + the mature builder; "frontier automation + synthetic/gene biology" slate. Authored from locked numbers
  (`/tmp/moon/model.py` young + `/tmp/moon/mature.py`) + prose by 4 parallel subagents; conviction tiers all **Low** (speculative;
  Arthur to confirm). **Findings (entry-price-vs-distribution; two frontier moonshots, two rallied names screening expensive):**
  **SERV +29.2%** (pre-scale sidewalk-delivery robots; modal base −63% on a half-idle 2,000-robot fleet + brutal forced dilution +
  thin LOGISTICS margins, but a fat tail if utilization inflects — a cheap option on the fleet scaling); **PRME +7.2%** (the
  **anti-BEAM** — same gene-editing family, opposite balance sheet: $149M / ~9-mo runway / GOING-CONCERN flag / $200M ATM vs BEAM's
  $1.21B; forced dilution doubles-to-triples the share count + a $0.40 distress floor almost exactly offset the platform tail → fair);
  **TWST −49.8%** (rich/priced-for-perfection — rallied +150%/52wk to ~14× sales while still adj-EBITDA-negative; the ILMN/RDDT/TEM
  family); **SYM −68.0%** (richest — a thin-margin 19%-GM systems integrator priced ~11× sales like software; SBC > adj-EBITDA so
  owner-FCF ~0, the $867M OCF is customer-funded backlog timing; only a margin transformation reaches spot; >84% Walmart concentration).
  **TWST + SYM reclassified young→mature** (TEM/TXG precedent: high-rev, near/at breakeven, net cash → the prev_rev=0 cash-runway check
  is an artifact). `visual_baseline.json` **now 50 tickers**; validator green; all 4 STRICT-clean; no drift on the existing 46.
  *Lessons: (1) thin-cash heavy-burn young names (SERV/PRME) need an **auto-raise sizer** — greedily raise just enough to keep the
  validator cash path ≥0, set final_shares to the implied diluted count — so the dilution drag is honest (without it the tails are
  wildly overstated). (2) **Calibrate terminal op margins to the BUSINESS**: a delivery-robot NETWORK is LOGISTICS (~15-24% op margin),
  not software (45%) — the wrong margin 10×'d SERV's tail. (3) **Page-6 back-matter binding row = PUSHBACK row 1 (items 0-2)**, not
  row 2 — the disclaimers section is fixed/shared; trim the tallest cell in the binding row.* **MERGED to main via PR #55**
  (2026-06-20); conviction tiers later set (Arthur): SERV + TWST **Med-Low**, PRME + SYM **Low** (site-only, PR #57).
- **Moonshot tier COMPLETE — finishing pair SHIPPED (2026-06-21; tickers 51–52): NVCR + CAI (both mature).** The last two
  named deferred moonshot-tier candidates (NVCR/CAI; "INFQ" was never a real entry). Both classify **mature** (TEM/TXG precedent:
  high-rev, unprofitable-but-net-cash). Sourced (SEC XBRL + web), modeled through the mature engine (SBC-adjusted ex-SBC owner FCF),
  prose by 2 parallel subagents. **Findings — notably the cheap/fair side of the ledger (breaking the "everything's rich" streak):**
  **NVCR +4.5%** (NovoCure; TTFields oncology device — *cheap* at ~2.5× sales, **net cash**, 78% GM; modal base ~fair with new-indication
  optionality (Optune Lua/Pax/METIS multiplying the TAM beyond GBM), held in check by the **fresh Jun-18-2026 Phase-3 TRIDENT GBM MISS**
  + years of unproven device operating leverage); **CAI +28.9%** (Caris Life Sciences; AI precision-oncology diagnostics, IPO Jun-2025
  @ $21, now ~$18 — **the anti-TEM**: same ~6.5× sales multiple, opposite finding because Caris is further along — already **FCF-positive
  at GAAP breakeven** on **+97%** growth with a real 47%→65% GM inflection, so the market is under-pricing the margin story; bear =
  reimbursement true-ups + steep deceleration + Halbert ~42% vote). `visual_baseline.json` **now 52 tickers**; validator green; both
  STRICT-clean; no drift on the existing 50. *Lessons: (1) device/diagnostics terminal FCF margins are GROSS-margin-capped — NVCR's
  78% GM allows ~15-18% owner FCF, but a 19%-GM systems integrator (SYM) cannot; calibrate the ceiling to the GM. (2) A fresh trial
  miss (TRIDENT) is a real, datable negative — bake it into the bear/base, not just a footnote. (3) the same ~6.5× sales multiple
  yields opposite findings (CAI +29% vs TEM −28%) purely on where each sits on the FCF curve — FCF-positivity is the swing.* Conviction
  tiers (Arthur): **CAI + NVCR both Med-Low** (PR #58 set CAI; NVCR bumped Low→Med-Low via PR #60). Shipped on `claude/epic-curie-ouHZL`.
- **Indicator simplification + Portfolio universe matrix + HHH SHIPPED (2026-06-21; ticker 53).** (1) **/indicator narrowed to the
  quarterly backtest** (PR #59, merged): dropped the annual-IC sausage-making; the zone-return "practical read" now reads off the same
  point-in-time quarterly panel (103 names / 61 xs), **3y-only**, with a NON-OVERLAPPING win-rate (green→red +124/+89/+92/+41%, win
  82/82/76/67%; reproduce `scripts/_models/zone_returns.py`). (2) **NVCR Low→Med-Low** (PR #60, merged). (3) **Portfolio universe matrix**
  (`/portfolio`): a conviction×category grid — 5 watchlist columns × 5 tier rows + an Untiered band for megacap/private — each ticker a
  chip tinted by DCF upside (`buildMatrix` in pages.jsx; site-only, no PDF/baseline change). (4) **HHH — Howard Hughes Holdings**, 53rd
  ticker, the **first real-estate / discount-to-NAV SOTP** (mature_company_sotp, `fcf-plus-plus-growth` / `real-economy-hard-assets`, tier
  **High** per Arthur). Finding **+41%** (weighted $94.31 vs $66.86): cheap, asymmetric — ~1.05× book but a ~37% discount to the company's
  own $104 SOTP NAV (~80% land / ~20% the new Vantage insurer), Ackman's $100 cash buy-in (May-2025, 48% premium) the floor, the
  Berkshire-style holdco conversion the catalyst; bear is the 15-yr value-trap, tail is Ackman's $211-by-2030. SEC-XBRL sourced (6 research
  subagents), modeled in `scripts/_models/model_hhh_sotp.py` (terminal = exit multiple / cap rate, not Gordon; all validator identities tie).
  **First NET-DEBT SOTP** (vs net-cash ZM/COIN). Renderer generalized (SOTP special-asset label now data-driven via `dcf_metrics.special_label`
  — "Vantage insurance" not hardcoded "Anthropic stake"; a special_label-gated exit-multiple row replaces "Terminal growth") — **ZM + COIN
  byte-identical** (COIN carries exit_fcf_multiple but has always shown term_g; the gate preserves it). 7pp, STRICT-clean; `visual_baseline.json`
  **now 53 tickers**; full `--check` clean (no drift on the existing 52). *Lessons: (1) forcing a land-bank NAV through a Gordon DCF makes the
  intermediate fields (term_g, starting FCF) read backwards — model RE on a stable run-rate FCF + an exit multiple (cap rate) instead.
  (2) Page-7 is the BACK MATTER (Page5BackMatter renders AFTER PagePOCD), not the POCD page — its binding rows are the pushback grid + the
  glossary term count.* Shipped on `claude/epic-curie-ouHZL`.
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
- **Arthur Indicator — dedicated site page LIVE (`/indicator`, 2026-06-13) + IC significance quantified.**
  `IndicatorPage` (pages.jsx, nav link in components.jsx, route in app.jsx): equation, plain-English
  explanation, color-coded zones, a LIVE "where today's names sit" table (from `memo.ai`), the backtest
  zone-return + OOS-IC tables, an **IC primer**, and an **honest significance section**. New
  `ai2_backtest.py --robustness` reports the per-year ICs + **t-stat** (reproduces the page's numbers):
  **1y mean IC +0.063, t +1.14, 59% years+; 3y +0.044, t +0.90, 47% years+ — POSITIVE BUT NOT
  STATISTICALLY SIGNIFICANT (t~1 << 2).** Key finding (durable): the value effect runs hot/cold year to
  year (yearly IC −0.31…+0.56), so per-year std ~0.2 ≫ mean ~0.05; with ~16 annual cross-sections it can't
  be pinned down. **Adding NAMES barely moves the t-stat** (within-year sampling std already ~0.14 at ~53
  names/yr); the only real lever to "robust" is **more PERIODS** = a point-in-time *quarterly* panel.
- **Arthur Indicator — ROBUSTNESS ESTABLISHED at the 3-year horizon (quarterly panel, v040, 2026-06-13).**
  Built `scripts/_models/source_ai2_quarterly.py` → committed `ai2_quarterly.csv`: rebalance every calendar
  quarter-end 2009–2024, fundamentals point-in-time by SEC **filing date** (no look-ahead), **3,399 rows /
  61 cross-sections / 103 tickers** (~4× the annual). Quarterly sampling of multi-year forward returns
  overlaps → **Newey-West (Bartlett)** correction applied (+ a non-overlapping 1-quarter horizon). **Result:
  3-year NW t ≈ +2.2 → SIGNIFICANT** (stable >2 for Bartlett lags 4–20: +2.6→+2.1; both halves positive;
  67% of cross-sections +). 1q and 1y are noise → **value is a slow signal** (predicts 3y, not next-quarter),
  the economically-correct shape, and exactly the §12 long-horizon-tilt use. `/indicator` page + `ai2_results.md`
  + spec §13/changelog v040 updated; reproduce `source_ai2_quarterly.py --analyze`. *Caveat:* survivors +
  known busts (no fully-delisted names) — possible mild survivorship inflation of levels, not the rank-IC.
  The `--robustness` (annual) mode stays for the annual contrast.
- **Arthur Indicator — VERSATILITY TEST: the edge does NOT generalize (v041, 2026-06-14). KEY HONEST FINDING.**
  (1) **Market-neutral framing** (`--longshort`): the real bar is the cheap-minus-rich **long-short spread**
  (beta cancels), not absolute return / not vs-S&P. Growth/quality universe: **+51%/3y, NW t +2.46**; but the
  cheap bucket beat the S&P +98% AND the rich bucket beat it +47% (universe + bull + survivorship inflate
  absolutes — only the SPREAD is the edge). (2) **Broad universe** (`harvest_broad_universe.py` → SEC XBRL
  *frames* API, the one bulk endpoint NOT 403-blocked; 794 all-sector names ≥ $400M gross profit →
  `ai2_quarterly_broad.csv`, 25,123 rows / 713 tickers): the long-short spread **collapses to +5.5% (t +0.69,
  50% of quarters = coin flip)**, 3y IC slightly negative. Split confirms: edge is **entirely in the curated
  growth/quality names** (+48%, t1.9, 73%+); broad-economy ~600 names = no edge (+5.5%, t0.69, 50%+). **So
  the Indicator is NOT a universal value factor — a relative screen among quality-growth compounders only**
  (cheap value/cyclicals are often cheap for a reason). v040's significance was real but universe-specific.
  §12 keeps it as a *gentle* tilt AND only on the growth/quality book — never market-wide, never leaned on.
  `/indicator` page + `ai2_results.md` + spec §13/v041 carry the honest scope. *Caveat:* survivors (today's filers).
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
- **Spec §12 portfolio construction — BUILT as a three-factor rule (v039, 2026-06-13):**
  `weight ∝ max(0, DCF upside) × conviction_mult × Arthur-Indicator_mult`, capped 15%, water-filled, cash
  residual. **The positioning ("the magic," Arthur's framing):** two human inputs (security *selection* +
  a per-name *conviction* tier) × one machine layer (the AI memo's prob-weighted fair value + the §13
  Indicator), meeting at sizing. Conviction tier (High 2.0 · Med-High 1.5 · Med 1.0 · Med-Low 0.6 · Low 0.35)
  is the only human number, conviction-neutral (sizing only). Indicator zone (green 1.25 · yellow 1.10 ·
  orange 0.90 · red 0.70; neutral where undefined) is a *gentle* validated-OOS tilt — value is the divergences
  (ISRG +20% DCF but red Indicator → halved). Built end-to-end: `arthur_indicator.py` (`compute_ai`/`ai_zone`),
  `build_site_data.py` surfaces `ai:{value,zone}` into `data.js`, `build_weights.py` writes the per-name
  breakdown to `weights.yml`, `pages.jsx` `computePortfolio` + `<PortfolioPage>` "Math" table render it
  transparently (Upside · Conviction · Indicator → Weight); page defaults to the 15% cap so it matches the
  tracked book. Replaced the old `upside × √P_pos` heuristic. Site-only (no PDF/baseline change).
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
  gated on a `pocd:` block, rendered just before the back matter. Extend to more tickers as People data is sourced.
  - **POCD rollout batch 1 — megacaps SHIPPED to the site (2026-06-22): META, GOOGL, AMZN, NVDA, TSLA, SHOP** (+ HHH earlier = 16 with POCD now).
    Observable People data web/SEC-sourced by 6 parallel subagents; scores discriminate as designed — **NVDA/AMZN 4** (clean single-class,
    split or LID-mitigated governance) · **GOOGL/SHOP 3** (dual-class with mitigants) · **META/TSLA 2** (most-entrenched: META super-voting
    +combined Chair/CEO+controlled-co; TSLA the Tornetta pay saga + related-party web + split attention). `founder_led:false` for the
    non-founder CEOs (Pichai, Jassy, Musk). All 6 STRICT-render 7pp clean. **Site-only this batch:** the embedded site memo shows POCD from
    `data.js`; the **PDFs + visual_baseline were NOT regenerated — this container has no poppler/pdftoppm**, so the on-disk 6pp PDFs stay in
    sync with the baseline and refresh at the launch flip (poppler env, July 1) or a future render pass. *Open: confirm the score notches
    (META 2 vs COIN 3 — the one subjective call) + the `founder_led` convention for control-retaining founders. Remaining ~40 memos = later batches.*
  - **POCD rollout batch 2 — tracked holdings (2026-06-22): NAUT, YETI, CROX, CART, CAI shipped to the site** (+these = 21 with POCD).
    Scores: **NAUT/YETI/CROX 4** (NAUT single-class + founder buying; YETI professionalized single-class, founders off-board; CROX clean single-class
    + buybacks, HEYDUDE-impairment offset) · **CART 3** (clean single-class but brand-new combined Chair/CEO Chris Rogers + concentrated VC board) ·
    **CAI 3** (founder Halbert ~44% econ ≈ vote on a clean SINGLE-class one-vote register — combined Chair/CEO + 44% concentration the flags; FCF
    inflection + new $100M buyback + fully-independent committees keep it off a 2. *Verification caught an error: the first agent's "Class B 10-vote /
    ~80-88% vote / controlled-company" was S-1 boilerplate bleed — primary XBRL + Exhibit 4.2 confirm single-class, one vote/share, likely NOT a controlled company.*)
    Site-only (same poppler caveat as batch 1). **GRAL HELD from the batch — and flagged: thesis-changing event the committed memo predates** —
    NHS-Galleri MISSED its primary endpoint (Feb 2026), stock ~$100→~$50, CEO changed (Ragusa→Ofman); GRAL is a ~4.2% tracked holding so the stale
    +9%/$73 finding mis-sizes the book → needs a re-research/re-price (not just POCD) before adding its scorecard.
  - **POCD rollout COMPLETED for all operating-company memos (2026-06-26→27): now 52 of 57 with POCD.** This session added 31 scorecards —
    PR #72 (gral/dis/tost/beam/aur/serv/adsk, 7) + batches 3-6 (24) — all observable/sourced/conviction-neutral, all four legs, ~6 parallel
    research subagents per batch, all STRICT 7pp, validator green, site-only (poppler caveat). **GRAL re-priced +6.4% & POCD'd (#72) — supersedes the
    batch-2 hold above.** Batch 3 (#73): PACB/RXRX/NVCR/PRME/ACHR 3, **YOU 2**. Batch 4 (#74): AAPL/JOBY **4**, OKLO/IONQ/HOOD 3, **RDDT 2**. Batch 5 (#75):
    **TEM/SYM 2**, TXG/TWST/U/WRBY 3. Batch 6 (#76): **DAL/DE/ALGN/CMG 4**, SHAK/LTH 3. **→ every tracked-book holding now has POCD.**
    **The now-stable score rubric (observable governance, NOT conviction):** **4** = clean one-share-one-vote + sound board (a combined Chair/CEO is fine if
    mitigated by an independent lead director, cf NVDA/DE; a separate *independent* chair is best, cf AAPL/DAL/ALGN); **3** = dual-class super-voting WITH
    mitigants (GOOGL/COIN/TXG/HOOD/WRBY) OR single-class with a structural flag — combined Chair/CEO + concentration, classified board, Up-C/TRA, or a
    related-party web (CAI/CART/TWST/U/SHAK/LTH); **2** = majority single-person/family voting control + combined Chair/CEO (META/TSLA/YOU/RDDT/TEM/SYM).
    No **1** used yet — **SYM is the standing candidate** (control entrenchment + a 2024 restatement / unremediated material-weakness integrity flag); Arthur
    to decide whether to open a "1". Observable corrections caught & folded in: **NVCR CEO now Frank Leonard (Dec-2025)**; **AAPL succession Cook→Ternus
    (eff Sept-2026)**; RXRX founder Gibson off CEO+board; ACHR super-voting sunset Dec-2024→single-class; OKLO Altman left the board entirely (Apr-2025);
    **U is NOT founder-led** (Bromberg turnaround CEO after the 2023 Runtime-Fee ouster). **DEFERRED — non-operating-company memos (Arthur's call):** BLGFF
    (closed-end fund → would need a tailored manager+board variant) + PYKA/ZIPLINE (private, no public proxy → skip the scored rubric). *Lessons:* (1) build
    the pocd block via **yaml.dump** (auto-handles quoting/colons/apostrophes — kills the CROX `Word: ` bug class); (2) `insider_ownership_pct` = the **economic**
    %, with voting % carried in `governance_flags` for dual-class names; (3) a few research subagents spawned nested sub-agents and stalled without compiling —
    resume via SendMessage ("synthesize now from gathered research, don't spawn").
  - **PACB re-priced +58.7% → +30.6% (#74).** Scenario-separation (#70) had left 62% of FV in the lone 7%-prob ultra-bull; ultra revenue is at the spread-rule
    floor and the equity convexity is structural (net debt > equity cap), so the one honest lever was the ultra **probability** — 0.07 was peer-inconsistent
    (lagging ACHR uses 0.04) → trimmed to 0.05, 2% to bear. Also fixed a **stale thesis** #70 left reading the pre-widening "−2.3%, modestly negative." Still
    tail-driven (the honest shape for a distressed/levered option).
  - **Segment-chart Y-axis bug FIXED (#76).** `MatureSegmentsChart` ("Revenue by segment") kept a fixed tick step capped at 1,000; segment revenue is in **$M**,
    so any $10B+ segment exploded into dozens-to-hundreds of stacked gridlines (NVDA ~218, AMZN ~687, GOOGL ~398, AAPL ~367) — an unreadable y-axis smear on
    EVERY mega-cap segment chart (Arthur flagged NVDA). Wave-2c fixed this class on the Revenue/FCF charts but **missed the segment chart**. Fix = `niceStep` +
    magnitude-aware $M/$B units + data-sized left margin (the same pattern the Revenue/FCF charts already use); affects all 41 mature memos; verified across the
    scale range, all STRICT-clean.
  - **Ultra-bear SHIPPED across the deep-bear outliers (NAUT/AUR/JOBY/LTH) → uniform 5-scenario book (2026-06-30, spec v045; Arthur's call).** Modeled an
    ultra-bear for all four through `model_dcf` and shipped them. **Findings unchanged** (NAUT +174% / AUR +5% / JOBY −20% / LTH −34%) — on these wipeout-class
    names the ultra-bear floors at the bear's $0 EV, so it's a **presentation/narrative** scenario (the deeper-failure story), not new analysis. Mechanism (in
    §6c.18): equity-dilution-funded pre-revenue names have a **non-monotonic downside in per-share terms** — negative distressed equity ÷ a larger diluted share
    count moves per-share *toward* zero, so the bear already sits at the trough; the ultra-bear is modeled beneath it with a negative going-concern terminal to
    stay monotonic. Ultra-bear probs split the large bear (NAUT 20 / AUR 15 / JOBY 13 / LTH 8%). Validator green; all four STRICT-clean 7pp (5-col layout fits).
    Site-only (4 ymls + `data.js`; PDFs/baseline refresh at the launch flip). *(Debt-funded PACB is the contrast — constant shares → cleanly monotonic → its
    ultra-bear genuinely moves value, the §6c.11.2 tail-concentrated finding.)*
- **Spec §15 (v036, DRAFT) — operating cadence & automation + 1 July 2026 "launch" (Arthur's ask).**
  **Monthly (22nd):** bump each re-priced ticker (= archive: grows the on-site "Prior versions" panel; replaces the `archive/YYYY-MM/` move — v042) → mechanically re-price + re-render all memos → update §12 weights →
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
  PRIVATE repo `ar2eb-archive` (Claude's GitHub scope is ar2eb-only — launch session can `add_repo` it);
  pre-launch memos stay in public git history regardless (no rewrite — decided).* **Private repo
  `ar2eb-archive` CREATED by Arthur (2026-06-12, via the Claude-for-Chrome runbook) — D3 prereq DONE.**
  **DONE — launch executed 2026-07-02; see the LAUNCHED bullet at the top of this section.** Live epoch
  t₀ = 2026-07-01 (daily routine live, first row committed). *(POCD scorecard page §14 is DONE — 52 tickers.)*
  **Launch DRY-RUN rehearsed (2026-06-22):** `--export` snapshots the current book (56 memos / 77 PDFs / MANIFEST);
  `--flip` dry-run plan clean; stamp-transform now verified on ALL 56 live YMLs. *Fixed a real bug the rehearsal caught:*
  `_PRIOR_RE` didn't match the **inline-empty `prior_versions: []`** the newest memos (hhh/blgff/pyka) ship, which would
  have tripped the flip's internal `assert "prior_versions" not in st` mid-launch — regex broadened to `prior_versions:[^\n]*`.
  Re-price (LAUNCH.md step 1) stays the June-30 judgment step (a dry-run re-price now would just be overwritten July 1).
- **Cleanup backlog — DONE (2026-06-12, via the Claude-for-Chrome runbook).** All 36 stale `claude/*`
  branches deleted (incl. `_probe-workflows`, the #21-squashed `ionq-ultra-bull-pressure-test`, the three
  #33-salvaged branches, and the #27-superseded `sweet-noether-80vbp` — verified superseded: ionq renders
  STRICT-clean on main). `origin` now carries **only `main` + the active feature branch** (`add-shak`, PR #36).
  Branch deletion + the private-repo creation were the two owner-only GitHub chores Claude couldn't do from a
  remote session (403 on branch delete; ar2eb-only scope) — both now cleared.
