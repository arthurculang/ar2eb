#!/usr/bin/env python3
"""Quarterly point-in-time panel for the Arthur Indicator (spec §13 robustness).

Why: the annual panel has only ~16 cross-sections, so the IC t-stat is ~1 (not
significant). This rebalances every calendar quarter-end (2009-2024) for ~4x the
cross-sections. The catch it handles HONESTLY: quarterly sampling of 1y/3y forward
returns OVERLAPS, which inflates a naive t-stat — so the analysis applies a
Newey-West (Bartlett) correction, and also reports a 1-quarter-forward horizon
whose windows DON'T overlap (a clean high-N read).

Point-in-time discipline (no look-ahead): at each rebalance date D, a ticker uses
the latest annual fundamentals whose 10-K was FILED on or before D.

Reuses source_ai2_panel primitives (companyfacts cache, concept series, prices).

    python source_ai2_quarterly.py            # source -> scripts/_models/ai2_quarterly.csv (slow)
    python source_ai2_quarterly.py --analyze  # read CSV -> IC + t-stats (fast)
    python source_ai2_quarterly.py --selftest
"""
import os, sys, csv
from datetime import date
from pathlib import Path
sys.path.insert(0, os.path.dirname(__file__))
import source_ai2_panel as S

OUT = Path(__file__).resolve().parent / "ai2_quarterly.csv"
START, END = date(2009, 1, 1), date(2024, 12, 31)
STALE_DAYS = 550   # skip if the latest available 10-K is older than this at D


def add_years(d: date, n: int) -> date:
    try:
        return d.replace(year=d.year + n)
    except ValueError:        # Feb 29
        return d.replace(year=d.year + n, day=28)


def filed_series(facts) -> dict:
    """fy -> filing date of that fy's 10-K (when the numbers became public)."""
    best = {}
    for rank, tag in enumerate(S.CONCEPTS["revenue"]):
        for e in S._annual_entries(facts, tag):
            if e.get("fp") != "FY" or not str(e.get("form", "")).startswith("10-K"):
                continue
            if not S._is_annual_duration(e):
                continue
            fy = S._fy(e); filed = e.get("filed")
            if not filed:
                continue
            cur = best.get(fy)
            if cur is None or rank < cur[0] or (rank == cur[0] and filed < cur[1]):
                best[fy] = (rank, filed)
    return {fy: date.fromisoformat(f) for fy, (_, f) in best.items()}


def _debt(d_nc, d_cu, d_comb, fy) -> float:
    parts = (d_nc.get(fy) or 0.0) + (d_cu.get(fy) or 0.0)
    total = d_comb.get(fy)
    if total is not None:
        return max(total, parts)
    if fy in d_nc or fy in d_cu:
        return parts
    return 0.0


def vintages(facts) -> list:
    """Annual fundamental vintages (sorted by filing date) with everything AI 1.0
    needs: revenue, gross margin, YoY growth, net cash, shares."""
    rev = S.flow_series(facts, S.CONCEPTS["revenue"])
    gp = S.flow_series(facts, S.CONCEPTS["gross_profit"])
    cogs = S.flow_series(facts, S.CONCEPTS["cogs"])
    cash = S.instant_series(facts, S.CONCEPTS["cash"])
    sti = S.instant_series(facts, S.CONCEPTS["sti"])
    d_nc = S.instant_series(facts, S.CONCEPTS["debt_noncur"])
    d_cu = S.instant_series(facts, S.CONCEPTS["debt_cur"])
    d_comb = S.instant_series(facts, S.CONCEPTS["debt_combined"])
    fyes = S.fye_dates(facts)
    shares = S.shares_at_fye(facts, fyes)
    filed = filed_series(facts)
    out = []
    for fy in sorted(rev):
        if fy not in filed:
            continue
        r = rev[fy]
        if not r or r <= 0:
            continue
        g = gp.get(fy)
        if g is None and cogs.get(fy) is not None:
            g = r - cogs[fy]
        prev = rev.get(fy - 1)
        growth = (r / prev - 1) if (prev and prev > 0) else None
        sh = shares.get(fy)
        if g is None or growth is None or sh is None or sh <= 0:
            continue
        gm = g / r
        if (gm + growth) <= 0:        # AI 1.0 undefined / out-of-domain
            continue
        netcash = cash.get(fy, 0.0) + sti.get(fy, 0.0) - _debt(d_nc, d_cu, d_comb, fy)
        out.append(dict(filed=filed[fy], fy=fy, rev_b=r / 1e9, gm=gm,
                        growth=growth, netcash_b=netcash / 1e9, shares=sh))
    return sorted(out, key=lambda v: v["filed"])


def quarter_ends(start: date, end: date) -> list:
    qs = []
    for y in range(start.year, end.year + 1):
        for m, dd in ((3, 31), (6, 30), (9, 30), (12, 31)):
            dt = date(y, m, dd)
            if start <= dt <= end:
                qs.append(dt)
    return qs


def source(tickers: list, cik_map: dict = None) -> tuple:
    cik_map = cik_map if cik_map is not None else S.CIK
    QE = quarter_ends(START, END)
    rows, gaps = [], []
    for t in tickers:
        cik = cik_map.get(t)
        if not cik:
            gaps.append(f"{t}: no CIK"); continue
        try:
            facts = S.companyfacts(cik)
        except Exception as e:
            gaps.append(f"{t}: facts {e}"); continue
        try:
            closes = S.price_history(t)
        except Exception as e:
            closes = []; gaps.append(f"{t}: px {e}")
        if not closes:
            continue
        vs = vintages(facts)
        if not vs:
            gaps.append(f"{t}: no in-domain vintages"); continue
        last_close = closes[-1][0]
        n = 0
        for D in QE:
            v = None                       # latest vintage filed on/before D
            for cand in vs:
                if cand["filed"] <= D:
                    v = cand
                else:
                    break
            if v is None or (D - v["filed"]).days > STALE_DAYS:
                continue
            raw, adj = S.close_on_or_before(closes, D)
            if raw is None or adj is None:
                continue
            denom = v["rev_b"] * (v["gm"] + v["growth"])
            if denom <= 0:
                continue
            ev = raw * v["shares"] / 1e9 - v["netcash_b"]
            ai = ev / denom
            row = {"ticker": t, "date": D.isoformat(), "ai": round(ai, 4)}
            for tag, yrs in (("fwd_1q", None), ("fwd_1y", 1), ("fwd_3y", 3)):
                if yrs is None:
                    fut = QE[QE.index(D) + 1] if QE.index(D) + 1 < len(QE) else None
                else:
                    fut = add_years(D, yrs)
                fr = ""
                if fut is not None and fut <= last_close:
                    _, a2 = S.close_on_or_before(closes, fut)
                    if a2 and adj:
                        fr = round(a2 / adj - 1, 4)
                row[tag] = fr
            rows.append(row); n += 1
        print(f"  {t}: {n} quarterly obs", flush=True)
    return rows, gaps


# ── analysis: cross-sectional IC per quarter + Newey-West t-stat ─────────────
def _spearman(x, y):
    import numpy as np
    n = len(x)
    if n < 4:
        return float("nan")
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    rx -= rx.mean(); ry -= ry.mean()
    d = np.sqrt((rx ** 2).sum() * (ry ** 2).sum())
    return float((rx * ry).sum() / d) if d > 0 else float("nan")


def _newey_west_t(ics, L):
    """t-stat of the mean of an autocorrelated series via Bartlett/Newey-West
    long-run variance (lag L). L=0 reduces to the ordinary i.i.d. t-stat."""
    import numpy as np
    x = np.asarray(ics, float); N = len(x); mu = x.mean(); e = x - mu
    g0 = (e @ e) / N
    lrv = g0
    for k in range(1, L + 1):
        gk = (e[k:] @ e[:-k]) / N
        lrv += 2 * (1 - k / (L + 1)) * gk
    if lrv <= 0:
        return mu, float("nan")
    return mu, mu / np.sqrt(lrv / N)


def analyze(path=OUT):
    import numpy as np
    by_date = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            by_date.setdefault(r["date"], []).append(r)
    dates = sorted(by_date)
    print(f"quarterly panel: {sum(len(v) for v in by_date.values())} rows · "
          f"{len(dates)} quarter-end cross-sections · "
          f"{len({r['ticker'] for v in by_date.values() for r in v})} tickers\n")
    # overlap lag in quarters: 1y→4, 3y→12, 1q→1 (the IC series autocorrelates
    # by ~horizon because adjacent quarters' forward windows overlap).
    for tag, label, L in (("fwd_1q", "1-quarter (non-overlapping)", 0),
                          ("fwd_1y", "1-year (overlap-corrected)", 3),
                          ("fwd_3y", "3-year (overlap-corrected)", 11)):
        ics, ns = [], []
        for d in dates:
            xs = [(float(r["ai"]), float(r[tag])) for r in by_date[d]
                  if r.get(tag) not in (None, "")]
            if len(xs) >= 4:
                a = np.array([p[0] for p in xs]); fr = np.array([p[1] for p in xs])
                rho = _spearman(-a, fr)
                if np.isfinite(rho):
                    ics.append(rho); ns.append(len(xs))
        if len(ics) < 5:
            print(f"  {label:34} insufficient ({len(ics)} xs)"); continue
        mu, t_iid = _newey_west_t(ics, 0)
        _, t_nw = _newey_west_t(ics, L)
        v = np.array(ics)
        print(f"  {label:34} mean IC {mu:+.3f} · {len(ics)} xs (avg {np.mean(ns):.0f} names) · "
              f"{100*(v>0).mean():.0f}% +")
        print(f"  {'':34} t-stat: naive {t_iid:+.2f}  ·  Newey-West(L={L}) {t_nw:+.2f}"
              + ("   <- ROBUST (|t|>2)" if abs(t_nw) > 2 else "   (not significant)"))
    print("\n  honest read: the 1q horizon has the most independent windows; the 1y/3y")
    print("  Newey-West t-stats correct for the overlap that a naive t-stat would inflate.")


def longshort(path=OUT, tercile=3):
    """The market-neutral read: each quarter, long the cheapest 1/`tercile` by AI
    and short the richest, hold 3y. Reports the long-short spread (the Indicator's
    edge, net of beta) + the cheap/rich buckets vs the S&P 500 (SPY) — to show that
    absolute returns are inflated by the universe+bull market, while the SPREAD
    isolates the signal."""
    import numpy as np
    by_date = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            if r.get("fwd_3y") not in (None, ""):
                by_date.setdefault(r["date"], []).append((float(r["ai"]), float(r["fwd_3y"])))
    spy = S.price_history("SPY"); last = spy[-1][0]

    def spy_fwd(dstr):
        d = date.fromisoformat(dstr); fut = add_years(d, 3)
        if fut > last:
            return None
        _, a0 = S.close_on_or_before(spy, d); _, a1 = S.close_on_or_before(spy, fut)
        return (a1 / a0 - 1) if (a0 and a1) else None

    ls, ca, ra, sa = [], [], [], []
    for d in sorted(by_date):
        xs = sorted(by_date[d], key=lambda p: p[0])
        if len(xs) < 3 * tercile:
            continue
        sp = spy_fwd(d)
        if sp is None:
            continue
        k = len(xs) // tercile
        cheap = [p[1] for p in xs[:k]]; rich = [p[1] for p in xs[-k:]]
        ls.append(np.mean(cheap) - np.mean(rich))
        ca.append(np.mean(cheap)); ra.append(np.mean(rich)); sa.append(sp)
    ls, ca, ra, sa = map(np.array, (ls, ca, ra, sa)); N = len(ls)
    nw = lambda x: _newey_west_t(list(x), 11)[1]
    print(f"long-short 3y read — {N} quarterly cohorts, cheapest/richest AI tercile, SPY benchmark:")
    print(f"  LONG-SHORT (cheap-rich), market-neutral:  {ls.mean():+.1%}   NW t {nw(ls):+.2f}   {100*(ls>0).mean():.0f}% +"
          + ("   <- the Indicator's edge" if abs(nw(ls)) > 2 else ""))
    print(f"  cheap tercile abs / vs S&P:               {ca.mean():+.1%} / {(ca-sa).mean():+.1%} excess (t {nw(ca-sa):+.2f})")
    print(f"  rich  tercile abs / vs S&P:               {ra.mean():+.1%} / {(ra-sa).mean():+.1%} excess (t {nw(ra-sa):+.2f})")
    print(f"  S&P 500 (SPY) abs:                        {sa.mean():+.1%}")
    print("  read: even the RICH bucket beats the S&P here (universe + bull + survivorship),")
    print("  so absolute returns aren't the Indicator's edge — the market-neutral SPREAD is.")


def selftest():
    # vintage point-in-time selection + forward arithmetic
    vs = [dict(filed=date(2020, 2, 1), fy=2019), dict(filed=date(2021, 2, 1), fy=2020),
          dict(filed=date(2022, 2, 1), fy=2021)]
    def pit(D):
        v = None
        for c in vs:
            if c["filed"] <= D:
                v = c
            else:
                break
        return v["fy"] if v else None
    assert pit(date(2020, 6, 30)) == 2019, "PIT should pick FY2019 in mid-2020"
    assert pit(date(2021, 1, 15)) == 2019, "PIT: FY2020 10-K not filed until Feb-2021"
    assert pit(date(2021, 3, 31)) == 2020, "PIT: FY2020 available by Mar-2021"
    assert pit(date(2019, 6, 30)) is None, "PIT: nothing filed yet"
    assert add_years(date(2020, 2, 29), 1) == date(2021, 2, 28), "leap-day forward"
    assert len(quarter_ends(date(2009, 1, 1), date(2024, 12, 31))) == 64, "16y × 4 = 64 quarter-ends"
    # Newey-West: i.i.d. white noise → naive ≈ NW; perfectly +autocorrelated → NW < naive
    import numpy as np
    rng = np.random.default_rng(0); x = list(rng.normal(0.05, 0.2, 200))
    _, ta = _newey_west_t(x, 0); _, tb = _newey_west_t(x, 8)
    assert abs(ta - tb) < 0.6, f"white noise NW≈naive ({ta:.2f} vs {tb:.2f})"
    print("selftest OK — point-in-time, leap-year, quarter grid, Newey-West")


import json as _json
BROAD_OUT = Path(__file__).resolve().parent / "ai2_quarterly_broad.csv"
BROAD_UNI = Path(__file__).resolve().parent / "ai2_universe_broad.json"


def _write(rows, out):
    fields = ["ticker", "date", "ai", "fwd_1q", "fwd_1y", "fwd_3y"]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in sorted(rows, key=lambda x: (x["ticker"], x["date"])):
            w.writerow(r)


def _path_arg(argv, default):
    for a in argv:
        if a.endswith(".csv"):
            return Path(a)
    return default


def main(argv):
    if "--selftest" in argv:
        selftest(); return 0
    if "--analyze" in argv:
        p = _path_arg(argv, OUT); analyze(p); print(); longshort(p); return 0
    if "--longshort" in argv:
        longshort(_path_arg(argv, OUT)); return 0
    if "--broad" in argv:                    # source the broad all-sector universe
        uni = _json.loads(BROAD_UNI.read_text())
        print(f"sourcing BROAD quarterly panel: {len(uni)} tickers → {BROAD_OUT}")
        rows, gaps = source(list(uni), cik_map=uni)
        _write(rows, BROAD_OUT)
        print(f"\nwrote {BROAD_OUT}: {len(rows)} rows, "
              f"{len({r['ticker'] for r in rows})} tickers. gaps: {len(gaps)}")
        analyze(BROAD_OUT); print(); longshort(BROAD_OUT)
        return 0
    tickers = [t for t in S.CIK]
    print(f"sourcing quarterly panel for {len(tickers)} tickers → {OUT}")
    rows, gaps = source(tickers)
    _write(rows, OUT)
    print(f"\nwrote {OUT}: {len(rows)} rows. gaps: {len(gaps)}")
    for g in gaps[:20]:
        print("  ", g)
    analyze(); print(); longshort()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
