#!/usr/bin/env python3
"""Bump a memo's PDF version + timestamp (memo-spec §10 convention).

Usage:
    python scripts/bump_pdf_version.py <ticker>

Edits data/<ticker>.yml's `stamp` block in place:
  - pdf_version   : NNN -> NNN+1 (3-digit, zero-padded)
  - pdf_timestamp : -> now (YYYY-MM-DD_HH-MM)
  - footer_version / footer_timestamp : synced to the new PDF version+time
    (memo-spec §10 version-bump checklist #4 — the footer in-file stamp
    must track the filename version; this resolves the historical
    canonical drift on the next real build).

Old PDFs are never touched — memo-spec §10: versions accumulate as
immutable history. After bumping, run `python memo.py <ticker>` to emit
the new public/memos/<ticker>-memo__v{NNN}__{timestamp}.pdf.

The canonical JSX reference is NOT auto-changed (a JSX bump is a separate,
deliberate act); update `stamp.canonical_jsx` by hand when the JSX bumps.
"""
import re
import sys
from datetime import datetime
from pathlib import Path

KEYS = ("pdf_version", "pdf_timestamp", "footer_version", "footer_timestamp")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/bump_pdf_version.py <ticker>", file=sys.stderr)
        return 2
    ticker = sys.argv[1].lower()
    yml = Path(__file__).resolve().parent.parent / "data" / f"{ticker}.yml"
    if not yml.exists():
        print(f"no data file: {yml}", file=sys.stderr)
        return 1

    text = yml.read_text(encoding="utf-8")
    m = re.search(r'pdf_version:\s*"?(\d+)"?', text)
    if not m:
        print(f"{ticker}: no stamp.pdf_version found", file=sys.stderr)
        return 1
    old_v = m.group(1)
    new_v = f"{int(old_v) + 1:03d}"
    now = datetime.now().strftime("%Y-%m-%d_%H-%M")
    repl = {
        "pdf_version": new_v,
        "pdf_timestamp": now,
        "footer_version": new_v,
        "footer_timestamp": now,
    }
    for k, v in repl.items():
        text, n = re.subn(rf'(^\s*{k}:\s*)"?[^"\n]*"?',
                          rf'\g<1>"{v}"', text, count=1, flags=re.M)
        if n != 1:
            print(f"{ticker}: could not update {k}", file=sys.stderr)
            return 1
    yml.write_text(text, encoding="utf-8")
    print(f"{ticker}: pdf_version {old_v} -> {new_v}  (timestamp {now})")
    print(f"  next: python memo.py {ticker}  "
          f"-> public/memos/{ticker}-memo__v{new_v}__{now}.pdf")
    print("  note: stamp.canonical_jsx unchanged — bump it by hand on a JSX change")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
