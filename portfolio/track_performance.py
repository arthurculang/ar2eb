#!/usr/bin/env python3
"""Daily portfolio performance vs a wide multi-asset benchmark set (spec §15 D4).

Reads portfolio/weights.yml; from the launch epoch (t0) computes the weighted-
portfolio cumulative total return and each benchmark's, using Yahoo split/dividend-
adjusted closes (keyless — same source proven in the AI 2.0 work). Upserts today's
row into portfolio/performance.csv (one row per date). No-op before the epoch or on
a day with no new close (weekend/holiday).

Deterministic arithmetic — NO Claude (§15: the daily job is a plain scheduled script).
    python portfolio/track_performance.py
    AI_EPOCH=2026-01-01 python portfolio/track_performance.py   # override epoch (testing)
"""
from __future__ import annotations
import csv
import json
import os
import sys
import urllib.request
import datetime as dt
from pathlib import Path
import yaml

REPO = Path(__file__).resolve().parent.parent
PORT = REPO / "portfolio"
# Wide multi-asset sleeve (§15 D4). BTC-USD optional — add "BTC-USD" to include crypto.
BENCHMARKS = ["VT", "SPY", "QQQ", "IWM", "EFA", "EEM", "AGG",
              "SHY", "IEF", "TLT", "TIP", "BIL", "GLD", "DBC", "VNQ"]
UA = "Mozilla/5.0 (compatible; ar2eb-perf; arthurculang@gmail.com)"


def adjclose(ticker: str, start: dt.date) -> dict[dt.date, float]:
    """{date: split/dividend-adjusted close} from Yahoo's v8 chart since `start`."""
    p1 = int(dt.datetime(start.year, start.month, start.day, tzinfo=dt.timezone.utc).timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
           f"?period1={p1}&period2=9999999999&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    res = (data.get("chart", {}).get("result") or [None])[0]
    if not res:
        return {}
    ts = res.get("timestamp") or []
    adj = ((res.get("indicators", {}).get("adjclose") or [{}])[0]).get("adjclose") or []
    out: dict[dt.date, float] = {}
    for t, a in zip(ts, adj):
        if a is not None:
            out[dt.datetime.fromtimestamp(t, dt.timezone.utc).date()] = float(a)
    return out


def cum_return(series: dict[dt.date, float], epoch: dt.date):
    """(cumulative return since the first close on/after epoch, as-of date)."""
    if not series:
        return None, None
    days = sorted(series)
    base = next((d for d in days if d >= epoch), None)
    last = days[-1]
    if base is None or last < epoch or series[base] <= 0:
        return None, last
    return series[last] / series[base] - 1.0, last


def main() -> int:
    wf = yaml.safe_load((PORT / "weights.yml").read_text())
    epoch = dt.date.fromisoformat(os.environ.get("AI_EPOCH") or str(wf["epoch"]))
    today = dt.date.today()
    if today < epoch:
        print(f"pre-launch (today {today} < epoch {epoch}) — no tracking yet.")
        return 0
    holdings = {t: w for t, w in wf["weights"].items() if t != "cash" and w}

    series: dict[str, dict] = {}
    for t in list(holdings) + BENCHMARKS:
        try:
            series[t.upper()] = adjclose(t, epoch)
        except Exception as e:
            print(f"  warn: {t} price fetch failed ({e})")
            series[t.upper()] = {}

    # weighted portfolio cumulative return (cash contributes 0)
    port, asof = 0.0, None
    for t, w in holdings.items():
        cr, d = cum_return(series.get(t.upper(), {}), epoch)
        if cr is not None:
            port += w * cr
            asof = d if (asof is None or (d and d > asof)) else asof
    if asof is None:
        print("no holding prices on/after epoch yet — skipping.")
        return 0

    row = {"date": asof.isoformat(), "portfolio": round(port, 5)}
    for b in BENCHMARKS:
        cr, _ = cum_return(series.get(b, {}), epoch)
        row[b] = round(cr, 5) if cr is not None else ""

    csvp = PORT / "performance.csv"
    cols = ["date", "portfolio"] + BENCHMARKS
    rows: dict[str, dict] = {}
    if csvp.exists():
        rows = {r["date"]: r for r in csv.DictReader(csvp.open())}
    rows[row["date"]] = row
    with csvp.open("w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=cols)
        wr.writeheader()
        for d in sorted(rows):
            wr.writerow({c: rows[d].get(c, "") for c in cols})
    print(f"performance {row['date']}: portfolio {port:+.2%}  ·  VT {row.get('VT','?')}  "
          f"SPY {row.get('SPY','?')}  TLT {row.get('TLT','?')}  GLD {row.get('GLD','?')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
