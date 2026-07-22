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
     Nothing else in the file is touched — theses/scenarios are prose the
     mechanical pass must never edit (that's the quarterly re-underwrite's
     job, §15.3).
  3. PIPELINE (unless --skip-render):
       validate.py (strict) -> rebuild_all.py --strict-layout
       -> portfolio/build_weights.py -> visual_hash.py (baseline regen)

Safety: ALL prices are fetched (with retries) before any file is modified;
a single failed fetch aborts the whole run unless --partial-ok, so the book
can't end up half-repriced (same discipline as track_performance's refusal
to write a partial perf row).

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


def fetch_price(ticker: str) -> tuple[float, str]:
    """(latest price, as-of date str) from Yahoo's keyless v8 chart endpoint.

    regularMarketPrice is the live/latest quote; the last daily close is the
    fallback. Retries with exponential backoff — Yahoo throttles bursts.
    """
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker.upper()}"
           f"?range=5d&interval=1d")
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
            return float(px), asof
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

    text = text[:m_spot.start()] + f"spot: {spot_str}" + text[m_spot.end():]
    m_date = re.search(r"^date:\s*(['\"]?)([0-9-]+)\1\s*$", text, re.M)
    text = text[:m_date.start()] + f"date: {q}{today}{q}" + text[m_date.end():]
    m_mcap = re.search(r"^(\s+market_cap_billion:\s*)([0-9.]+)", text, re.M)
    text = (text[:m_mcap.start()] + m_mcap.group(1) + mcap_str
            + text[m_mcap.end():])

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
            prices[t] = fetch_price(t)
            print(f"  {t.upper():6s} ${prices[t][0]:>10.2f}  (as of {prices[t][1]})")
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
