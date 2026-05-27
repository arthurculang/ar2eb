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
  - prior_versions : the OLD stamp values (version, timestamp, plus the
    top-level `date:` and `spot:` from the moment-before-bump) are
    prepended to stamp.prior_versions so the website can surface every
    historical PDF, not just the current one. Physical PDFs already
    accumulate in public/memos/; this is the metadata that lets the site
    UI link to them with human-readable date/spot context.

Old PDFs are never touched — memo-spec §10: versions accumulate as
immutable history. After bumping, run `python scripts/rebuild_all.py`
to emit the new public/memos/<ticker>-memo__v{NNN}__{timestamp}.pdf via
the JSX print harness (Phase 2: memo.py was retired).

The canonical JSX reference is NOT auto-changed (a JSX bump is a separate,
deliberate act); update `stamp.canonical_jsx` by hand when the JSX bumps.
"""
import re
import sys
from datetime import datetime
from pathlib import Path


def _read_top_scalar(text: str, key: str) -> str | None:
    """Read a top-level scalar like `spot: 100.01` or `date: 2026-05-16`."""
    m = re.search(rf'^{key}:\s*"?([^"\n#]+?)"?\s*(?:#.*)?$', text, re.M)
    return m.group(1).strip() if m else None


def _read_stamp_scalar(text: str, key: str) -> str | None:
    """Read a stamp.* key (indented two spaces, lives inside `stamp:` block)."""
    m = re.search(rf'^\s+{key}:\s*"?([^"\n#]+?)"?\s*(?:#.*)?$', text, re.M)
    return m.group(1).strip() if m else None


def _insert_prior_version(text: str, entry: dict) -> str:
    """Prepend `entry` to stamp.prior_versions. Creates the block if absent.

    Stringly-typed insert keeps PyYAML out of the loop so existing comments
    in the YAML file aren't stripped (PyYAML 6 doesn't round-trip them and
    ruamel.yaml isn't installed in this environment).
    """
    snippet = (
        f'  - version: "{entry["version"]}"\n'
        f'    timestamp: "{entry["timestamp"]}"\n'
        f'    asOfDate: "{entry["asOfDate"]}"\n'
        f'    spotPrice: {entry["spotPrice"]}\n'
    )
    if re.search(r'^\s+prior_versions:\s*$', text, re.M):
        return re.sub(
            r'(^\s+prior_versions:\s*\n)',
            rf'\1{snippet}',
            text, count=1, flags=re.M,
        )
    # No prior_versions yet — anchor on pdf_timestamp (the last stamp key)
    # and append a new prior_versions block right after it.
    return re.sub(
        r'(^\s+pdf_timestamp:\s*"?[^"\n]*"?\s*\n)',
        rf'\1  prior_versions:\n{snippet}',
        text, count=1, flags=re.M,
    )


KEYS_TO_BUMP = ("pdf_version", "pdf_timestamp", "footer_version", "footer_timestamp")


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
    old_v = _read_stamp_scalar(text, "pdf_version")
    old_ts = _read_stamp_scalar(text, "pdf_timestamp")
    old_spot = _read_top_scalar(text, "spot")
    old_date = _read_top_scalar(text, "date")
    if not (old_v and old_ts and old_spot and old_date):
        print(f"{ticker}: could not read old stamp/spot/date "
              f"(v={old_v} ts={old_ts} spot={old_spot} date={old_date})",
              file=sys.stderr)
        return 1

    # Capture the OLD state into prior_versions BEFORE bumping. The user's
    # subsequent edits to spot/date apply to the NEW (just-bumped) version.
    text = _insert_prior_version(text, {
        "version": old_v,
        "timestamp": old_ts,
        "asOfDate": old_date,
        "spotPrice": old_spot,
    })

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
    print(f"  archived: v{old_v} @ {old_ts} (asOf {old_date}, spot ${old_spot}) "
          f"-> stamp.prior_versions")
    print(f"  next: python scripts/rebuild_all.py  "
          f"-> public/memos/{ticker}-memo__v{new_v}__{now}.pdf")
    print("  note: stamp.canonical_jsx unchanged — bump it by hand on a JSX change")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
