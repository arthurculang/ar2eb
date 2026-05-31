#!/usr/bin/env python3
"""Math QC validator for ar2eb scenario data (spec §3.5).

Reads each data/<ticker>.yml and verifies internal consistency. Reports
ERRORs (objective invariants — exit 1) and WARNs (derived quantities that
may follow undocumented conventions — exit 0 unless --strict).

Checks:
  ERROR — probability sum = 1.0
  ERROR — equity bridge: op_ev + cash - net_debt (+ special_assets) = total_equity
  ERROR — operating EV: sum_pv_fcf + pv_terminal = op_ev
  ERROR — sum_pv_fcf matches sum of pv_fcf array (rounding-tolerant)
  ERROR — cash runway >= 0 across all years (Variant B)
  ERROR — raise_total = sum(raises) (Variant B)
  ERROR — probability_rationale present per scenario
  WARN  — sum_pv_fcf vs recomputed from fcf + wacc_path (may differ if YAML
          stores already-rounded per-year PVs)
  WARN  — terminal_value vs Gordon perpetuity (young-company uses an
          undocumented formula; mature uses Gordon)
  WARN  — dcf_per_share vs total_equity * 1000 / final_shares (young-company
          stored values systematically diverge — convention not in spec)
  WARN  — final_shares vs starting + sum(raises[i]/price[i]) (YAML carries
          some rounding in raise schedules)
  WARN  — expected_per_share vs (1-pf)*dcf + pf*distress
  WARN  — rev_path[-1] vs TAM × tam_share (young) or rev_b growth (mature)

Usage:
    python scripts/validate.py             # all tickers, errors fail
    python scripts/validate.py naut        # one ticker
    python scripts/validate.py --strict    # warns also fail
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parent.parent
TICKERS = ["joby", "aur", "lth", "zm", "naut", "isrg", "ionq", "coin", "anthropic", "rklb", "oklo"]
# Required scenario keys (every ticker must have these four). `ultra_bear`
# is an optional 5th — present on ZM, may be added to other tickers later.
SCEN_KEYS = ["bear", "base", "bull", "ultra_bull"]
SCEN_KEYS_ALL = ["ultra_bear", "bear", "base", "bull", "ultra_bull"]

# Tolerances
TOL_B = 0.05          # $B equity-bridge / EV
TOL_PV = 0.02         # $B PV-of-FCF (sum of per-year PVs)
TOL_PV_RECOMPUTE = 0.20  # $B re-derived from fcf + wacc (rounding compounds)
TOL_PER_SHARE = 0.10  # $/share
TOL_EXPECTED = 0.20   # $/share — expected has compound rounding
TOL_PROB = 0.001
TOL_SHARES_PCT = 5.0  # final_shares % — raise prices round in YAML
TOL_TAM_PCT = 25.0    # TAM × share is a soft sanity check, mature_share is rounded


def f_err(check: str, expected: Any, got: Any, extra: str = "") -> str:
    base = f"  - {check}: got {got}, expected {expected}"
    return f"{base} ({extra})" if extra else base


# Canonical Helm taxonomy — load once. Per-ticker taxonomy blocks must reference
# slugs (watchlist/themes) that exist in this file.
_TAXONOMY = yaml.safe_load((REPO / "data" / "taxonomy.yml").read_text())
_THEME_TO_UMBRELLA = {
    t: u for u, ublock in _TAXONOMY["umbrellas"].items()
    for t in ublock.get("themes", {})
}


_EXIT_KINDS = {"ipo", "acquisition", "down_round", "stay_private", "wipeout"}


def _private_exit_errors(key: str, sc: dict) -> list[str]:
    """Validate a private_prevaluation scenario's exit_terms block.

    The equity math here is `outcome × prob / (1+r)^t`, not a DCF. We check:
      - exit_terms present with a valid kind
      - pv_per_share = exit_per_share_nominal × (1 - lp_haircut) / (1+wacc)^t
      - expected_per_share = (1-p_loss)×pv×(1-ipo_haircut) + p_loss×distress
    so a typo in any input fails the build (the analog of the equity-bridge
    ERROR checks for public memos).
    """
    et = sc.get("exit_terms")
    if not et:
        return [f_err("exit_terms", "present", "missing")]
    errs: list[str] = []
    if et.get("kind") not in _EXIT_KINDS:
        errs.append(f_err("exit_terms.kind", f"one of {sorted(_EXIT_KINDS)}", repr(et.get('kind'))))
    nom = et.get("exit_per_share_nominal")
    yrs = et.get("years_to_exit")
    wacc = et.get("venture_wacc")
    lp = et.get("lp_haircut_pct", 0) / 100
    if None not in (nom, yrs, wacc):
        pv_calc = nom * (1 - lp) / (1 + wacc) ** yrs
        if abs(pv_calc - et.get("pv_per_share", 0)) > max(0.01 * pv_calc, 0.5):
            errs.append(f_err(
                f"pv_per_share (nom {nom} × (1-{lp:.2f}) / (1+{wacc})^{yrs})",
                f"{et.get('pv_per_share')}", f"{pv_calc:.2f}"))
        p_loss = et.get("p_total_loss", 0)
        ipo_hc = et.get("ipo_underperformance_haircut_pct", 0) / 100
        distress = et.get("distress_per_share", 0) or 0
        exp_calc = (1 - p_loss) * pv_calc * (1 - ipo_hc) + p_loss * distress
        if abs(exp_calc - sc.get("expected_per_share", 0)) > max(0.02 * abs(exp_calc), 0.5):
            errs.append(f_err(
                f"expected_per_share ((1-{p_loss:.2f})×{pv_calc:.1f}×(1-{ipo_hc:.2f}) + {p_loss:.2f}×{distress:.1f})",
                f"{sc.get('expected_per_share')}", f"{exp_calc:.2f}"))
    return errs


def _taxonomy_errors(tax: dict | None) -> list[str]:
    if not tax:
        return [f_err("taxonomy block", "present", "missing")]
    errs: list[str] = []
    wl = tax.get("watchlist")
    if wl not in _TAXONOMY["watchlists"]:
        errs.append(f_err("taxonomy.watchlist", f"one of {list(_TAXONOMY['watchlists'])}", repr(wl)))
        return errs  # downstream checks depend on a valid watchlist
    w = _TAXONOMY["watchlists"][wl]
    tier = tax.get("tier")
    if w.get("allows_tiers", True):
        if tier not in _TAXONOMY["tiers"]:
            errs.append(f_err("taxonomy.tier", f"one of {_TAXONOMY['tiers']}", repr(tier)))
    elif tier is not None:
        errs.append(f_err("taxonomy.tier", "null (watchlist is tier-less)", repr(tier)))
    themes = tax.get("themes") or []
    if not themes:
        errs.append(f_err("taxonomy.themes", "≥1 entry", "[]"))
    for t in themes:
        if t not in _THEME_TO_UMBRELLA:
            errs.append(f_err("taxonomy.themes entry", "valid theme slug", repr(t)))
    primary = tax.get("primary_theme") or (themes[0] if themes else None)
    if primary and primary not in themes:
        errs.append(f_err("taxonomy.primary_theme", "one of taxonomy.themes", repr(primary)))
    return errs


# 7 Powers (Helmer) — the keys the Page-4 competitive scorecard expects (§6d).
_POWER_KEYS = {"scale_economies", "network_economies", "counter_positioning",
               "switching_costs", "branding", "cornered_resource", "process_power"}
_LENSES = {"power_audit", "power_origination"}


def _competitive_warnings(comp: dict | None) -> list[str]:
    """WARN-only structural checks on the optional `competitive:` block (§6d).
    Promote to ERROR once the block is required for new memos."""
    if not comp:
        return []  # optional at introduction; absence is fine (memo stays 5pp)
    w: list[str] = []
    lens = comp.get("lens")
    if lens not in _LENSES:
        w.append(f_err("competitive.lens", f"one of {sorted(_LENSES)}", repr(lens)))
    if not comp.get("arena"):
        w.append(f_err("competitive.arena", "present", "missing"))
    if not comp.get("takeaway"):
        w.append(f_err("competitive.takeaway", "present", "missing"))
    powers = comp.get("powers", {})
    dom = comp.get("dominant_power")
    if dom not in _POWER_KEYS:
        w.append(f_err("competitive.dominant_power", f"one of the 7 Powers", repr(dom)))
    elif (powers.get(dom, {}) or {}).get("score", 0) < 2:
        # "you can't lean on a Power you don't have" (§6d QC)
        w.append(f_err(f"competitive.powers.{dom}.score", "≥2 (it's the dominant power)",
                       repr((powers.get(dom, {}) or {}).get("score"))))
    # lens-appropriate falsifiers present
    if lens == "power_origination" and not comp.get("lead_lag"):
        w.append(f_err("competitive.lead_lag", "≥1 entry (origination lens)", "missing"))
    if lens == "power_audit" and not comp.get("threats"):
        w.append(f_err("competitive.threats", "≥1 entry (audit lens)", "missing"))
    return w


def young_cash_path(sc: dict, start_cash: float) -> list[float]:
    """Mirrors charts/young_company.py::_cash_path.

    cash[0] = start_cash; for each year, cash += raises[i] + FCF[i] where
    FCF = rev*op_margin - (rev - prev_rev)/s2c. NOLs assumed (no tax).
    """
    cash = start_cash
    prev_rev = 0.0
    raises = sc["chart_data"]["raises"]
    rev = sc["dcf_path"]["rev_path"]
    op_margin = sc["dcf_path"]["op_margin"]
    s2c = sc["dcf_metrics"]["s2c"]
    out = [cash]
    for i in range(len(rev)):
        delta = rev[i] - prev_rev
        nopat = rev[i] * op_margin[i]
        reinv = delta / s2c if s2c else 0
        fcf = nopat - reinv
        cash = cash + raises[i] + fcf
        out.append(cash)
        prev_rev = rev[i]
    return out


def check_scenario(key: str, sc: dict, data: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warns: list[str] = []
    dcf_type = data["dcf_type"]
    mkt = data["market"]
    dp = sc["dcf_path"]
    dm = sc["dcf_metrics"]

    # ── ERROR: equity bridge ────────────────────────────────────────────
    cash = dp["cash"]
    net_debt = dp.get("net_debt", 0.0)
    sa = dp.get("special_assets", 0.0)
    eq_calc = dp["op_ev"] + cash - net_debt + sa
    if abs(eq_calc - dp["total_equity"]) > TOL_B:
        bits = [f"op_ev={dp['op_ev']:+.3f}", f"cash={cash:.3f}",
                f"net_debt={net_debt:.3f}"]
        if sa:
            bits.append(f"special_assets={sa:.3f}")
        errors.append(f_err(
            f"equity bridge ({' + '.join(bits)})",
            f"{dp['total_equity']:+.3f}", f"{eq_calc:+.3f}"))

    # ── ERROR: op_ev = sum_pv_fcf + pv_terminal ─────────────────────────
    op_ev_calc = dp["sum_pv_fcf"] + dp.get("pv_terminal", 0)
    if abs(op_ev_calc - dp["op_ev"]) > TOL_B:
        errors.append(f_err(
            "op_ev (sum_pv_fcf + pv_terminal)",
            f"{dp['op_ev']:+.3f}", f"{op_ev_calc:+.3f}"))

    # ── ERROR: sum_pv_fcf matches sum of pv_fcf array ───────────────────
    if "pv_fcf" in dp:
        pv_sum_yaml = sum(dp["pv_fcf"])
        if abs(pv_sum_yaml - dp["sum_pv_fcf"]) > TOL_PV:
            errors.append(f_err(
                "sum_pv_fcf (sum of pv_fcf array)",
                f"{dp['sum_pv_fcf']:+.3f}", f"{pv_sum_yaml:+.3f}"))

    # ── ERROR: probability_rationale present ────────────────────────────
    if not sc.get("probability_rationale", "").strip():
        errors.append(f_err("probability_rationale", "non-empty", "empty"))

    # ── WARN: PV recompute from fcf + wacc_path ─────────────────────────
    if "fcf" in dp and "wacc_path" in dp:
        factor = 1.0
        pv_sum = 0.0
        for i, f in enumerate(dp["fcf"]):
            factor *= 1 + dp["wacc_path"][i]
            pv_sum += f / factor
        if abs(pv_sum - dp["sum_pv_fcf"]) > TOL_PV_RECOMPUTE:
            warns.append(f_err(
                "sum_pv_fcf (recomputed from fcf + wacc_path)",
                f"{dp['sum_pv_fcf']:+.3f}", f"{pv_sum:+.3f}",
                "may indicate stale pv_fcf array"))

    # ── WARN: terminal value — Gordon perpetuity OR exit-multiple ───────
    # High-multiple compounders (e.g. ISRG) are valued on an exit multiple,
    # not a Gordon perpetuity — a Gordon TV at a defensible terminal growth
    # systematically undervalues them. When dcf_metrics.exit_fcf_multiple is
    # present, validate terminal_value against (exit_mult × fcf[-1]) instead.
    # Otherwise fall back to the Gordon perpetuity check.
    if dp.get("terminal_value", 0) and "fcf" in dp:
        exit_mult = dm.get("exit_fcf_multiple")
        if exit_mult:
            tv_calc = dp["fcf"][-1] * exit_mult
            tol = TOL_B * 4
            if abs(tv_calc - dp["terminal_value"]) > tol:
                warns.append(f_err(
                    f"terminal_value (exit-multiple: fcf[-1]={dp['fcf'][-1]:+.3f} "
                    f"× {exit_mult}×)",
                    f"{dp['terminal_value']:.3f}", f"{tv_calc:.3f}"))
        else:
            wt = dp["wacc_path"][-1]
            g = dp["term_g"]
            if wt > g:
                tv_calc = dp["fcf"][-1] * (1 + g) / (wt - g)
                # Mature: tight match expected. Young: undocumented formula.
                tol = TOL_B * 4 if dcf_type != "young_company" else 50.0
                if abs(tv_calc - dp["terminal_value"]) > tol:
                    warns.append(f_err(
                        f"terminal_value (Gordon: fcf[-1]={dp['fcf'][-1]:+.3f} * "
                        f"(1+{g}) / ({wt}-{g}))",
                        f"{dp['terminal_value']:.3f}", f"{tv_calc:.3f}",
                        "young-company uses different terminal formula" if dcf_type == "young_company" else ""))

    # ── ERROR: per-share = equity * 1000 / shares (spec §3.5 template) ──
    # Promoted from WARN to ERROR in Phase 2 cleanup. Young tickers
    # previously had stored per-share values that diverged inconsistently
    # from the equity-bridge math; re-derived to match. All five tickers
    # now satisfy the invariant.
    shares = dp["final_shares"]
    if shares > 0:
        ps_calc = dp["total_equity"] * 1000 / shares
        if abs(ps_calc - dp["dcf_per_share"]) > TOL_PER_SHARE:
            errors.append(f_err(
                f"dcf_per_share ({dp['total_equity']:+.3f}B * 1000 / {shares})",
                f"{dp['dcf_per_share']:+.2f}", f"{ps_calc:+.2f}"))

    # ── Variant B: cash, dilution, expected, TAM ────────────────────────
    if dcf_type == "young_company":
        # ERROR: cash runway
        cash_path = young_cash_path(sc, mkt["cash_billion"])
        min_cash = min(cash_path)
        if min_cash < -TOL_B:
            yr_min = cash_path.index(min_cash)
            errors.append(f_err(
                f"cash runway (min cash year-{yr_min} = {min_cash:+.3f}B)",
                ">= 0", f"{min_cash:+.3f}",
                "raise schedule must keep cumulative cash non-negative"))

        # ERROR: raise_total = sum(raises)
        raises = sc["chart_data"]["raises"]
        rt_calc = sum(raises)
        if abs(rt_calc - dp["raise_total"]) > TOL_B:
            errors.append(f_err(
                "raise_total (sum of raises)",
                f"{dp['raise_total']:.3f}", f"{rt_calc:.3f}"))

        # WARN: final_shares from dilution
        sh0 = mkt["shares_outstanding_million"]
        prices = sc["chart_data"]["raise_prices"]
        new_sh = sum((r * 1000 / p) for r, p in zip(raises, prices) if p > 0)
        sh_calc = sh0 + new_sh
        sh_err_pct = abs(sh_calc - shares) / max(shares, 1) * 100
        if sh_err_pct > TOL_SHARES_PCT:
            warns.append(f_err(
                f"final_shares (start {sh0:.0f}M + Sum(raise/price) = {new_sh:.0f}M)",
                f"{shares}M", f"{sh_calc:.0f}M",
                f"{sh_err_pct:.1f}% off — raise schedule may be inconsistent"))

        # WARN: expected = (1-pf)*dcf + pf*distress
        pf = dm["p_fail"] / 100
        exp_calc = (1 - pf) * dp["dcf_per_share"] + pf * dp["distress"]
        exp_clamped = max(exp_calc, 0.0)
        if (abs(exp_clamped - sc["expected_per_share"]) > TOL_EXPECTED
                and abs(exp_calc - sc["expected_per_share"]) > TOL_EXPECTED):
            warns.append(f_err(
                f"expected_per_share ((1-{pf:.2f})*{dp['dcf_per_share']:+.2f} "
                f"+ {pf:.2f}*{dp['distress']:.2f})",
                f"{sc['expected_per_share']:.2f}", f"{exp_clamped:.2f}"))

        # WARN: TAM consistency — rev_path[-1] ~ tam_billion * tam_share/100
        tam = data.get("chart_reference", {}).get("tam_billion", 0)
        if tam:
            rev10_calc = tam * dm["tam_share"] / 100
            err_pct = abs(rev10_calc - dp["rev_path"][-1]) / max(rev10_calc, 0.001) * 100
            if err_pct > TOL_TAM_PCT:
                warns.append(f_err(
                    f"rev_path[-1] (tam {tam} * tam_share {dm['tam_share']}% = {rev10_calc:.2f}B)",
                    f"{rev10_calc:.2f}", f"{dp['rev_path'][-1]:.2f}",
                    f"{err_pct:.1f}% off"))

    # Variant A (mature): rev_path is growth rates, rev_b is starting revenue.
    # Validate: rev_b * prod(1+rev_path[i]) ~ rev_b * (1+cagr_5y/100)^5
    if dcf_type in ("mature_company", "mature_company_sotp"):
        rev_b = dp.get("rev_b")
        cagr = dm.get("cagr_5y")
        rev_growth = dp.get("rev_path")
        if rev_b and cagr is not None and rev_growth:
            implied_rev5 = rev_b
            for g in rev_growth:
                implied_rev5 *= (1 + g)
            cagr_rev5 = rev_b * (1 + cagr / 100) ** 5
            err_pct = abs(implied_rev5 - cagr_rev5) / max(cagr_rev5, 0.001) * 100
            if err_pct > 5.0:
                warns.append(f_err(
                    f"rev_b growth (compounded {' * '.join(f'(1{g:+.2f})' for g in rev_growth)})",
                    f"{cagr_rev5:.2f}B (from cagr_5y={cagr}%)",
                    f"{implied_rev5:.2f}B",
                    f"{err_pct:.1f}% off"))

    return errors, warns


def validate_ticker(ticker: str) -> tuple[list[str], list[str]]:
    yml = REPO / "data" / f"{ticker}.yml"
    if not yml.exists():
        return [f"data file not found: {yml}"], []
    data = yaml.safe_load(yml.read_text())

    errors: list[str] = []
    warns: list[str] = []

    # Taxonomy — every ticker must carry a Helm-aligned taxonomy block. Values
    # validated against data/taxonomy.yml (the canonical source of truth).
    tax_errors = _taxonomy_errors(data.get("taxonomy"))
    errors.extend(tax_errors)

    # Page 4 — competitive block (§6d). WARN-only while optional.
    warns.extend(_competitive_warnings(data.get("competitive")))

    # Probabilities sum to 1.0
    prob_sum = sum(s["probability"] for s in data["scenarios"].values())
    if abs(prob_sum - 1.0) > TOL_PROB:
        errors.append(f_err("probabilities sum", "1.000", f"{prob_sum:.3f}"))

    # Private companies use a distinct scenario shape (exit_terms, not
    # dcf_path); validate those and return early — the public-equity checks
    # below don't apply.
    if data.get("dcf_type") == "private_prevaluation":
        for key in SCEN_KEYS_ALL:
            if key not in data["scenarios"]:
                continue
            pe = _private_exit_errors(key, data["scenarios"][key])
            if pe:
                errors.append(f"  [{key}]")
                errors.extend(pe)
        return errors, warns

    # Scenario keys — the four required ones must exist; ultra_bear optional.
    missing = [k for k in SCEN_KEYS if k not in data["scenarios"]]
    if missing:
        errors.append(f_err("scenario keys", f"all of {SCEN_KEYS}", f"missing {missing}"))

    for key in SCEN_KEYS_ALL:
        if key not in data["scenarios"]:
            continue
        sc = data["scenarios"][key]
        scen_e, scen_w = check_scenario(key, sc, data)
        if scen_e:
            errors.append(f"  [{key}]")
            errors.extend(scen_e)
        if scen_w:
            warns.append(f"  [{key}]")
            warns.extend(scen_w)

    return errors, warns


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    strict = "--strict" in sys.argv
    targets = [args[0].lower()] if args else TICKERS

    total_err = 0
    total_warn_tickers = 0

    for t in targets:
        errors, warns = validate_ticker(t)
        if errors:
            total_err += 1
            print(f"[{t}] ERROR")
            for e in errors:
                print(e)
        if warns:
            total_warn_tickers += 1
            print(f"[{t}] WARN")
            for w in warns:
                print(w)
        if not errors and not warns:
            print(f"[{t}] ok")
        if errors or warns:
            print()

    if total_err:
        print(f"validator: {total_err}/{len(targets)} ticker(s) have ERRORs")
        return 1
    if total_warn_tickers and strict:
        print(f"validator: {total_warn_tickers}/{len(targets)} ticker(s) have WARNs (--strict)")
        return 1
    summary = f"validator: all {len(targets)} ticker(s) pass error checks"
    if total_warn_tickers:
        summary += f" ({total_warn_tickers} with warnings)"
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
