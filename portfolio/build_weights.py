#!/usr/bin/env python3
"""Portfolio weights — EV-tilted, capped, long-only, cash residual (spec §12 / §15 D1).

    weight_i  ∝  max(0, expected_upside_i)
    expected_upside_i = weighted_dcf_i / spot_i − 1
    weighted_dcf_i    = Σ_scenario  probability × expected_per_share   (the memo's headline EV)

Each name is capped at CAP (water-filled — capped excess redistributes to the
uncapped names; whatever can't be placed falls to cash). Negative-EV names get
zero (this is a long-only book). Reads data/<ticker>.yml; writes portfolio/weights.yml.

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
CAP = 0.15               # max weight per name (§15 D1)
EPOCH = "2026-07-01"     # launch t0 for performance tracking (§15)
EXCLUDE = {"taxonomy"}


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
        findings[t] = {"spot": float(d["spot"]),
                       "weighted_dcf": round(weighted_dcf(d), 2),
                       "upside": round(u, 4)}

    pos = {t: max(0.0, fv["upside"]) for t, fv in findings.items()}
    s = sum(pos.values())
    weights = {t: round(w, 4) for t, w in water_fill(
        {t: v / s for t, v in pos.items() if v > 0}, CAP).items()} if s > 0 else {}
    cash = round(1.0 - sum(weights.values()), 4)

    out = {
        "as_of": dt.date.today().isoformat(),
        "epoch": EPOCH,
        "rule": (f"EV-tilted (weight proportional to max(0, weighted_DCF/spot - 1)), "
                 f"cap {CAP:.0%}/name, cash residual (spec §12 / §15 D1)"),
        "weights": {**dict(sorted(weights.items(), key=lambda kv: -kv[1])), "cash": cash},
        "excluded_private": sorted(excluded),   # no public price → not in the tracked book
        "findings": dict(sorted(findings.items(), key=lambda kv: -kv[1]["upside"])),
    }
    PORT.mkdir(exist_ok=True)
    (PORT / "weights.yml").write_text(yaml.safe_dump(out, sort_keys=False, allow_unicode=True))

    held = [t for t in weights if weights[t] > 0]
    print(f"wrote portfolio/weights.yml  ({len(held)} holdings + {cash:.0%} cash, of {len(findings)} "
          f"tradeable memos; excluded private: {excluded or 'none'})")
    for t, w in out["weights"].items():
        if not w:
            continue
        tag = f"(upside {findings[t]['upside']:+.0%})" if t in findings else ""
        print(f"  {t:<7} {w:6.1%}  {tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
