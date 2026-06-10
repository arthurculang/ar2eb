# Prompt for Claude Design: Alameda Research 2 site

*v004 · 2026-05-18_19-00 · standalone artifact (no synced counterpart)*

## Changelog

- **v004** (2026-05-18_19-00) — Tagline updated to match new logo asset (v3). The current canonical tagline is "Long Horizons · Structural Shifts · Imagination" (replacing v003's "Asymmetric Technocultural Sortino Juice."). Tagline is baked into the logo asset itself (`ar2eb-logo-v3-cropped.png`, 1990×458, AR ≈ 4.34) — do not render as separate text on the site. Brand identity + hero band updated to reflect new tagline.

- **v003** (2026-05-18_03-30) — Collapsed the two-tagline distinction from v002. New logo bakes the tagline directly into the mark; site no longer renders it as separate hero text.

- **v002** (2026-05-18_01-30) — Added public-facing hero tagline distinct from formal logo tagline.

- **v001** (2026-05-18_01-00) — Initial Claude Design prompt covering site structure, design system, page templates, disclaimer requirements, technical handoff.

---

Build a research-distribution website for **Alameda Research 2: Electric Boogaloo** (AR2EB) — a personal investment research operation publishing probability-weighted DCF memos on individual equities. The site is a public-facing index that lets visitors browse memos and access the PDFs directly. No accounts, no paywall, no comments — it's a clean reading-room.

## Brand & design system

**Brand identity**:
- Name: Alameda Research 2: Electric Boogaloo (AR2EB for short)
- **Tagline** (baked into the logo asset itself, beneath horizontal rule): "Long Horizons · Structural Shifts · Imagination." — three-pillar framing that signals time-horizon discipline + structural-thesis investing + creative scope. Do not re-render this as separate text on the site; it's already part of the logo PNG.
- Logo: boxed AR2EB monogram + ALAMEDA RESEARCH / 2: ELECTRIC BOOGALOO stacked headline + tagline beneath horizontal rule, all in one mark. Logo asset attached as `ar2eb-logo-v3-cropped.png` (1990×458, AR ≈ 4.34). Preserve aspect ratio at all rendering sizes. Works at 200pt+ for hero placement and 100pt+ for running-header placement.

**Design system** (matches the PDF memos so the brand reads consistent from web → PDF):

- **Typography**: Inter for sans (universal), JetBrains Mono for code/data/numbers. No serif.
- **Color**: neutral grayscale base. Single accent — a desaturated dark-blue/indigo (think Linear's accent — `#3a4ce0` ish, dial saturation down). Semantic colors only where meaning is carried: red for negative price action, green for positive, deep purple (`rgb(118, 41, 166)` / `#7629a6`) ONLY for "ultra-bull" scenario references. No gradients, no shadows, no decoration.
- **Spacing**: 4px base unit. Document mode (this site is a document, not a product surface). Generous margins (96px+ on desktop, 24px on mobile). Whitespace is content.
- **Hierarchy through type and space**, not chrome. Headings semibold, never bold-and-boxed. Body 16-18px desktop, 15-16px mobile.
- **Tables**: tabular figures, right-aligned numbers, headers semibold with narrow rule below — never bold-and-boxed, never with fill colors.
- **Icons**: lucide only. Mono-line, single weight throughout. Icons earn their place — no decoration.
- **Border-radius**: small (4-6px) or zero. No pill shapes.
- **Dual reference**: Linear (product polish, restraint) and Stripe Press (editorial gravitas, generous whitespace). This site leans Stripe Press — it's a document.

## Site structure

```
/                            home / overview
/asymmetrical-moonshots      category index
/fcf-plus-plus-growth        category index
/memo/joby                   memo detail
/memo/aur                    memo detail
/memo/lth                    memo detail
/memo/zm                     memo detail
/disclaimers                 full disclaimer page
/about                       about the operation
```

## Home page

Hero band:
- Logo (large — 280-320px wide). The tagline ("Long Horizons · Structural Shifts · Imagination.") is part of the logo asset itself; do not duplicate it as separate text.
- Single positioning sentence beneath the logo (16-18px Inter regular, muted color, generous whitespace above): "Probability-weighted DCF research on individual equities. Asymmetric bets and free-cash-flow compounders."

Below the hero, two category cards side-by-side (stacked on mobile):

**Asymmetrical Moonshots**
- Subtitle: "Young-company DCFs. Compound conditional tails. Show your work."
- Brief description: "Pre-revenue or pre-profitability category-defining companies where the standard 5-year DCF generates nonsense. The young-company framework asks what mature TAM share is plausible, what terminal margins look like at scale, and what probability of outright failure. Three scenarios plus an ultra-bull tail, weighted; show your work."
- Memo count badge
- Click → `/asymmetrical-moonshots`

**FCF++Growth**
- Subtitle: "Mature-company DCFs. Cash machines with optionality."
- Brief description: "Established businesses generating real free cash flow today, with credible paths to growth-rate inflection. The mature-company framework uses 5-year explicit DCFs with terminal-value treatment, and prices in the bull case where the company gets re-rated AS WELL AS executes operationally."
- Memo count badge
- Click → `/fcf-plus-plus-growth`

Beneath the cards, a "Recent memos" strip (3-4 most recent across categories) with title, ticker, date, and one-line headline.

Footer: standard disclaimer strip (see disclaimer section below) + link to /disclaimers + link to /about.

## Category index pages

`/asymmetrical-moonshots` and `/fcf-plus-plus-growth` follow the same template. Top of page:

- Category name as H1
- Category description (same as the home-page cards but expanded — 2-3 sentences)
- Filter/sort affordance: dropdown for "Newest first / Oldest first" (visual only, no backend needed yet)

Memo list: each entry is a horizontal card with:
- Ticker badge on left (e.g. "JOBY", "AUR" — monospace, bordered, ~40-50px square)
- Company name + ticker on first line, semibold (e.g. "Joby Aviation · NYSE: JOBY")
- DCF type on second line, smaller muted (e.g. "Young-Company DCF (Damodaran)")
- One-line central question (e.g. "Will Joby capture meaningful share of a $250B global UAM TAM by 2036 — or is today's $10B market cap pricing certainty that competitive eVTOL economics don't support?")
- Right-aligned: spot price, probability-weighted expected fair value, % vs spot in red/green (Mono, right-aligned, tabular figures)
- Click anywhere on the card → memo detail page

Categories map to tickers:
- **Asymmetrical Moonshots**: JOBY, AUR
- **FCF++Growth**: LTH, ZM

Card hover state: subtle background lift (no shadow — change background-color a notch). Cursor pointer.

## Memo detail pages

`/memo/[ticker]`. Each page renders:

**Header band**:
- Logo (small, 110px wide, top-left, links to /)
- Eyebrow: INTERNAL RESEARCH · MEMO · NOT INVESTMENT ADVICE · AI-ASSISTED (small caps, accent color)
- H1: Company name (e.g. "Joby Aviation")
- Sub-line: ticker · exchange · DCF type · key metrics (mkt cap, share count, cash)
- Right-aligned spot price (large, Mono)

**Central question** (large, ~22-28px Inter, generous line-height):
> "Will Joby capture meaningful share of a $250B global UAM TAM by 2036 — or is today's $10B market cap pricing certainty that competitive eVTOL economics don't support?"

**Probability-weighted expected value** ribbon (Linear-style, restrained):
- $X.XX expected fair value today
- ±Y% vs spot $Z.ZZ
- Below: forward compounded value at +5y / +10y / +15y / +20y (each with × spot multiple)

**Four scenario cards** in a 4-column grid (collapse to 2x2 on tablet, single column on mobile):
- BEAR / BASE / BULL / ULTRA BULL
- Each card: probability, expected price, % vs spot, one-line headline
- Each card has color-coded accent (red for Bear, neutral for Base, green for Bull, deep purple for Ultra Bull)

**PDF download CTA** (sticky on desktop right rail, inline on mobile):
- Big button: "Read full memo (PDF)"
- File size label below
- Linked to the actual PDF: `joby-memo__v025__2026-05-18_01-00.pdf` (and equivalent for other tickers — exact filenames will be provided when PDFs are uploaded)

**Scenario narratives** (full text from Page 2 of the PDF — reproduce inline):
- 4 columns on desktop, 2x2 on tablet, single column on mobile
- For each: label / price / probability / headline / WHY paragraph / WHAT HAPPENS paragraphs

**Methodology note** at the bottom (small, muted):
- "DCF framework: [Damodaran young-company three-scenario or mature-company 5y-explicit DCF with SOTP]. Probability weighting: [Bear/Base/Bull/Ultra Bull breakdown]. Spot price reference: [date]."

**Disclaimer strip** (always at footer of every memo page).

## Disclaimer / Not investment advice

Must appear:
- At the bottom of every memo page
- As a footer on every site page
- Full-text on /disclaimers

**Full disclaimer text** (use exactly):

> **Not investment advice.** This research is published for educational and informational purposes only by an individual not registered as an investment advisor. Nothing on this site constitutes a recommendation to buy, sell, or hold any security, or a solicitation to make any investment decision.
>
> **AI-assisted analysis.** Research is produced with assistance from large language models (Claude, primarily). Numbers, scenarios, and probability weights reflect the author's independent judgment; LLM-generated content is reviewed and edited before publication. Errors and omissions remain the author's responsibility.
>
> **Author may hold positions.** The author may hold long or short positions in any security discussed, and may transact in those securities at any time, without notice. Position disclosures are not provided.
>
> **No warranties.** Information is provided on an "as is" basis. The author makes no representations as to accuracy, completeness, or fitness for any particular purpose. Past performance is not indicative of future results. Probability-weighted expected values are model outputs, not predictions.
>
> **Do your own research.** Consult a registered investment advisor before making any investment decision.

Footer strip (every page): "NOT INVESTMENT ADVICE · Not from a registered investment advisor · AI-assisted analysis · Author may hold positions · [See full disclaimers]" — last item links to /disclaimers.

## About page

Short and personal:
- Who: an individual investor running a single-operator portfolio with a concentrated, single-name conviction approach.
- What: publishing the same probability-weighted DCF research used internally, so the work product gets pressure-tested by readership rather than sitting in private docs.
- Method: probability-weighted DCFs with explicit scenarios (Bear / Base / Bull / Ultra Bull), Damodaran young-company framework where appropriate, and mature-company DCFs with SOTP framing where there's significant non-operating value.
- Cadence: irregular — research is published when conviction crystallizes, not on a schedule.
- Contact: arthur@culang.co

## Technical notes for Claude Design

- Build with HTML/CSS/JS or React (Next.js if React) — your call based on what exports cleanly. The final destination is a GitHub repo + static hosting (Vercel or Netlify probably).
- No backend needed at this stage. The four memo PDFs are static assets; the site is essentially a wrapper + index over them.
- Make routing simple — top-level pages plus dynamic `/memo/[ticker]` routes.
- All PDF references should use the exact filenames I'll provide (versioned with timestamps per the spec convention).
- Include a `/public/memos/` (or equivalent) directory structure for PDF placement so I can drop files in once exported.
- Responsive: mobile-first, but desktop is the primary reading experience. 768px and 1024px breakpoints.
- Accessibility: semantic HTML, alt text on the logo, keyboard navigation, ARIA labels where appropriate.

## Hard constraints (do not violate)

- No emojis anywhere on the site.
- No drop shadows unless functional.
- No multi-color palettes — neutrals + one accent + semantic red/green/purple only.
- No pill-shaped buttons or rounded-everything aesthetic.
- No animated decoration. Transitions on hover state only (200ms ease).
- Numbers in tables: tabular figures, right-aligned, monospace.
- The disclaimer strip is non-negotiable and appears in the footer of every page.

## Deliverable

Build the site as a single project. Pages: `/`, `/asymmetrical-moonshots`, `/fcf-plus-plus-growth`, `/memo/joby`, `/memo/aur`, `/memo/lth`, `/memo/zm`, `/disclaimers`, `/about`. I'll provide PDF assets and final memo content separately once you have a draft structure ready — for now, use placeholder memo content drawn from the descriptions above and lorem-equivalent for the scenario narratives.
