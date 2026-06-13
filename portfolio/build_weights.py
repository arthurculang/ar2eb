#!/usr/bin/env python3
"""Portfolio weights — human conviction × quantitative forecast (spec §12 / §15 D1).

    weight_i  ∝  max(0, expected_upside_i) × conviction_mult_i × ai_mult_i

Three factors, transparent and separable:
  · expected_upside_i = weighted_dcf_i / spot_i − 1   — the AI-written memo's
        probability-weighted fair value vs. spot (the quantitative forecast).
  · conviction_mult_i — the HUMAN input: Arthur's conviction tier per name
        (High 2.0 … Low 0.35), his synthesis of the qualitative read (SWOT /
        People-POCD) the model can't price. Conviction-neutral: it enters ONLY
        here at sizing, never the analysis (spec §3.5 B).
  · ai_mult_i — the Arthur Indicator valuation zone (spec §13), a gentle tilt
        (green 1.25 … red 0.70) applied only where the Indicator is defined
        (profitable names; pre-revenue moonshots get a neutral 1.0). It's a
        validated-OOS cheapness screen that refines — not dominates — the DCF.

Each name is capped at CAP (water-filled — capped excess redistributes to the
uncapped names; whatever can't be placed falls to cash). Negative-EV names get
zero (this is a long-only book). Reads data/<ticker>.yml; writes portfolio/weights.yml
with the full per-name calculation so the portfolio page can render it transparently.

This is the deterministic rule the monthly rebuild (§15) calls; run by hand anytime:
    python portfolio/build_weights.py
"""
from __future__ import annotations
import sys
import datetime as dt
from pathlib import Path
import yaml

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
PORT = REPO / "portfolio"
sys.path.insert(0, str(REPO / "scripts"))
from arthur_indicator import compute_ai, ai_zone, ai_weight_mult  # noqa: E402

CAP = 0.15               # max weight per name (§15 D1)
EPOCH = "2026-07-01"     # launch t0 for performance tracking (§15)
EXCLUDE = {"taxonomy"}

# Human conviction tier → sizing multiplier (spec §12). High-conviction names
# get up to 2x the tilt; tier-less mega-caps and unrated names are neutral (1.0).
CONVICTION_MULT = {"High": 2.0, "Med-High": 1.5, "Med": 1.0, "Med-Low": 0.6,
                   "Low": 0.35, None: 1.0}


def weighted_dcf(d: dict) -> float:
    return sum(s["probability"] * s["expected_per_share"] for s in d["scenarios"].values())


def upside(d: dict) -> float | None:
    spot = float(d.get("spot") or 0)
    return (weighted_dcf(d) / spot - 1.0) if spot > 0 else None


def water_fill(raw: dict[str, float], cap: float) -> dict[str, float]:
    """Cap each weight at `cap`, redistributing the capped excess proportionally
    among the names still under the cap. Excess that can't be placed (all names
    capped) is left unallocated → it becomes cash in main()."""
    w = dict(raw)
    for _ in range(100):
        over = {t: v for t, v in w.items() if v > cap + 1e-12}
        if not over:
            break
        excess = sum(v - cap for v in over.values())
        for t in over:
            w[t] = cap
        room = {t: v for t, v in w.items() if v < cap - 1e-12}
        tot = sum(room.values())
        if tot <= 0:
            break
        for t in room:
            w[t] += excess * room[t] / tot
    return w


def main() -> int:
    findings: dict[str, dict] = {}
    excluded: list[str] = []
    for f in sorted(DATA.glob("*.yml")):
        t = f.stem
        if t in EXCLUDE:
            continue
        d = yaml.safe_load(f.read_text())
        if "scenarios" not in d or "spot" not in d:
            continue
        # The tracked book is publicly tradeable names only — a private name
        # (private_prevaluation, e.g. Anthropic) has no daily public price to mark
        # or to benchmark against, so it can't sit in the weighted portfolio.
        if d.get("dcf_type") == "private_prevaluation":
            excluded.append(t)
            continue
        u = upside(d)
        if u is None:
            continue
        tier = (d.get("taxonomy") or {}).get("tier")
        conv = CONVICTION_MULT.get(tier, 1.0)
        ai = compute_ai(d, t)
        ai_mult = ai_weight_mult(ai)
        raw = max(0.0, u) * conv * ai_mult        # upside × conviction × indicator
        findings[t] = {"spot": float(d["spot"]),
                       "weighted_dcf": round(weighted_dcf(d), 2),
                       "upside": round(u, 4),
                       "tier": tier,
                       "conviction_mult": conv,
                       "ai": round(ai, 2) if ai is not None else None,
                       "ai_zone": ai_zone(ai),
                       "ai_mult": ai_mult,
                       "raw_score": round(raw, 4)}

    pos = {t: fv["raw_score"] for t, fv in findings.items()}
    s = sum(pos.values())
    weights = {t: round(w, 4) for t, w in water_fill(
        {t: v / s for t, v in pos.items() if v > 0}, CAP).items()} if s > 0 else {}
    cash = round(1.0 - sum(weights.values()), 4)
    for t, fv in findings.items():
        fv["weight"] = weights.get(t, 0.0)

    out = {
        "as_of": dt.date.today().isoformat(),
        "epoch": EPOCH,
        "rule": (f"weight ∝ max(0, weighted_DCF/spot - 1) × conviction_mult × arthur_indicator_mult, "
                 f"cap {CAP:.0%}/name, cash residual (spec §12 / §15 D1). "
                 f"conviction: High 2.0 · Med-High 1.5 · Med 1.0 · Med-Low 0.6 · Low 0.35. "
                 f"indicator zone: green 1.25 · yellow 1.10 · orange 0.90 · red 0.70 · n/a 1.0."),
        "weights": {**dict(sorted(weights.items(), key=lambda kv: -kv[1])), "cash": cash},
        "excluded_private": sorted(excluded),   # no public price → not in the tracked book
        "findings": dict(sorted(findings.items(),
                                key=lambda kv: (-kv[1]["weight"], -kv[1]["upside"]))),
    }
    PORT.mkdir(exist_ok=True)
    (PORT / "weights.yml").write_text(yaml.safe_dump(out, sort_keys=False, allow_unicode=True))

    held = [t for t in weights if weights[t] > 0]
    print(f"wrote portfolio/weights.yml  ({len(held)} holdings + {cash:.0%} cash, of {len(findings)} "
          f"tradeable memos; excluded private: {excluded or 'none'})")
    print(f"  {'name':<7}{'upside':>8}{'conv':>10}{'×':>5}{'indicator':>16}{'×':>6}{'weight':>9}")
    for t, fv in out["findings"].items():
        if not fv["weight"]:
            continue
        conv = f"{fv['tier'] or '—'} {fv['conviction_mult']:.2f}"
        ind = (f"{fv['ai_zone']} {fv['ai']:.1f}" if fv["ai"] is not None else "n/a") + f" {fv['ai_mult']:.2f}"
        print(f"  {t:<7}{fv['upside']:>+8.0%}{conv:>10}{'':>5}{ind:>16}{'':>6}{fv['weight']:>9.1%}")
    if cash > 0.001:
        print(f"  {'cash':<7}{'':>8}{'':>10}{'':>5}{'':>16}{'':>6}{cash:>9.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
