#!/usr/bin/env python3
"""Source clean multi-year fundamentals for the Mega-7 mature memos straight from
SEC XBRL companyfacts (no transcription). Prints, per ticker, the last 6 fiscal
years of revenue / operating margin / free cash flow / cash+STI / total debt /
shares — the load-bearing inputs for the mature DCF + the page-3 history chart.

Reuses the battle-tested parsers in source_ai2_panel.py (per-fy priority merge,
weighted-avg-share fallback for dual-class names, etc.). Run:
    python scripts/_models/source_mega7.py
"""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import source_ai2_panel as S

# DIS isn't in the AI2 panel CIK dict (it's not an AI2 growth/quality name) —
# CIK 1744489 = The Walt Disney Company (post-2019 reorg entity), confirmed from
# its FY2026 8-K EDGAR path data/0001744489/.
CIK = dict(S.CIK)
CIK["DIS"] = 1744489

TICKERS = ["META", "AMZN", "GOOGL", "AAPL", "NVDA", "TSLA", "DIS"]
SPOT = {"META": 566.98, "AMZN": 238.55, "GOOGL": 359.68, "AAPL": 291.13,
        "NVDA": 205.19, "TSLA": 406.43, "DIS": 100.04}


def series(ticker):
    cik = CIK[ticker]
    f = S.companyfacts(cik)
    name = f.get("entityName", "?")
    rev = S.flow_series(f, S.CONCEPTS["revenue"])
    opi = S.flow_series(f, S.CONCEPTS["op_income"])
    ocf = S.flow_series(f, S.CONCEPTS["ocf"])
    cpx = S.flow_series(f, S.CONCEPTS["capex"])
    cash = S.instant_series(f, S.CONCEPTS["cash"])
    sti = S.instant_series(f, S.CONCEPTS["sti"])
    dnc = S.instant_series(f, S.CONCEPTS["debt_noncur"])
    dcur = S.instant_series(f, S.CONCEPTS["debt_cur"])
    dcomb = S.instant_series(f, S.CONCEPTS["debt_combined"])
    fyes = S.fye_dates(f)
    sh = S.shares_at_fye(f, fyes)
    years = sorted(rev)[-6:]
    print(f"\n=== {ticker}  ({name}, CIK {cik})  spot ${SPOT[ticker]} ===")
    print(f"  {'FY':>6}{'rev$B':>9}{'opm%':>8}{'fcf$B':>9}{'cash+sti$B':>12}{'debt$B':>9}{'sh(M)':>10}{'mktcap$B':>10}")
    for y in years:
        r = rev.get(y)
        if not r:
            continue
        rb = r / 1e9
        om = (opi[y] / r * 100) if (y in opi and r) else float("nan")
        fcf = ((ocf.get(y, 0) - cpx.get(y, 0)) / 1e9) if y in ocf else float("nan")
        cs = ((cash.get(y, 0) + sti.get(y, 0)) / 1e9)
        debt = ((dnc.get(y, 0) + dcur.get(y, 0)) or dcomb.get(y, 0)) / 1e9
        shm = (sh.get(y) / 1e6) if y in sh else float("nan")
        mc = (shm * SPOT[ticker] / 1e3) if shm == shm else float("nan")
        print(f"  {y:>6}{rb:>9.1f}{om:>8.1f}{fcf:>9.1f}{cs:>12.1f}{debt:>9.1f}{shm:>10.0f}{mc:>10.0f}")
    # latest-FY snapshot for the spec
    ly = years[-1]
    rb = rev[ly] / 1e9
    cs = (cash.get(ly, 0) + sti.get(ly, 0)) / 1e9
    debt = ((dnc.get(ly, 0) + dcur.get(ly, 0)) or dcomb.get(ly, 0)) / 1e9
    shm = (sh.get(ly) / 1e6) if ly in sh else float("nan")
    print(f"  -> latest FY{ly}: rev_b={rb:.3f}  cash+sti={cs:.3f}  debt={debt:.3f}  "
          f"net_debt={debt-cs:+.3f}  shares={shm:.1f}M  mktcap=${shm*SPOT[ticker]/1e3:.1f}B")


if __name__ == "__main__":
    for t in (sys.argv[1:] or TICKERS):
        try:
            series(t.upper())
        except Exception as e:
            print(f"\n=== {t}: ERROR {type(e).__name__}: {e} ===")
