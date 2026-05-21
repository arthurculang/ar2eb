#!/usr/bin/env python3
"""Rebuild the whole AR2EB pipeline in one command.

Migration decision #1 (rebuild-all = option b; spec §10 / decision #5):
  - charts + public/data.js are ALWAYS regenerated;
  - a memo PDF is (re)built only when its `stamp` version has no file yet
    — i.e. you ran scripts/bump_pdf_version.py first. Existing immutable
    versions are never overwritten;
  - MEMO_FORCE=1 forces an in-place rebuild of every PDF (for a
    from-scratch visual verify). NOTE: reportlab embeds a CreationDate/ID,
    so a forced rebuild is visually identical but NOT byte-identical — it
    will show as a git diff on the canonical PDFs. Use it deliberately.

Usage:
    python scripts/rebuild_all.py              # build only bumped tickers
    MEMO_FORCE=1 python scripts/rebuild_all.py # rebuild every PDF in place
"""
import os
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
TICKERS = ["joby", "aur", "lth", "zm", "naut"]
FORCE = bool(os.environ.get("MEMO_FORCE"))


def run(cmd, env=None):
    print("  $", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=REPO, env=env)


def target_pdf(ticker: str) -> Path:
    st = yaml.safe_load((REPO / "data" / f"{ticker}.yml").read_text())["stamp"]
    return REPO / "public" / "memos" / \
        f"{ticker}-memo__v{st['pdf_version']}__{st['pdf_timestamp']}.pdf"


def main() -> None:
    built, skipped = [], []
    for t in TICKERS:
        pdf = target_pdf(t)
        if pdf.exists() and not FORCE:
            print(f"[{t}] {pdf.name} exists — skip "
                  f"(scripts/bump_pdf_version.py {t} to rebuild, or MEMO_FORCE=1)")
            skipped.append(t)
            continue
        print(f"[{t}] charts + memo -> {pdf.name}")
        # Parameterized chart builders dispatch on dcf_type (spec §7 variant):
        #   young_company       -> charts/young_company.py (JOBY, AUR)
        #   mature_company / _sotp -> charts/mature_company.py (LTH, ZM)
        dcf_type = yaml.safe_load(
            (REPO / "data" / f"{t}.yml").read_text())["dcf_type"]
        builder = "young_company.py" if dcf_type == "young_company" else "mature_company.py"
        run([sys.executable, f"charts/{builder}", t])
        env = {**os.environ, "MEMO_FORCE": "1"} if FORCE else None
        run([sys.executable, "memo.py", t], env=env)
        built.append(t)

    print("\n[site] regenerating public/data.js")
    run([sys.executable, "scripts/build_site_data.py"])

    print(f"\nrebuild-all done — built: {built or 'none'}  "
          f"skipped (unchanged): {skipped or 'none'}")
    if skipped and not FORCE:
        print("  tip: edit data/<ticker>.yml -> scripts/bump_pdf_version.py "
              "<ticker> -> rerun, to pick up changes.")


if __name__ == "__main__":
    main()
