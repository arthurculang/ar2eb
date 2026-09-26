#!/usr/bin/env python3
"""Book-wide mechanical re-price — the §15 quant refresh as one deterministic
command (extracted from the monthly-rebuild routine's steps 1-3 so any run —
monthly Routine, quarterly re-underwrite, ad-hoc session — reprices the book
identically instead of re-deriving the procedure in prose).

Per public ticker (dcf_type != private_prevaluation):
  1. BUMP = ARCHIVE (scripts/bump_pdf_version.py) — snapshots the OUTGOING
     stamp (version/timestamp/as-of/spot) into stamp.prior_versions and
     increments the version. Bump happens BEFORE the re-price so the old
     spot/date are filed under the old version.
  2. RE-PRICE — fetch the current price from Yahoo (keyless v8 chart, the
     same feed track_performance.py uses), then surgically rewrite ONLY:
       spot:                      -> latest price
       market.market_cap_billion: -> shares-held-constant mcap
                                     (shares = old_mcap / old_spot)
       date:                      -> today (UTC)
     historical_prices:         -> kept aligned with the new date (below)
     Nothing else in the file is touched — theses/scenarios are prose the
     mechanical pass must never edit (that's the quarterly re-underwrite's
     job, §15.3).
     History alignment: chart points are stored as years BEFORE the memo's
     date, so advancing `date:` by Δ must shift every point (and x_min) by −Δ
     — otherwise the whole history drifts toward "today" by a month per
     re-price. The outgoing spot is appended at t = −Δ (last month's "today"
     becomes a real history point), so the line stays continuous.
  3. PIPELINE (unless --skip-render):
       validate.py (strict) -> rebuild_all.py --strict-layout
       -> portfolio/build_weights.py -> visual_hash.py (baseline regen)

Safety: ALL prices are fetched (with retries) before any file is modified;
a single failed fetch aborts the whole run unless --partial-ok, so the book
can't end up half-repriced (same discipline as track_performance's refusal
to write a partial perf row). SPLIT GUARD: the same fetch returns Yahoo's
split events since each memo's own `date:`; a split counts as a failure,
because holding shares constant across a split would silently corrupt market
cap and every per-share comparison (a 1:10 reverse split — the usual cure for
a sub-$1 Nasdaq listing — would read as a 10x rally against a stale share
count). Rescale shares and per-share fields first, then re-run.

Usage:
    python scripts/reprice.py                     # full book
    python scripts/reprice.py naut rklb           # subset
    python scripts/reprice.py --dry-run           # fetch + report, touch nothing
    python scripts/reprice.py --no-bump           # re-price without archiving
    python scripts/reprice.py --skip-render       # yml edits only (caller renders)
    python scripts/reprice.py --partial-ok        # proceed past failed fetches
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.request
import datetime as dt
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
UA = "Mozilla/5.0 (compatible; ar2eb-reprice; arthurculang@gmail.com)"
RETRIES = 4          # per-ticker fetch attempts
BACKOFF = 2.0        # seconds, doubles per retry


def public_tickers() -> list[str]:
    """Every data/*.yml except taxonomy/_-prefixed and private_prevaluation."""
    out = []
    for p in sorted(DATA.glob("*.yml")):
        if p.stem.startswith("_") or p.stem == "taxonomy":
            continue
        doc = yaml.safe_load(p.read_text())
        if doc.get("dcf_type") == "private_prevaluation":
            continue
        out.append(p.stem)
    return out


def memo_date(ticker: str) -> str:
    """The memo's current top-level `date:` (its as-of date), ISO string."""
    return str(yaml.safe_load((DATA / f"{ticker}.yml").read_text())["date"])


def fetch_price(ticker: str, since: str) -> tuple[float, str, list[tuple[str, str]]]:
    """(latest price, as-of date str, splits since `since`) from Yahoo's keyless
    v8 chart endpoint, in ONE request (events=split over the memo-date window).

    regularMarketPrice is the live/latest quote; the last daily close is the
    fallback. Retries with exponential backoff — Yahoo throttles bursts.
    """
    p1 = int(dt.datetime.fromisoformat(since).replace(tzinfo=dt.timezone.utc).timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker.upper()}"
           f"?period1={p1}&period2=9999999999&interval=1d&events=split")
    last_err: Exception | None = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read())
            res = (data.get("chart", {}).get("result") or [None])[0]
            if not res:
                raise ValueError("empty chart result")
            meta = res.get("meta", {})
            px = meta.get("regularMarketPrice")
            ts = meta.get("regularMarketTime")
            if px is None:  # fall back to the last non-null daily close
                closes = ((res.get("indicators", {}).get("quote") or [{}])[0]
                          .get("close") or [])
                stamps = res.get("timestamp") or []
                pairs = [(t, c) for t, c in zip(stamps, closes) if c is not None]
                if not pairs:
                    raise ValueError("no close data")
                ts, px = pairs[-1]
            asof = (dt.datetime.fromtimestamp(ts, dt.timezone.utc).date().isoformat()
                    if ts else dt.datetime.now(dt.timezone.utc).date().isoformat())
            splits = sorted(
                (dt.datetime.fromtimestamp(ev["date"], dt.timezone.utc).date().isoformat(),
                 ev.get("splitRatio") or f'{ev["numerator"]}:{ev["denominator"]}')
                for ev in (res.get("events", {}).get("splits") or {}).values())
            return float(px), asof, [sp for sp in splits if sp[0] > since]
        except Exception as e:  # noqa: BLE001 — retry any transport/parse error
            last_err = e
            if attempt < RETRIES - 1:
                time.sleep(BACKOFF * (2 ** attempt))
    raise RuntimeError(f"{ticker}: fetch failed after {RETRIES} tries: {last_err}")


def _decimals(num_str: str, floor: int = 2) -> int:
    """Decimal places of the existing value (min `floor`) so rewrites keep
    the file's own precision convention."""
    frac = num_str.split(".")[1] if "." in num_str else ""
    return max(floor, len(frac))


_T_BLOCK = re.compile(r"^(\s+- - )(-?\d+(?:\.\d+)?)(\s*(?:#.*)?)$")      # block pair: t line
_T_FLOW = re.compile(r"^(\s+- \[\s*)(-?\d+(?:\.\d+)?)(\s*,.*)$")         # flow pair: [t, p]
_X_MIN = re.compile(r"^(\s+x_min:\s*)(-?\d+(?:\.\d+)?)(.*)$")
_ASOF_NOTE = re.compile(r"(years before the )\d{4}-\d{2}-\d{2}( as-of)")


def shift_history(text: str, old_date: str, new_date: str, old_spot: str) -> str:
    """Re-anchor historical_prices from old_date to new_date (see module doc).

    Edits values IN PLACE line by line (comments/format survive), then
    verifies against a YAML reload; raises rather than write anything else.
    No-op when the date doesn't advance or the memo has no history block."""
    delta = (dt.date.fromisoformat(new_date) - dt.date.fromisoformat(old_date)).days / 365.25
    lines = text.split("\n")
    starts = [i for i, l in enumerate(lines) if l.startswith("historical_prices:")]
    if delta <= 0 or not starts:
        return text
    i = starts[0]; j = i + 1
    while j < len(lines) and (lines[j].startswith(" ") or not lines[j].strip()):
        j += 1
    while j > i + 1 and not lines[j - 1].strip():            # trailing blanks belong outside
        j -= 1
    before = yaml.safe_load(text)["historical_prices"]
    def shifted(num: str) -> str:
        dec = max(2, len(num.split(".")[1]) if "." in num else 0)
        return f"{float(num) - delta:.{dec}f}"
    last_pt, style = None, None
    for k in range(i + 1, j):
        l = lines[k]
        for rx, st in ((_T_BLOCK, "block"), (_T_FLOW, "flow")):
            m = rx.match(l)
            if m:
                lines[k] = f"{m.group(1)}{shifted(m.group(2))}{m.group(3)}"
                last_pt, style = k, st
                break
        else:
            m = _X_MIN.match(l)
            if m:
                lines[k] = f"{m.group(1)}{shifted(m.group(2))}{m.group(3)}"
            lines[k] = _ASOF_NOTE.sub(rf"\g<1>{new_date}\g<2>", lines[k])
    if last_pt is None:
        raise ValueError("historical_prices has no recognizable points")
    # append the outgoing spot at t = -delta, unless the (shifted) last point is already there
    last_t = before["points"][-1][0] - delta
    append = abs(last_t - (-delta)) > 0.006
    if append:
        if style == "block":
            ind = lines[last_pt][: len(lines[last_pt]) - len(lines[last_pt].lstrip())]
            ins = [f"{ind}- - {-delta:.2f}", f"{ind}  - {old_spot}"]
            at = last_pt + 2                                    # after the pair's price line
        else:
            ind = lines[last_pt][: len(lines[last_pt]) - len(lines[last_pt].lstrip())]
            ins = [f"{ind}- [{-delta:.2f}, {old_spot}]   # {old_date} spot (prior as-of, reprice.py)"]
            at = last_pt + 1
        lines[at:at] = ins
    new = "\n".join(lines)
    # verify: exactly the intended history change, nothing else
    after_doc, before_doc = yaml.safe_load(new), yaml.safe_load(text)
    want = [[t - delta, p] for t, p in before["points"]]
    if append:
        want.append([-delta, float(old_spot)])
    got = after_doc["historical_prices"]
    tol = 0.0051                                              # rounding to >=2 decimals
    ok = (len(got["points"]) == len(want)
          and all(abs(g[0] - w[0]) <= tol and g[1] == w[1] for g, w in zip(got["points"], want))
          and abs(got["x_min"] - (before["x_min"] - delta)) <= tol
          and {k: v for k, v in got.items() if k not in ("points", "x_min")}
              == {k: v for k, v in before.items() if k not in ("points", "x_min")}
          and {k: v for k, v in after_doc.items() if k != "historical_prices"}
              == {k: v for k, v in before_doc.items() if k != "historical_prices"})
    if not ok:
        raise ValueError("historical_prices shift failed verification — file left untouched")
    return new


def reprice_yml(ticker: str, new_px: float, today: str) -> dict:
    """Surgically rewrite spot / market.market_cap_billion / date in place.
    Returns the change record for the run report."""
    path = DATA / f"{ticker}.yml"
    text = path.read_text(encoding="utf-8")

    m_spot = re.search(r"^spot:\s*([0-9.]+)\s*$", text, re.M)
    m_date = re.search(r"^date:\s*(['\"]?)([0-9-]+)\1\s*$", text, re.M)
    m_mcap = re.search(r"^(\s+market_cap_billion:\s*)([0-9.]+)", text, re.M)
    if not (m_spot and m_date and m_mcap):
        raise ValueError(f"{ticker}: masthead fields not found "
                         f"(spot={bool(m_spot)} date={bool(m_date)} mcap={bool(m_mcap)})")

    old_spot = float(m_spot.group(1))
    old_mcap = float(m_mcap.group(2))
    shares_b = old_mcap / old_spot                    # shares held constant
    new_mcap = shares_b * new_px

    spot_str = f"{new_px:.{_decimals(m_spot.group(1))}f}"
    mcap_str = f"{new_mcap:.{_decimals(m_mcap.group(2))}f}"
    q = m_date.group(1) or "'"
    old_date = m_date.group(2)

    text = text[:m_spot.start()] + f"spot: {spot_str}" + text[m_spot.end():]
    m_date = re.search(r"^date:\s*(['\"]?)([0-9-]+)\1\s*$", text, re.M)
    text = text[:m_date.start()] + f"date: {q}{today}{q}" + text[m_date.end():]
    m_mcap = re.search(r"^(\s+market_cap_billion:\s*)([0-9.]+)", text, re.M)
    text = (text[:m_mcap.start()] + m_mcap.group(1) + mcap_str
            + text[m_mcap.end():])
    text = shift_history(text, old_date, today, m_spot.group(1))

    path.write_text(text, encoding="utf-8")
    return {"ticker": ticker, "old_spot": old_spot, "new_spot": new_px,
            "px_move": new_px / old_spot - 1.0,
            "old_mcap": old_mcap, "new_mcap": float(mcap_str)}


def run(cmd: list[str]) -> None:
    print("  $", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=REPO)


def main() -> int:
    args = sys.argv[1:]
    flags = {a for a in args if a.startswith("--")}
    known = {"--dry-run", "--no-bump", "--skip-render", "--partial-ok"}
    if flags - known:
        print(f"unknown flag(s): {sorted(flags - known)}  (valid: {sorted(known)})",
              file=sys.stderr)
        return 2
    subset = [a.lower() for a in args if not a.startswith("--")]
    universe = public_tickers()
    bad = [t for t in subset if t not in universe]
    if bad:
        print(f"unknown/private ticker(s): {bad}", file=sys.stderr)
        return 2
    tickers = subset or universe
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    print(f"[reprice] {len(tickers)} tickers, date -> {today}")

    # Phase 1 — fetch everything BEFORE touching any file (all-or-nothing).
    prices: dict[str, tuple[float, str]] = {}
    failed: list[str] = []
    for t in tickers:
        try:
            px, asof, splits = fetch_price(t, memo_date(t))
            if splits:
                raise RuntimeError(
                    f"{t}: split(s) since memo date {memo_date(t)}: {splits} — rescale "
                    f"shares and per-share fields before repricing (holding shares "
                    f"constant across a split corrupts mcap and every per-share value)")
            prices[t] = (px, asof)
            print(f"  {t.upper():6s} ${px:>10.2f}  (as of {asof})")
        except RuntimeError as e:
            print(f"  {t.upper():6s} FETCH FAILED — {e}", file=sys.stderr)
            failed.append(t)
        time.sleep(0.4)  # be polite to the keyless feed
    if failed and "--partial-ok" not in flags:
        print(f"\n[reprice] aborting before any edit — {len(failed)} fetch "
              f"failure(s): {failed}  (--partial-ok to proceed without them)",
              file=sys.stderr)
        return 1

    if "--dry-run" in flags:
        print("[reprice] --dry-run: no files modified")
        return 0

    # Phase 2 — bump (= archive) then surgically re-price, per ticker.
    changes = []
    for t in tickers:
        if t not in prices:
            continue
        if "--no-bump" not in flags:
            run([sys.executable, "scripts/bump_pdf_version.py", t])
        changes.append(reprice_yml(t, prices[t][0], today))

    moves = sorted(changes, key=lambda c: abs(c["px_move"]), reverse=True)
    print("\n[reprice] largest moves:")
    for c in moves[:10]:
        print(f"  {c['ticker'].upper():6s} {c['px_move']:+7.1%}  "
              f"${c['old_spot']:.2f} -> ${c['new_spot']:.2f}")

    # Phase 3 — pipeline.
    if "--skip-render" not in flags:
        print("\n[reprice] pipeline")
        run([sys.executable, "scripts/validate.py"])
        run([sys.executable, "scripts/rebuild_all.py", "--strict-layout"])
        run([sys.executable, "portfolio/build_weights.py"])
        run([sys.executable, "scripts/visual_hash.py"])
    print("\n[reprice] done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
