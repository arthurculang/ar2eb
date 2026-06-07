#!/usr/bin/env python3
"""Source FY history operating margins from SEC XBRL — for chart_reference.history_op_margin.

The mature Page-3 "Op margin — history + scenarios" chart (memo_pdf.jsx
MatureMarginsChart) plots chart_reference.history_op_margin as its historical
leg. When that field is absent the renderer falls back to an empty series and
pins every scenario's fan to 0% at the FY-hinge — so the whole history reads as
a flat zero (the DASH bug). This script sources the real figures deterministically
(no transcription, no memory) so the backfill is conviction-neutral and reproducible.

Definition: history_op_margin = GAAP operating income (us-gaap:OperatingIncomeLoss)
÷ revenue, in percent, for each year in the ticker's chart_reference.history_years.

Alignment: each memo history_year is matched to the SEC fiscal year whose sourced
revenue is closest to the memo's already-authored history_revenue[i] (searching
{Y, Y+1} to absorb late-January fiscal years like LULU/ZM). A match outside
REV_TOL is flagged ⚠ rather than silently trusted — the same sanity-gate posture
as source_ai2_panel.py.

Reuses scripts/_models/source_ai2_panel.py for the SEC fetch + XBRL flow_series.

USAGE:
    python scripts/source_op_margin.py                 # all mature/sotp targets → table
    python scripts/source_op_margin.py dash uber       # subset
    python scripts/source_op_margin.py --emit          # also print the YAML arrays to paste
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts" / "_models"))
import source_ai2_panel as S  # noqa: E402  (SEC fetch + flow_series + CONCEPTS + CIK)

# CIK table — reuse the verified map in source_ai2_panel, plus COIN (ticker-
# verified vs data.sec.gov/submissions: CIK 1679788 → "Coinbase Global, Inc.").
CIK = dict(S.CIK)
CIK["COIN"] = 1679788

# Mature / SOTP tickers that render MatureMarginsChart (LTH already authored).
TARGETS = ["dash", "abnb", "txg", "yeti", "isrg", "uber", "ilmn", "lulu", "zm", "coin"]

REV_TOL = 0.08  # ±8% — memo history_revenue may round or use a slightly different revenue line


def _annual_by_end(facts: dict, names: list[str]) -> dict[str, float]:
    """end_date_iso → full-year value (10-K, FY, ~annual duration), priority-merged.

    Keys on the exact period-END date rather than the end-date YEAR (S.flow_series).
    52/53-week filers (YETI, ILMN) can close two consecutive fiscal years in the
    same calendar year (e.g. Jan 1 2022 and Dec 31 2022); a year key collides them
    and silently drops one. An ISO end-date key keeps both."""
    best: dict[str, tuple[int, str, float]] = {}   # end → (tag_rank, filed, val)
    for rank, tag in enumerate(names):
        for e in S._annual_entries(facts, tag):
            if e.get("fp") != "FY" or not str(e.get("form", "")).startswith("10-K"):
                continue
            if not S._is_annual_duration(e):
                continue
            end = e["end"]
            filed = e.get("filed", "9999-99-99")
            cur = best.get(end)
            if cur is None or rank < cur[0] or (rank == cur[0] and filed < cur[1]):
                best[end] = (rank, filed, float(e["val"]))
    return {end: v for end, (_, _, v) in best.items()}


def op_margin_series(ticker: str) -> tuple[list, list[str]]:
    """Return (history_op_margin list aligned to history_years, report rows).

    A mature memo's history_years is N consecutive fiscal years. We pick the
    window of N consecutive SEC fiscal periods (each having both a revenue and an
    op-income annual fact) whose sourced revenues best fit the memo's already-
    authored history_revenue, then align positionally within that window. Fitting
    the window (not each year independently) anchors on the right fiscal periods
    even when the memo's revenue is slightly imprecise or two years are nearly
    flat (ILMN's GRAIL-era restatements); the window choice respects the memo's
    actual period labels (ZM's Jan-31 fiscal years, not the just-filed FY2026).
    history_revenue is kept as a per-row sanity cross-check: ⚠ flags a divergence."""
    facts = S.companyfacts(CIK[ticker.upper()])
    rev_by_end = _annual_by_end(facts, S.CONCEPTS["revenue"])
    op_by_end = _annual_by_end(facts, S.CONCEPTS["op_income"])

    data = yaml.safe_load((REPO / "data" / f"{ticker}.yml").read_text())
    cr = data["chart_reference"]
    years = cr["history_years"]
    memo_rev = cr.get("history_revenue") or []

    ends = sorted(e for e in rev_by_end if e in op_by_end)
    n = len(years)
    # Best window of N consecutive fiscal periods by total |sourced − memo| revenue.
    best_win, best_cost = ends[-n:], None
    for s in range(0, max(0, len(ends) - n) + 1):
        win = ends[s:s + n]
        if len(win) < n:
            continue
        cost = sum(abs(rev_by_end[win[k]] / 1e9 - memo_rev[k])
                   for k in range(n) if k < len(memo_rev) and memo_rev[k] is not None)
        if best_cost is None or cost < best_cost:
            best_cost, best_win = cost, win
    chosen = best_win
    pad = n - len(chosen)  # >0 only if SEC has fewer than N years on file

    out: list = []
    rows: list[str] = []
    for i, Y in enumerate(years):
        R = (memo_rev[i] if i < len(memo_rev) else None)
        j = i - pad
        if j < 0:
            out.append(None)
            rows.append(f"  {ticker.upper():5} {Y}  ⚠ no SEC fiscal year (only {len(chosen)} on file)")
            continue
        ed = chosen[j]
        sec_rev = rev_by_end[ed] / 1e9
        sec_op = op_by_end[ed] / 1e9
        margin = round(sec_op / sec_rev * 100, 1)
        out.append(margin)
        err = (abs(sec_rev - R) / max(R, 1e-6)) if R else 0.0
        flag = "" if err <= REV_TOL else f" ⚠rev-mismatch ({err*100:.0f}%)"
        rows.append(
            f"  {ticker.upper():5} {Y}→FYE {ed}  sec_rev=${sec_rev:6.2f}B "
            f"memo_rev=${(R or 0):6.2f}B  sec_op=${sec_op:+7.3f}B  op_margin={margin:+6.1f}%{flag}"
        )
    return out, rows


def _insert_block(path: Path, series: list) -> str:
    """Insert a block-style history_op_margin into a YAML's chart_reference,
    right after history_revenue. Idempotent (skips if already present); text-
    based to keep the diff minimal and the file's existing style intact."""
    if not path.exists():
        return "skip (file not found)"
    text = path.read_text()
    if "history_op_margin:" in text:
        return "skip (already present)"
    lines = text.splitlines(keepends=True)
    start = next((i for i, ln in enumerate(lines)
                  if ln.startswith("  history_revenue:")), None)
    if start is None:
        return "skip (no history_revenue)"
    j = start + 1
    while j < len(lines) and not re.match(r"^  [^\s-]", lines[j]) and not re.match(r"^\S", lines[j]):
        j += 1   # walk past the history_revenue sequence items
    block = "  history_op_margin:   # %  GAAP operating income / revenue (SEC XBRL OperatingIncomeLoss)\n"
    block += "".join(f"  - {'null' if v is None else v}\n" for v in series)
    lines.insert(j, block)
    path.write_text("".join(lines))
    return f"inserted ({len(series)} vals)"


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    emit = "--emit" in sys.argv
    write = "--write" in sys.argv
    targets = [a.lower() for a in args] if args else TARGETS

    emitted: dict[str, list] = {}
    for t in targets:
        series, rows = op_margin_series(t)
        print("\n".join(rows))
        emitted[t] = series
        print()

    if emit:
        print("# ── history_op_margin arrays (paste into chart_reference) ──")
        for t, series in emitted.items():
            arr = "[" + ", ".join("null" if v is None else f"{v}" for v in series) + "]"
            print(f"{t}: history_op_margin: {arr}  # %  GAAP op income / revenue (SEC XBRL)")

    if write:
        print("\n# ── backfill ──")
        for t, series in emitted.items():
            if any(v is None for v in series):
                print(f"  {t}: SKIP write — incomplete series {series} (resolve ⚠ first)")
                continue
            for path in (REPO / "data" / f"{t}.yml", REPO / "data" / "_intake" / f"{t}.yml"):
                print(f"  {path.relative_to(REPO)}: {_insert_block(path, series)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
