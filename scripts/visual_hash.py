#!/usr/bin/env python3
"""Visual regression hashing for memo PDFs.

Renders each ticker's PDF via the JSX print harness, rasterizes every
page to PNG at a fixed DPI, and hashes the bytes. Baseline lives at
tests/visual_baseline.json; --check compares the current render against
the baseline and fails on mismatches.

Usage:
    python scripts/visual_hash.py                   # write/update baseline
    python scripts/visual_hash.py --check           # compare; exit 1 on diff
    python scripts/visual_hash.py joby              # single ticker baseline
    python scripts/visual_hash.py joby --check      # single ticker compare

Hash inputs:
- Rendered PDF (Playwright + Chromium 1194, pinned), rasterized at 150 dpi
  via pdftoppm.
- SHA-256 of the PNG bytes.

This is BRITTLE — any anti-aliasing or font-hinting drift breaks it.
That's the point during the JSX migration: catch any change. Switch to
perceptual hashing (imagehash, dhash, or similar) when ready to allow
small renderer drift.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASELINE = REPO / "tests" / "visual_baseline.json"
TICKERS = ["joby", "aur", "lth", "zm", "naut", "coin", "anthropic", "ionq", "isrg", "rklb", "oklo", "achr", "gral", "txg", "lulu", "abnb", "uber", "yeti", "dash", "ilmn", "shak", "meta", "amzn", "googl", "aapl", "nvda", "tsla", "dis"]
DPI = 150


def render_and_hash(ticker: str) -> dict[str, str]:
    """Render <ticker> PDF + hash each page. Returns {pageN: sha256}."""
    # 1. Render PDF via the JSX harness.
    subprocess.run(
        [sys.executable, "scripts/render_memo_pdf.py", ticker],
        cwd=REPO, check=True, capture_output=True,
    )

    # 2. Find the rendered PDF — render_memo_pdf.py writes to
    # out/<ticker>-memo__v{N}__{ts}.pdf using the stamp version.
    import yaml
    st = yaml.safe_load((REPO / "data" / f"{ticker}.yml").read_text())["stamp"]
    pdf = REPO / "out" / f"{ticker}-memo__v{st['pdf_version']}__{st['pdf_timestamp']}.pdf"
    if not pdf.exists():
        raise FileNotFoundError(f"expected {pdf}")

    # 3. Rasterize each page; hash bytes.
    with tempfile.TemporaryDirectory() as td:
        out_prefix = Path(td) / "p"
        subprocess.run(
            ["pdftoppm", "-png", "-r", str(DPI), str(pdf), str(out_prefix)],
            check=True, capture_output=True,
        )
        page_hashes = {}
        for png in sorted(Path(td).glob("p-*.png")):
            # pdftoppm names p-N.png where N is 1-indexed.
            page_num = png.stem.split("-")[-1]
            data = png.read_bytes()
            page_hashes[f"page{int(page_num)}"] = hashlib.sha256(data).hexdigest()
        return page_hashes


def write_baseline(tickers: list[str]) -> None:
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    baseline = json.loads(BASELINE.read_text()) if BASELINE.exists() else {}
    for t in tickers:
        print(f"[{t}] rendering + hashing", flush=True)
        baseline[t] = render_and_hash(t)
        for pn, h in sorted(baseline[t].items()):
            print(f"  {pn}: {h[:16]}…")
    BASELINE.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n")
    print(f"\nwrote {BASELINE.relative_to(REPO)}  ({len(baseline)} tickers)")


def check_baseline(tickers: list[str]) -> int:
    if not BASELINE.exists():
        print(f"no baseline at {BASELINE}; run without --check to create",
              file=sys.stderr)
        return 1
    baseline = json.loads(BASELINE.read_text())
    failed = 0
    for t in tickers:
        if t not in baseline:
            print(f"[{t}] no baseline entry — skipping (rerun without --check "
                  f"to add)")
            continue
        print(f"[{t}] rendering + hashing", flush=True)
        current = render_and_hash(t)
        for pn, h in sorted(current.items()):
            expected = baseline[t].get(pn)
            if expected == h:
                print(f"  {pn}: ok")
            else:
                print(f"  {pn}: DRIFT  expected {expected[:16] if expected else '(missing)'}…  "
                      f"got {h[:16]}…")
                failed += 1
    if failed:
        print(f"\nvisual_hash: {failed} page(s) drifted")
        return 1
    print("\nvisual_hash: all pages match baseline")
    return 0


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check = "--check" in sys.argv
    tickers = [args[0].lower()] if args else TICKERS
    if check:
        return check_baseline(tickers)
    write_baseline(tickers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
