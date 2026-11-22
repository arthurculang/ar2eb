#!/usr/bin/env python3
"""NVDA out-of-cycle re-underwrite (2026-11-22, spot $125.53 at the 2026-11-20 close).

Reproducible record of the re-model. Numerics through model_mature.model_m (the
validator's mature bridge). Writes the scenario numerics + balance sheet into
data/nvda.yml surgically (reusing stock_comp.py's line writer). Stock comp is
applied AFTERWARDS with scripts/stock_comp.py (--sbc-pct 0.0296 --shares 24285),
so the fcf written here is REPORTED FCF; the tool converts it to owner FCF.

Evidence (all dated):
- FQ1 FY27 revenue $81.6B; FQ2 $96.2B (rep. 2026-08-26); FQ3 $115.8B, +103% YoY,
  Data Center $107.6B, GAAP op income $77.5B (66.9%), GAAP GM 74.8% (rep. 2026-11-17);
  FQ4 guide $130.0B +/-3%, GM 71-72% (memory costs; "trough"), no China DC compute.
  -> FY27 revenue $419.7B / $423.6B / $427.5B at the low / mid / high of the guide
  (+94.4% / +96.2% / +98.0% on FY26 $215.9B). Year 1 is therefore nearly reported.
- Nine-month FY27 FCF $113.7B on $293.6B revenue = 38.7% -> FY27 FCF margin 0.38-0.39.
- FY28 outlook raised to ~+75% growth on the 2026-11-17 call (from ~70% in Aug);
  FY28 GM 72-73%. Sell-side FY28 consensus ~$709B (~+69%); DA Davidson 25-50%.
- Balance sheet 2026-10-25: cash + marketable debt securities $53.5B; long-term debt
  $32.4B (gross, book convention). Marketable equity ($44.2B) and non-marketable
  ($65.5B) stakes are EXCLUDED from the bridge (conservative; revenue-quality overhang).
- Downside events: CEO Jensen Huang resigned 2026-11-12 (8-K; CFO Kress interim CEO);
  Reuters 2026-11-20: SEC enforcement staff examining NVIDIA's accounting.
  -> probabilities shift 5 points toward the two downside scenarios.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import yaml
from model_mature import model_m, report_m
import stock_comp as sc

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PATH = os.path.join(REPO, "data", "nvda.yml")
SPOT, CASH, DEBT, REV0 = 125.53, 53.5, 32.4, 215.9

SCN = {
 "ultra_bear": dict(probability=0.18, g=[0.944, -0.10, -0.35, -0.15, 0.03],
                    fcfm=[0.38, 0.33, 0.27, 0.26, 0.26], opm=[0.62, 0.52, 0.42, 0.40, 0.40],
                    wacc=0.105, tg=0.025, fs=24400),
 "bear":       dict(probability=0.27, g=[0.95, 0.25, -0.20, -0.05, 0.03],
                    fcfm=[0.38, 0.38, 0.34, 0.34, 0.35], opm=[0.64, 0.60, 0.55, 0.55, 0.55],
                    wacc=0.095, tg=0.03, fs=24400),
 "base":       dict(probability=0.30, g=[0.962, 0.65, 0.10, 0.04, 0.03],
                    fcfm=[0.39, 0.42, 0.44, 0.45, 0.45], opm=[0.65, 0.62, 0.62, 0.62, 0.62],
                    wacc=0.09, tg=0.035, fs=24300),
 "bull":       dict(probability=0.18, g=[0.98, 0.75, 0.18, 0.08, 0.05],
                    fcfm=[0.39, 0.44, 0.46, 0.47, 0.47], opm=[0.66, 0.64, 0.64, 0.64, 0.64],
                    wacc=0.085, tg=0.04, fs=24200),
 "ultra_bull": dict(probability=0.07, g=[0.98, 0.85, 0.28, 0.15, 0.10],
                    fcfm=[0.39, 0.45, 0.48, 0.49, 0.49], opm=[0.66, 0.65, 0.66, 0.66, 0.66],
                    wacc=0.082, tg=0.04, fs=24000),
}


def run():
    scen = {}
    for k, s in SCN.items():
        scen[k] = dict(rev_b=REV0, rev_path=s["g"], fcf_margin=s["fcfm"],
                       wacc_path=[s["wacc"]] * 5, term_g=s["tg"], final_shares=s["fs"],
                       probability=s["probability"])
    report_m(SPOT, scen, CASH, DEBT)
    return scen


def fl(v, f="{:.3f}"):
    return "[" + ", ".join(f.format(x) for x in v) + "]"


def write(scen):
    raw = open(PATH, encoding="utf-8").read()
    lines = raw.split("\n")
    mk = next(i for i, l in enumerate(lines) if l.startswith("market:"))
    mke = sc._block_end(lines, mk, 0, len(lines))
    sc._set(lines, mk, mke, "cash_billion", f"{CASH}", 2, True)
    sc._set(lines, mk, mke, "net_debt_billion", f"{DEBT}", 2, True)
    top = next(i for i, l in enumerate(lines) if l.startswith("scenarios:"))
    end = sc._block_end(lines, top, 0, len(lines))
    starts = [(m.group(1), i) for i in range(top + 1, end) if (m := sc.SCN_RE.match(lines[i]))]
    bounds = [(k, s, starts[n + 1][1] if n + 1 < len(starts) else end)
              for n, (k, s) in enumerate(starts)]
    for k, s, e in reversed(bounds):
        d, S = scen[k]["_d"], SCN[k]
        tm = d["term_mult"]
        evf = [round(x, 1) for x in (tm + 6, tm + 3, tm + 1, tm, tm)]
        evr = [round(f * m, 1) for f, m in zip(evf, S["fcfm"])]
        def put(lo, hi, key, text, ind):
            nonlocal e
            delta = sc._set(lines, lo, hi, key, text, ind, False)
            e += delta
            return delta
        # chart_data (bottom of block first)
        cd = next(i for i in range(s, e) if re.match(r"^    chart_data:", lines[i]))
        cde = sc._block_end(lines, cd, 4, e)
        cde += put(cd, cde, "ev_rev_multiple", fl(evr, "{:.1f}"), 6)
        put(cd, cde, "ev_fcf_multiple", fl(evf, "{:.1f}"), 6)
        dpl = next(i for i in range(s, e) if re.match(r"^    dcf_path:", lines[i]))
        dpe = sc._block_end(lines, dpl, 4, e)
        vals = [("rev_path", fl(S["g"])), ("op_margin", fl(S["opm"])),
                ("wacc_path", fl([S["wacc"]] * 5)), ("term_g", f"{S['tg']}"),
                ("fcf", fl(d["fcf"])), ("cash", f"{CASH}"), ("net_debt", f"{DEBT}"),
                ("final_shares", f"{S['fs']}"),
                ("pv_fcf", fl([round(d['fcf'][i] / sc._cum(scen[k]['wacc_path'], i), 3) for i in range(5)])),
                ("sum_pv_fcf", f"{d['sum_pv_fcf']:.2f}"), ("terminal_value", f"{d['terminal_value']:.2f}"),
                ("pv_terminal", f"{d['pv_terminal']:.2f}"), ("op_ev", f"{d['op_ev']:.2f}"),
                ("total_equity", f"{d['total_equity']:.2f}"), ("dcf_per_share", f"{d['dcf_ps']:.2f}")]
        for key, text in vals:
            dpe += put(dpl, dpe, key, text, 6)
        dm = next(i for i in range(s, e) if re.match(r"^    dcf_metrics:", lines[i]))
        dme = sc._block_end(lines, dm, 4, e)
        put(dm, dme, "cagr_5y", f"{d['cagr5']}", 6)
        put(dm, dme, "wacc", f"{S['wacc']}", 6)
        put(s, e, "expected_per_share", f"{d['expected']:.2f}", 4)
        put(s, e, "probability", f"{S['probability']}", 4)
    out = "\n".join(lines)
    yaml.safe_load(out)
    open(PATH, "w", encoding="utf-8").write(out)


if __name__ == "__main__":
    scen = run()
    if "--write" in sys.argv:
        write(scen)
        print("wrote", PATH)
