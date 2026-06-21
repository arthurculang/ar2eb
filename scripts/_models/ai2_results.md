# Arthur Indicator — AI 1.0 vs AI 2.0: backtest results (of record)

Verbatim output of `scripts/_models/ai2_backtest.py` on the sourced 104-name panel
(`ai2_panel.csv`, 1,483 rows / 111 tickers / FY2007–26). Deterministic — re-running
the flags below reproduces these tables. Methodology in spec §13; changelog v032/v034/v035.

**Method.** Within each fiscal-year cross-section, rank *cheapness* (`−AI`) against the
forward (1y / 3y) return; take the Spearman rank-IC; judge generalization by
**leave-one-year-out out-of-sample (LOYO-OOS)**, never in-sample. AI 1.0 is the
zero-free-parameter special case `w1=w2=1` (`Q = GrossMargin + RevGrowth`); any
enrichment must beat it *out-of-sample* to earn its weights.

---

## TL;DR

- **The full 8-weight AI 2.0 overfits.** In-sample IC rises with parameters; LOYO-OOS does not
  (it goes negative / sign-flips). On 104 names the unconstrained fit: in-sample +0.107 (3y) →
  **LOYO-OOS −0.034 (3y)**.
- **No enrichment beats AI 1.0 OOS at *both* horizons** — not the FCF-margin term, the
  operating-margin term, any Δ (rate-of-change) term, or the full eight weights. Each wins one
  horizon and loses the other.
- **An exhaustive deterministic grid confirms it** — ~2,500 of 15,625 combinations beat AI 1.0
  in-sample (with economically backwards, negative-margin weights), but nested out-of-sample the
  best still wins one horizon and loses the other. The random search missed nothing.
- **AI 1.0 itself is validated** — positive and stable OOS at **both** horizons (+0.044 / +0.063).
- The FCF-margin term that beat AI 1.0 on a narrow 26-name panel (v034) was a **small-sample
  artifact** — it does not survive the 104-name universe (L3 → −0.041 at 3y).

**Verdict: AI 1.0 (`scripts/arthur_indicator.py`) is the screen; AI 2.0 earns none of its eight weights.**

---

## 1. The 8-weight fit overfits  — `ai2_backtest.py`

```
panel: 1483 rows · 111 tickers · 20 fiscal years · horizon 3y

AI_1.0 (gm+g):  rank-IC = +0.074  over 15 cross-sections  (coverage 71%)
AI_2.0 (fitted): rank-IC = +0.107  over 15 cross-sections  (coverage 64%)
  weights:  g=+1.80  gm=+0.00  opm=+0.10  fcfm=+0.10  Δg=+0.12  Δgm=-0.15  Δopm=-0.08  Δfcfm=+0.78
  leave-one-year-out OOS rank-IC = -0.034  (15 folds)

lift (in-sample): +0.034   AI_2.0 helps   ← in-sample only; OOS is NEGATIVE
```

(For reference, the narrow 26-name panel, v034: in-sample +0.156/+0.212 at 3y/1y but LOYO-OOS
−0.063/−0.068, weights sign-flipping across horizons.)

## 2. Nested model ladder  — `ai2_backtest.py --select`

Each model fit with Δ-weights sign-constrained ≥ 0; judged by LOYO-OOS at both horizons.

```
model                 k    IS-3y  OOS-3y    IS-1y  OOS-1y
----------------------------------------------------------------
AI 1.0  (g,gm @1,1)   0   +0.074  +0.044   +0.062  +0.063
L2  g,gm              2   +0.092  -0.015   +0.085  +0.078
L3  +fcfm             3   +0.096  -0.041   +0.096  +0.080
L4  +opm,fcfm         4   +0.096  -0.022   +0.098  +0.078
L4+Δfcfm              5   +0.098  +0.013   +0.100  +0.054
L2+Δg,Δgm             4   +0.110  +0.053   +0.096  +0.052
Full-8                8   +0.113  +0.041   +0.110  +0.074
----------------------------------------------------------------
AI 1.0 OOS baseline:  3y +0.044   1y +0.063
```

No model beats AI 1.0 OOS at **both** horizons. In-sample IC climbs monotonically with parameters
(+0.074 → +0.113 at 3y); OOS does not — the textbook overfit signature.

## 3. Parsimonious "AI 1.0 + λ·fcfm"  — `ai2_backtest.py --fcfm`

The single most-promising enrichment (one knob), λ chosen by OOS.

```
    λ    IS-3y  OOS-3y    IS-1y  OOS-1y
----------------------------------------
 0.00   +0.074  +0.044   +0.062  +0.063     (λ=0 ≡ AI 1.0)
 0.10   +0.072  +0.043   +0.062  +0.065
 0.20   +0.067  +0.039   +0.063  +0.067
 0.30   +0.062  +0.031   +0.058  +0.061
 0.40   +0.063  +0.034   +0.062  +0.066
 0.50   +0.059  +0.029   +0.059  +0.064
 0.60   +0.056  +0.024   +0.051  +0.055
 0.70   +0.051  +0.018   +0.044  +0.047
 0.80   +0.044  +0.011   +0.036  +0.040
 0.90   +0.042  +0.009   +0.034  +0.039
 1.00   +0.035  +0.002   +0.026  +0.031
 1.10   +0.044  +0.013   +0.032  +0.037
 1.20   +0.041  +0.010   +0.025  +0.032
 1.30   +0.038  +0.007   +0.023  +0.030
 1.40   +0.036  +0.006   +0.020  +0.027
 1.50   +0.038  +0.006   +0.024  +0.029

3y: in-sample-optimal λ = 0.00 · nested-LOYO OOS (λ re-fit per fold) = +0.044  (vs AI 1.0 +0.044)
1y: in-sample-optimal λ = 0.20 · nested-LOYO OOS (λ re-fit per fold) = +0.058  (vs AI 1.0 +0.063)
```

The honest nested-LOYO (λ re-fit on each training fold) does **not** beat AI 1.0: 3y picks λ=0
(no improvement); 1y is +0.058 vs AI 1.0's +0.063 (slightly worse). The FCF-margin term adds nothing.

## 4. Exhaustive deterministic grid (belt-and-suspenders)  — `ai2_backtest.py --grid`

15,625 fixed combinations of the 6 added weights ∈ {−1, −0.5, 0, 0.5, 1}, g=gm=1 fixed, no sampler.

```
AI 1.0 OOS baseline:  3y +0.044   1y +0.063
combinations beating AI 1.0 OOS at BOTH horizons (in-sample): 2462 / 15625
  best-both:  opm=-1.0  fcfm=-1.0  Δg=0.0  Δgm=-1.0  Δopm=-1.0  Δfcfm=+0.5  → 3y +0.104 / 1y +0.112
  best single horizon:  3y +0.160 (vs +0.044)   1y +0.112 (vs +0.063)
nested grid-LOYO (best grid w chosen per train fold, scored OOS):
  3y +0.084  (AI 1.0 +0.044)     1y +0.032  (AI 1.0 +0.063)
```

~2,500 combinations "beat" AI 1.0 in-sample — but the best loads operating- and FCF-margin
**negatively** ("worse margins = cheaper"): noise-fitting. Nested OOS, the best still wins one
horizon (3y +0.084) and loses the other (1y +0.032). The random search missed nothing.

## 5. Empirical valuation zones  — `zone_returns.py` (point-in-time quarterly)

Forward return by AI 1.0 *level* — grounds the green/yellow/orange/red bands. This is the
**point-in-time quarterly** cut (the one the `/indicator` page shows): mean over all quarterly
rows in the zone (overlap is unbiased for a mean), win-rate over NON-OVERLAPPING windows only
(one per name every 3 years → honest hit-rate at a true smaller N).

```
AI 1.0 valuation zones — 3y forward return by band  (point-in-time quarterly panel; 103 names / 61 xs)

  band                                      n     mean   median   win%(N, non-overlap)
  GREEN  · extremely undervalued (<6)    1194  +124.4%   +70.1%   82%  (146)
  YELLOW · somewhat undervalued (6-10)    616   +89.0%   +66.9%   82%   (89)
  ORANGE · somewhat overvalued (10-15)    454   +91.8%   +62.0%   76%   (54)
  RED    · extremely overvalued (>15)     486   +41.2%   +14.6%   67%   (30)
```

GREEN clearly best, RED clearly worst, and the ordering falls **straight down the zones** (the
mean 3y return and the non-overlapping win-rate both decline monotonically). Median 3y is even
cleaner (+70/+67/+62/+15) — RED's +41% mean is propped up by a few outliers. Absolute returns are
inflated by the 2009–24 bull sample; the durable takeaway is the **ordering** (cheaper → higher
forward return), the effect the rank-IC validated. A screen, not a timing tool — confirm with the
memo DCF (§6) before acting.

*(The legacy annual `ai2_backtest.py --zones` cut read GREEN 3y +159%/87% → RED +48%/58% — same
shape, higher absolutes; superseded by the point-in-time quarterly table above.)*

**Bands (validated):** GREEN < 6 · YELLOW 6–10 · ORANGE 10–15 · RED > 15 (EV / (Rev × (GM + growth))).

---

## Reproduce

```
pip install numpy
python scripts/_models/ai2_backtest.py            # full 8-weight fit (3y)
python scripts/_models/ai2_backtest.py --select   # nested ladder (both horizons)
python scripts/_models/ai2_backtest.py --fcfm     # AI 1.0 + λ·fcfm
python scripts/_models/ai2_backtest.py --grid     # exhaustive deterministic grid
python scripts/_models/ai2_backtest.py --zones    # empirical valuation bands
python scripts/_models/ai2_backtest.py --robustness  # IC significance / t-stat per horizon
```

## Significance — is the IC robust? (`--robustness`)

Positive but **not yet statistically significant**. Per-fiscal-year ICs (AI 1.0 weights), then the
t-stat (≈ mean / (std/√N_years); >2 is the conventional "real, not luck" bar):

```
 horizon   N years   mean IC    std    t-stat   % years +
 1-year      17      +0.063    0.229   +1.14      59%
 3-year      15      +0.044    0.188   +0.90      47%
```

Directionally positive every way it's sliced (both horizons, both halves), but t-stat ~1, under 2.
Structural, not fixable by adding names: the value effect runs hot/cold year to year (yearly IC
swings −0.31…+0.56), so its per-year std (~0.2) dwarfs its mean (~0.05), and ~16 annual cross-sections
can't pin that mean down. Decomposition: at ~53 names/year the within-year sampling std is already
only ~0.14, so **more names barely moves the t-stat** — the real lever is **more time periods**
(quarterly/monthly cross-sections, ~4–12× the count), which needs a point-in-time quarterly panel
rebuild.

## Quarterly panel — the robustness rebuild (`source_ai2_quarterly.py`)

Built it: rebalance every calendar quarter-end 2009–2024 (point-in-time by SEC **filing date** —
no look-ahead), **3,399 rows · 61 cross-sections · 103 tickers**. Because quarterly sampling of
1y/3y forward returns **overlaps**, a naive t-stat would be inflated, so we apply a **Newey-West
(Bartlett)** correction, and also report a non-overlapping 1-quarter horizon.

```
 horizon                         mean IC   naive t   Newey-West t   verdict
 1-quarter (non-overlapping)      -0.011    -0.40      -0.40 (L=0)   noise
 1-year     (overlap-corrected)   +0.004    +0.18      +0.13 (L=3)   noise
 3-year     (overlap-corrected)   +0.052    +3.17      +2.21 (L=11)  SIGNIFICANT (|t|>2)
```

**The 3-year horizon is statistically significant** — Newey-West t ≈ +2.2, stable **above 2 for every
Bartlett lag from 4 to 20** (+2.6 → +2.1), positive in **both halves**, 67% of cross-sections positive.
1q/1y are noise → **value is a slow signal**.

### Market-neutral read (`--longshort`)

The IC's dollar twin: each quarter long the cheapest AI tercile, short the richest, hold 3y. The bar
is the **spread** (cheap − rich), which differences out the market (beta) — NOT absolute return and
NOT "beat the S&P." On the growth/quality universe: **long-short +51%/3y, NW t +2.46, 77% of quarters
positive**. The cheap bucket beat the S&P by +98% — *but the rich bucket beat it by +47% too*, so most
of the raw outperformance is the universe + a 2009–25 bull + survivorship; only the **spread** is the
Indicator's edge.

### Versatility — does it generalize? **NO** (`--broad`)

Re-ran the whole test on a **broad 794-name, all-sector universe** (value/cyclical/staples/industrials/
defense — harvested from the SEC XBRL *frames* API, `harvest_broad_universe.py`, not hand-picked):
**25,123 rows · 62 cross-sections · ~400 names/quarter**. The edge **does not survive**:

```
 long-short 3y spread          mean    NW t   quarters+
 growth/quality (~111 curated) +48%   +1.88     73%
 broad-economy (~600 others)   +5.5%  +0.69     50%
 whole broad universe          +2.3%  +0.31     56%
```

On the broad market the cheap-minus-rich spread is a **coin flip** (50% of quarters), and the 3-year
IC is even slightly negative (−0.028). **The Indicator is NOT a universal value factor** — it's a
relative screen that works *among quality-growth compounders* (cheap value/cyclical names are often
cheap for a reason). The significant result is real but **universe-specific**. This is the honest
scope, and it is exactly why §12 uses it only as a *gentle* tilt on a growth/quality book — never
leaned on, never as a market-wide signal. *Caveat:* both universes are survivors (today's filers).
Reproduce: `source_ai2_quarterly.py --analyze` (narrow) · `--broad` (broad) · `--longshort`.

A 2-page visual summary of the earlier (annual) work is in `public/ai2_report.jsx`
(render: open `public/ai2_report.html` via the print harness).

## Data limitations (documented)

- ~14 high-quality compounders (ORCL/V/MA/INTU/CDNS/TMO/SBUX…) stopped tagging a consolidated
  gross profit in companyfacts after ~2018 (the API drops total/dimensional cost lines), so their
  recent gross-margin rows are absent and they partly drop. Fabricating a margin would break
  conviction-neutrality (§3.5 B).
- Fiscal-year cross-sections group by period-end-year label, so a Jan-FYE name's "2024" is ~11
  months offset from a Dec-FYE name's; forward returns are within-ticker self-consistent.
