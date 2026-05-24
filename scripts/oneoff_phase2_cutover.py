#!/usr/bin/env python3
"""One-off: bump all 5 tickers' PDF stamps for the Phase 2 cutover.

Each ticker's pdf_version increments by 1, timestamp set to now, and
canonical_jsx is updated to point at the single JSX print harness
(public/memo_pdf.jsx) which replaces the per-ticker JSX files referenced
under the old matplotlib pipeline.

After bump, runs scripts/rebuild_all.py to render the new PDFs into
public/memos at the new filenames; the old matplotlib-rendered PDFs at
the prior filenames remain untouched (memo-spec §10: immutable version
history).
"""
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
TICKERS = ["joby", "aur", "lth", "zm", "naut"]
NEW_JSX = "public/memo_pdf.jsx"  # single Phase 2 JSX harness
MEMOS_DIR = REPO / "public" / "memos"


def bump(ticker: str, now: str) -> str:
    yml = REPO / "data" / f"{ticker}.yml"
    text = yml.read_text()

    # Existing YAMLs use a mix of single quotes, double quotes, and
    # bare values for stamp fields. Match all.
    m = re.search(r'''pdf_version:\s*['"]?(\d+)['"]?''', text)
    if not m:
        raise ValueError(f"{ticker}: no pdf_version")
    old_v = m.group(1)
    new_v = f"{int(old_v) + 1:03d}"

    for k, v in [("pdf_version", new_v),
                 ("pdf_timestamp", now),
                 ("footer_version", new_v),
                 ("footer_timestamp", now),
                 ("canonical_jsx", NEW_JSX)]:
        text, n = re.subn(
            rf'''(^\s*{k}:\s*)['"]?[^'"\n]*['"]?''',
            rf'\g<1>"{v}"', text, count=1, flags=re.M)
        if n != 1:
            raise ValueError(f"{ticker}: could not update {k}")
    yml.write_text(text)
    return new_v


def main() -> int:
    now = datetime.now().strftime("%Y-%m-%d_%H-%M")
    bumped = []
    for t in TICKERS:
        new_v = bump(t, now)
        print(f"[{t}] pdf_version -> {new_v}, timestamp -> {now}")
        bumped.append((t, new_v))

    # Render each PDF directly via the JSX harness, then copy into
    # public/memos at the new stamped filename. (build_site_data.py runs
    # after, since it asserts those files exist before writing data.js.)
    for t, _ in bumped:
        st = yaml.safe_load((REPO / "data" / f"{t}.yml").read_text())["stamp"]
        target = MEMOS_DIR / f"{t}-memo__v{st['pdf_version']}__{st['pdf_timestamp']}.pdf"
        print(f"\n[{t}] rendering -> {target.name}")
        subprocess.run(
            [sys.executable, "scripts/render_memo_pdf.py", t],
            cwd=REPO, check=True,
        )
        src = REPO / "out" / target.name
        shutil.copyfile(src, target)

    print("\n[site] regenerating public/data.js with new stamps")
    subprocess.run(
        [sys.executable, "scripts/build_site_data.py"],
        cwd=REPO, check=True,
    )
    print("\nDone. New JSX-rendered PDFs in public/memos/ alongside the "
          "matplotlib-rendered originals at the prior version stamps.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
