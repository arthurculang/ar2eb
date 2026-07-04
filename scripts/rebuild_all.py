#!/usr/bin/env python3
"""Rebuild the AR2EB pipeline end-to-end in one command.

Pipeline:
  1. Math QC validator (scripts/validate.py) — spec §3.5.
  2. Site data regen (scripts/build_site_data.py) — public/data.js from
     data/*.yml.
  3. For each bumped ticker (or all under MEMO_FORCE=1): render PDF via
     the JSX print harness (scripts/render_memo_pdf.py).

Phase 2 retired memo.py + the matplotlib chart builders. The print harness
(public/print.html + public/memo_pdf.jsx) is the sole PDF generator.
PDFs land at public/memos/<ticker>-memo__v{NNN}__{timestamp}.pdf where
{NNN}/{timestamp} come from data/<ticker>.yml's `stamp` block (bump via
scripts/bump_pdf_version.py).

Usage:
    python scripts/rebuild_all.py                       # all tickers, bumped only
    python scripts/rebuild_all.py joby aur              # subset (positional)
    MEMO_FORCE=1 python scripts/rebuild_all.py          # rebuild all
    python scripts/rebuild_all.py --strict-validate     # fail on validator errors
    python scripts/rebuild_all.py --strict-layout       # fail on STRICT_LAYOUT violations
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
# Derived from data/*.yml so a new memo is always rendered (a hand-kept list
# could silently skip one — the site would link a 404 PDF).
TICKERS = sorted(
    p.stem for p in (REPO / "data").glob("*.yml")
    if not p.stem.startswith("_") and p.stem != "taxonomy")
FORCE = bool(os.environ.get("MEMO_FORCE"))
MEMOS_DIR = REPO / "public" / "memos"


def run(cmd, env=None):
    print("  $", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=REPO, env=env)


def target_pdf(ticker: str) -> Path:
    st = yaml.safe_load((REPO / "data" / f"{ticker}.yml").read_text())["stamp"]
    return MEMOS_DIR / f"{ticker}-memo__v{st['pdf_version']}__{st['pdf_timestamp']}.pdf"


def main() -> None:
    # Positional args (non-flag) = ticker subset; otherwise rebuild all.
    # Lets the pilot / a single-wave rebuild target just the tickers we touched
    # without churning the rest. Validation + site-data regen still run over
    # ALL tickers (their cross-cutting checks shouldn't skip).
    strict = "--strict-validate" in sys.argv
    strict_layout = "--strict-layout" in sys.argv
    unknown = [a for a in sys.argv[1:] if a.startswith("--")
               and a not in ("--strict-validate", "--strict-layout")]
    if unknown:
        # A misspelled --strict-layout must not silently run an ungated build.
        print(f"unknown flag(s): {unknown}  "
              f"(valid: --strict-validate, --strict-layout)", file=sys.stderr)
        sys.exit(2)
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    bad = [t for t in positional if t not in TICKERS]
    if bad:
        print(f"unknown ticker(s): {bad}  (known: {TICKERS})", file=sys.stderr)
        sys.exit(2)
    tickers = positional if positional else TICKERS
    print(f"[rebuild_all] tickers: {tickers}")

    # 1. Math QC.
    print("[validate] running Math QC")
    rc = subprocess.run(
        [sys.executable, "scripts/validate.py"], cwd=REPO,
    ).returncode
    if rc != 0:
        if strict:
            print("[validate] ERRORs found; --strict-validate set — aborting")
            sys.exit(rc)
        print("[validate] ERRORs found — continuing anyway")

    # 2. Site data.
    print("\n[site] regenerating public/data.js")
    run([sys.executable, "scripts/build_site_data.py"])

    # 2b. Bundles — the print harness loads the pre-compiled bundle, so a
    # stale committed bundle would render outdated JSX (and re-stamp data.js).
    print("\n[bundle] node build.js")
    run(["node", "build.js"])

    # 3. PDFs.
    MEMOS_DIR.mkdir(parents=True, exist_ok=True)
    built, skipped = [], []
    for t in tickers:
        pdf = target_pdf(t)
        if pdf.exists() and not FORCE:
            print(f"[{t}] {pdf.name} exists — skip (bump_pdf_version.py to rebuild)")
            skipped.append(t)
            continue
        print(f"[{t}] rendering JSX -> {pdf.name}")
        # Pass STRICT_LAYOUT=1 via env if --strict-layout was set, so the
        # renderer fails on Page-boundary bleeds rather than just warning.
        env = {**os.environ}
        if strict_layout:
            env["STRICT_LAYOUT"] = "1"
        run([sys.executable, "scripts/render_memo_pdf.py", t], env=env)
        # render_memo_pdf.py writes to out/<stamped_name>.pdf using the
        # same stamp the PDF lives under in public/memos.
        src = REPO / "out" / pdf.name
        if src.exists():
            shutil.copyfile(src, pdf)
        built.append(t)

    # 4. Site data again — data.js embeds each PDF's size and 404-guards the
    # prior-versions list against disk, so it must be regenerated AFTER the
    # renders land (running it only before left "size": "—" on every fresh
    # PDF — the launch flip shipped that em-dash to the live site).
    if built:
        print("\n[site] regenerating public/data.js (post-render sizes)")
        run([sys.executable, "scripts/build_site_data.py"])
        # ...and restamp the ?v= cache-bust hashes, since data.js just changed.
        run(["node", "build.js"])

    print(f"\nrebuild-all done — built: {built or 'none'}  "
          f"skipped (unchanged): {skipped or 'none'}")
    if skipped and not FORCE:
        print("  tip: edit data/<ticker>.yml -> scripts/bump_pdf_version.py "
              "<ticker> -> rerun, to pick up changes.")


if __name__ == "__main__":
    main()
