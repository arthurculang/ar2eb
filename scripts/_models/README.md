# Modeling record (the "model the DCF in python for internal consistency" step)

Reusable DCF engines that reproduce `scripts/validate.py` + `scripts/scaffold_ticker.py`
math to the cent (verified: model_dcf vs RKLB, model_mature vs ZM):
- `model_dcf.py`    — young_company (Damodaran): reinvest=Δrev/s2c, Gordon terminal, expected=(1-pf)·dcf+pf·distress, cash-runway check.
- `model_mature.py` — mature_company: fcf=rev·fcf_margin (or provided), Gordon/exit terminal, expected=dcf (no p_fail).

Per-ticker scenario inputs (the locked Wave-1 models):
- `model_lulu.py`, `model_uber.py`, `model_batchb.py` (ILMN/ABNB/YETI/DASH) — Batch-B mature inputs + findings.
Run: `python scripts/_models/model_lulu.py` etc. (prints the per-scenario dcf + weighted vs spot).

## Arthur Indicator 2.0 — backtest (spec §13)

- `ai2_backtest.py` — fits the eight AI 2.0 weights `w1…w8` against forward
  returns via per-fiscal-year cross-section rank-IC (cheapness = −AI vs forward
  return), with a Q>0 coverage penalty and leave-one-year-out CV. numpy-only;
  self-tested (`--selftest` recovers a known weight vector, OOS IC +0.91).
- `ai2_panel.csv` — the fundamentals panel, one row per (ticker, fiscal year),
  26 names FY2014–FY2025 spanning winners (META/NVDA/MSFT/…) and busts
  (PTON/BYND/SNAP/W/ZM/…). **Provenance is uneven and the file flags it with
  `[e]`:** the *operating* columns (revenue, gross/op margin, growth) are
  research-sourced and reliable (many cross-checked to the dollar); the
  *valuation* columns (`mktcap_b`, `net_cash_b`) and `price_fye` came back as
  **training-knowledge estimates `[e]` or blank** — every finance data host
  (SEC EDGAR, stooq, Yahoo Finance, FMP, AlphaVantage) is **egress-blocked by
  the environment's network allowlist**, so they could not be sourced. Two
  corrupted columns were blanked on assembly (ISRG/LULU `fcf_margin` came back
  as absolute $B, not a ratio).

**Status — AI 2.0 cannot yet be credibly fit (the result, not a failure).**
On this memory-grade EV/price data the 8-weight fit *overfits*: in-sample
rank-IC rises (AI 1.0 ≈ +0.12 → AI 2.0 ≈ +0.51 at 3y) but **leave-one-year-out
OOS IC collapses** (≈ +0.03 at 1y, +0.16 at 3y) and the fitted weights are
unstable across horizons/subsamples. The harness + CV are working — they're
correctly reporting the data is insufficient. **To trust `w1…w8` we need
sourced EV + FYE prices** (allowlist `data.sec.gov` + a price host, or load a
CSV export), then re-run `python scripts/_models/ai2_backtest.py`. Until then
**AI 1.0 remains the live screen.**

- `source_ai2_panel.py` — the deterministic sourcing path (no transcription, no
  memory). Pulls fundamentals + shares from SEC XBRL companyfacts and
  split-adjusted FYE closes from stooq, computes EV / margins / growth / forward
  prices, and writes the panel schema. **Gated on the network allowlist:**
  needs `data.sec.gov` + `stooq.com` opened (it exits gracefully with that
  instruction otherwise). `--selftest` unit-tests the XBRL parser offline (flow
  vs instant facts, 10-K/FY filtering, as-first-reported dedup); `--probe` tests
  host reachability. Once it runs: review the printed coverage gaps, then
  `--out ai2_panel.csv` to promote and re-fit.
