"""charts/mature_company.py — Page 3 business-snapshot charts for
Mature-Company DCF tickers (LTH, ZM; spec §7 Variant A).

Replaces build_lth_charts.py + build_zm_charts.py. Dispatches on dcf_type
for chart 4 (LTH = net debt bars; ZM = net cash bars) and chart 6
(LTH = club count by format; ZM = SOTP equity decomposition).

Scenario/market data is read from data/<ticker>.yml. Chart-only
historical reference series + per-scenario chart aesthetic paths
(gross_margin / mem-inc growth / buybacks for LTH, historical margins +
cash + EV multiples for ZM) live in CONFIG below — chart aesthetic data,
not memo content.

Usage:
    python charts/mature_company.py <ticker>     # ticker in {lth, zm}
"""
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import yaml

REPO = Path(__file__).resolve().parent.parent
FONT_DIR = REPO / "public" / "assets" / "fonts"
for _f in os.listdir(FONT_DIR):
    if _f.endswith(".ttf"):
        fm.fontManager.addfont(str(FONT_DIR / _f))

plt.rcParams.update({
    "font.family": "Inter",
    "font.size": 9, "axes.labelsize": 9, "axes.titlesize": 10,
    "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.5,
    "xtick.major.width": 0.5, "ytick.major.width": 0.5,
    "xtick.major.size": 3, "ytick.major.size": 3,
})

INK, TEXT, MUTED, DIM, RULE = "#0a0a0a", "#1f2937", "#6b7280", "#9ca3af", "#e5e7eb"
ACCENT, ACCENT_SOFT = "#1e3a8a", "#94a3b8"
COLORS = {"bear": "#b91c1c", "base": "#1e3a8a", "bull": "#15803d", "ultra_bull": "#7629a6"}

FIG_W, FIG_H, DPI = 3.5, 2.4, 200
FY_PROJ = ["FY26", "FY27", "FY28", "FY29", "FY30"]
SCEN_ORDER = ["bear", "base", "bull", "ultra_bull"]

# ── Per-ticker chart-only config ─────────────────────────────────────────────
CONFIG = {
    "lth": {
        "fy_hist":            ["FY21", "FY22", "FY23", "FY24", "FY25"],
        "segments":           ("Membership", "In-center"),
        # historical series (chart_reference already carries these — used directly)
        "scenario_paths": {
            # per-scenario chart-aesthetic paths NOT in memo YAML
            "bear":  {"gross_margin": [0.380, 0.375, 0.370, 0.365, 0.360],
                      "mem_growth":   [0.10, 0.06, 0.04, 0.03, 0.02],
                      "inc_growth":   [0.14, 0.06, 0.04, 0.03, 0.02],
                      "buybacks":     [0.0, 0.0, 0.0, 0.0, 0.0]},
            "base":  {"gross_margin": [0.385, 0.388, 0.390, 0.390, 0.390],
                      "mem_growth":   [0.10, 0.09, 0.08, 0.07, 0.06],
                      "inc_growth":   [0.14, 0.09, 0.08, 0.06, 0.04],
                      "buybacks":     [0.0, 0.0, 0.10, 0.15, 0.15]},
            "bull":  {"gross_margin": [0.390, 0.395, 0.400, 0.405, 0.410],
                      "mem_growth":   [0.11, 0.10, 0.09, 0.08, 0.07],
                      "inc_growth":   [0.15, 0.13, 0.12, 0.11, 0.08],
                      "buybacks":     [0.0, 0.10, 0.20, 0.30, 0.40]},
            "ultra_bull": {"gross_margin": [0.395, 0.405, 0.415, 0.420, 0.425],
                           "mem_growth":   [0.12, 0.11, 0.10, 0.09, 0.08],
                           "inc_growth":   [0.16, 0.15, 0.14, 0.13, 0.10],
                           "buybacks":     [0.0, 0.15, 0.30, 0.40, 0.50]},
        },
    },
    "zm": {
        "fy_hist":            ["FY21", "FY22", "FY23", "FY24", "FY25"],
        "segments":           ("Enterprise", "Online"),
        "hist_ent_split":     [0.55, 0.58, 0.59, 0.60, 0.603],
        "hist_gross_margin":  [73.5, 76.0, 76.4, 76.6, 76.5],
        "hist_op_margin":     [25.0, 35.0, 38.0, 38.5, 39.0],
        "hist_fcf_margin":    [29.0, 36.0, 37.0, 36.0, 36.0],
        "hist_cash":          [4.7, 5.4, 6.7, 7.4, 7.8],
        "hist_ev_rev":        [11.5, 4.0, 3.8, 4.0, 4.3],
        "hist_ev_fcf":        [40, 11, 10, 11, 12],
        "fcf_margin_proj":    {"bear":  [35, 34, 33, 31, 29],
                                "base":  [35, 35, 35, 35, 35],
                                "bull":  [38, 39, 40, 41, 41],
                                "ultra_bull": [39, 41, 43, 44, 45]},
        "cash_acc_per_year":  {"bear":  1.2, "base": 0.8, "bull": 1.4, "ultra_bull": 1.6},
        "segment_ent_coef":   {"bear": (0.60, -0.01), "base": (0.62, 0.02),
                                "bull": (0.64, 0.025), "ultra_bull": (0.66, 0.03)},
    },
}


def parse_args():
    if len(sys.argv) != 2 or sys.argv[1].lower() not in CONFIG:
        print(f"usage: python charts/mature_company.py <{'|'.join(CONFIG)}>",
              file=sys.stderr)
        sys.exit(2)
    return sys.argv[1].lower()


def load(ticker):
    d = yaml.safe_load((REPO / "data" / f"{ticker}.yml").read_text())
    assert d["dcf_type"] in ("mature_company", "mature_company_sotp"), \
        f"{ticker}: dcf_type={d['dcf_type']}, expected mature_*"
    return d


def style_ax(ax):
    ax.spines["left"].set_color(MUTED)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(colors=MUTED)
    ax.grid(axis="y", color=RULE, linewidth=0.4, zorder=0)
    ax.set_axisbelow(True)


def today_marker(ax, x):
    ax.axvline(x, color=DIM, linewidth=0.4, linestyle=":", zorder=1)


def project_revenue(rev_b, rev_growth):
    rev, out = rev_b, [rev_b]
    for g in rev_growth:
        rev = rev * (1 + g)
        out.append(rev)
    return out


# ─── Chart 1 — Revenue history bars + scenario projections ──────────────────
def chart_revenue(data, cfg, scn_growth, out):
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.11, right=0.93, top=0.84, bottom=0.18)

    cr = data["chart_reference"]
    rev_hist = cr["history_revenue"]
    n_hist = len(cfg["fy_hist"])
    fy_short = [s[2:] for s in cfg["fy_hist"] + FY_PROJ]
    bars = ax.bar(range(n_hist), rev_hist, color=ACCENT_SOFT, width=0.62, zorder=2)
    bars[-1].set_color(ACCENT)
    for i, v in enumerate(rev_hist):
        ax.text(i, v + 0.07, f"{v:.1f}", ha="center", va="bottom", fontsize=7, color=TEXT)

    rev_b = next(iter(data["scenarios"].values()))["dcf_path"]["rev_b"]
    proj_x = list(range(n_hist - 1, n_hist + 5))
    for k in SCEN_ORDER:
        proj_y = project_revenue(rev_b, scn_growth[k])
        ax.plot(proj_x, proj_y, color=COLORS[k], linewidth=1.4, linestyle="--",
                marker="o", markersize=2.5, markerfacecolor=COLORS[k],
                markeredgecolor="white", markeredgewidth=0.6, zorder=3)
        ax.text(proj_x[-1] + 0.12, proj_y[-1],
                f'{data["scenarios"][k]["short_label"]} {proj_y[-1]:.1f}',
                color=COLORS[k], fontsize=7, va="center", ha="left", fontweight="medium")

    today_marker(ax, n_hist - 0.5)
    ax.set_xticks(list(range(n_hist + 5)))
    ax.set_xticklabels(fy_short, fontsize=7.5)
    ax.set_xlim(-0.5, n_hist + 5 + 1.5)
    # ylim: builder's "max(rev_hist) * 1.8" plus a safety bound for projections
    proj_max = max(project_revenue(rev_b, scn_growth[k])[-1] for k in SCEN_ORDER)
    ax.set_ylim(0, max(max(rev_hist) * 1.8, proj_max * 1.1))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"${x:.0f}B"))
    style_ax(ax)
    ax.set_title("Revenue ($B) — history + scenario projections to FY30",
                 fontsize=9, color=INK, loc="left", pad=8, fontweight="semibold")
    plt.savefig(f"{out}/01_revenue.png", dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close()


# ─── Chart 2 — Revenue by segment ────────────────────────────────────────────
def chart_segments(data, cfg, scn_growth, ticker, out):
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.14, right=0.93, top=0.84, bottom=0.18)
    cr = data["chart_reference"]
    n_hist = len(cfg["fy_hist"])
    seg_a, seg_b = cfg["segments"]

    if ticker == "lth":
        a_hist = cr["history_ent_revenue_m"]
        b_hist = cr["history_onl_revenue_m"]
        ax.plot(range(n_hist), a_hist, color=ACCENT, linewidth=1.8, marker="o", markersize=3.5,
                markerfacecolor=ACCENT, markeredgecolor="white", markeredgewidth=0.6, zorder=4)
        ax.plot(range(n_hist), b_hist, color=ACCENT_SOFT, linewidth=1.4, marker="o", markersize=3,
                markerfacecolor=ACCENT_SOFT, markeredgecolor="white", markeredgewidth=0.6, zorder=3)
        proj_x = list(range(n_hist - 1, n_hist + 5))
        for k in SCEN_ORDER:
            paths = CONFIG["lth"]["scenario_paths"][k]
            mem, inc = a_hist[-1], b_hist[-1]
            mem_p, inc_p = [mem], [inc]
            for gm, gi in zip(paths["mem_growth"], paths["inc_growth"]):
                mem *= 1 + gm; inc *= 1 + gi
                mem_p.append(mem); inc_p.append(inc)
            ax.plot(proj_x, mem_p, color=COLORS[k], linewidth=1.4, linestyle="--",
                    marker="o", markersize=2.5, markerfacecolor=COLORS[k],
                    markeredgecolor="white", markeredgewidth=0.6, zorder=3)
            ax.plot(proj_x, inc_p, color=COLORS[k], linewidth=0.9, linestyle=":",
                    alpha=0.7, zorder=2)
            ax.text(proj_x[-1] + 0.12, mem_p[-1],
                    f'{data["scenarios"][k]["short_label"]} {mem_p[-1] / 1000:.1f}K',
                    color=COLORS[k], fontsize=7, va="center", ha="left", fontweight="medium")
        ax.text(-0.18, a_hist[0], seg_a, color=ACCENT, fontsize=7.5,
                va="center", ha="right", fontweight="medium")
        ax.text(-0.18, b_hist[0], seg_b, color=MUTED, fontsize=7.5,
                va="center", ha="right", fontweight="medium")
        ax.set_ylim(200, 3800)
        ax.set_yticks([500, 1000, 2000, 3000])
        ax.set_yticklabels(["0.5K", "1K", "2K", "3K"])
        ax.set_xlim(-2.0, n_hist + 5 + 1.5)
    else:  # zm — Enterprise/Online with projection per scenario derived from total rev × split coef
        rev_hist = cr["history_revenue"]
        ent_hist = [r * s for r, s in zip(rev_hist, cfg["hist_ent_split"])]
        onl_hist = [r - e for r, e in zip(rev_hist, ent_hist)]
        ax.plot(range(n_hist), ent_hist, "-o", color=ACCENT, ms=2.5, lw=1.2, label=seg_a)
        ax.plot(range(n_hist), onl_hist, "-o", color=MUTED, ms=2.5, lw=1.2, label=seg_b)
        proj_years = list(range(n_hist - 1, n_hist + 5))
        rev_b = next(iter(data["scenarios"].values()))["dcf_path"]["rev_b"]
        for k in SCEN_ORDER:
            proj_rev = project_revenue(rev_b, scn_growth[k])
            coef0, slope = cfg["segment_ent_coef"][k]
            proj_ent = [proj_rev[i] * (coef0 + i * slope) for i in range(len(proj_rev))]
            line_style = "--" if k == "base" else ":"
            ax.plot(proj_years, proj_ent, line_style, color=COLORS[k],
                    lw=0.9 if k != "base" else 0.9, alpha=0.8 if k == "base" else 0.6)
        ax.annotate(seg_a, xy=(n_hist - 0.7, ent_hist[-1] + 0.05), color=ACCENT, fontsize=8)
        ax.annotate(seg_b, xy=(n_hist - 0.7, onl_hist[-1] + 0.05), color=MUTED, fontsize=8)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"${x:.1f}B"))

    today_marker(ax, n_hist - 0.5)
    fy_short = [s[2:] for s in cfg["fy_hist"] + FY_PROJ]
    ax.set_xticks(list(range(n_hist + 5)))
    ax.set_xticklabels(fy_short, fontsize=7.5)
    style_ax(ax)
    if ticker == "lth":
        ax.set_title("Revenue by segment ($M) — dashed Membership, dotted In-center",
                     fontsize=8.5, color=INK, loc="left", pad=8, fontweight="semibold")
    else:
        ax.set_title("Revenue by segment ($B) — dashed=base, dotted=bear/bull",
                     fontsize=8.5, color=INK, loc="left", pad=8, fontweight="semibold")
    plt.savefig(f"{out}/02_segments.png", dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close()


# ─── Chart 3 — Margin trends ─────────────────────────────────────────────────
def chart_margins(data, cfg, scn_growth, ticker, out):
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.13, right=0.93, top=0.84, bottom=0.18)
    cr = data["chart_reference"]
    n_hist = len(cfg["fy_hist"])
    fy_short = [s[2:] for s in cfg["fy_hist"] + FY_PROJ]

    if ticker == "lth":
        gross_h = cr["history_gross_margin"]; op_h = cr["history_op_margin"]; fcf_h = cr["history_fcf_margin"]
        ax.plot(range(n_hist), gross_h, color=INK, linewidth=1.6, marker="o", markersize=3,
                markerfacecolor=INK, markeredgecolor="white", markeredgewidth=0.6, zorder=4)
        ax.plot(range(n_hist), op_h, color=ACCENT, linewidth=1.6, marker="o", markersize=3,
                markerfacecolor=ACCENT, markeredgecolor="white", markeredgewidth=0.6, zorder=3)
        ax.plot(range(n_hist), fcf_h, color=ACCENT_SOFT, linewidth=1.4, marker="o", markersize=3,
                markerfacecolor=ACCENT_SOFT, markeredgecolor="white", markeredgewidth=0.6, zorder=2)

        proj_x = list(range(n_hist - 1, n_hist + 5))
        rev_b = next(iter(data["scenarios"].values()))["dcf_path"]["rev_b"]
        for k in SCEN_ORDER:
            # derive FCF margin from YAML dcf_path.fcf / compounded revenue
            sc = data["scenarios"][k]
            rev_path = project_revenue(rev_b, scn_growth[k])[1:]
            fcf_margin = [(sc["dcf_path"]["fcf"][i] / rev_path[i]) * 100 for i in range(5)]
            fcf_p = [fcf_h[-1]] + fcf_margin
            ax.plot(proj_x, fcf_p, color=COLORS[k], linewidth=1.3, linestyle="--",
                    marker="o", markersize=2.5, markerfacecolor=COLORS[k],
                    markeredgecolor="white", markeredgewidth=0.5, zorder=3)
            ax.text(proj_x[-1] + 0.12, fcf_p[-1],
                    f'{sc["short_label"]} {fcf_p[-1]:.0f}%',
                    color=COLORS[k], fontsize=7, va="center", ha="left", fontweight="medium")

        proj_x_only = list(range(n_hist, n_hist + 5))
        ax.plot([n_hist - 1] + proj_x_only, [gross_h[-1]] + [gross_h[-1]] * 5,
                color=INK, linewidth=0.7, linestyle=":", alpha=0.5, zorder=2)
        ax.plot([n_hist - 1] + proj_x_only, [op_h[-1]] + [op_h[-1] + 1.0] * 5,
                color=ACCENT, linewidth=0.7, linestyle=":", alpha=0.5, zorder=2)
        ax.text(n_hist - 1 + 0.12, gross_h[-1] + 1.5, f"Gross {gross_h[-1]:.0f}%",
                color=INK, fontsize=6.5, va="center", ha="left")
        ax.text(n_hist - 1 + 0.12, op_h[-1] + 1.5, f"Op {op_h[-1]:.0f}%",
                color=ACCENT, fontsize=6.5, va="center", ha="left")
        ax.set_ylim(-15, 50)
        ax.set_yticks([-10, 0, 10, 20, 30, 40, 50])
        ax.set_yticklabels(["-10%", "0%", "10%", "20%", "30%", "40%", "50%"])
        ax.set_xlim(-0.4, n_hist + 5 + 1.6)
    else:  # zm
        gross_h = cfg["hist_gross_margin"]; op_h = cfg["hist_op_margin"]; fcf_h = cfg["hist_fcf_margin"]
        ax.plot(range(n_hist), gross_h, "-o", color=INK, ms=2.5, lw=1.2)
        ax.plot(range(n_hist), op_h, "-o", color=ACCENT, ms=2.5, lw=1.2)
        ax.plot(range(n_hist), fcf_h, "-o", color=MUTED, ms=2.5, lw=1.2)
        proj_years = list(range(n_hist - 1, n_hist + 5))
        for k in SCEN_ORDER:
            fcf_proj = cfg["fcf_margin_proj"][k]
            ax.plot(proj_years, [fcf_h[-1]] + fcf_proj, "--", color=COLORS[k], lw=1.0)
        ax.annotate(f"Gross {gross_h[-1]:.0f}%", xy=(n_hist - 0.8, gross_h[-1]), color=INK, fontsize=7)
        ax.annotate(f"Op {op_h[-1]:.0f}%", xy=(n_hist - 0.8, op_h[-1]), color=ACCENT, fontsize=7)
        for k in SCEN_ORDER:
            v = cfg["fcf_margin_proj"][k][-1]
            ax.annotate(f'{data["scenarios"][k]["short_label"]} {v}%',
                        xy=(n_hist + 5 - 0.8, v),
                        color=COLORS[k], fontsize=7, va="center")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.0f}%"))
        ax.set_ylim(20, 85)

    today_marker(ax, n_hist - 0.5)
    ax.set_xticks(list(range(n_hist + 5)))
    ax.set_xticklabels(fy_short, fontsize=7.5)
    style_ax(ax)
    ax.set_title("Margin trends — dashed = FCF margin scenarios",
                 fontsize=9, color=INK, loc="left", pad=8, fontweight="semibold")
    plt.savefig(f"{out}/03_margins.png", dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close()


# ─── Chart 4 — Net debt (LTH) OR Net cash (ZM, SOTP) ─────────────────────────
def chart_balance(data, cfg, scn_growth, ticker, out):
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.12, right=0.93, top=0.84, bottom=0.18)
    cr = data["chart_reference"]
    n_hist = len(cfg["fy_hist"])
    fy_short = [s[2:] for s in cfg["fy_hist"] + FY_PROJ]

    if ticker == "lth":  # net debt: bars history + scenario debt-paydown projections
        debt_h = cr["history_net_debt"]
        bars = ax.bar(range(n_hist), debt_h, color=ACCENT_SOFT, width=0.6, zorder=2)
        bars[-1].set_color(ACCENT)
        for i, v in enumerate(debt_h):
            ax.text(i, v + 0.04, f"{v:.1f}", ha="center", va="bottom", fontsize=7, color=TEXT)
        proj_x = list(range(n_hist - 1, n_hist + 5))
        rev_b = next(iter(data["scenarios"].values()))["dcf_path"]["rev_b"]
        for k in SCEN_ORDER:
            paths = CONFIG["lth"]["scenario_paths"][k]
            sc = data["scenarios"][k]
            rev_path = project_revenue(rev_b, scn_growth[k])[1:]
            fcf_margin = [sc["dcf_path"]["fcf"][i] / rev_path[i] for i in range(5)]
            debt, debt_p = debt_h[-1], [debt_h[-1]]
            for i in range(5):
                fcf = rev_path[i] * fcf_margin[i]
                debt = max(debt - fcf + paths["buybacks"][i], 0)
                debt_p.append(debt)
            ax.plot(proj_x, debt_p, color=COLORS[k], linewidth=1.4, linestyle="--",
                    marker="o", markersize=2.5, markerfacecolor=COLORS[k],
                    markeredgecolor="white", markeredgewidth=0.6, zorder=3)
            ax.text(proj_x[-1] + 0.12, debt_p[-1],
                    f'{sc["short_label"]} {debt_p[-1]:.1f}',
                    color=COLORS[k], fontsize=7, va="center", ha="left", fontweight="medium")
        ax.set_ylim(0, 2.0)
        ax.set_yticks([0, 0.5, 1.0, 1.5, 2.0])
        ax.set_yticklabels(["$0", "$0.5B", "$1B", "$1.5B", "$2B"])
        ax.set_xlim(-0.5, n_hist + 5 + 1.6)
        title = "Net financial debt ($B) — debt paydown via FCF (incl. SLB)"
    else:  # zm — net cash position grows
        cash_h = cfg["hist_cash"]
        bars = ax.bar(range(n_hist), cash_h, color=ACCENT_SOFT, width=0.6, zorder=2)
        bars[-1].set_color(ACCENT)
        proj_x = list(range(n_hist - 1, n_hist + 5))
        for k in SCEN_ORDER:
            acc = cfg["cash_acc_per_year"][k]
            cash_p = [cash_h[-1] + i * acc for i in range(6)]
            ax.plot(proj_x, cash_p, "--o", color=COLORS[k], ms=3, lw=1)
            ax.annotate(f'{data["scenarios"][k]["short_label"]} ${cash_p[-1]:.1f}B',
                        xy=(proj_x[-1] + 0.2, cash_p[-1]),
                        color=COLORS[k], fontsize=7, va="center")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"${x:.0f}B"))
        title = "Cash & investments ($B) — net cash position grows"

    today_marker(ax, n_hist - 0.5)
    ax.set_xticks(list(range(n_hist + 5)))
    ax.set_xticklabels(fy_short, fontsize=7.5)
    style_ax(ax)
    ax.set_title(title, fontsize=8.5, color=INK, loc="left", pad=8, fontweight="semibold")
    plt.savefig(f"{out}/04_net_debt.png" if ticker == "lth" else f"{out}/04_net_debt.png",
                dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close()


# ─── Chart 5 — EV multiples (dual axis: EV/Rev left, EV/EBITDA right) ────────
def chart_ev_multiples(data, cfg, ticker, out):
    fig, ax1 = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.13, right=0.83, top=0.84, bottom=0.18)
    cr = data["chart_reference"]
    n_hist = len(cfg["fy_hist"])
    fy_short = [s[2:] for s in cfg["fy_hist"] + FY_PROJ]

    if ticker == "lth":
        ev_rev_h = cr["history_ev_rev"]; ev_ebitda_h = cr["history_ev_ebitda"]
        valid = [(i, v) for i, v in enumerate(ev_rev_h) if v is not None]
        ax1.plot([i for i, _ in valid], [v for _, v in valid],
                 color=ACCENT, linewidth=1.6, marker="o", markersize=3.5,
                 markerfacecolor=ACCENT, markeredgecolor="white", markeredgewidth=0.6, zorder=3)
        proj_x = list(range(n_hist - 1, n_hist + 5))
        # project from FY25 close toward terminal multiple computed from scenario terminal math
        for k in SCEN_ORDER:
            sc = data["scenarios"][k]
            wacc = sc["dcf_metrics"]["wacc"]; tg = sc["dcf_path"]["term_g"]
            fcf_eb = sc["chart_data"]["fcf_to_ebitda_ratio"]
            term_fcf_mult = 1.0 / (wacc - tg)
            term_ev_ebitda = term_fcf_mult * fcf_eb
            term_ebitda_margin = sc["dcf_path"]["op_margin"][-1] + 0.08
            term_ev_rev = term_ev_ebitda * term_ebitda_margin
            anchor_rev = ev_rev_h[-1]; anchor_eb = ev_ebitda_h[-1]
            rev_out = [anchor_rev]; eb_out = [anchor_eb]
            for i in range(5):
                t = (i + 1) / 5.0
                rev_out.append(anchor_rev * (1 - t) + term_ev_rev * t)
                eb_out.append(anchor_eb * (1 - t) + term_ev_ebitda * t)
            ax1.plot(proj_x, rev_out, color=COLORS[k], linewidth=1.3, linestyle="--",
                     marker="o", markersize=2, markerfacecolor=COLORS[k],
                     markeredgecolor="white", markeredgewidth=0.5, zorder=2)
            ax1.text(proj_x[-1] + 0.12, rev_out[-1], f"{rev_out[-1]:.1f}×",
                     color=COLORS[k], fontsize=7, va="center", ha="left", fontweight="medium")
        ax2 = ax1.twinx()
        ax2.plot([i for i, v in enumerate(ev_ebitda_h) if v is not None],
                 [v for v in ev_ebitda_h if v is not None],
                 color=INK, linewidth=1.4, marker="s", markersize=3,
                 markerfacecolor=INK, markeredgecolor="white",
                 markeredgewidth=0.6, zorder=3, alpha=0.85)
        for k in SCEN_ORDER:
            sc = data["scenarios"][k]
            wacc = sc["dcf_metrics"]["wacc"]; tg = sc["dcf_path"]["term_g"]
            fcf_eb = sc["chart_data"]["fcf_to_ebitda_ratio"]
            term_ev_ebitda = (1.0 / (wacc - tg)) * fcf_eb
            anchor_eb = ev_ebitda_h[-1]
            eb_out = [anchor_eb] + [anchor_eb * (1 - (i + 1) / 5.0) + term_ev_ebitda * ((i + 1) / 5.0)
                                    for i in range(5)]
            ax2.plot(proj_x, eb_out, color=COLORS[k], linewidth=1.0, linestyle=":",
                     marker="s", markersize=2, markerfacecolor=COLORS[k],
                     markeredgecolor="white", markeredgewidth=0.4, zorder=2, alpha=0.85)
        ax1.set_ylim(0, 8); ax1.set_yticks([0, 2, 4, 6, 8])
        ax1.set_yticklabels(["0×", "2×", "4×", "6×", "8×"])
        ax1.set_ylabel("EV / Revenue", fontsize=7.5, color=ACCENT, labelpad=4)
        ax2.set_ylim(0, 35); ax2.set_yticks([0, 10, 20, 30])
        ax2.set_yticklabels(["0×", "10×", "20×", "30×"])
        ax2.spines["top"].set_visible(False)
        ax2.spines["right"].set_color(MUTED); ax2.spines["left"].set_visible(False)
        ax2.tick_params(colors=MUTED, axis="y")
        ax2.set_ylabel("EV / EBITDA", fontsize=7.5, color=INK, labelpad=4)
        fig.text(0.13, 0.05, "Solid line = EV/Rev (left). Square markers + dotted = EV/EBITDA (right).",
                 fontsize=6, color=MUTED, ha="left")
    else:  # zm — uses scenarios.chart_data.ev_rev_multiple from YAML
        ev_rev_h = cfg["hist_ev_rev"]
        ax1.plot(range(n_hist), ev_rev_h, "-o", color=INK, ms=3, lw=1.2)
        proj_x = list(range(n_hist - 1, n_hist + 5))
        for k in SCEN_ORDER:
            proj = [ev_rev_h[-1]] + data["scenarios"][k]["chart_data"]["ev_rev_multiple"]
            ax1.plot(proj_x, proj, "--", color=COLORS[k], lw=1.0 if k == "base" else 0.9)
            ax1.annotate(f"{proj[-1]:.1f}×", xy=(proj_x[-1] + 0.2, proj[-1]),
                         color=COLORS[k], fontsize=7, va="center")
        ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.0f}×"))
        ax1.set_ylim(0, 14)
        ax1.set_ylabel("EV / Rev", fontsize=8)
        ax2 = ax1.twinx()
        ax2.plot(range(n_hist), cfg["hist_ev_fcf"], "s:", color=MUTED, ms=3, lw=0.8, alpha=0.7)
        ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.0f}×"))
        ax2.set_ylim(0, 45)
        ax2.set_ylabel("EV / FCF", fontsize=8)
        ax2.spines["top"].set_visible(False)

    today_marker(ax1, n_hist - 0.5)
    ax1.set_xticks(list(range(n_hist + 5)))
    ax1.set_xticklabels(fy_short, fontsize=7.5)
    ax1.set_xlim(-0.4, n_hist + 5 + 1.4)
    title = ("EV multiples — dual axis (Rev left, EBITDA right)" if ticker == "lth"
             else "EV multiples (operating-EV basis, ex-Anthropic)")
    ax1.set_title(title, fontsize=8.5, color=INK, loc="left", pad=8, fontweight="semibold")
    plt.savefig(f"{out}/05_ev_multiples.png", dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close()


# ─── Chart 6 — Club count by format (LTH) OR SOTP decomposition (ZM SOTP) ────
def chart_terminal(data, cfg, ticker, out):
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    if ticker == "lth":
        fig.subplots_adjust(left=0.20, right=0.95, top=0.84, bottom=0.18)
        cr = data["chart_reference"]
        clubs_lux_hist = cr["club_history_luxury"]
        clubs_std_hist = cr["club_history_standard"]
        std_proj = cr["club_standard_proj_fy30"]
        # FY30E = average across scenarios (visual summary, since 4 scenarios into 1 bar)
        luxury_avg = sum(data["scenarios"][k]["chart_data"]["luxury_club_count_fy30"]
                         for k in SCEN_ORDER) / 4
        BULL = COLORS["bull"]
        years = ["FY23", "FY24", "FY25", "FY30E"]
        y_pos = list(range(4))
        bar_h = 0.55
        for i in range(3):
            ax.barh(y_pos[i], clubs_lux_hist[i], height=bar_h, color=BULL, alpha=1.0, zorder=2)
            ax.barh(y_pos[i], clubs_std_hist[i], height=bar_h, left=clubs_lux_hist[i],
                    color=ACCENT_SOFT, alpha=1.0, zorder=2)
        ax.barh(y_pos[3], luxury_avg, height=bar_h, color=BULL, alpha=0.55, zorder=2)
        ax.barh(y_pos[3], std_proj, height=bar_h, left=luxury_avg,
                color=ACCENT_SOFT, alpha=0.55, zorder=2)
        for i in range(3):
            ax.text(clubs_lux_hist[i] / 2, y_pos[i], f"{clubs_lux_hist[i]}",
                    ha="center", va="center", color="white", fontsize=7.5, fontweight="medium")
            ax.text(clubs_lux_hist[i] + clubs_std_hist[i] / 2, y_pos[i],
                    f"{clubs_std_hist[i]}",
                    ha="center", va="center", color="white", fontsize=7.5)
        ax.text(luxury_avg / 2, y_pos[3], f"{int(luxury_avg)}",
                ha="center", va="center", color="white", fontsize=7.5, fontweight="medium")
        ax.text(luxury_avg + std_proj / 2, y_pos[3], f"{std_proj}",
                ha="center", va="center", color="white", fontsize=7.5)
        ax.set_yticks(y_pos); ax.set_yticklabels(years, fontsize=9, color=TEXT)
        ax.set_xlim(0, 260); ax.set_xticks([])
        ax.spines["bottom"].set_visible(False); ax.spines["left"].set_color(MUTED)
        ax.tick_params(colors=MUTED, length=0)
        ax.set_title("Club count by format — Luxury vs Standard",
                     fontsize=9, color=INK, loc="left", pad=8, fontweight="semibold")
        fig.text(0.20, 0.04,
                 "FY30E: scenario average. Luxury clubs are the growth engine; +5-13 added per year.",
                 fontsize=6.5, color=MUTED, ha="left")
        fig.text(0.55, 0.95, "Luxury", color=BULL, fontsize=7, ha="left", fontweight="medium")
        fig.text(0.70, 0.95, "Standard", color=ACCENT_SOFT, fontsize=7, ha="left", fontweight="medium")
        savename = "06_clubs.png"
    else:  # zm SOTP decomposition (operating EV + cash + Anthropic stake)
        fig.subplots_adjust(left=0.10, right=0.95, top=0.84, bottom=0.18)
        rows = []
        for k in SCEN_ORDER:
            sc = data["scenarios"][k]
            opev = sc["dcf_path"]["op_ev"]; cash = sc["dcf_path"]["cash"]
            anth = sc["dcf_path"].get("special_assets", 0)
            rows.append((sc["short_label"], opev, cash, anth, COLORS[k]))
        y_pos = [3.5, 2.5, 1.5, 0.5]
        for i, (lbl, opev, cash, anth, color) in enumerate(rows):
            ax.barh(y_pos[i], opev, color=color, height=0.6, alpha=0.9,
                    label="Op EV" if i == 0 else "")
            ax.barh(y_pos[i], cash, left=opev, color=MUTED, height=0.6, alpha=0.6,
                    label="Cash & inv" if i == 0 else "")
            ax.barh(y_pos[i], anth, left=opev + cash, color=INK, height=0.6, alpha=0.7,
                    label="Anthropic stake" if i == 0 else "")
            ax.text(opev / 2, y_pos[i], f"${opev:.1f}B", color="white", fontsize=7,
                    ha="center", va="center", fontweight="bold")
            ax.text(opev + cash / 2, y_pos[i], f"${cash:.1f}B", color="white",
                    fontsize=7, ha="center", va="center")
            ax.text(opev + cash + anth / 2, y_pos[i], f"${anth:.1f}B",
                    color="white", fontsize=7, ha="center", va="center")
            ax.text(opev + cash + anth + 1, y_pos[i], f"${opev + cash + anth:.1f}B",
                    color=INK, fontsize=8, va="center", fontweight="bold")
        ax.set_yticks(y_pos)
        ax.set_yticklabels([r[0] for r in rows])
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"${x:.0f}B"))
        ax.legend(loc="lower right", fontsize=7, frameon=False)
        ax.set_xlim(0, max(r[1] + r[2] + r[3] for r in rows) * 1.15)
        style_ax(ax)
        ax.set_title("Equity value decomposition (SOTP) by scenario",
                     fontsize=9, color=INK, loc="left", pad=8, fontweight="semibold")
        savename = "06_sotp.png"

    plt.savefig(f"{out}/{savename}", dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close()


def main():
    ticker = parse_args()
    cfg = CONFIG[ticker]
    data = load(ticker)
    # Per-scenario revenue-growth rates (Mature stores growth, not absolute $B).
    scn_growth = {k: data["scenarios"][k]["dcf_path"]["rev_path"] for k in SCEN_ORDER}
    out = REPO / "charts" / ticker
    out.mkdir(parents=True, exist_ok=True)
    chart_revenue(data, cfg, scn_growth, str(out))
    chart_segments(data, cfg, scn_growth, ticker, str(out))
    chart_margins(data, cfg, scn_growth, ticker, str(out))
    chart_balance(data, cfg, scn_growth, ticker, str(out))
    chart_ev_multiples(data, cfg, ticker, str(out))
    chart_terminal(data, cfg, ticker, str(out))
    print(f"{ticker}: 6 charts -> {out.relative_to(REPO)}/")


if __name__ == "__main__":
    main()
