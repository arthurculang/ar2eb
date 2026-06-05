# Modeling record (the "model the DCF in python for internal consistency" step)

Reusable DCF engines that reproduce `scripts/validate.py` + `scripts/scaffold_ticker.py`
math to the cent (verified: model_dcf vs RKLB, model_mature vs ZM):
- `model_dcf.py`    — young_company (Damodaran): reinvest=Δrev/s2c, Gordon terminal, expected=(1-pf)·dcf+pf·distress, cash-runway check.
- `model_mature.py` — mature_company: fcf=rev·fcf_margin (or provided), Gordon/exit terminal, expected=dcf (no p_fail).

Per-ticker scenario inputs (the locked Wave-1 models):
- `model_lulu.py`, `model_uber.py`, `model_batchb.py` (ILMN/ABNB/YETI/DASH) — Batch-B mature inputs + findings.
Run: `python scripts/_models/model_lulu.py` etc. (prints the per-scenario dcf + weighted vs spot).

## Arthur Indicator 2.0 — backtest (spec §13)

**Result (v035, sourced 104-name panel): AI 2.0 does NOT calibrate; AI 1.0 is validated.**
On a broad 104-ticker universe (winners + busts), *no* AI 2.0 enrichment — FCF-margin,
operating-margin, or any Δ (rate-of-change) term — beats AI 1.0 out-of-sample (leave-one-
year-out) at both horizons. The FCF-margin term that won on the narrow 26-name panel (v034)
was a small-sample artifact. **AI 1.0 (gross margin + growth) is itself validated** — positive
and stable OOS at both horizons on the wide universe — and **remains the live screen**
(`scripts/arthur_indicator.py`).

- `source_ai2_panel.py` — the deterministic sourcing path (no transcription, no memory):
  SEC XBRL companyfacts (fundamentals, debt, shares) + Yahoo v8 chart JSON (FYE prices) →
  the panel schema. **104-ticker universe, 1483 rows / FY2007–26, ~1245 usable rows** (gross
  margin + mktcap + price); each fiscal-year cross-section is ~95 names (was ~26).
    - raw (unadjusted) close × reported shares → market cap; split+dividend-adjusted close → forward returns.
    - **Two bugs a market-cap sanity-gate caught + fixed (both self-tested in `--selftest`):**
      (i) Yahoo's `quote.close` is *split-adjusted, not raw* → `close × pre-split shares`
      understated old-year caps by the cumulative post-FYE split factor (NVDA FY2024 read
      $152B, ~10× low); the unadjusted close is now rebuilt from the `events.splits` payload.
      (ii) dual-class names (META/GOOGL/SNAP/W) expose **no consolidated point-in-time share
      count** in companyfacts (the API drops per-class dimensional facts); now back-filled
      from the income-statement weighted-average share count.
    - Post-fix caps match truth: META FY2024 $1.48T · NVDA FY2025 $3.48T · AVGO $792B · COST $395B.
    - **CIKs.** `www.sec.gov`'s ticker→CIK map is not allowlisted, so the expansion CIKs were
      seeded then **verified** against `data.sec.gov/submissions` (ticker + entity-name match) —
      a wrong seed is caught, not trusted.
    - **Known data limit:** ~14 high-quality compounders (ORCL/V/MA/INTU/CDNS/TMO/SBUX/CMG…)
      stopped tagging a consolidated GrossProfit/CostOfRevenue after ~2018 — they report only
      total `CostsAndExpenses` or dimensional cost components the API drops — so their recent
      gross-margin rows are absent and they partly drop. Fabricating a margin would break
      conviction-neutrality. (op-income gaps are immaterial: opm isn't in AI 1.0 / the surviving model.)
    - `--probe` tests host reachability (SEC + Yahoo); `--selftest` unit-tests the parser
      offline. `--out ai2_panel.csv` promotes the sourced file for the fit.

- `ai2_panel_sourced.csv` / `ai2_panel.csv` — the sourced fundamentals + price panel, one row
  per (ticker, fiscal year). `…_sourced.csv` is the sourcing output; `ai2_panel.csv` is the
  promoted copy the backtest fits. Provenance is fully sourced (no `[e]` estimates).

- `ai2_backtest.py` — fits the AI 2.0 weights against forward returns via per-fiscal-year
  cross-section rank-IC (cheapness `−AI` vs forward return, n-weighted, `Q>0` coverage
  penalty), judged by **LOYO-OOS, not in-sample**. numpy-only; self-tested. Modes:
    - (default) `python ai2_backtest.py [--1y]` — fit the full 8-weight model; report IC, weights, LOYO-OOS.
    - `--select` — the **nested-model ladder** (AI 1.0 → +levels → +Δ → full-8), Δ-weights ≥ 0,
      judged by LOYO-OOS at both horizons. The regularizer that picks the model.
    - `--fcfm` — the parsimonious **AI 1.0 + λ·fcfm** model (one knob): λ-curve + nested-LOYO OOS.
    - `--ridge X` / `--allow-neg-delta` — ridge shrinkage toward AI 1.0 / lift the Δ ≥ 0 constraint.

**The finding (judge = LOYO-OOS), expanded 104-name panel.** AI 1.0 baseline OOS: **+0.044 (3y)
/ +0.063 (1y)** — positive and stable (on the narrow 26-name panel its 3y was ≈ 0). The nested
ladder: every richer model wins at most one horizon and loses the other, and **none beats AI 1.0
at both** — L3 (+fcfm) flips to **−0.041 at 3y**; L2/L4/Δ-models split horizons; the full eight
weights overfit (in-sample IC climbs +0.074→+0.113 at 3y, OOS does not). The 26-name FCF-margin
"win" did not replicate. **Net: AI 2.0 earns none of its extra parameters on a broad universe;
AI 1.0 is the screen, now with broad out-of-sample support.**
