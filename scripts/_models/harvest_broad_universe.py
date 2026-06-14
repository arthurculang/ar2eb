#!/usr/bin/env python3
"""Harvest a BROAD, all-sector universe for the Arthur Indicator backtest.

The hand-curated CIK list (source_ai2_panel.CIK) is ~111 growth/quality names —
too narrow to judge whether the Indicator generalises. This harvests every filer
that reports a GROSS PROFIT line (the Indicator's domain — excludes banks/insurers
that have no gross margin) above a size floor, from the data.sec.gov XBRL *frames*
API (the bulk SEC ticker map on www.sec.gov is 403-blocked here; frames is not).
Then submissions → ticker for each. Writes {ticker: cik} to ai2_universe_broad.json.

    python harvest_broad_universe.py            # harvest -> ai2_universe_broad.json
"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import source_ai2_panel as S

HERE = Path(__file__).resolve().parent
OUT = HERE / "ai2_universe_broad.json"
GP_FLOOR = 4e8                      # >= $400M gross profit (large/mid, all sectors)
YEARS = ["CY2015", "CY2018", "CY2021", "CY2023"]   # snapshots to catch names over time


def harvest_ciks() -> dict:
    """cik -> entityName, for every GrossProfit reporter >= GP_FLOOR in any snapshot year."""
    ciks = {}
    for cy in YEARS:
        url = f"https://data.sec.gov/api/xbrl/frames/us-gaap/GrossProfit/USD/{cy}.json"
        try:
            data = json.loads(S._get(url)).get("data", [])
        except Exception as e:
            print(f"  {cy}: frames failed ({e})"); continue
        n = 0
        for x in data:
            if x.get("val", 0) >= GP_FLOOR:
                ciks[int(x["cik"])] = x.get("entityName", "")
                n += 1
        print(f"  {cy}: {n} reporters >= ${GP_FLOOR/1e6:.0f}M GP  (universe now {len(ciks)})", flush=True)
        time.sleep(0.3)
    return ciks


def cik_to_ticker(cik: int) -> str | None:
    """Primary US-listed ticker for a CIK via the submissions API; None if no ticker."""
    url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
    try:
        sub = json.loads(S._get(url))
    except Exception:
        return None
    tks = sub.get("tickers") or []
    exch = sub.get("exchanges") or []
    # prefer a NASDAQ/NYSE listing; else first ticker
    for tk, ex in zip(tks, exch):
        if ex and ex.upper() in ("NASDAQ", "NYSE", "NYSEAMERICAN", "CBOE"):
            return tk.upper()
    return tks[0].upper() if tks else None


def main():
    print(f"harvesting GrossProfit reporters >= ${GP_FLOOR/1e6:.0f}M from frames {YEARS}…")
    ciks = harvest_ciks()
    print(f"\n{len(ciks)} unique CIKs; mapping to tickers via submissions…")
    uni, miss = {}, 0
    for i, cik in enumerate(sorted(ciks)):
        tk = cik_to_ticker(cik)
        if tk and tk.isalpha() and 1 <= len(tk) <= 5:
            uni[tk] = cik
        else:
            miss += 1
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(ciks)} mapped ({len(uni)} tickers, {miss} skipped)", flush=True)
        time.sleep(0.12)
    OUT.write_text(json.dumps(dict(sorted(uni.items())), indent=0))
    print(f"\nwrote {OUT}: {len(uni)} tickers across all sectors (skipped {miss} no-ticker/ADR/etc.)")


if __name__ == "__main__":
    main()
