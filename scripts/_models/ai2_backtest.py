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


def objective(rows, w, horizon=HORIZON, ridge=0.0):
    ic, cov, n = cross_section_ic(rows, w, horizon)
    if not np.isfinite(ic) or n == 0:
        return -1.0
    score = ic * (0.5 + 0.5 * cov)   # reward IC, gently penalise low coverage
    if ridge:                        # shrink toward AI 1.0 (Q = gm + g)
        score -= ridge * float(np.sum((w - W_AI1) ** 2))
    return score


# ── fit: random search + coordinate pattern-search refine ────────────────────
# Regularisation knobs (used by the model-selection ladder — see model_select):
#   · free          — indices of the 8 weights that are FREE to move; the rest
#                     are pinned at 0 (nested models: fit only a subset). Levels
#                     in `free` are renormalised to sum 2 (AI 1.0's gauge), so the
#                     delta block's magnitude is comparable across models.
#   · delta_nonneg  — constrain Δ-weights (w5..w8) ≥ 0: improving margins / accel-
#                     erating growth may only make a name screen CHEAPER, never
#                     richer. Kills the sign-flips the unconstrained fit produced.
#   · ridge         — shrink toward AI 1.0 (penalise ‖w − w_AI1‖²).
def _sample_w(rng, free=None, delta_nonneg=False) -> np.ndarray:
    if free is None:
        free = list(range(8))
    w = np.zeros(8)
    lvl_free = [i for i in free if i < 4]
    dlt_free = [i for i in free if i >= 4]
    if lvl_free:
        d = rng.dirichlet(np.ones(len(lvl_free))) * 2.0   # free levels ≥ 0, sum = 2
        for i, v in zip(lvl_free, d):
            w[i] = v
    lo = 0.0 if delta_nonneg else -1.0
    for i in dlt_free:
        w[i] = rng.uniform(lo, 1.0)
    return w


def fit(rows, horizon=HORIZON, n_random=4000, seed=0,
        free=None, delta_nonneg=False, ridge=0.0):
    if free is None:
        free = list(range(8))
    lvl_free = [i for i in free if i < 4]
    rng = np.random.default_rng(seed)
    # start from AI 1.0 restricted to the model's free set
    w0 = np.zeros(8)
    for i in (0, 1):
        if i in free:
            w0[i] = 1.0
    if not lvl_free:           # degenerate guard (shouldn't happen in the ladder)
        w0[0] = w0[1] = 1.0
    best_w, best_s = w0.copy(), objective(rows, w0, horizon, ridge)
    for _ in range(n_random):
        w = _sample_w(rng, free, delta_nonneg)
        s = objective(rows, w, horizon, ridge)
        if s > best_s:
            best_w, best_s = w, s
    # pattern-search refine over FREE indices (renormalise the free level block to 2)
    lo = 0.0 if delta_nonneg else -1.0
    step = 0.25
    for _ in range(60):
        improved = False
        for i in free:
            for sign in (+1, -1):
                w = best_w.copy(); w[i] += sign * step
                if i < 4:
                    w[lvl_free] = np.clip(w[lvl_free], 0, None)
                    if w[lvl_free].sum() > 0:
                        w[lvl_free] *= 2.0 / w[lvl_free].sum()
                else:
                    w[i] = float(np.clip(w[i], lo, 1))
                s = objective(rows, w, horizon, ridge)
                if s > best_s:
                    best_w, best_s, improved = w, s, True
        if not improved:
            step *= 0.5
            if step < 1e-3:
                break
    return best_w, best_s


def loyo_cv(rows, horizon=HORIZON, seed=0, free=None, delta_nonneg=False, ridge=0.0):
    """Leave-one-year-out: fit on all-but-one fy, score that held-out fy."""
    years = sorted({r["fy"] for r in rows})
    oos = []
    for fy in years:
        train = [r for r in rows if r["fy"] != fy]
        test = [r for r in rows if r["fy"] == fy]
        if len({r["fy"] for r in train}) < 3 or len(test) < MIN_XS:
            continue
        w, _ = fit(train, horizon, n_random=1500, seed=seed,
                   free=free, delta_nonneg=delta_nonneg, ridge=ridge)
        ic, _, n = cross_section_ic(test, w, horizon)
        if n:
            oos.append(ic)
    return (float(np.nanmean(oos)) if oos else np.nan), len(oos)


def loyo_fixed(rows, w_fixed, horizon=HORIZON):
    """OOS for a NON-fitted model (e.g. AI 1.0): score a fixed w on each held-out
    fy. No training → its OOS ≈ in-sample, the right zero-parameter benchmark."""
    oos = []
    for fy in sorted({r["fy"] for r in rows}):
        test = [r for r in rows if r["fy"] == fy]
        if len(test) < MIN_XS:
            continue
        ic, _, n = cross_section_ic(test, w_fixed, horizon)
        if n:
            oos.append(ic)
    return (float(np.nanmean(oos)) if oos else np.nan), len(oos)


# ── nested-model selection ladder (judge by LOYO-OOS, prefer the simplest) ───
# Index map: 0=g 1=gm 2=opm 3=fcfm · 4=Δg 5=Δgm 6=Δopm 7=Δfcfm.  Every model keeps
# the AI 1.0 core {g, gm}; we add terms one block at a time and let OOS decide.
MODELS = {
    "AI 1.0  (g,gm @1,1)":  [],                 # 0 free params — the baseline
    "L2  g,gm":             [0, 1],             # re-weighted levels
    "L3  +fcfm":            [0, 1, 3],
    "L4  +opm,fcfm":        [0, 1, 2, 3],
    "L4+Δfcfm":             [0, 1, 2, 3, 7],
    "L2+Δg,Δgm":            [0, 1, 4, 5],
    "Full-8":               [0, 1, 2, 3, 4, 5, 6, 7],
}


def fcfm_model(rows, grid=None):
    """The parsimonious calibrated AI 2.0 the ladder points to: AI 1.0's proven
    denominator plus ONE FCF-margin term — Q = g + gm + λ·fcfm. A single knob
    (can't overfit 8), λ chosen by OOS. Prints the λ-curve (in-sample + fixed-λ
    OOS at both horizons) and the honest nested-LOYO OOS (λ re-fit on each training
    fold, scored on the held-out year). Returns per-horizon (λ*, nested-OOS, OOS@0)."""
    if grid is None:
        grid = [round(0.1 * i, 2) for i in range(0, 16)]   # 0.0 … 1.5
    def w_of(lam):
        return np.array([1, 1, 0, lam, 0, 0, 0, 0], float)
    print("parsimonious AI 2.0:  Q = g + gm + λ·fcfm   (λ = 0 is exactly AI 1.0)\n")
    print(f"{'λ':>5}  {'IS-3y':>7} {'OOS-3y':>7}  {'IS-1y':>7} {'OOS-1y':>7}")
    print("-" * 40)
    for lam in grid:
        w = w_of(lam)
        is3, oo3 = cross_section_ic(rows, w, "3y")[0], loyo_fixed(rows, w, "3y")[0]
        is1, oo1 = cross_section_ic(rows, w, "1y")[0], loyo_fixed(rows, w, "1y")[0]
        print(f"{lam:>5.2f}  {is3:>+7.3f} {oo3:>+7.3f}  {is1:>+7.3f} {oo1:>+7.3f}")
    out = {}
    for horizon in ("3y", "1y"):
        # honest nested LOYO: pick λ on the train folds (by train IS-IC), score test
        oos = []
        for fy in sorted({r["fy"] for r in rows}):
            train = [r for r in rows if r["fy"] != fy]
            test = [r for r in rows if r["fy"] == fy]
            if len(test) < MIN_XS or len({r["fy"] for r in train}) < 3:
                continue
            lam = max(grid, key=lambda L: cross_section_ic(train, w_of(L), horizon)[0])
            ic = cross_section_ic(test, w_of(lam), horizon)[0]
            if np.isfinite(ic):
                oos.append(ic)
        nested = float(np.nanmean(oos)) if oos else np.nan
        lam_star = max(grid, key=lambda L: cross_section_ic(rows, w_of(L), horizon)[0])
        oos0 = loyo_fixed(rows, w_of(0.0), horizon)[0]
        out[horizon] = (lam_star, nested, oos0)
        print(f"\n{horizon}: in-sample-optimal λ = {lam_star:.2f}  ·  "
              f"nested-LOYO OOS (λ re-fit per fold) = {nested:+.3f}  "
              f"(vs AI 1.0 OOS {oos0:+.3f})")
    return out


def model_select(rows, delta_nonneg=True, ridge=0.0, seed=0):
    """Fit the nested ladder at both horizons; report IS + LOYO-OOS for each so the
    simplest model that beats AI 1.0 OOS at BOTH horizons is visible. Δ-weights are
    sign-constrained ≥ 0 by default (the economic prior)."""
    nt = len({r["ticker"] for r in rows})
    print(f"panel: {len(rows)} rows · {nt} tickers · "
          f"{len({r['fy'] for r in rows})} fiscal years")
    print(f"nested model selection  (Δ-weights ≥ 0: {delta_nonneg}; ridge={ridge})")
    print("judge = leave-one-year-out OOS rank-IC (NOT in-sample).\n")
    base3 = loyo_fixed(rows, W_AI1, "3y")[0]
    base1 = loyo_fixed(rows, W_AI1, "1y")[0]
    print(f"{'model':<20} {'k':>2}  {'IS-3y':>7} {'OOS-3y':>7}  {'IS-1y':>7} {'OOS-1y':>7}")
    print("-" * 64)
    results = {}
    for name, free in MODELS.items():
        cells, ws = [], {}
        for hz in ("3y", "1y"):
            if not free:
                isamp = cross_section_ic(rows, W_AI1, hz)[0]
                oos = loyo_fixed(rows, W_AI1, hz)[0]
                ws[hz] = W_AI1
            else:
                w, _ = fit(rows, hz, free=free, delta_nonneg=delta_nonneg,
                           ridge=ridge, seed=seed)
                isamp = cross_section_ic(rows, w, hz)[0]
                oos = loyo_cv(rows, hz, free=free, delta_nonneg=delta_nonneg,
                              ridge=ridge, seed=seed)[0]
                ws[hz] = w
            cells.append((isamp, oos))
        results[name] = (free, cells, ws)
        beats = (cells[0][1] > base3 + 1e-9) and (cells[1][1] > base1 + 1e-9)
        mark = "  ◀ beats AI 1.0 OOS (both)" if (free and beats) else ""
        print(f"{name:<20} {len(free):>2}  {cells[0][0]:>+7.3f} {cells[0][1]:>+7.3f}  "
              f"{cells[1][0]:>+7.3f} {cells[1][1]:>+7.3f}{mark}")
    print("-" * 64)
    print(f"AI 1.0 OOS baseline:  3y {base3:+.3f}   1y {base1:+.3f}")
    return results


# ── reporting ────────────────────────────────────────────────────────────────
def _fmt_w(w):
    names = ["g", "gm", "opm", "fcfm", "Δg", "Δgm", "Δopm", "Δfcfm"]
    return "  ".join(f"{n}={v:+.2f}" for n, v in zip(names, w))


# ── belt-and-suspenders: deterministic exhaustive grid (no sampler) ──────────
def _year_arrays(rows, horizon):
    """Per fiscal year, the (features, ev_rev, fwd) arrays — built once so the grid
    scan can score thousands of fixed weight vectors fast."""
    fwd = "fwd_1y" if horizon == "1y" else "fwd_3y"
    feats = ("g", "gm", "opm", "fcfm", "dg", "dgm", "dopm", "dfcfm")
    # Match the harness's universe exactly: quality() sums w·features where
    # 0·NaN = NaN, so ai() drops a row if ANY of the 8 features is NaN — for every
    # w. That puts AI 1.0 and every enriched model on the SAME cross-sections (a
    # fair comparison), so the grid must require all 8 features present too.
    out = []
    for fy in sorted({r["fy"] for r in rows}):
        xs = [r for r in rows if r["fy"] == fy
              and np.isfinite(r.get(fwd, np.nan)) and np.isfinite(r.get("ev_rev", np.nan))
              and all(np.isfinite(r.get(k, np.nan)) for k in feats)]
        if len(xs) < MIN_XS:
            continue
        F = np.array([[r[k] for k in feats] for r in xs], float)
        ev = np.array([r["ev_rev"] for r in xs], float)
        fw = np.array([r[fwd] for r in xs], float)
        out.append((F, ev, fw))
    return out


def _grid_year_ics(year_arrays, w):
    """Per-year Spearman(−AI, fwd) for a FIXED w (np.nan where a year is unscorable);
    AI = ev/(F·w); a row is dropped if any USED (w≠0) feature is NaN or Q ≤ 0. The
    NaN-of-a-zero-weighted feature is treated as 0 (not propagated), matching ai()."""
    nz = w != 0
    ics = []
    for F, ev, fw in year_arrays:
        bad = np.isnan(F[:, nz]).any(axis=1)
        Q = np.where(np.isnan(F), 0.0, F) @ w
        ok = (~bad) & np.isfinite(Q) & (Q > 0)
        rho = spearman(-(ev[ok] / Q[ok]), fw[ok]) if ok.sum() >= MIN_XS else np.nan
        ics.append(rho)
    return np.array(ics, float)


def grid_scan(rows, levels=(-1.0, -0.5, 0.0, 0.5, 1.0)):
    """Deterministic EXHAUSTIVE grid over the 6 *added* AI 2.0 variables (opm, fcfm,
    Δg, Δgm, Δopm, Δfcfm), g=gm=1 fixed, each weight ∈ `levels` — no random sampler.
    Scores every combination by leave-one-year-out OOS (fixed-w per-year IC) at both
    horizons; reports how many beat AI 1.0 at both, the best, and a nested grid-LOYO
    (best grid w chosen on the train folds, scored on the held-out year)."""
    import itertools
    by1, by3 = _year_arrays(rows, "1y"), _year_arrays(rows, "3y")
    base1 = float(np.nanmean(_grid_year_ics(by1, W_AI1)))
    base3 = float(np.nanmean(_grid_year_ics(by3, W_AI1)))
    # self-validate the fast scorer against the tested loyo_fixed before trusting it
    assert abs(base1 - loyo_fixed(rows, W_AI1, "1y")[0]) < 1e-9, "fast scorer ≠ loyo_fixed (1y)"
    assert abs(base3 - loyo_fixed(rows, W_AI1, "3y")[0]) < 1e-9, "fast scorer ≠ loyo_fixed (3y)"
    grid = list(itertools.product(levels, repeat=6))
    names = ["opm", "fcfm", "Δg", "Δgm", "Δopm", "Δfcfm"]
    print(f"exhaustive grid: g=gm=1 fixed · 6 added weights ∈ {levels} → "
          f"{len(grid)} combinations, each scored by LOYO-OOS at both horizons (no sampler)")
    print(f"AI 1.0 OOS baseline:  3y {base3:+.3f}   1y {base1:+.3f}\n")
    Y1 = np.full((len(grid), len(by1)), np.nan)
    Y3 = np.full((len(grid), len(by3)), np.nan)
    n_both = 0; best_both = None; max1 = (-9.0, None); max3 = (-9.0, None)
    for gi, combo in enumerate(grid):
        w = np.array([1.0, 1.0, *combo])
        Y1[gi] = _grid_year_ics(by1, w); Y3[gi] = _grid_year_ics(by3, w)
        ic1, ic3 = float(np.nanmean(Y1[gi])), float(np.nanmean(Y3[gi]))
        if ic1 > max1[0]: max1 = (ic1, combo)
        if ic3 > max3[0]: max3 = (ic3, combo)
        if ic1 > base1 and ic3 > base3:
            n_both += 1
            edge = min(ic1 - base1, ic3 - base3)
            if best_both is None or edge > best_both[0]:
                best_both = (edge, combo, ic3, ic1)
    print(f"combinations beating AI 1.0 OOS at BOTH horizons: {n_both} / {len(grid)}")
    if best_both:
        c = best_both[1]
        print("  best-both: " + "  ".join(f"{n}={v:+.1f}" for n, v in zip(names, c))
              + f"  → 3y {best_both[2]:+.3f}  1y {best_both[3]:+.3f}")
    print(f"  best single horizon:  3y {max3[0]:+.3f} (vs {base3:+.3f})   "
          f"1y {max1[0]:+.3f} (vs {base1:+.3f})")

    def nested(Y):
        ny = Y.shape[1]; oos = []
        for ty in range(ny):
            train = np.nanmean(Y[:, np.delete(np.arange(ny), ty)], axis=1)
            gi = int(np.nanargmax(train))
            if np.isfinite(Y[gi, ty]):
                oos.append(Y[gi, ty])
        return float(np.nanmean(oos)) if oos else np.nan
    print("\nnested grid-LOYO (best grid w chosen per train fold, scored on the held-out year):")
    print(f"  3y {nested(Y3):+.3f}  (AI 1.0 {base3:+.3f})    1y {nested(Y1):+.3f}  (AI 1.0 {base1:+.3f})")


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
    ok_fit = cross_section_ic(rows, w, "1y")[0] > 0.15
    # regularisation machinery: nested mask pins non-free weights at 0; the
    # sign-constraint holds Δ-weights ≥ 0; a heavy ridge collapses w toward AI 1.0.
    wL2, _ = fit(rows, "1y", free=[0, 1], n_random=400, seed=1)
    assert np.allclose(wL2[2:], 0.0), ("free mask leaked", wL2)
    wC, _ = fit(rows, "1y", free=list(range(8)), delta_nonneg=True, n_random=400, seed=1)
    assert (wC[4:] >= -1e-9).all(), ("Δ sign-constraint violated", wC)
    wR, _ = fit(rows, "1y", free=list(range(8)), ridge=50.0, n_random=400, seed=1)
    assert np.allclose(wR, W_AI1, atol=0.05), ("heavy ridge should collapse to AI 1.0", wR)
    res = model_select(rows, delta_nonneg=True, seed=1)
    assert set(res) == set(MODELS), "model ladder incomplete"
    # exhaustive-grid path (small grid for speed): self-validates its fast scorer
    # against loyo_fixed via internal asserts, and must run end-to-end.
    grid_scan(rows, levels=(0.0, 1.0))
    # parsimonious AI 1.0 + λ·fcfm: at λ=0 it must reproduce AI 1.0's OOS exactly.
    fc = fcfm_model(rows)
    for hz in ("3y", "1y"):
        assert abs(fc[hz][2] - loyo_fixed(rows, W_AI1, hz)[0]) < 1e-9, ("λ=0 ≠ AI 1.0", hz)
    print("\nreg machinery OK — mask pins non-free=0, Δ≥0 enforced, ridge→AI 1.0, "
          "ladder + fcfm model run (λ=0 ≡ AI 1.0)")
    print("PASS" if ok_fit else "CHECK fitter")


def main(argv):
    if "--selftest" in argv:
        selftest(); return 0
    by_t = load_panel()
    if not by_t:
        print(f"No panel at {PANEL} yet — assemble the research-agent CSVs into it.")
        print("Run --selftest to verify the harness on synthetic data.")
        return 0
    rows = build_rows(by_t)
    if "--select" in argv:                     # nested-model regularised selection
        ridge = float(argv[argv.index("--ridge") + 1]) if "--ridge" in argv else 0.0
        model_select(rows, delta_nonneg="--allow-neg-delta" not in argv, ridge=ridge)
        return 0
    if "--fcfm" in argv:                        # parsimonious AI 1.0 + λ·fcfm model
        fcfm_model(rows)
        return 0
    if "--grid" in argv:                        # deterministic exhaustive grid (no sampler)
        grid_scan(rows)
        return 0
    horizon = "1y" if "--1y" in argv else HORIZON
    report(rows, horizon)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
