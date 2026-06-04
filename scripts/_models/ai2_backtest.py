#!/usr/bin/env python3
"""Arthur Indicator 2.0 — backtest harness that fits the eight weights w1…w8.

    AI_2.0 = EV / ( Revenue × Q ),   EV = MktCap − NetCash
    Q = w1·g + w2·gm + w3·opm + w4·fcfm                       (levels)
      + w5·Δg + w6·Δgm + w7·Δopm + w8·Δfcfm                   (rate-of-change)

where g = revenue growth, gm/opm/fcfm = gross/operating/FCF margin, and Δx is
the YoY change in x. AI_1.0 is the special case w1=w2=1, w3..w8=0 (Q = gm+g).

Lower AI = cheaper-for-quality, so *cheapness* = −AI should predict higher
forward return. We fit w to maximise that predictive power.

────────────────────────────────────────────────────────────────────────────
DATA  — scripts/_models/ai2_panel.csv, one row per (ticker, fiscal year):
    ticker,fy,fye_month,mktcap_b,net_cash_b,revenue_b,gross_margin,
    op_margin,fcf_margin,rev_growth,price_fye
  · mktcap_b / net_cash_b / revenue_b in $B; net_cash + = net cash.
  · margins + rev_growth as decimals (e.g. 0.821, −0.40); may be negative.
  · price_fye = split-adjusted close at fiscal-year-end (for forward returns).
  Cells may carry a trailing "[e]" (estimate) or be blank — both tolerated.

DERIVED (computed here, per ticker, ordered by fy):
  · EV = mktcap − net_cash ;  ev_rev = EV / revenue.
  · Δg, Δgm, Δopm, Δfcfm = this year − prior year (needs the prior fy row).
  · fwd_ret_1y / _3y = price_fye[t+k]/price_fye[t] − 1 (within-ticker; the
    fiscal-calendar offset is therefore self-consistent per name).

OBJECTIVE  — factor-IC: within each fiscal-year cross-section (n ≥ MIN_XS),
rank cheapness (−AI) and the forward return, take Spearman ρ, then average
across cross-sections weighted by n. Reported for AI_1.0 vs the fitted AI_2.0
so the lift is explicit. A coverage penalty (fraction of rows with Q>0) keeps
the fit from choosing weights that make the quality denominator go negative.

FIT  — random search over {w1..w4 ≥ 0, Σ=2} × {w5..w8 ∈ [−1,1]} then a
coordinate pattern-search refine. (The IC objective is non-smooth; gradient
methods don't help.) Leave-one-year-out CV guards against overfitting 8 knobs.

Run:  python scripts/_models/ai2_backtest.py            # fit on the panel
      python scripts/_models/ai2_backtest.py --selftest # synthetic recovery
"""
from __future__ import annotations
import csv
import sys
from pathlib import Path
import numpy as np

PANEL = Path(__file__).resolve().parent / "ai2_panel.csv"
MIN_XS = 4          # min names in a cross-section to score it
HORIZON = "3y"      # primary forward-return horizon ("1y" or "3y")
FIELDS = ("mktcap_b", "net_cash_b", "revenue_b", "gross_margin",
          "op_margin", "fcf_margin", "rev_growth", "price_fye")


# ── parsing ────────────────────────────────────────────────────────────────
def _num(s):
    """Float from a cell, tolerating a trailing [e] flag and blanks."""
    if s is None:
        return np.nan
    s = s.strip().replace("[e]", "").replace("%", "").strip()
    if s == "" or s.lower() in ("na", "n/a", "nan", "-", "—"):
        return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


def load_panel(path: Path = PANEL) -> dict[str, list[dict]]:
    """ticker → list of year-dicts sorted by fy."""
    if not path.exists():
        return {}
    by_t: dict[str, list[dict]] = {}
    with path.open() as fh:
        for r in csv.DictReader(fh):
            t = (r.get("ticker") or "").strip().upper()
            if not t:
                continue
            row = {"ticker": t, "fy": int(_num(r.get("fy"))),
                   "fye_month": (r.get("fye_month") or "").strip()}
            for k in FIELDS:
                row[k] = _num(r.get(k))
            by_t.setdefault(t, []).append(row)
    for t in by_t:
        by_t[t].sort(key=lambda x: x["fy"])
    return by_t


# ── derive Δ terms + forward returns ────────────────────────────────────────
def build_rows(by_t: dict[str, list[dict]]) -> list[dict]:
    rows = []
    for t, series in by_t.items():
        by_fy = {r["fy"]: r for r in series}
        for r in series:
            fy = r["fy"]
            prev = by_fy.get(fy - 1)
            ev = r["mktcap_b"] - r["net_cash_b"]
            rev = r["revenue_b"]
            d = dict(r)
            d["ev_rev"] = ev / rev if rev and rev > 0 else np.nan
            d["g"], d["gm"] = r["rev_growth"], r["gross_margin"]
            d["opm"], d["fcfm"] = r["op_margin"], r["fcf_margin"]
            for nm, key in (("dg", "rev_growth"), ("dgm", "gross_margin"),
                            ("dopm", "op_margin"), ("dfcfm", "fcf_margin")):
                d[nm] = (r[key] - prev[key]) if prev else np.nan
            for k, nm in ((1, "fwd_1y"), (3, "fwd_3y")):
                nxt = by_fy.get(fy + k)
                p0, p1 = r["price_fye"], (nxt["price_fye"] if nxt else np.nan)
                d[nm] = (p1 / p0 - 1) if (p0 and p0 > 0 and np.isfinite(p1)) else np.nan
            rows.append(d)
    return rows


# ── indicator ───────────────────────────────────────────────────────────────
def quality(d: dict, w: np.ndarray) -> float:
    return (w[0] * d["g"] + w[1] * d["gm"] + w[2] * d["opm"] + w[3] * d["fcfm"]
            + w[4] * d["dg"] + w[5] * d["dgm"] + w[6] * d["dopm"] + w[7] * d["dfcfm"])


W_AI1 = np.array([1, 1, 0, 0, 0, 0, 0, 0], float)  # AI 1.0 = gm + g


def ai(d: dict, w: np.ndarray) -> float:
    q = quality(d, w)
    if not np.isfinite(d["ev_rev"]) or not np.isfinite(q) or q <= 0:
        return np.nan
    return d["ev_rev"] / q


# ── Spearman rank-IC ────────────────────────────────────────────────────────
def _rankdata(a: np.ndarray) -> np.ndarray:
    order = a.argsort()
    ranks = np.empty(len(a), float)
    ranks[order] = np.arange(len(a), dtype=float)
    # average ties
    _, inv, cnt = np.unique(a, return_inverse=True, return_counts=True)
    sums = np.zeros(len(cnt)); np.add.at(sums, inv, ranks)
    return (sums / cnt)[inv]


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3:
        return np.nan
    rx, ry = _rankdata(x), _rankdata(y)
    rx -= rx.mean(); ry -= ry.mean()
    denom = np.sqrt((rx * rx).sum() * (ry * ry).sum())
    return float((rx * ry).sum() / denom) if denom > 0 else np.nan


def cross_section_ic(rows: list[dict], w: np.ndarray, horizon: str = HORIZON):
    """Mean per-fy Spearman(cheapness=−AI, forward return), n-weighted.
    Returns (ic, coverage, n_cross_sections). coverage = usable rows / scored rows."""
    fwd = "fwd_1y" if horizon == "1y" else "fwd_3y"
    years = sorted({r["fy"] for r in rows})
    ics, wts, used, scored = [], [], 0, 0
    for fy in years:
        xs = [r for r in rows if r["fy"] == fy and np.isfinite(r.get(fwd, np.nan))]
        scored += len(xs)
        a = np.array([ai(r, w) for r in xs])
        fr = np.array([r[fwd] for r in xs])
        ok = np.isfinite(a) & np.isfinite(fr)
        used += int(ok.sum())
        if ok.sum() >= MIN_XS:
            rho = spearman(-a[ok], fr[ok])      # cheapness vs return
            if np.isfinite(rho):
                ics.append(rho); wts.append(ok.sum())
    if not ics:
        return np.nan, (used / scored if scored else 0.0), 0
    ic = float(np.average(ics, weights=wts))
    return ic, (used / scored if scored else 0.0), len(ics)


def objective(rows, w, horizon=HORIZON):
    ic, cov, n = cross_section_ic(rows, w, horizon)
    if not np.isfinite(ic) or n == 0:
        return -1.0
    return ic * (0.5 + 0.5 * cov)   # reward IC, gently penalise low coverage


# ── fit: random search + coordinate pattern-search refine ────────────────────
def _sample_w(rng) -> np.ndarray:
    lvl = rng.dirichlet(np.ones(4)) * 2.0          # w1..w4 ≥ 0, sum = 2
    dlt = rng.uniform(-1, 1, 4)                     # w5..w8 ∈ [−1,1]
    return np.concatenate([lvl, dlt])


def fit(rows, horizon=HORIZON, n_random=4000, seed=0):
    rng = np.random.default_rng(seed)
    best_w, best_s = W_AI1.copy(), objective(rows, W_AI1, horizon)
    for _ in range(n_random):
        w = _sample_w(rng)
        s = objective(rows, w, horizon)
        if s > best_s:
            best_w, best_s = w, s
    # pattern-search refine (keep Σw1..4 ≈ 2 by renormalising the level block)
    step = 0.25
    for _ in range(60):
        improved = False
        for i in range(8):
            for sign in (+1, -1):
                w = best_w.copy(); w[i] += sign * step
                if i < 4:
                    w[:4] = np.clip(w[:4], 0, None)
                    if w[:4].sum() > 0:
                        w[:4] *= 2.0 / w[:4].sum()
                else:
                    w[i] = float(np.clip(w[i], -1, 1))
                s = objective(rows, w, horizon)
                if s > best_s:
                    best_w, best_s, improved = w, s, True
        if not improved:
            step *= 0.5
            if step < 1e-3:
                break
    return best_w, best_s


def loyo_cv(rows, horizon=HORIZON, seed=0):
    """Leave-one-year-out: fit on all-but-one fy, score that held-out fy."""
    years = sorted({r["fy"] for r in rows})
    oos = []
    for fy in years:
        train = [r for r in rows if r["fy"] != fy]
        test = [r for r in rows if r["fy"] == fy]
        if len({r["fy"] for r in train}) < 3 or len(test) < MIN_XS:
            continue
        w, _ = fit(train, horizon, n_random=1500, seed=seed)
        ic, _, n = cross_section_ic(test, w, horizon)
        if n:
            oos.append(ic)
    return (float(np.nanmean(oos)) if oos else np.nan), len(oos)


# ── reporting ────────────────────────────────────────────────────────────────
def _fmt_w(w):
    names = ["g", "gm", "opm", "fcfm", "Δg", "Δgm", "Δopm", "Δfcfm"]
    return "  ".join(f"{n}={v:+.2f}" for n, v in zip(names, w))


def report(rows, horizon=HORIZON):
    nt = len({r["ticker"] for r in rows})
    print(f"panel: {len(rows)} rows · {nt} tickers · "
          f"{len({r['fy'] for r in rows})} fiscal years · horizon {horizon}")
    ic1, cov1, n1 = cross_section_ic(rows, W_AI1, horizon)
    print(f"\nAI_1.0 (gm+g):  rank-IC = {ic1:+.3f}  over {n1} cross-sections  "
          f"(coverage {cov1:.0%})")
    w, s = fit(rows, horizon)
    ic2, cov2, n2 = cross_section_ic(rows, w, horizon)
    print(f"AI_2.0 (fitted): rank-IC = {ic2:+.3f}  over {n2} cross-sections  "
          f"(coverage {cov2:.0%})")
    print(f"  weights:  {_fmt_w(w)}")
    cv, ncv = loyo_cv(rows, horizon)
    print(f"  leave-one-year-out OOS rank-IC = {cv:+.3f}  ({ncv} folds)")
    lift = ic2 - ic1
    print(f"\nlift (in-sample): {lift:+.3f}   "
          f"{'AI_2.0 helps' if lift > 0.02 else 'marginal — needs more data'}")
    return w


# ── synthetic self-test (verifies the machinery before the real panel) ───────
def selftest():
    """Generate a panel where cheapness defined by a KNOWN weight vector drives
    forward returns, then confirm the fitter recovers a high IC vs AI_1.0."""
    rng = np.random.default_rng(42)
    true_w = np.array([1.0, 0.6, 0.3, 0.1, 0.4, 0.2, 0.1, 0.1])
    tickers = [f"T{i:02d}" for i in range(24)]
    by_t = {}
    for t in tickers:
        g, gm = rng.uniform(0, .6), rng.uniform(.3, .85)
        opm, fcfm = rng.uniform(-.3, .4), rng.uniform(-.3, .35)
        series = []
        for fy in range(2015, 2026):
            g = float(np.clip(g + rng.normal(0, .08), -.3, .9))
            gm = float(np.clip(gm + rng.normal(0, .02), .1, .9))
            opm = float(np.clip(opm + rng.normal(0, .04), -.5, .5))
            fcfm = float(np.clip(fcfm + rng.normal(0, .04), -.5, .45))
            rev = rng.uniform(1, 50)
            ev_rev = rng.uniform(2, 25)
            series.append(dict(ticker=t, fy=fy, fye_month="Dec",
                               revenue_b=rev, mktcap_b=ev_rev * rev, net_cash_b=0.0,
                               gross_margin=gm, op_margin=opm, fcf_margin=fcfm,
                               rev_growth=g, price_fye=np.nan))
        by_t[t] = series
    rows = build_rows(by_t)
    # define "true" cheapness, make next-year price encode it + noise
    true_ai = {(r["ticker"], r["fy"]): ai(r, true_w) for r in rows}
    px = {t: {} for t in by_t}
    for t, series in by_t.items():
        p = 100.0
        for r in series:
            px[t][r["fy"]] = p
            a = true_ai.get((t, r["fy"]), np.nan)
            cheap = -(a if np.isfinite(a) else 0.0)
            ret = 0.06 * cheap + rng.normal(0, 0.25)     # signal + noise
            p *= (1 + ret)
    for t, series in by_t.items():
        for r in series:
            r["price_fye"] = px[t][r["fy"]]
    rows = build_rows(by_t)
    print("── self-test (synthetic; true cheapness drives returns) ──")
    w = report(rows, "1y")
    ic_true, _, _ = cross_section_ic(rows, true_w, "1y")
    print(f"\noracle (true weights) rank-IC = {ic_true:+.3f}")
    print("PASS" if cross_section_ic(rows, w, "1y")[0] > 0.15 else "CHECK fitter")


def main(argv):
    if "--selftest" in argv:
        selftest(); return 0
    by_t = load_panel()
    if not by_t:
        print(f"No panel at {PANEL} yet — assemble the research-agent CSVs into it.")
        print("Run --selftest to verify the harness on synthetic data.")
        return 0
    rows = build_rows(by_t)
    horizon = "1y" if "--1y" in argv else HORIZON
    report(rows, horizon)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
