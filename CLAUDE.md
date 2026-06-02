# CLAUDE.md — operating guide for ar2eb

Context for any Claude session on this repo. Threads here hit length limits and
get restarted often, so the durable context lives in the repo, not the thread:
this file + `spec/memo-spec__v023__2026-05-23_21-30.md` (the methodology spec,
changelog-driven — currently at logical **v030**) are the source of truth.

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
- **Wave 1 — Batch B (mature) MODELED 2026-06-01; memos NOT yet shipped.** All 6 researched
  (web subagents) + modeled through the mature engine (now preserved in `scripts/_models/`,
  verified vs ZM), audit lens. **Findings (same entry-price-vs-distribution logic as Batch A —
  beaten-down quality screens cheap, rallied names expensive):** **LULU +65%** (de-rated ~60% to
  ~10× FCF; modal stabilization overshoots the decline the market prices — even a real
  brand-impairment ultra_bear is −34%); **UBER +48%** (~14× EV/FCF; market over-discounts the AV
  threat, but the AV-disruption ultra_bear is −44%); **ABNB +38%** (~15× EV/FCF FCF-machine,
  decelerating but cheap); **YETI +4%** and **DASH −1%** (fair — DASH down 40% but still ~33× FCF
  + SBC dilution offsets 20%+ growth); **ILMN −30%** (rallied ~80% to near highs, priced for a
  re-acceleration the base doesn't deliver — the TXG mirror). **Watchlist:** UBER → `fcf-megacap`;
  ILMN → `fcf-megacap` (debatable vs ++growth); ABNB/DASH/LULU/YETI → `fcf-plus-plus-growth`.
  **NEXT (ship):** author the 6 intakes (clone the TXG mature generator — `dcf_type:
  mature_company`, growth-rate `rev_path`, fcf=rev·fcf_margin, Power-Audit `competitive:` block,
  ZM-style chart_reference/page3_chart_config) → scaffold → validate → render under STRICT_LAYOUT
  (trim Page-1 thesis ~RKLB length) → ship → baseline. Then the **Wave-1 PR to main**.
- **Spec §12 portfolio construction** — still a draft; refine as it's exercised.
