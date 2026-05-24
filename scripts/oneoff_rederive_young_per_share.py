#!/usr/bin/env python3
"""One-off: re-derive dcf_per_share + expected_per_share for young tickers.

The spec §3.5 template states:
    dcf_per_share = total_equity * 1000 / final_shares
    expected_per_share = (1 - p_fail/100) * dcf_per_share + (p_fail/100) * distress

Mature tickers (LTH, ZM) match this. Young tickers (JOBY, AUR, NAUT) had
stored dcf_per_share values that systematically diverged — sometimes by
5× (AUR ultra_bull) — with no documented convention explaining the gap.

Re-derives both fields from the equity bridge for young tickers and
patches them into YAML in place. Prints before/after for audit.
"""
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
TICKERS = ["joby", "aur", "lth", "zm", "naut"]
SCN_ORDER = ["bear", "base", "bull", "ultra_bull"]


def main() -> int:
    for ticker in TICKERS:
        yml = REPO / "data" / f"{ticker}.yml"
        data = yaml.safe_load(yml.read_text())
        text = yml.read_text()
        print(f"\n[{ticker}]")
        is_young = data["dcf_type"] == "young_company"
        for key in SCN_ORDER:
            sc = data["scenarios"][key]
            dp = sc["dcf_path"]
            shares = dp["final_shares"]
            equity = dp["total_equity"]
            old_dcf = dp["dcf_per_share"]
            old_exp = sc["expected_per_share"]

            new_dcf = equity * 1000 / shares
            if is_young:
                p_fail = sc["dcf_metrics"]["p_fail"] / 100
                distress = dp["distress"]
                new_exp = (1 - p_fail) * new_dcf + p_fail * distress
            else:
                # Mature DCF has no failure haircut; expected = dcf per share.
                new_exp = new_dcf
            # Bear with negative DCF often clamps to $0 in display; preserve
            # legacy "wipeout = $0.00" semantics.
            new_exp_clamped = max(new_exp, 0.0)

            print(f"  {key:10}: dcf {old_dcf:>7.2f} -> {new_dcf:>7.2f}   "
                  f"expected {old_exp:>7.2f} -> {new_exp_clamped:>7.2f}")

            # Patch dcf_per_share: replace the first match within the
            # scenario block. The block starts at `  {key}:` and ends at
            # the next `  <word>:` at indent 2.
            text = _patch_in_scenario(
                text, key, "dcf_per_share", f"{new_dcf:.2f}")
            text = _patch_in_scenario(
                text, key, "expected_per_share", f"{new_exp_clamped:.2f}")
        yml.write_text(text)
        print(f"  wrote {yml.relative_to(REPO)}")
    return 0


def _patch_in_scenario(text: str, scenario_key: str, field: str, new_value: str) -> str:
    """Replace `field: <num>` within the named scenario block. Idempotent."""
    # Find the scenario block bounds.
    scn_re = re.compile(rf'^  {scenario_key}:\n', re.M)
    m = scn_re.search(text)
    if not m:
        raise ValueError(f"scenario {scenario_key} not found")
    start = m.end()
    # Next sibling: another `  <word>:` at indent 2.
    next_m = re.compile(r'^  [a-z_]+:', re.M).search(text, start)
    end = next_m.start() if next_m else len(text)
    block = text[start:end]
    # Patch the field line within block.
    field_re = re.compile(rf'(^\s+{field}:\s+)[-\d.]+', re.M)
    new_block, n = field_re.subn(rf'\g<1>{new_value}', block, count=1)
    if n != 1:
        raise ValueError(f"could not patch {scenario_key}.{field}")
    return text[:start] + new_block + text[end:]


if __name__ == "__main__":
    sys.exit(main())
