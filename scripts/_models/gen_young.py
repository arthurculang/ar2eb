#!/usr/bin/env python3
"""Reusable YOUNG-company (Damodaran) memo builder — the young-archetype analog
of gen_b1.build(). Emits data/_intake/<ticker>.yml from a compact content spec;
numerics via model_dcf.model_scenario (10-year explicit window + Gordon terminal
+ p_fail/distress weighting + raise/dilution schedule + cash-runway check), so a
spec that prints clean through /tmp/<batch>/model.py (model_dcf.report) scaffolds
and validates on the first try.

Import the builder; do NOT define live SPECS at module top (that would re-run on
import, like gen_b1's LULU footgun). Per-ticker gen_<T>.py files:

    from gen_young import build_young, lin
    build_young(dict(ticker="RXRX", ... , scn={...}))

Scenario spec (compact) — each of ultra_bear/bear/base/bull/ultra_bull:
    p     probability
    rev   rev_path, 10 absolute $B (FY+1..FY+10)         [analytical core]
    opm   op_margin, 10 fractions                         [analytical core]
    wacc  wacc_path: 10 fractions, OR (start,end) tuple -> lin()
    tg    term_g
    s2c   sales-to-capital (reinvestment efficiency)
    pf    p_fail (%)            dist  distress per-share floor
    raises  10 $B capital-raise schedule (0 where none)
    rprices raise_prices: 10 $/sh, OR a scalar (applied where raises>0)
    dil   dilution_pct (informational; carried to YAML)
    fs    final_shares (M)
    tam   tam_share (% of TAM at FY+10)   comp  tam_competitor_share (%)
    rpu   rev_per_unit chart series (10), default [1.0]*10
    hl narr pr   headline / narrative (list) / probability_rationale

Top-level spec mirrors gen_b1 + young extras (tam_billion, hist_fleet, the
page3_chart_config young fields, competitive power_origination block)."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from model_dcf import model_scenario
import yaml
from collections import OrderedDict
yaml.add_representer(type(None), lambda d, _: d.represent_scalar('tag:yaml.org,2002:null', ''))
yaml.add_representer(OrderedDict, lambda d, data: d.represent_dict(data.items()))

SK = ["ultra_bear", "bear", "base", "bull", "ultra_bull"]
LAB = {"ultra_bear": ("Ultra Bear", "UltBear"), "bear": ("Bear", "Bear"), "base": ("Base", "Base"),
       "bull": ("Bull", "Bull"), "ultra_bull": ("Ultra Bull", "UltBull")}


def rnd(xs):
    return [round(float(x), 3) for x in xs]


def lin(a, b, n=10):
    """Linear path a -> b inclusive, length n (for declining wacc_path etc.)."""
    if n == 1:
        return [round(a, 4)]
    return [round(a + (b - a) * i / (n - 1), 4) for i in range(n)]


def _wacc(w, n):
    return lin(w[0], w[1], n) if isinstance(w, tuple) else list(w)


def _rprices(rp, raises):
    """Scalar -> price where a raise occurs, else 0; list -> as-is."""
    if isinstance(rp, (list, tuple)):
        return list(rp)
    return [float(rp) if float(raises[i]) > 0 else 0.0 for i in range(len(raises))]


def build_young(s):
    cash = s["cash"]; nd = s.get("net_debt", 0.0); TICK = s["ticker"].lower()
    last_rev = s["last_rev"]; shares0 = s.get("shares0", s["sh"])
    scen = OrderedDict()
    weighted = 0.0
    for k in SK:
        n = s["scn"][k]
        N = len(n["rev"])
        wacc = _wacc(n["wacc"], N)
        rprices = _rprices(n["rprices"], n["raises"])
        sd = dict(rev_path=list(n["rev"]), op_margin=list(n["opm"]), wacc_path=wacc,
                  term_g=n["tg"], s2c=n["s2c"], p_fail=n["pf"], distress=n["dist"],
                  raises=list(n["raises"]), raise_prices=rprices, final_shares=n["fs"],
                  net_debt=nd, special_assets=s.get("special_assets", 0.0), cash=cash,
                  shares0=shares0, probability=n["p"])
        r = model_scenario(sd, cash, last_rev)
        if r["min_cash"] < -0.05:
            print(f"  !! {s['ticker']}.{k}: CASH RUNWAY < 0 at min ${r['min_cash']:.3f}B — fix raises/fcf")
        weighted += n["p"] * r["expected"]
        lab, slab = LAB[k]
        scen[k] = OrderedDict([
            ("label", lab), ("short_label", slab), ("probability", n["p"]),
            ("expected_per_share", r["expected"]), ("headline", n["hl"]), ("narrative", n["narr"]),
            ("probability_rationale", n["pr"]),
            ("dcf_metrics", OrderedDict([("tam_share", n["tam"]), ("p_fail", n["pf"]), ("s2c", n["s2c"])])),
            ("dcf_path", OrderedDict([
                ("rev_path", rnd(n["rev"])), ("op_margin", rnd(n["opm"])), ("wacc_path", rnd(wacc)),
                ("term_g", n["tg"]), ("nopat", r["nopat"]), ("reinvest", r["reinvest"]), ("fcf", r["fcf"]),
                ("cash", cash), ("net_debt", nd), ("raise_total", r["raise_total"]),
                ("dilution_pct", n["dil"]), ("final_shares", n["fs"]), ("distress", n["dist"]),
                ("pv_fcf", r["pv_fcf"]), ("sum_pv_fcf", r["sum_pv_fcf"]), ("terminal_value", r["terminal_value"]),
                ("pv_terminal", r["pv_terminal"]), ("op_ev", r["op_ev"]), ("total_equity", r["total_equity"]),
                ("dcf_per_share", r["dcf_ps"])])),
            ("chart_data", OrderedDict([
                ("raises", rnd(n["raises"])), ("raise_prices", rnd(rprices)),
                ("rev_per_unit", rnd(n.get("rpu", [1.0] * N))), ("tam_competitor_share", n["comp"])]))])
    comp = s["competitive"]
    intake = OrderedDict([
        ("ticker", s["ticker"]), ("company", s["company"]), ("exchange", s["exch"]),
        ("dcf_type", "young_company"), ("date", s.get("date", "2026-06-16")), ("spot", s["spot"]),
        ("market", OrderedDict([("market_cap_billion", s["cap"]), ("shares_outstanding_million", s["sh"]),
            ("cash_billion", cash), ("net_debt_billion", nd), ("extras", s["extras"])])),
        ("taxonomy", OrderedDict([("watchlist", s["wl"]), ("tier", s.get("tier")), ("themes", s["themes"]),
            ("primary_theme", s["themes"][0])])),
        ("central_question", s["cq"]), ("thesis", s["thesis"]),
        ("chart_reference", OrderedDict([("tam_billion", s["tam_billion"]),
            ("history_years", s["hist_years"]), ("history_revenue", rnd(s["hist_rev"])),
            ("history_fleet", s.get("hist_fleet", [0] * len(s["hist_years"])))])),
        ("page3_chart_config", OrderedDict(s["p3cfg"])),
        ("page3", OrderedDict([("subtitle", s["subtitle"]), ("sources", s["sources"])])),
        ("scenarios", scen),
        ("historical_prices", OrderedDict([("ipo_marker", s["ipo"]), ("x_min", s["xmin"]), ("points", s["points"])])),
        ("weighting_rationale", [OrderedDict([("label", l), ("body", b)]) for l, b in s["wr"]]),
        ("appendix", OrderedDict([("pushback", [OrderedDict([("label", l), ("body", b)]) for l, b in s["pb"]]),
            ("triggers", [OrderedDict([("label", l), ("body", b)]) for l, b in s["tr"]])])),
        ("glossary", [OrderedDict([("term", t), ("definition", d)]) for t, d in s["gloss"]]),
        ("competitive", OrderedDict([("arena", comp["arena"]), ("lens", "power_origination"),
            ("powers", OrderedDict([(p, OrderedDict([("score", sc), ("note", nt)])) for p, sc, nt in comp["powers"]])),
            ("dominant_power", comp["dom"]), ("window", comp["window"]),
            ("rivals", [OrderedDict([("name", nm), ("kind", kd), ("note", nt), ("share_now", sn),
                ("share_terminal", st), ("capital", cp)]) for nm, kd, nt, sn, st, cp in comp["rivals"]]),
            ("lead_lag", [OrderedDict([("metric", m), ("company", co), ("best_rival", br), ("verdict", v)])
                for m, co, br, v in comp["lead_lag"]]),
            ("takeaway", comp["take"])]))])
    if "pocd" in s:
        intake["pocd"] = s["pocd"]
    out = f"/home/user/ar2eb/data/_intake/{TICK}.yml"
    open(out, "w").write(f"# {s['ticker']} — {s['company']} ({s['exch']}) · INTAKE (YOUNG; python-modeled; scaffold-ready)\n"
                         + yaml.dump(intake, sort_keys=False, default_flow_style=False, width=120, allow_unicode=True))
    print(f"  {s['ticker']}: weighted ${weighted:.2f} vs spot ${s['spot']} = {(weighted/s['spot']-1)*100:+.1f}%  -> {out}")
    return weighted


if __name__ == "__main__":
    print("gen_young is a library — import build_young from a per-ticker gen_<T>.py. "
          "See scripts/_models/gen_b1.py for the mature analog.")
