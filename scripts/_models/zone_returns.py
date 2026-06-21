#!/usr/bin/env python3
"""Zone-return table for the /indicator page (the "practical read").

Reads the point-in-time quarterly panel (ai2_quarterly.csv) and reports, per
Arthur-Indicator zone (green <6 · yellow 6-10 · orange 10-15 · red >15):

  - mean forward return (1y, 3y) over ALL quarterly rows in the zone. Overlapping
    forward windows don't BIAS a mean (only its standard error), so the average is
    an honest descriptive point estimate at full sample size.
  - win-rate (share finishing positive) over NON-OVERLAPPING windows only — per
    ticker, greedily keep observations whose forward windows don't overlap (≥1yr
    apart for the 1y read, ≥3yr for the 3y read). This is an honest hit-rate at a
    true, smaller N (no overlap-inflated false precision).

Significance lives elsewhere (source_ai2_quarterly.py --analyze / --longshort:
the Newey-West-corrected cheap-minus-rich spread). This script is the intuitive
companion table only; the page shows the 3y columns.

    python scripts/_models/zone_returns.py
"""
import csv
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path

CSV = Path(__file__).resolve().parent / "ai2_quarterly.csv"
ORDER = ["green", "yellow", "orange", "red"]
BANDS = {"green": "< 6", "yellow": "6 – 10", "orange": "10 – 15", "red": "> 15"}


def zone(ai: float) -> str:
    return "green" if ai < 6 else "yellow" if ai < 10 else "orange" if ai < 15 else "red"


def _d(s: str) -> date:
    y, m, dd = map(int, s.split("-"))
    return date(y, m, dd)


def _plus_years(d: date, n: int) -> date:
    try:
        return d.replace(year=d.year + n)
    except ValueError:                     # Feb 29
        return d.replace(year=d.year + n, day=28)


def load(path=CSV):
    return list(csv.DictReader(open(path)))


def zone_means(rows):
    """Mean forward return per zone over ALL rows (overlap doesn't bias a mean)."""
    agg = defaultdict(lambda: {"r1": [], "r3": []})
    for r in rows:
        z = zone(float(r["ai"]))
        for tag, key in (("fwd_1y", "r1"), ("fwd_3y", "r3")):
            v = r.get(tag)
            if v not in (None, ""):
                agg[z][key].append(float(v))
    return agg


def nonoverlap_winrate(rows, tag, years):
    """Per ticker, greedily keep observations whose `years`-forward windows don't
    overlap; return {zone: (wins, n)} and the total kept."""
    by_t = defaultdict(list)
    for r in rows:
        by_t[r["ticker"]].append(r)
    kept = defaultdict(lambda: [0, 0])
    total = 0
    for t, rs in by_t.items():
        rs.sort(key=lambda r: r["date"])
        last_end = None
        for r in rs:
            v = r.get(tag)
            if v in (None, ""):
                continue
            start = _d(r["date"])
            if last_end is not None and start < last_end:
                continue                   # window overlaps the last kept one — skip
            z = zone(float(r["ai"]))
            kept[z][1] += 1
            if float(v) > 0:
                kept[z][0] += 1
            last_end = _plus_years(start, years)
            total += 1
    return kept, total


def main() -> int:
    rows = load()
    agg = zone_means(rows)
    wr1, n1 = nonoverlap_winrate(rows, "fwd_1y", 1)
    wr3, n3 = nonoverlap_winrate(rows, "fwd_3y", 3)
    dates = sorted({r["date"] for r in rows})
    print(f"quarterly panel: {len(rows)} rows · {len(dates)} cross-sections · "
          f"{len({r['ticker'] for r in rows})} tickers ({dates[0]}…{dates[-1]})\n")
    print(f"{'zone':<8}{'band':<10}{'n':>7}{'mean 1y':>9}{'mean 3y':>9}"
          f"{'win1y*':>8}{'(N)':>6}{'win3y*':>8}{'(N)':>6}{'med 3y':>9}")
    print("-" * 80)
    for z in ORDER:
        a = agg[z]
        r1 = statistics.mean(a["r1"]) if a["r1"] else float("nan")
        r3 = statistics.mean(a["r3"]) if a["r3"] else float("nan")
        m3 = statistics.median(a["r3"]) if a["r3"] else float("nan")
        w1 = wr1[z][0] / wr1[z][1] if wr1[z][1] else float("nan")
        w3 = wr3[z][0] / wr3[z][1] if wr3[z][1] else float("nan")
        print(f"{z:<8}{BANDS[z]:<10}{len(a['r3']):>7}{r1:>+8.0%}{r3:>+8.0%}"
              f"{w1:>7.0%}{wr1[z][1]:>6}{w3:>7.0%}{wr3[z][1]:>6}{m3:>+8.0%}")
    print("-" * 80)
    print(f"* win-rate on NON-OVERLAPPING windows; totals: 1y N={n1}, 3y N={n3} "
          f"(vs {len(rows)} quarterly rows).")
    print("Means use all rows (overlap is unbiased for a mean); the page shows the 3y columns.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
