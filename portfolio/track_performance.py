#!/usr/bin/env python3
"""Daily portfolio performance vs a wide multi-asset benchmark set (spec §15 D4),
plus a modified Sortino-ratio comparison against the S&P 500 (SPY) and NASDAQ-100 (QQQ).

Reads portfolio/weights.yml; from the launch epoch (t0) computes the weighted-
portfolio cumulative total return and each benchmark's, using Yahoo split/dividend-
adjusted closes (keyless — same source proven in the AI 2.0 work). Upserts today's
row into portfolio/performance.csv (one row per date).

It ALSO reconstructs the (buy-and-hold, drifting-weight) portfolio's daily return
series and computes a **modified Sortino ratio** for the portfolio vs SPY (S&P 500)
and QQQ (NASDAQ-100), persisting the snapshot to portfolio/risk_stats.csv.

  Modified Sortino = (annualized return − MAR) / annualized downside deviation,
  where the downside deviation is the FULL-SAMPLE target semideviation below the MAR
  —  DD = sqrt( (1/N) · Σ_t min(0, r_t − τ)² )  —  summed over ALL N periods (not just
  down periods; the statistically-correct form), annualized by √252. The target τ is
  the per-period MAR; MAR defaults to the realized risk-free rate (BIL) over the
  window, with the SAME target in numerator and denominator (a consistent-target
  Sortino). Sharpe, downside deviation, and max drawdown are reported alongside.

No-op before the epoch or on a day with no new close (weekend/holiday). Deterministic
arithmetic — NO Claude (§15: the daily job is a plain scheduled script).
    python portfolio/track_performance.py
    python portfolio/track_performance.py --sortino     # only the Sortino comparison
    AI_EPOCH=2025-06-01 python portfolio/track_performance.py --sortino   # trailing-window backtest
    AI_MAR=0 python portfolio/track_performance.py --sortino              # MAR = 0% instead of rf
"""
from __future__ import annotations
import csv
import json
import math
import os
import statistics
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
RISKFREE_TICKER = "BIL"   # 1-3mo T-bill ETF — realized risk-free proxy for the Sortino MAR
ANN = 252                 # trading days/yr for annualization
SORTINO_BENCH = {"SPY": "S&P 500", "QQQ": "NASDAQ-100"}   # the head-to-head comparison set
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


# ───────────────────────── modified Sortino ─────────────────────────

def _returns(levels: list[float]) -> list[float]:
    """Simple period returns from a level/value path."""
    return [levels[i] / levels[i - 1] - 1.0 for i in range(1, len(levels)) if levels[i - 1] > 0]


def modified_sortino(rets: list[float], tau: float, ann: int = ANN) -> dict | None:
    """Annualized modified Sortino over `rets`, target (per-period MAR) `tau`.

    Downside deviation = FULL-SAMPLE target semideviation below tau (denominator =
    all N periods, the statistically-correct form). Consistent target in numerator
    and denominator. Returns Sharpe, downside dev, vol, max drawdown alongside."""
    n = len(rets)
    if n < 2:
        return None
    mean = sum(rets) / n
    ann_ret = mean * ann
    mar_ann = tau * ann
    dvar = sum(min(0.0, r - tau) ** 2 for r in rets) / n          # target semivariance over ALL n
    dd_ann = math.sqrt(dvar) * math.sqrt(ann)
    vol_ann = statistics.pstdev(rets) * math.sqrt(ann)
    sortino = (ann_ret - mar_ann) / dd_ann if dd_ann > 0 else float("inf")
    sharpe = (ann_ret - mar_ann) / vol_ann if vol_ann > 0 else float("inf")
    v, peak, mdd = 1.0, 1.0, 0.0                                   # max drawdown of the compounded path
    for r in rets:
        v *= (1 + r); peak = max(peak, v); mdd = min(mdd, v / peak - 1.0)
    return dict(n=n, ann_ret=ann_ret, mar_ann=mar_ann, dd_ann=dd_ann, vol_ann=vol_ann,
                sortino=sortino, sharpe=sharpe, maxdd=mdd, pct_down=sum(r < tau for r in rets) / n)


def sortino_compare(weights: dict, series: dict[str, dict], epoch: dt.date,
                    mar_annual: float | None = None, ann: int = ANN):
    """Reconstruct the buy-and-hold (drifting-weight) portfolio's daily returns and
    SPY/QQQ's, over their COMMON trading days since epoch, and compute the modified
    Sortino for each. MAR (τ) defaults to the realized BIL return over the window;
    override with `mar_annual` (annual %). Returns (rows, meta) and prints a table."""
    holdings = {t: w for t, w in weights.items() if t != "cash" and w}
    cashw = float(weights.get("cash", 0.0) or 0.0)
    need = list(holdings) + list(SORTINO_BENCH) + [RISKFREE_TICKER]
    sets = [{d for d in series.get(t.upper(), {}) if d >= epoch} for t in need]
    sets = [s for s in sets if s]
    if not sets:
        print("  sortino: no overlapping price history on/after the epoch yet.")
        return [], {}
    common = sorted(set.intersection(*sets))
    dropped = [t for t in holdings if not {d for d in series.get(t.upper(), {}) if d in set(common)}]
    if len(common) < 3:
        print(f"  sortino: only {len(common)} common trading day(s) since {epoch} — need history to accrue.")
        return [], {"n": len(common)}

    # per-period risk-free target (τ): realized BIL mean daily return, or an explicit MAR.
    bil = [series[RISKFREE_TICKER][d] for d in common]
    bil_rets = _returns(bil)
    rf_daily = sum(bil_rets) / len(bil_rets) if bil_rets else 0.0
    tau = (mar_annual / 100.0 / ann) if mar_annual is not None else rf_daily
    mar_lbl = (f"{mar_annual:.1f}%/yr (set)" if mar_annual is not None
               else f"realized rf {rf_daily*ann*100:.1f}%/yr (BIL)")

    # portfolio value path: V_t = Σ w_i · (P_i,t / P_i,base) + cash·1.0  (drifting weights).
    base = {t: series[t.upper()][common[0]] for t in holdings if series.get(t.upper())}
    pv = []
    for d in common:
        v = cashw
        for t, w in holdings.items():
            s = series.get(t.upper(), {})
            if d in s and base.get(t, 0) > 0:
                v += w * (s[d] / base[t])
        pv.append(v)

    rows = [("Portfolio", modified_sortino(_returns(pv), tau, ann))]
    for tk, name in SORTINO_BENCH.items():
        rows.append((f"{name} ({tk})", modified_sortino(_returns([series[tk][d] for d in common]), tau, ann)))

    meta = {"asof": common[-1], "start": common[0], "n": len(common), "tau": tau,
            "mar_annual": (mar_annual if mar_annual is not None else rf_daily * ann * 100), "dropped": dropped}
    print(f"  Modified Sortino — portfolio vs S&P 500 (SPY) vs NASDAQ-100 (QQQ)")
    print(f"    window {common[0]} → {common[-1]}  ·  {len(common)} trading days  ·  MAR = {mar_lbl}")
    if dropped:
        print(f"    note: no price for {dropped} on the window — excluded (portfolio under-weighted by their weight)")
    if len(common) < 25:
        print(f"    (small sample: {len(common)} days — the annualized ratio is noisy until ~1 quarter of history accrues)")
    print(f"    {'series':<18}{'annRet':>9}{'downDev':>9}{'Sortino':>9}{'Sharpe':>8}{'maxDD':>9}")
    for name, m in rows:
        if not m:
            print(f"    {name:<18}{'— insufficient data —':>35}"); continue
        sr = "  inf" if m["sortino"] == float("inf") else f"{m['sortino']:.2f}"
        sh = "  inf" if m["sharpe"] == float("inf") else f"{m['sharpe']:.2f}"
        print(f"    {name:<18}{m['ann_ret']*100:>+8.1f}%{m['dd_ann']*100:>8.1f}%{sr:>9}{sh:>8}{m['maxdd']*100:>+8.1f}%")
    return rows, meta


def persist_risk_stats(rows: list, meta: dict) -> None:
    """Upsert one row per (date, series) into portfolio/risk_stats.csv (long format)."""
    if not rows or not meta.get("asof"):
        return
    csvp = PORT / "risk_stats.csv"
    cols = ["date", "window_start", "n_days", "mar_annual_pct", "series",
            "ann_return", "downside_dev", "sortino", "sharpe", "max_drawdown"]
    existing: dict[tuple, dict] = {}
    if csvp.exists():
        existing = {(r["date"], r["series"]): r for r in csv.DictReader(csvp.open())}
    d = meta["asof"].isoformat()
    for name, m in rows:
        if not m:
            continue
        existing[(d, name)] = {
            "date": d, "window_start": meta["start"].isoformat(), "n_days": meta["n"],
            "mar_annual_pct": round(meta["mar_annual"], 3), "series": name,
            "ann_return": round(m["ann_ret"], 5), "downside_dev": round(m["dd_ann"], 5),
            "sortino": ("inf" if m["sortino"] == float("inf") else round(m["sortino"], 4)),
            "sharpe": ("inf" if m["sharpe"] == float("inf") else round(m["sharpe"], 4)),
            "max_drawdown": round(m["maxdd"], 5)}
    with csvp.open("w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=cols)
        wr.writeheader()
        for k in sorted(existing):
            wr.writerow({c: existing[k].get(c, "") for c in cols})


def main() -> int:
    wf = yaml.safe_load((PORT / "weights.yml").read_text())
    epoch = dt.date.fromisoformat(os.environ.get("AI_EPOCH") or str(wf["epoch"]))
    mar = float(os.environ["AI_MAR"]) if os.environ.get("AI_MAR") not in (None, "") else None
    sortino_only = "--sortino" in sys.argv[1:]
    today = dt.date.today()

    if not sortino_only and today < epoch:
        print(f"pre-launch (today {today} < epoch {epoch}) — no tracking yet.")
        print(f"  tip: run with AI_EPOCH=<YYYY-MM-DD> --sortino for a trailing-window Sortino backtest now.")
        return 0

    holdings = {t: w for t, w in wf["weights"].items() if t != "cash" and w}
    fetch = list(holdings) + ([RISKFREE_TICKER] + list(SORTINO_BENCH) if sortino_only else BENCHMARKS)
    series: dict[str, dict] = {}
    for t in dict.fromkeys(fetch):
        try:
            series[t.upper()] = adjclose(t, epoch)
        except Exception as e:
            print(f"  warn: {t} price fetch failed ({e})")
            series[t.upper()] = {}

    if sortino_only:
        rows, meta = sortino_compare(wf["weights"], series, epoch, mar)
        persist_risk_stats(rows, meta)
        return 0

    # ── cumulative-return tracking (existing behaviour) ──
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
    rows = {}
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

    # ── modified Sortino vs S&P / NASDAQ (needs return history to be meaningful) ──
    sc_rows, meta = sortino_compare(wf["weights"], series, epoch, mar)
    persist_risk_stats(sc_rows, meta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
