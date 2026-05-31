# CLAUDE.md — operating guide for ar2eb

Context for any Claude session on this repo. Threads here hit length limits and
get restarted often, so the durable context lives in the repo, not the thread:
this file + `spec/memo-spec__v023__2026-05-23_21-30.md` (the methodology spec,
changelog-driven — currently at logical **v028**) are the source of truth.

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
  custom domain via `public/CNAME` (ar2eb.com). `netlify.toml` is **vestigial**
  (safe to delete). *History note: the deploy host churned (Cloudflare Worker →
  Cloudflare Pages → GitHub Pages) — if anything deploy-related is in doubt,
  confirm the live DNS target before acting.*
- **DNS** is managed at **Cloudflare**. Mail is on **@culang.co**, so `ar2eb.com`
  sends no email (this is why hard anti-spoof lockdown — null-MX + DMARC
  `p=reject` — is safe).

## Open items (keep reminding Arthur)

- **DNS housekeeping** (do at a computer): `www.ar2eb.com` → apex redirect
  (Cloudflare CNAME + Redirect Rule) and DMARC + null-MX anti-spoof on the
  `ar2eb.com` zone. A reviewed prompt exists; before adding SPF, check for an
  existing apex `v=spf1` TXT (a domain may have only one).
- **Competitive page rollout:** shipped + grounded on IONQ (origination) and ISRG
  (audit); still to author `competitive:` blocks for the other 7 tickers, ship
  bumped 6-page PDFs, regen `tests/visual_baseline.json`, and sweep residual
  "Page 4/5" cross-refs in the spec (§6a, §6c.11).
- **Wave 1** new tickers (when ready): ACHR, GRAL, TXG, RKLB, OKLO (young); LULU,
  YETI, ILMN, ABNB, UBER, DASH (mature) — each fundamentals-only, with the
  competitive page baked in.
