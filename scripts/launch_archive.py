#!/usr/bin/env python3
"""Launch-day tooling for the 1 July 2026 "start fresh" (spec §15, decision D3).

Two operations, run in this order on launch day (full runbook: LAUNCH.md):

  python scripts/launch_archive.py --export
      SAFE / idempotent. Snapshots the complete pre-launch published record
      into archive-export/prelaunch-<UTC-date>/ (gitignored):
        - data/ (every YAML, incl. _intake/) — the source of truth as-of now
        - public/memos/*.pdf — ALL accumulated versions (current + prior)
        - portfolio/weights.yml (+ performance.csv if present)
        - tests/visual_baseline.json, spec/*.md
        - MANIFEST.md — git sha, per-ticker stamp/spot table, sha256 of every
          file (integrity record for the private archive)
      The export is then pushed to the PRIVATE archive repo (owner/launch
      session does this — see LAUNCH.md; this public repo never carries it).

  python scripts/launch_archive.py --flip --yes
      DESTRUCTIVE to the working tree (refuses without --yes; requires a
      clean tree and a same-day export unless overridden). The "start fresh":
        1. Every memo stamp: pdf_version +1, pdf_timestamp = one shared
           launch timestamp, footer synced, and stamp.prior_versions REMOVED
           (the site's "Prior versions (N)" panel links pre-launch PDFs;
           clearing the block is what un-publishes the history — the archive
           export is its new home).
        2. git rm every existing public/memos/*.pdf (pre-launch artifacts).
        3. Full pipeline re-render: validate → build_site_data → node
           build.js → MEMO_FORCE=1 STRICT_LAYOUT=1 rebuild_all → regenerate
           tests/visual_baseline.json.
        4. git add -A and print the launch-commit checklist (commit/PR is
           left to the operator for review — the script never commits).

Conviction-neutral by construction: --flip is purely mechanical (stamps,
files, renders). It does NOT touch spot/date/theses — an optional re-price
pass happens BEFORE the flip, per LAUNCH.md.

Caveat (documented in spec §15 / CLAUDE.md): this repo is public, so
pre-launch memos remain reachable in git HISTORY regardless; the flip
un-publishes them from the deployed site and the site UI. Truly-private =
the separate private archive repo. No history rewrite — by decision.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
MEMOS = REPO / "public" / "memos"
EXPORT_ROOT = REPO / "archive-export"


# ── shared helpers ──────────────────────────────────────────────────────

def memo_tickers() -> list[str]:
    """Every data/*.yml that is a memo (has a stamp block). Excludes
    taxonomy.yml and any future non-memo data file by construction."""
    out = []
    for p in sorted(DATA.glob("*.yml")):
        try:
            d = yaml.safe_load(p.read_text())
        except yaml.YAMLError:
            continue
        if isinstance(d, dict) and "stamp" in d:
            out.append(p.stem)
    return out


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, check=True,
                          capture_output=True, text=True).stdout.strip()


def _run(cmd: list[str], env: dict | None = None) -> None:
    print(f"  $ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=REPO, check=True, env=env)


# ── --export ────────────────────────────────────────────────────────────

def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def export(dest: Path | None) -> Path:
    stamp_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dest = dest or EXPORT_ROOT / f"prelaunch-{stamp_date}"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    # 1. Copy the published record.
    copied: list[Path] = []

    def _copy(src: Path, rel_to: Path = REPO) -> None:
        rel = src.relative_to(rel_to)
        tgt = dest / rel
        tgt.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, tgt)
        copied.append(tgt)

    for p in sorted(DATA.rglob("*.yml")):
        _copy(p)
    for p in sorted(MEMOS.glob("*.pdf")):
        _copy(p)
    for name in ("portfolio/weights.yml", "portfolio/performance.csv",
                 "tests/visual_baseline.json"):
        p = REPO / name
        if p.exists():
            _copy(p)
    for p in sorted((REPO / "spec").glob("*.md")):
        _copy(p)

    # 2. MANIFEST.
    tickers = memo_tickers()
    rows = []
    for t in tickers:
        d = yaml.safe_load((DATA / f"{t}.yml").read_text())
        st = d["stamp"]
        rows.append(
            f"| {t.upper()} | {d.get('dcf_type','?')} | v{st['pdf_version']} "
            f"@ {st['pdf_timestamp']} | {d.get('spot','?')} | {d.get('date','?')} "
            f"| {len(st.get('prior_versions') or [])} |")
    total_bytes = sum(p.stat().st_size for p in copied)
    sha_lines = [
        f"    {_sha256(p)}  {p.relative_to(dest)}" for p in sorted(copied)
    ]
    manifest = "\n".join([
        "# ar2eb pre-launch archive — MANIFEST",
        "",
        f"Snapshot of the complete pre-launch published record, taken "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
        f"for the 1 July 2026 launch (spec §15, decision D3: truly-private "
        f"archive).",
        "",
        f"- source repo: arthurculang/ar2eb @ `{_git('rev-parse', 'HEAD')}` "
        f"(branch `{_git('rev-parse', '--abbrev-ref', 'HEAD')}`)",
        f"- files: {len(copied)}  ·  total {total_bytes/1e6:.1f} MB",
        "- privacy note: the source repo is PUBLIC — these artifacts also "
        "remain in its git history. This archive is the canonical private "
        "record; the launch flip un-publishes them from the deployed site.",
        "",
        "## Memos at snapshot",
        "",
        "| ticker | dcf_type | current stamp | spot | as-of | prior versions |",
        "|---|---|---|---|---|---|",
        *rows,
        "",
        "## File integrity (sha256)",
        "",
        *sha_lines,
        "",
    ])
    (dest / "MANIFEST.md").write_text(manifest)

    print(f"export complete → {dest.relative_to(REPO)}")
    print(f"  {len(copied)} files ({total_bytes/1e6:.1f} MB) + MANIFEST.md")
    print(f"  memos: {len(tickers)} tickers, "
          f"{len(list(MEMOS.glob('*.pdf')))} PDF versions")
    print("next: push this directory to the PRIVATE archive repo "
          "(LAUNCH.md step 3).")
    return dest


# ── --flip ──────────────────────────────────────────────────────────────

# stamp.prior_versions block: optional preceding blank line, the key line
# (either `prior_versions:` opening a block, or an inline `prior_versions: []`),
# then every entry line ("  - ..." dash lines and their "    ..." children).
_PRIOR_RE = re.compile(
    r"(?:^[ \t]*\n)?^[ ]{2}prior_versions:[^\n]*\n"
    r"(?:^[ ]{2}-[^\n]*\n|^[ ]{4}[^\n]*\n)*",
    re.M,
)


def _flip_stamp_text(text: str, ticker: str, now: str) -> str:
    """Bump pdf/footer version+timestamp; delete prior_versions. Pure-text
    (comment-preserving), mirroring bump_pdf_version.py's approach."""
    m = re.search(r'''^\s+pdf_version:\s*["']?(\d+)["']?\s*(?:#.*)?$''',
                  text, re.M)
    if not m:
        raise SystemExit(f"{ticker}: no stamp.pdf_version found")
    new_v = f"{int(m.group(1)) + 1:03d}"
    for k, v in (("pdf_version", new_v), ("pdf_timestamp", now),
                 ("footer_version", new_v), ("footer_timestamp", now)):
        text, n = re.subn(rf'''(^\s*{k}:\s*)["']?[^"'\n#]*["']?''',
                          rf'\g<1>"{v}"', text, count=1, flags=re.M)
        if n != 1:
            raise SystemExit(f"{ticker}: could not update stamp.{k}")
    text, _ = _PRIOR_RE.subn("\n", text, count=1)
    return text


def flip(yes: bool, skip_export_check: bool) -> None:
    tickers = memo_tickers()
    old_pdfs = sorted(MEMOS.glob("*.pdf"))
    now = datetime.now().strftime("%Y-%m-%d_%H-%M")

    print(f"launch flip plan — {len(tickers)} memos, "
          f"{len(old_pdfs)} pre-launch PDFs:")
    print(f"  1. all stamps → version+1 @ shared timestamp {now}; "
          f"prior_versions cleared")
    print(f"  2. git rm {len(old_pdfs)} PDFs from public/memos/")
    print(f"  3. validate → build_site_data → node build.js → "
          f"MEMO_FORCE+STRICT rebuild_all → regenerate baseline")
    print(f"  4. git add -A (commit/PR left to you)")

    if not yes:
        print("\nDRY RUN (no changes). Execute with:  "
              "python scripts/launch_archive.py --flip --yes")
        return

    # Guards: clean tree; a same-day export exists (the archive must be
    # captured BEFORE the tree mutates).
    if _git("status", "--porcelain"):
        raise SystemExit("working tree not clean — commit/stash first "
                         "(the launch flip must start from a clean state)")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not skip_export_check:
        exp = EXPORT_ROOT / f"prelaunch-{today}"
        if not (exp / "MANIFEST.md").exists():
            raise SystemExit(
                f"no export at {exp.relative_to(REPO)} — run --export first "
                f"(or --skip-export-check if the archive was pushed already)")

    # 1. Stamps.
    for t in tickers:
        p = DATA / f"{t}.yml"
        p.write_text(_flip_stamp_text(p.read_text(), t, now))
        st = yaml.safe_load(p.read_text())["stamp"]  # parse check
        assert "prior_versions" not in st, t
        print(f"  [{t}] stamp → v{st['pdf_version']} @ {now}, history cleared")

    # 2. Old PDFs out.
    _run(["git", "rm", "-q", "--"] + [str(p.relative_to(REPO)) for p in old_pdfs])

    # 3. Pipeline.
    import os
    env = {**os.environ, "MEMO_FORCE": "1", "STRICT_LAYOUT": "1"}
    _run([sys.executable, "scripts/validate.py"])
    _run([sys.executable, "scripts/build_site_data.py"])
    _run(["node", "build.js"])
    _run([sys.executable, "scripts/rebuild_all.py", "--strict-layout"], env=env)
    (REPO / "tests" / "visual_baseline.json").write_text("{}\n")
    _run([sys.executable, "scripts/visual_hash.py"])

    # Sanity: every memo's new PDF landed.
    missing = [t for t in tickers
               if not list(MEMOS.glob(f"{t}-memo__*__{now}.pdf"))]
    if missing:
        raise SystemExit(f"render incomplete — missing launch PDFs: {missing}")

    # 4. Stage.
    _run(["git", "add", "-A"])
    print(f"\nflip complete — {len(tickers)} official memos at launch stamp "
          f"{now}; {len(old_pdfs)} pre-launch PDFs removed; baseline "
          f"regenerated. Staged, NOT committed.")
    print("next: review `git status` + `git diff --cached --stat`, then "
          "commit/PR per LAUNCH.md step 5.")


# ── cli ─────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--export", action="store_true",
                   help="snapshot the pre-launch record (safe)")
    g.add_argument("--flip", action="store_true",
                   help="the launch-day start-fresh (dry-run without --yes)")
    ap.add_argument("--dest", type=Path, default=None,
                    help="--export destination (default archive-export/prelaunch-<date>)")
    ap.add_argument("--yes", action="store_true",
                    help="actually execute --flip")
    ap.add_argument("--skip-export-check", action="store_true",
                    help="--flip without a same-day export present")
    a = ap.parse_args()
    if a.export:
        export(a.dest)
    else:
        flip(a.yes, a.skip_export_check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
