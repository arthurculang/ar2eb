#!/usr/bin/env python3
"""Arthur Indicator v1.0 — valuation-efficiency screen for revenue-generating names.

    AI_1.0 = EV / ( Revenue x (GrossMargin + RevGrowth) )

Lower = cheaper-for-quality. Per the AI.pdf zones (anchored on META): green <~6 (buy),
~10 fair, red >15 rich. EV / revenue / the weighted-DCF finding are read straight from
data/<ticker>.yml (the memo source of truth); gross margin + forward revenue growth — the
two inputs the YAML doesn't carry — come from the research-sourced table below.

The indicator is a deliberate complement to the memo DCF (§AI.pdf): it values from a
*product-economics* angle (EV/Rev, gross-margin Rule-of-40) and ignores the near-term
"fixable" stuff (SBC, R&D, CapEx) the FCF-DCF penalises — so it shouldn't be expected to
agree with the DCF everywhere; the divergences are the signal.

Note: it is undefined for pre-revenue names (Revenue ~ 0) — OKLO/ACHR/NAUT/AUR are the
young-company DCF's domain, not the indicator's. GRAIL excluded (gross loss today).
"""
import sys
from pathlib import Path
import yaml

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"

# (gross_margin, fwd_rev_growth) — research-sourced; [e] = estimate to refine.
GM_GROWTH = {
    "lulu": (0.57, 0.05), "yeti": (0.57, 0.05), "abnb": (0.82, 0.10),
    "dash": (0.48, 0.20), "uber": (0.40, 0.18),  # uber GM [e] (take-rate model)
    "ilmn": (0.70, 0.04), "txg": (0.70, 0.02), "zm": (0.76, 0.03),
    "isrg": (0.67, 0.15), "coin": (0.86, 0.20),  # coin GM/growth [e] (volatile)
    "rklb": (0.30, 0.38),  # rklb GM [e] (aerospace)
    "ionq": (0.50, 0.90),  # ionq GM/growth [e] (sub-scale)
}
PRE_REV = {"oklo", "achr", "naut", "aur", "joby", "anthropic", "gral", "lth"}  # AI N/A (see docstring)


def latest_revenue(d: dict) -> float:
    """Latest actual revenue ($B): mature carries rev_b; young carries history_revenue[]."""
    base = d["scenarios"]["base"]["dcf_path"]
    if "rev_b" in base:
        return float(base["rev_b"])
    hist = d.get("chart_reference", {}).get("history_revenue") or []
    return float(hist[-1]) if hist else 0.0


def weighted_dcf(d: dict) -> float:
    return sum(s["probability"] * s["expected_per_share"] for s in d["scenarios"].values())


def main() -> int:
    rows = []
    for f in sorted(DATA.glob("*.yml")):
        t = f.stem
        if t in ("taxonomy",) or t in PRE_REV or t not in GM_GROWTH:
            continue
        d = yaml.safe_load(f.read_text())
        spot = d["spot"]; m = d["market"]
        ev = m["market_cap_billion"] + m.get("net_debt_billion", 0) - m.get("cash_billion", 0)
        rev = latest_revenue(d)
        gm, g = GM_GROWTH[t]
        ai = ev / (rev * (gm + g)) if rev > 0.01 and (gm + g) > 0 else float("inf")
        dcf = weighted_dcf(d); dcf_pct = (dcf / spot - 1) * 100
        rows.append((t.upper(), ev / rev, gm + g, ai, dcf_pct))
    rows.sort(key=lambda r: r[3])

    def zone(ai):
        return "GREEN (cheap)" if ai < 6 else "fair" if ai < 11 else "RED (rich)" if ai < 25 else "RED+ (priced beyond rev)"
    print(f"{'ticker':<7}{'EV/Rev':>8}{'GM+grw':>8}{'AI_1.0':>9}  {'zone':<24}{'DCF vs spot':>12}")
    print("-" * 70)
    for t, evr, gmg, ai, dcf in rows:
        ai_s = f"{ai:.2f}" if ai < 1e3 else f"{ai:.0f}"
        print(f"{t:<7}{evr:>8.1f}{gmg:>8.2f}{ai_s:>9}  {zone(ai):<24}{dcf:>+11.0f}%")
    print("-" * 70)
    print("zones (per AI.pdf, anchored on META ~8.5): GREEN <6 buy · fair 6-11 · RED >15 rich")
    print("N/A (pre-revenue / gross-loss — the young-company DCF's domain): " + ", ".join(sorted(t.upper() for t in PRE_REV)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
