# Prompt to migrate the AR2EB memo project to Claude Code

*v005 · 2026-05-18_19-30 · supersedes v004*

## Changelog

- **v005** (2026-05-18_19-30) — Added "Receiving the upload" section at the top to handle batched file delivery. The upload UI limits to 5 files per batch; the 19-file bundle arrives in 4 batches. This section tells Claude Code to wait for all batches before starting Setup, and includes a checklist of expected files. Suggested batch order added for logical ordering.

- **v004** (2026-05-18_19-00) — Major rewrite for the post-refactor architecture. Four per-ticker generators collapsed into single parameterized `memo.py`. Four JSX scenario data files deprecated; `/data/{ticker}.yml` is now single source of truth (schema v003). Chart builders remain per-ticker. Logo asset bumped to v3. Spec bumped to v020. PDFs bumped: JOBY v028, AUR v022, LTH v021, ZM v020.

- **v003** (2026-05-18_03-30) — Added font bundle. Expanded path-translation guidance.

- **v002** (2026-05-18_03-15) — Updated canonical filenames; chartfix13 generators; added chart-builder Python scripts.

- **v001** (2026-05-18_01-00) — Initial Claude Code migration prompt.

---

## Receiving the upload

These materials arrive in **batches of 5 files** (upload UI limit). The full bundle is **19 files** including this prompt. Do not begin the Setup phase until all 19 have arrived. Briefly acknowledge each batch as it lands, then wait.

Expected files (suggested batch order; any ordering works as long as all 19 arrive):

**Batch 1 — prompts, spec, generator, first data file (5 files):**
- [ ] `prompt-for-claude-code__v005__2026-05-18_19-30.md` ← this file
- [ ] `prompt-for-claude-design__v004__2026-05-18_19-00.md`
- [ ] `memo-spec__v020__2026-05-18_04-00.md`
- [ ] `memo.py`
- [ ] `joby.yml`

**Batch 2 — remaining data files + first chart builders (5 files):**
- [ ] `aur.yml`
- [ ] `lth.yml`
- [ ] `zm.yml`
- [ ] `build_joby_charts.py`
- [ ] `build_aur_charts.py`

**Batch 3 — remaining chart builders + draft + first 2 PDFs (5 files):**
- [ ] `build_lth_charts.py`
- [ ] `build_zm_charts.py`
- [ ] `young_company__DRAFT__needs_visual_polish.py`
- [ ] `joby-memo__v028__2026-05-18_04-00.pdf`
- [ ] `aur-memo__v022__2026-05-18_04-00.pdf`

**Batch 4 — remaining PDFs + brand assets (4 files):**
- [ ] `lth-memo__v021__2026-05-18_04-00.pdf`
- [ ] `zm-memo__v020__2026-05-18_04-00.pdf`
- [ ] `ar2eb-logo-v3-cropped.png`
- [ ] `ar2eb-fonts__v001__2026-05-18_03-30.zip`

When all 19 are received, confirm completeness with a brief inventory check, then begin the Setup phase below.

---

# Project migration brief

This is the handoff from a long chat thread that built four investment memos as 5-page PDFs. The PDFs are good — what's polished is what gets posted to the AR2EB website. The chat-based workflow has worked, but everything is fragmented across files in a sandbox filesystem and edited turn-by-turn. Moving to Claude Code to push site + PDF updates from a single repo.

## What we built

Four investment memos covering JOBY, AUR, LTH, ZM. Each memo is a 5-page landscape legal PDF (14" × 8.5") following a fixed structure documented in `memo-spec__v020`. The framework is probability-weighted scenario DCF with four scenarios (Bear, Base, Bull, Ultra Bull) per ticker.

Two DCF frameworks are in use, dispatched on a ticker's `dcf_type`:

| dcf_type | Period | Tickers | Equity equation |
|---|---|---|---|
| `young_company` | 10y (FY27-36) | JOBY, AUR | op_ev + cash − net_debt; failure-prob haircut |
| `mature_company` | 5y (FY26-30) | LTH | op_ev + cash − net_debt |
| `mature_company_sotp` | 5y (FY26-30) | ZM | op_ev + cash − net_debt + special_assets |

## Architecture (post-refactor)

```
/data/                        ← single source of truth (YAML)
  joby.yml                    schema v003
  aur.yml
  lth.yml
  zm.yml

/                             ← code at repo root for now; can modularize later
  memo.py                     single generator, takes ticker arg

/charts/                      ← chart-builder scripts + per-ticker chart PNGs
  build_joby_charts.py        per-ticker (working, hand-tuned)
  build_aur_charts.py
  build_lth_charts.py
  build_zm_charts.py
  young_company__DRAFT__needs_visual_polish.py   ← future-work parameterization
  joby/                       ← generated PNGs (gitignored)
  aur/
  lth/
  zm/

/public/
  memos/                      ← output PDFs (canonical, version-stamped)
    joby-memo__v028__2026-05-18_04-00.pdf
    aur-memo__v022__2026-05-18_04-00.pdf
    lth-memo__v021__2026-05-18_04-00.pdf
    zm-memo__v020__2026-05-18_04-00.pdf
  assets/
    ar2eb-logo-v3-cropped.png        (1990×459, current logo with new tagline)
    fonts/                            (Inter × 5 + JetBrains Mono × 2, unzip from bundle)

/spec/
  memo-spec__v020__2026-05-18_04-00.md
```

## Workflow once set up

```bash
# Regenerate one memo end-to-end:
python charts/build_joby_charts.py    # produces 6 PNGs in charts/joby/
python memo.py joby                   # produces public/memos/joby-memo__*.pdf

# Regenerate all four:
make build-memos                      # or rebuild-all.py — set this up
```

When the data changes (probability bump, narrative tweak, new ultra_bull headline), the workflow is: edit one `data/{ticker}.yml`, rebuild the memo, push. That's the whole loop.

## File inventory for this migration

**Code** (place at repo root or `/scripts/`):
- `memo.py` — 1,542 lines, single generator. Reads `data/{ticker}.yml`, dispatches on `dcf_type`, produces PDF. Replaces the four prior `generate_*_chartfix14.py` files (which can be dropped).
- `build_{joby,aur,lth,zm}_charts.py` — 4 chart builders, ~500 lines each. Per-ticker for now; each reads its YAML and produces 6 PNG charts. Place these in `/charts/`.
- `young_company__DRAFT__needs_visual_polish.py` — first attempt at parameterized chart builder for JOBY+AUR. Loads YAML, dispatches like memo.py does. Visual regressions in chart 1 (label collisions), chart 3 (right-axis range), chart 4 (label positioning), chart 5 (P/S mismatch with YAML market cap), chart 6 (TAM bar proportions). ~45 minutes of matplotlib tuning to ship. Future work.

**Data** (in `/data/`):
- `joby.yml`, `aur.yml`, `lth.yml`, `zm.yml` — schema v003. Each contains: ticker identity, market data, central question, thesis, chart reference data, four scenarios (each with probability, expected_per_share, headline, narrative, probability_rationale, dcf_metrics, dcf_path, chart_data), historical_prices, weighting_rationale, page3 subtitle+sources, appendix (pushback + falsification triggers). ~20 KB each, ~360 lines each.

**Spec** (in `/spec/`):
- `memo-spec__v020__2026-05-18_04-00.md` — 138 KB, 1,480 lines. Fourteen formal §6c rules; full design system documentation; data schema reference. Read end-to-end before touching layout code.

**Brand assets** (in `/public/assets/`):
- `ar2eb-logo-v3-cropped.png` — 1990×458, AR ≈ 4.34. Current logo with "Long Horizons · Structural Shifts · Imagination" tagline baked into the asset. Per §6c.12, this is the single source of truth for the logo across PDFs and website.

**Fonts** (in `/public/assets/fonts/` — unzip `ar2eb-fonts__v001__2026-05-18_03-30.zip` here):
- Inter-Regular, Inter-Medium, Inter-SemiBold, Inter-Bold, Inter-Italic (OFL)
- JetBrainsMono-Regular, JetBrainsMono-Bold (OFL — license included)

**Canonical PDFs** (in `/public/memos/`):
- `joby-memo__v028__2026-05-18_04-00.pdf`
- `aur-memo__v022__2026-05-18_04-00.pdf`
- `lth-memo__v021__2026-05-18_04-00.pdf`
- `zm-memo__v020__2026-05-18_04-00.pdf`

**Deprecated** (do not bring forward unless needed for site reference):
- The four `{ticker}-dcf-valuation__*.jsx` files. These were the prior canonical data store; data has fully migrated to `/data/*.yml`. Their `synced with` PDF references may be useful one last time for the site copy, then drop.
- The four `generate_{ticker}_memo_*_chartfix14.py` files. Superseded by `memo.py`. Drop after verification that `memo.py` produces matching output.

---

## What I want you to do FIRST

**Setup phase** (before any feature work):

1. Read `/spec/memo-spec__v020__*.md` end-to-end. Internalize the fourteen §6c rules and the data schema.

2. Read `memo.py` end-to-end. Map the structure:
   - Top: `parse_args()` + `load_data(ticker)` + dispatch helpers (`subtitle_for`, `ribbon_metrics`, `assumptions_rows`, `equity_build_rows`, `dcf_period_years`, `format_masthead_extras`)
   - Scenarios loaded from YAML via `_flatten_scenario` (turns nested `dcf_path`/`dcf_metrics`/`chart_data` into flat dict the rendering code expects)
   - Then page-by-page rendering (P1 → P5)

3. Read `data/joby.yml` end-to-end. This is the canonical data shape. Note the dispatch fields (`dcf_type`, `dcf_metrics`, `dcf_path`) and how they differ across the three DCF types — compare to `zm.yml` for SOTP variant and `lth.yml` for plain mature.

4. **Path translation** — `memo.py` and `build_*_charts.py` have `/home/claude/` paths hardcoded throughout. Translate per the table below.

| Path in source | Files affected | Canonical replacement |
|---|---|---|
| `LOGO_UNIFIED = "/home/claude/ar2eb-logo-v3-cropped.png"` | `memo.py` (one line) | `public/assets/ar2eb-logo-v3-cropped.png` |
| `FONT_DIR = "/home/claude/fonts/ttf"` | `memo.py`, all 4 chart builders | `public/assets/fonts` |
| `JBM_DIR = "/mnt/skills/examples/canvas-design/canvas-fonts"` | `memo.py` (one line) | `public/assets/fonts` — flatten Inter + JetBrains Mono into one directory |
| `CHARTS_DIR = f"/home/claude/{TICKER}_charts"` | `memo.py` (one line, templated) | `charts/{ticker}` |
| `OUT = '/home/claude/{ticker}_charts'` | All 4 chart builders | `charts/{ticker}` (matches `memo.py`'s CHARTS_DIR) |
| `OUT_PATH = f"/mnt/user-data/outputs/{TICKER}-memo__v999__refactored.pdf"` | `memo.py` (one line, templated) | `public/memos/{ticker}-memo__{version}__{timestamp}.pdf` — version-stamping is a workflow decision; see below |

5. Run end-to-end:
   ```bash
   python charts/build_joby_charts.py
   python memo.py joby
   ```
   Should produce a PDF in `public/memos/`. Compare visually against the canonical `joby-memo__v028__2026-05-18_04-00.pdf` already in the bundle. Expect three classes of cosmetic differences:
   - Computed upside values may differ by ±0.1 pp (canonical hardcoded; `memo.py` computes from `(expected/spot - 1) * 100`)
   - Masthead "cash & debt" string formatting may differ slightly per ticker (e.g. canonical says "$7.8B cash, zero debt" vs `memo.py`'s generic formatter)
   - ZM SOTP equity build row labels: `memo.py` outputs "+ Anthropic stake" (named); canonical says "+ Anthropic stake" too — should match

   If you see substantive differences (wrong numbers, missing charts, layout shifts), flag those before proceeding.

6. Repeat for AUR, LTH, ZM. All four should match.

7. **Version-stamping decision**: the canonical PDFs are `joby-memo__v028__*`, `aur-memo__v022__*`, etc. Once you confirm `memo.py` produces matching output, the next regeneration bumps these to v029 / v023 / v022 / v021. Codify this in a small helper script (`bump_pdf_version.sh` or similar) — the convention is `{name}__v{NNN}__{YYYY-MM-DD_HH-MM}.{ext}` per the design system in user preferences.

**Then**, once setup is solid, proceed to feature work:

8. Mobile-optimize the site (when Claude Design export lands).
9. Wire up routing so each memo's category/ticker resolves correctly.
10. Build a `rebuild-all.py` or `make build-memos` that regenerates all four PDFs in one command and updates references everywhere they appear.
11. **(Optional, ~45 min)** Polish `young_company__DRAFT__needs_visual_polish.py` to match canonical chart output. Same trick for `mature_company.py` (LTH + ZM). Once both work, drop the four per-ticker chart builders. This collapses chart code from ~2,000 lines (4 files) to ~1,200 lines (2 files).

---

## Conventions to know

**Versioning**: `{name}__v{NNN}__{YYYY-MM-DD_HH-MM}.{ext}` for anything we revisit (memos, spec, data files, etc.). Three-digit version, zero-padded. Each material edit bumps version + timestamp. Old versions stay — never overwrite. The `data/*.yml` files currently use 2-digit `v{NN}` for backward compatibility; can migrate to 3-digit when convenient.

**In-file stamp**: every versioned artifact has a stamp in the header (text) or footer (visual). Format: `v001 · 2026-05-18_HH-MM · synced with {paired_artifact}`. See top of `memo-spec__v020` for an example.

**Design system**: Inter sans + JetBrains Mono (numbers/data/stamps); single accent (desaturated indigo `#1e3a8a`); restraint over decoration; whitespace is content; tabular numbers right-aligned. Full design system in spec §6c.

**Tone for prompts/specs**: prose for documents, tables for structured data, decisions presented as a table with `# | Question | Recommendation | Confidence | Rationale` columns when feedback is needed. Per Arthur's `userPreferences`.

**Don't refactor without explicit go-ahead.** Surface concerns as decisions, not unilateral changes.

---

## What this thread did NOT solve (out of scope for migration)

- Chart-builder parameterization. Draft included; ~45 min to ship.
- Cross-ticker site copy (per-ticker page templates, category page, memo index). That's the Claude Design export, coming separately.
- Production deployment pipeline. Will design that in Claude Code with full tooling.
- Test coverage for `memo.py`. No tests written yet; could add property-based tests for the YAML loader + flatten logic.

---

## Trust the spec

When in doubt about layout, typography, color, or page structure — read the spec section. Fourteen §6c rules cover everything that's been hand-tuned over dozens of iterations. Don't re-derive from scratch.
