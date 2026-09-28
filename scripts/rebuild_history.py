#!/usr/bin/env python3
"""Rebuild a memo's page-1 price history from Yahoo (keyless v8 chart feed).

Why: `historical_prices` points are stored as years BEFORE the memo's `date:`.
Until reprice.py learned to shift them (Sep-2026), every re-price advanced the
date without moving the points, drifting each chart 2-4 months toward "today";
some series were also hand-authored and simply wrong (NAUT's 2025 was 3-5x
too high). This replaces a memo's points with sourced data:

  - month-end closes from DAILY bars (true last-trading-day dates; split-
    adjusted `close`, comparable with today's spot); complete months only
  - keep quarter-end months + the last three months inside the memo's window
    (x_min, unchanged) — the first in-window close anchors the left edge
  - t = years before the memo's date (2 decimals; 3 where two points collide)

ipo_marker and x_min are preserved; only the `points:` block is rewritten, in
flow style with the close date on each line. The renderer appends [0, spot].
Verified by reloading the YAML: every other field must be unchanged.

    python scripts/rebuild_history.py --dry-run            # all drifted memos
    python scripts/rebuild_history.py aur zm               # subset, write
    python scripts/rebuild_history.py --x-min-from W.json  # also restore drifted window starts
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
UA = "Mozilla/5.0 (compatible; ar2eb-reprice; arthurculang@gmail.com)"   # reprice.py's feed identity


def month_end_closes(ticker: str, memo_date: dt.date, x_min: float) -> list[tuple[dt.date, float]]:
    """(date, close) for the LAST TRADING DAY of each complete month before the
    memo's month, from daily bars — so every point carries its true date. (Yahoo's
    monthly bars are stamped with the month's START while their close is the
    month's END — dating by the stamp would shift every point ~a month early; the
    in-progress month's close is a live price from after the memo date.)"""
    start = memo_date - dt.timedelta(days=int(-x_min * 365.25) + 40)
    p1 = int(dt.datetime(start.year, start.month, start.day, tzinfo=dt.timezone.utc).timestamp())
    first_of_memo_month = memo_date.replace(day=1)
    p2 = int(dt.datetime(first_of_memo_month.year, first_of_memo_month.month, 1,
                         tzinfo=dt.timezone.utc).timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker.upper()}"
           f"?period1={p1}&period2={p2}&interval=1d")
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                res = json.loads(r.read())["chart"]["result"][0]
            last = {}
            for ts, c in zip(res.get("timestamp") or [], res["indicators"]["quote"][0].get("close") or []):
                if c is None or c <= 0:
                    continue
                d = dt.datetime.fromtimestamp(ts, dt.timezone.utc).date()
                if d < first_of_memo_month:
                    last[(d.year, d.month)] = (d, float(c))      # later days overwrite -> month's last close
            return [last[k] for k in sorted(last)]
        except Exception:  # noqa: BLE001 — retry transport/parse errors
            time.sleep(2 * 2 ** attempt)
    raise RuntimeError(f"{ticker}: Yahoo fetch failed")


def build_points(closes, memo_date: dt.date, x_min: float):
    window = [(d, c) for d, c in closes
              if d < memo_date and (d - memo_date).days / 365.25 >= x_min]
    if not window:
        raise ValueError("no closes inside the window")
    keep = {window[0][0]} | {d for d, _ in window[-3:]} | {d for d, _ in window if d.month in (3, 6, 9, 12)}
    pts = [(d, c) for d, c in window if d in keep]
    out, seen = [], set()
    for d, c in pts:
        t = round((d - memo_date).days / 365.25, 2)
        if t in seen:
            t = round((d - memo_date).days / 365.25, 3)
        seen.add(t)
        out.append((t, round(c, 2), d))
    return out


def rebuild(ticker: str, write: bool, x_min_override: float | None = None) -> str:
    path = DATA / f"{ticker}.yml"
    raw = path.read_text(encoding="utf-8")
    doc = yaml.safe_load(raw)
    hp = doc["historical_prices"]
    memo_date = dt.date.fromisoformat(str(doc["date"]))
    x_min = float(hp["x_min"]) if x_min_override is None else float(x_min_override)
    pts = build_points(month_end_closes(ticker, memo_date, x_min), memo_date, x_min)
    lines = raw.split("\n")
    i = next(k for k, l in enumerate(lines) if l.startswith("historical_prices:"))
    j = i + 1
    while j < len(lines) and (lines[j].startswith(" ") or not lines[j].strip()):
        j += 1
    while not lines[j - 1].strip():
        j -= 1
    block = lines[i:j]
    p = next(k for k, l in enumerate(block) if re.match(r"^\s+points:", l))
    ind = block[p][: len(block[p]) - len(block[p].lstrip())]
    new_pts = [f"{ind}points:   # Yahoo month-end closes (quarter-ends + last 3 months); "
               f"x = years before the {memo_date.isoformat()} as-of"]
    new_pts += [f"{ind}- [{t}, {c:.2f}]   # {d.isoformat()}" for t, c, d in pts]
    rest = [l for l in block[p + 1:] if not (re.match(r"^\s*-", l) or re.match(r"^\s+- ", l)
                                              or (l.strip().startswith("- ") or l.strip().startswith("#")) and
                                              len(l) - len(l.lstrip()) >= len(ind))]
    new_block = block[:p] + new_pts + rest
    if x_min_override is not None:        # restore the originally authored window start
        new_block = [re.sub(r"^(\s+x_min:\s*)(-?[0-9.]+)", lambda m: f"{m.group(1)}{x_min}", l)
                     if re.match(r"^\s+x_min:", l) else l for l in new_block]
    new_raw = "\n".join(lines[:i] + new_block + lines[j:])
    after = yaml.safe_load(new_raw)
    ahp = after["historical_prices"]
    assert [q[:2] for q in ahp["points"]] == [[t, c] for t, c, _ in pts], "points mismatch"
    assert abs(float(ahp["x_min"]) - x_min) < 1e-9, "x_min mismatch"
    assert {k: v for k, v in ahp.items() if k not in ("points", "x_min")} == \
           {k: v for k, v in hp.items() if k not in ("points", "x_min")}
    assert {k: v for k, v in after.items() if k != "historical_prices"} == \
           {k: v for k, v in doc.items() if k != "historical_prices"}, "unexpected change outside history"
    if write:
        path.write_text(new_raw, encoding="utf-8")
    first, last = pts[0], pts[-1]
    return (f"{ticker.upper():5s} {len(hp['points']):3d} -> {len(pts):3d} pts | window {hp['x_min']} -> {x_min} | "
            f"first {first[2]} ${first[1]:.2f} | last {last[2]} ${last[1]:.2f} vs spot ${float(doc['spot']):.2f}")


ALIGNED = {"cai", "coin", "naut", "yeti"}   # rebuilt from Yahoo in the Sep-2026 re-underwrite


def main() -> int:
    args = sys.argv[1:]
    write = "--dry-run" not in args
    overrides = {}
    if "--x-min-from" in args:            # one-time window restoration: {ticker: {"x_min_restored": v}}
        src = args[args.index("--x-min-from") + 1]
        overrides = {t: v["x_min_restored"] for t, v in json.load(open(src)).items() if v.get("drift_y", 0) > 0.01}
        args = [a for a in args if a not in ("--x-min-from", src)]
    names = [a.lower() for a in args if not a.startswith("--")]
    if not names:
        names = []
        for f in sorted(DATA.glob("*.yml")):
            if f.stem.startswith("_") or f.stem == "taxonomy" or f.stem in ALIGNED:
                continue
            d = yaml.safe_load(f.read_text())
            if d.get("dcf_type") != "private_prevaluation" and "historical_prices" in d:
                names.append(f.stem)
    for t in names:
        try:
            print(rebuild(t, write, overrides.get(t)))
        except Exception as e:  # noqa: BLE001
            print(f"{t.upper():5s} FAILED: {e}")
        time.sleep(0.4)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
