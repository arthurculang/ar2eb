# Modeling record (the "model the DCF in python for internal consistency" step)

Reusable DCF engines that reproduce `scripts/validate.py` + `scripts/scaffold_ticker.py`
math to the cent (verified: model_dcf vs RKLB, model_mature vs ZM):
- `model_dcf.py`    — young_company (Damodaran): reinvest=Δrev/s2c, Gordon terminal, expected=(1-pf)·dcf+pf·distress, cash-runway check.
- `model_mature.py` — mature_company: fcf=rev·fcf_margin (or provided), Gordon/exit terminal, expected=dcf (no p_fail).

Per-ticker scenario inputs (the locked Wave-1 models):
- `model_lulu.py`, `model_uber.py`, `model_batchb.py` (ILMN/ABNB/YETI/DASH) — Batch-B mature inputs + findings.
Run: `python scripts/_models/model_lulu.py` etc. (prints the per-scenario dcf + weighted vs spot).
