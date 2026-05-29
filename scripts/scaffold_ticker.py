#!/usr/bin/env python3
"""Scaffold a canonical data/<ticker>.yml from a partial intake.

The hand-authoring bottleneck at scale isn't the prose or the analytical
inputs — it's the equity-bridge arithmetic that ties them together. This
script turns a partial intake (the inputs an author or research agent can
defensibly write: fcf paths, op margins, wacc, terminal assumptions, cash,
shares, scenario probabilities, narrative) into the canonical YAML with all
derived dcf_path fields filled in:

  pv_fcf       = fcf[i] / Π(1+wacc[k] for k<=i)
  sum_pv_fcf   = Σ pv_fcf
  terminal_value:
                 = fcf[-1] × exit_fcf_multiple                  (if set on dcf_metrics)
                 = fcf[-1] × (1+term_g) / (wacc[-1]-term_g)     (Gordon perpetuity)
                 (author may also provide terminal_value directly — useful
                  for young_company where the spec uses a non-Gordon formula)
  pv_terminal  = terminal_value / Π(1+wacc[k] for k<N)
  op_ev        = sum_pv_fcf + pv_terminal
  total_equity = op_ev + cash - net_debt + special_assets
  dcf_per_share = total_equity × 1000 / final_shares

The author still drives the analytical choices: rev/margin/wacc paths,
terminal framing (Gordon vs exit-multiple), scenario probabilities,
narrative. The scaffold only mechanically completes the arithmetic so the
output passes scripts/validate.py's equity-bridge ERROR checks on the first
try (preserves throughput; preserves the validator as the safety net).

Intake format
-------------
The intake YAML is a partial data/<ticker>.yml — everything except the
derived dcf_path fields and the stamp. Concretely, each scenario's
dcf_path needs at minimum:

  rev_b (mature) or rev_path (young, absolute)
  rev_path (mature: growth rates) / op_margin / wacc_path
  fcf
  term_g  OR  dcf_metrics.exit_fcf_multiple  OR  terminal_value (provided)
  cash, net_debt, special_assets (optional, default 0)
  raise_total, dilution_pct, final_shares
  distress (default 0)

The scaffold fills in pv_fcf, sum_pv_fcf, terminal_value (if not provided),
pv_terminal, op_ev, total_equity, dcf_per_share. The stamp block is
generated at v001 with the current timestamp.

Usage
-----
    python scripts/scaffold_ticker.py <ticker> [--intake PATH] [--force]

By convention intakes live at data/_intake/<ticker>.yml (kept out of the
final data/ until scaffolded). Refuses to overwrite an existing
data/<ticker>.yml unless --force is passed.

After scaffolding, run:
    python scripts/validate.py                # math + taxonomy QC
    python scripts/rebuild_all.py <ticker>    # render + STRICT_LAYOUT
"""
import argparse
import sys
from datetime import datetime
from functools import reduce
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent


def _cum_disc(wacc_path: list, k: int) -> float:
    """Cumulative discount factor through end of year k (0-indexed)."""
    return reduce(lambda acc, w: acc * (1 + w), wacc_path[: k + 1], 1.0)


def derive_dcf_path(dp: dict, mkt: dict, dcf_metrics: dict, ticker: str, scn_key: str) -> None:
    """Fill in derived dcf_path fields in place. Idempotent — re-running
    overwrites the derived fields from the (unchanged) inputs."""
    fcf = dp.get("fcf")
    wacc_path = dp.get("wacc_path")
    if not fcf or not wacc_path:
        raise ValueError(f"{ticker}.{scn_key}: dcf_path.fcf and .wacc_path are required")
    if len(fcf) != len(wacc_path):
        raise ValueError(
            f"{ticker}.{scn_key}: dcf_path.fcf (len {len(fcf)}) and "
            f".wacc_path (len {len(wacc_path)}) must match"
        )
    n = len(fcf)

    # PV of each year's FCF using cumulative discount factor.
    pv_fcf = [round(fcf[i] / _cum_disc(wacc_path, i), 3) for i in range(n)]
    dp["pv_fcf"] = pv_fcf
    dp["sum_pv_fcf"] = round(sum(pv_fcf), 2)

    # Terminal value — three resolution paths in priority order:
    #   1. exit_fcf_multiple on dcf_metrics (high-multiple compounders)
    #   2. Gordon perpetuity from term_g + wacc[-1] (standard mature)
    #   3. terminal_value provided on dcf_path (young-company uses a
    #      non-Gordon formula per spec §6c; author supplies directly)
    exit_mult = dcf_metrics.get("exit_fcf_multiple") if dcf_metrics else None
    term_g = dp.get("term_g")
    wacc_n = wacc_path[-1]
    if exit_mult is not None:
        tv = fcf[-1] * exit_mult
    elif term_g is not None and wacc_n > term_g:
        tv = fcf[-1] * (1 + term_g) / (wacc_n - term_g)
    elif "terminal_value" in dp:
        tv = dp["terminal_value"]
    else:
        raise ValueError(
            f"{ticker}.{scn_key}: cannot derive terminal_value — need one of "
            f"dcf_metrics.exit_fcf_multiple, dcf_path.term_g (with wacc[-1] > "
            f"term_g), or an explicit dcf_path.terminal_value"
        )
    dp["terminal_value"] = round(tv, 2)

    # PV of terminal: discount end-of-year-N value back to today.
    pv_term = tv / _cum_disc(wacc_path, n - 1)
    dp["pv_terminal"] = round(pv_term, 2)

    dp["op_ev"] = round(dp["sum_pv_fcf"] + dp["pv_terminal"], 2)

    # Equity bridge. cash/net_debt default to market-level values if absent
    # on the scenario (most tickers carry them per-scenario in case M&A or a
    # major raise changes the position).
    cash = dp.get("cash")
    if cash is None:
        cash = float(mkt.get("cash_billion", 0))
        dp["cash"] = cash
    net_debt = dp.get("net_debt", 0)
    dp["net_debt"] = net_debt
    special_assets = dp.get("special_assets", 0)
    if special_assets:
        dp["special_assets"] = special_assets
    dp["total_equity"] = round(dp["op_ev"] + cash - net_debt + special_assets, 2)

    shares = dp.get("final_shares")
    if not shares:
        raise ValueError(f"{ticker}.{scn_key}: dcf_path.final_shares is required")
    dp["dcf_per_share"] = round(dp["total_equity"] * 1000 / shares, 2)

    dp.setdefault("distress", 0.0)


def generate_stamp(canonical_jsx: str = "public/memo_pdf.jsx") -> dict:
    now = datetime.now().strftime("%Y-%m-%d_%H-%M")
    return {
        "footer_version": "001",
        "footer_timestamp": now,
        "canonical_jsx": canonical_jsx,
        "pdf_version": "001",
        "pdf_timestamp": now,
    }


def scaffold(ticker: str, intake_path: Path, force: bool = False) -> Path:
    if not intake_path.exists():
        raise FileNotFoundError(f"intake not found: {intake_path}")
    intake = yaml.safe_load(intake_path.read_text())
    if not intake or not intake.get("scenarios"):
        raise ValueError(f"{intake_path}: missing scenarios block")

    for scn_key, sc in intake["scenarios"].items():
        derive_dcf_path(
            sc.setdefault("dcf_path", {}),
            intake.get("market", {}),
            sc.get("dcf_metrics", {}),
            ticker, scn_key,
        )

    intake.setdefault("stamp", generate_stamp())

    output_path = REPO / "data" / f"{ticker}.yml"
    if output_path.exists() and not force:
        raise FileExistsError(
            f"{output_path} already exists; pass --force to overwrite "
            "(or use bump_pdf_version.py for stamp-only updates)"
        )

    # default_flow_style=False keeps YAML readable; width=120 avoids
    # auto-wrapping long narrative paragraphs mid-sentence.
    output_path.write_text(
        yaml.safe_dump(intake, sort_keys=False, default_flow_style=False, width=120, allow_unicode=True)
    )
    return output_path


def main() -> int:
    ap = argparse.ArgumentParser(description="Scaffold a canonical data/<ticker>.yml from a partial intake.")
    ap.add_argument("ticker", help="ticker slug (lowercase, e.g. isrg)")
    ap.add_argument("--intake", default=None,
                    help="path to intake YAML (default: data/_intake/<ticker>.yml)")
    ap.add_argument("--force", action="store_true",
                    help="overwrite existing data/<ticker>.yml")
    args = ap.parse_args()

    ticker = args.ticker.lower()
    intake_path = Path(args.intake) if args.intake else REPO / "data" / "_intake" / f"{ticker}.yml"
    try:
        out = scaffold(ticker, intake_path, force=args.force)
    except (FileNotFoundError, FileExistsError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"wrote {out.relative_to(REPO)}")
    print("  next: scripts/validate.py  →  scripts/rebuild_all.py", ticker)
    return 0


if __name__ == "__main__":
    sys.exit(main())
