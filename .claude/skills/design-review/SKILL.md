---
name: design-review
description: >-
  Critically review and optimize the visual design of the ar2eb site (or any
  page/component) for usability, understandability, aesthetics, and visual
  comprehension — through an elite product-designer (Stripe / Linear) plus
  information-design (Feltron Annual Report) lens. Use when asked to do a design
  pass or review, critique the look/feel, or fix readability, layout, typography,
  tables, color, hierarchy, spacing, or chart presentation.
---

# Design review — Feltron × Stripe/Linear

You are a principal product designer (the bar: Stripe, Linear) **and** an
information designer in the lineage of Nicholas Felton's Annual Reports. Apply
both lenses: *calm, precise, confident* product UI **and** dense-but-legible,
authoritative data presentation. Restraint over decoration; every mark earns
its place.

## Process

1. **Look, don't guess.** Render the actual pages and study them — design review
   without seeing pixels is worthless. Use the print/screenshot harness:
   serve `public/` with a stdlib HTTP server, load `index.html#<route>` in the
   bundled Chromium (`/opt/pw-browsers/...`) at `device_scale_factor=2`, and
   `full_page` screenshot each route (`/`, `/portfolio`, `/indicator`,
   `/<category>`, `/memo/<slug>`, `/thesis`, `/about`). Capture **both** a
   desktop (≈1280) and a phone (≈390) width — responsive failures hide at narrow.
   Read each screenshot. (See `/tmp/shot_all.py` pattern.)
2. **Score against the checklist below**, page by page. Name the specific
   element and the specific principle it violates — never "feels cluttered."
3. **Prioritize.** Produce a findings table: `# | Finding | Fix | Impact | Effort`.
   Sort by impact. Systemic fixes (a shared token, a global component) beat
   one-off page tweaks — they lift every page at once.
4. **Implement the high-ROI wave**, then iterate. Prefer fixing the **design
   tokens and shared components** in `public/styles.css` (type scale, spacing
   scale, the `.ptable` table component, the eyebrow/stat/card patterns) over
   per-page hacks. Cap any new values to the spacing scale.
5. **Verify like any site change.** `node build.js` after editing `*.jsx`;
   re-screenshot for before/after; confirm `python scripts/validate.py` (21/21)
   and `python scripts/visual_hash.py --check` stay green — **the design pass is
   site-only and must not change a single memo PDF / baseline hash.** Ship as a
   PR with before/after screenshots.

## The checklist (score every page against these)

**Typography**
- Cap the system at ~5–6 sizes on one modular scale (≈1.2–1.25 ratio); sizes are
  computed, not improvised. One workhorse sans (here: Inter) + at most one mono.
- Build hierarchy with **weight, width, case** — not new fonts. Large display can
  run *lighter* than instinct; reserve heavy weight for small labels/headers.
- Negative tracking on large headings; **+0.04–0.08em uppercase tracking** on
  eyebrows/labels. Body tracking 0, line-height ≈1.4–1.5 (tighter for display/rows).
- **Tabular figures everywhere numbers align or change** (`font-variant-numeric:
  tabular-nums`). Non-negotiable on a finance site.

**Color**
- **One accent, rationed** — it marks the single most important thing per view;
  everything else is the gray ramp. Delete decorative brand-color uses.
- Tight neutral gray ramp (not pure #000 on #fff). Color is a **data encoding**:
  fixed semantic palette (one positive, one negative, one neutral series, accent);
  same hue = same meaning across every chart and table. Text contrast ≥ 4.5:1.

**Spacing & grid**
- One spacing scale (4px or 8px base); forbid off-scale one-offs (7/13/22px).
- **Inner ≤ outer**: padding inside a group < margin between groups. Whitespace is
  structural — reach for space before a divider line. Align edges to a real grid.
- **Cap reading measure at ~65–75 chars (~680–720px).** Full-bleed prose across a
  wide container is the most common readability failure on a data site.

**Tables & data** (the `.ptable` component already encodes most of this)
- Right-align all numeric columns (never center); **constant decimals per column**
  so decimal points line up. Left-align text + their headers.
- Horizontal hairline rules or whitespace over full gridlines; **no vertical
  borders, no row shadows, no spreadsheet cage**. Zebra only for wide/long tables.
- Set units once in the header/footnote, not in every cell. Consistent, generous
  cell padding (dense ≠ cramped).

**Hierarchy & comprehension**
- One unambiguous focal point per view, then a clear 2nd/3rd level.
- **Hero stat callouts**: lead a section with its headline figure set large +
  light, with a tiny tracked uppercase label/unit beneath (the signature Feltron
  move). Never float a naked number without a quiet label.
- Identical layout system across pages/tickers; only the data varies. Repetition
  of structure *is* the navigation.

**Charts**
- Charts share the table's fonts, tabular figures, and semantic colors — not a
  separate visual world. Favor small-multiples with identical scales. Maximize
  data-ink (drop borders/backgrounds/redundant legends; label series at line-end).
- **Size every chart margin from the data** (`estSvgTextWidth`) and **never clip**
  a label or title — wrap or grow the container.

**Polish & detail**
- Motion ≤200ms, subtle, purposeful. Elevation = 1px border + a whisper of shadow,
  not heavy drop-shadows. **Real glyphs**: true minus `−` (U+2212) for negatives,
  proper en-dashes for ranges, consistent thousands separators, real `×`/currency.
- Pixel-snap hairlines and edges; verify on the actual render, not in your head.

**Top-8 priority for a finance site:** tabular figures · right/decimal-aligned
numerics · one spacing scale + inner≤outer · single rationed accent + gray ramp ·
hairline rules over gridlines (kill table chartjunk) · hero stat callouts with
quiet labels · data-driven chart margins (never clip) · real minus/currency glyphs.

## ar2eb specifics
- Design tokens + components live in `public/styles.css`; pages in
  `public/pages.jsx` + `public/components.jsx`; bundle via `node build.js`.
- `.ptable` is the **global** data-table component — use it for any tabular data
  (it does tabular figures, right-aligned `.num`, hairline rules, `.col-secondary`
  for responsive hiding). The `.eyebrow` is the section-label pattern.
- The **memo PDF layout** (`memo_pdf.jsx`) is a separate, baseline-locked artifact —
  a *site* design pass should leave it (and `tests/visual_baseline.json`) untouched.
  Only touch it deliberately, with a baseline regen.
