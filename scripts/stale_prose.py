#!/usr/bin/env python3
"""Flag rendered prose that restates a price or finding the model no longer has.

A mechanical re-price (scripts/reprice.py) moves `spot`, market cap and `date:`
but never edits prose, so a thesis written at an old price keeps quoting it —
while page 1 renders the live headline right beside it. This scanner lists the
candidates for the monthly's prose-sync step (and the quarterly's checks):

  1. an EARLIER spot price (from stamp.prior_versions) quoted in prose;
  2. a finding-like percentage ("weighted … −25%", "the finding is +12%",
     "(+31%)" after "vs spot") that matches NEITHER the current finding NOR any
     scenario's current value vs spot (within 2 pts) — so a correctly synced
     "the bull lands −55%" is not flagged.

It is a heuristic helper, not a gate: it can miss a stale number phrased
differently. Read every hit in context before editing. Private memos are skipped.

Usage:
    python scripts/stale_prose.py            # all public memos
    python scripts/stale_prose.py gral pacb  # subset
Exit code 0 always (informational).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"


def prose_fields(d: dict):
    """(path, text) for every rendered prose field that commonly restates price."""
    for f in ("central_question", "thesis"):
        if d.get(f):
            yield f, d[f]
    for i, e in enumerate((d.get("market") or {}).get("extras") or []):
        yield f"market.extras[{i}]", str(e)
    for i, r in enumerate(d.get("weighting_rationale") or []):
        yield f"weighting_rationale[{i}]", str(r.get("body", ""))
    for k, s in (d.get("scenarios") or {}).items():
        for fld in ("headline", "probability_rationale"):
            if s.get(fld):
                yield f"scenarios.{k}.{fld}", str(s[fld])
        nar = s.get("narrative")
        for i, p in enumerate(nar if isinstance(nar, list) else [nar] if nar else []):
            yield f"scenarios.{k}.narrative[{i}]", str(p)
    ap = d.get("appendix") or {}
    for sec in ("pushback", "triggers"):
        for i, r in enumerate(ap.get(sec) or []):
            yield f"appendix.{sec}[{i}]", f"{r.get('label', '')} {r.get('body', '')}"
    comp = d.get("competitive") or {}
    if comp.get("takeaway"):
        yield "competitive.takeaway", str(comp["takeaway"])
    pocd = d.get("pocd") or {}
    for k in ("opportunity_ref", "context_ref", "deal"):
        if pocd.get(k):
            yield f"pocd.{k}", str(pocd[k])


def scan(ticker: str) -> list[str]:
    d = yaml.safe_load((DATA / f"{ticker}.yml").read_text())
    if d.get("dcf_type") == "private_prevaluation":
        return []
    spot = float(d["spot"])
    sc = d["scenarios"]
    weighted = sum(s["probability"] * s["expected_per_share"] for s in sc.values())
    finding = (weighted / spot - 1) * 100
    valid = [finding] + [(s["expected_per_share"] / spot - 1) * 100 for s in sc.values()]
    stale = lambda v: all(abs(v - x) > 2.0 for x in valid)
    priors = {float(pv["spot"]) for pv in (d["stamp"].get("prior_versions") or [])
              if pv.get("spot")}
    hits = []
    for path, text in prose_fields(d):
        for ps in priors:
            if abs(ps - spot) / spot < 0.005:
                continue
            for fmt in (f"${ps:.2f}", f"${ps:,.2f}"):
                if fmt in text:
                    hits.append(f"{path}: earlier spot {fmt} (now ${spot:.2f})")
        for m in re.finditer(r"(weighted|finding|expected)[^.;]{0,60}?([+\-−]\d+(?:\.\d)?)%", text, re.I):
            v = float(m.group(2).replace("−", "-"))
            if stale(v):
                hits.append(f"{path}: finding-like {m.group(2)}% (now {finding:+.1f}%) — …{m.group(0)[:70]}")
        for m in re.finditer(r"\(([+\-−]\d+(?:\.\d)?)%\)", text):
            v = float(m.group(1).replace("−", "-"))
            ctx = text[max(0, m.start() - 60):m.start()]
            if stale(v) and re.search(r"weighted|vs spot|vs the price", ctx, re.I):
                hits.append(f"{path}: ({m.group(1)}%) after '{ctx[-30:]}' (now {finding:+.1f}%)")
    return hits


def main() -> int:
    args = [a.lower() for a in sys.argv[1:] if not a.startswith("-")]
    tickers = args or sorted(p.stem for p in DATA.glob("*.yml")
                             if not p.stem.startswith("_") and p.stem != "taxonomy")
    n = 0
    for t in tickers:
        hits = scan(t)
        if hits:
            n += 1
            print(f"== {t}")
            for h in hits:
                print(f"   {h}")
    print(f"stale_prose: {n} memo(s) with candidate stale restatements")
    return 0


if __name__ == "__main__":
    sys.exit(main())
