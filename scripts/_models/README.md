# Modeling record (the "model the DCF in python for internal consistency" step)

Reusable DCF engines that reproduce `scripts/validate.py` + `scripts/scaffold_ticker.py`
math to the cent (verified: model_dcf vs RKLB, model_mature vs ZM):
- `model_dcf.py`    — young_company (Damodaran): reinvest=Δrev/s2c, Gordon terminal, expected=(1-pf)·dcf+pf·distress, cash-runway check.
- `model_mature.py` — mature_company: fcf=rev·fcf_margin (or provided), Gordon/exit terminal, expected=dcf (no p_fail).

Per-ticker scenario inputs (the locked Wave-1 models):
- `model_lulu.py`, `model_uber.py`, `model_batchb.py` (ILMN/ABNB/YETI/DASH) — Batch-B mature inputs + findings.
Run: `python scripts/_models/model_lulu.py` etc. (prints the per-scenario dcf + weighted vs spot).

## Arthur Indicator 2.0 — backtest (spec §13)

**Result (v034, sourced panel): AI 2.0 does NOT calibrate as a full 8-weight model.**
The only enrichment that survives leave-one-year-out (LOYO) OOS is a single FCF-margin
term, and even that is modest and 1-year-concentrated. **AI 1.0 (`scripts/arthur_indicator.py`)
remains the live screen** — the FCF-margin loading is the one validated extension.

- `source_ai2_panel.py` — the deterministic sourcing path (no transcription, no memory):
  SEC XBRL companyfacts (fundamentals, debt, shares) + Yahoo v8 chart JSON (FYE prices) →
  the panel schema. **Sourced cleanly: 347 rows / 26 tickers / FY2007–25, 0 fundamentals
  gaps, 316 rows with a market-cap + price** (the rest are pre-IPO years with no public price).
    - raw (unadjusted) close × reported shares → market cap; split+dividend-adjusted close → forward returns.
    - **Two bugs a market-cap sanity-gate caught + fixed (both self-tested in `--selftest`):**
      (i) Yahoo's `quote.close` is *split-adjusted, not raw* → `close × pre-split shares`
      understated old-year caps by the cumulative post-FYE split factor (NVDA FY2024 read
      $152B, ~10× low, pre the 2024 10:1); the unadjusted close is now rebuilt from the
      `events.splits` payload. (ii) dual-class names (META/GOOGL/SNAP/W) expose **no
      consolidated point-in-time share count** in companyfacts (the API drops per-class
      dimensional facts), so META had zero caps; now back-filled from the income-statement
      weighted-average share count.
    - Post-fix caps match truth: META FY2024 $1.48T · NVDA FY2025 $3.48T · AAPL FY2024 $3.44T;
      split-year adjusted-price transitions are artifact-free.
    - `--probe` tests host reachability (SEC + Yahoo); `--selftest` unit-tests the parser
      offline. `--out ai2_panel.csv` promotes the sourced file for the fit.

- `ai2_panel_sourced.csv` / `ai2_panel.csv` — the sourced fundamentals + price panel, one
  row per (ticker, fiscal year), 26 names FY2007–25 spanning winners (META/NVDA/MSFT/…) and
  busts (PTON/BYND/SNAP/W/ZM/…). `…_sourced.csv` is the sourcing output; `ai2_panel.csv` is
  the promoted copy the backtest fits. (Provenance is now fully sourced — the old `[e]`
  training-knowledge estimates are gone.)

- `ai2_backtest.py` — fits the AI 2.0 weights against forward returns via per-fiscal-year
  cross-section rank-IC (cheapness `−AI` vs forward return, n-weighted, `Q>0` coverage
  penalty), judged by **LOYO-OOS, not in-sample**. numpy-only; self-tested (`--selftest`
  recovers a known weight vector *and* checks the regularizers). Modes:
    - (default) `python ai2_backtest.py [--1y]` — fit the full 8-weight model; report
      in-sample IC, fitted weights, LOYO-OOS.
    - `--select` — the **nested-model ladder** (AI 1.0 → +levels → +Δ → full-8) with the
      Δ-weights sign-constrained ≥ 0, judged by LOYO-OOS at both horizons. The regularizer
      that picks the model.
    - `--fcfm` — the parsimonious **AI 1.0 + λ·fcfm** model (one knob): the λ-curve + the
      honest nested-LOYO OOS (λ re-fit per training fold).
    - `--ridge X` / `--allow-neg-delta` — ridge shrinkage toward AI 1.0 / lift the Δ ≥ 0 constraint.

**The finding (judge = LOYO-OOS).** The full 8-weight fit **overfits**: in-sample rank-IC
+0.156 (3y) / +0.212 (1y) but LOYO-OOS −0.063 / −0.068, weights sign-flipping across
horizons; even Δ ≥ 0-constrained the full model is +0.140 (3y) / −0.012 (1y) — tops one
horizon, negative on the other. Regularized, the **only** model beating AI 1.0 OOS at *both*
horizons is **AI 1.0 + an FCF-margin term**; the operating-margin term and all four Δ terms
fail OOS. Even the FCF-margin term is modest + 1y-concentrated (1y OOS +0.107 → ~+0.11–0.12
at λ ≈ 0.4, cheaper-for-higher-FCF-margin, sign-stable across seeds; 3y has no reliable
signal for any model — ~15 drawdown-dominated cross-sections). **26 names × ~20 thin
cross-sections cannot support 8 free parameters.** AI 1.0 stays live.
