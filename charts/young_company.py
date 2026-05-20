"""charts/young_company.py — Page 3 business-snapshot charts for
Young-Company DCF tickers (JOBY, AUR; spec §7 Variant B).

Replaces build_joby_charts.py + build_aur_charts.py. Scenario/market data
is read from data/<ticker>.yml; per-ticker chart-only historical reference
series and labels live in CONFIG below (chart aesthetic data, not memo
content — kept here to avoid bloating the canonical YAML).

Emits 6 PNGs into charts/<ticker>/ in the slot order memo.py expects:
  01_revenue · 02_path_to_profit · 03_cash_dilution
  04_fleet   · 05_valuation       · 06_tam

Usage:
    python charts/young_company.py <ticker>     # ticker in {joby, aur}
"""
import math
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
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
FY_PROJ = ["FY27", "FY28", "FY29", "FY30", "FY31", "FY32", "FY33", "FY34", "FY35", "FY36"]

# ── Per-ticker chart-only config (historical reference series + labels) ─────
CONFIG = {
    "joby": {
        "fy_hist":           ["FY24", "FY25", "FY26"],
        "rev_history":       [0.000136, 0.053, 0.110],  # $B
        "cash_history":      [1.10, 1.40, 2.50],
        "shares_history":    [710, 800, 984],
        "fleet_history":     [1, 2, 5],
        "fleet_anchor":      5,
        "fleet_chart_title": "eVTOL aircraft deployed (log scale)",
        "peer_text":         "Aerospace + operator peer median ~15%",
        "peer_y":            15,
        "valn_anchor_text":  "Mature aerospace P/S ~2-4×",
        "valn_anchor_y":     3,
        "valn_caption":      ("Bear=very stretched (6.9×), base=full (1.5×), "
                              "bull/ultbull=cheap (0.5×/0.3×)."),
        "tam_title":         "$250B global UAM TAM (FY36) — Joby's share by scenario",
        "tam_legend":        ("JOBY", "Competitors", "Other UAM (cargo, etc.)"),
        "fleet_reference":   None,
        "rev_zero_label":    "$0",   # FY24 ≈ $136K → label as $0 on log axis
    },
    "aur": {
        "fy_hist":           ["FY24", "FY25", "FY26"],
        "rev_history":       [0.000, 0.003, 0.004],
        "cash_history":      [1.22, 1.45, 1.28],
        "shares_history":    [1733, 1943, 1956],
        "fleet_history":     [6, 20, 50],
        "fleet_anchor":      50,
        "fleet_chart_title": "Driverless trucks deployed (log scale)",
        "peer_text":         "Mature tech-auto peer median ~20%",
        "peer_y":            20,
        "valn_anchor_text":  "Mature peer P/S ~3-5×",
        "valn_anchor_y":     4,
        "valn_caption":      ("Bear=stretched (6×), base=fair (1.3×), "
                              "bull/ultbull=cheap (0.4×/0.4×)."),
        "tam_title":         "$160B US autonomous trucking TAM (FY36) — Aurora's share by scenario",
        "tam_legend":        ("AUR", "Competitors", "Non-autonomous (legacy)"),
        "fleet_reference":   {"value": 750000, "label": "US Class 8 long-haul fleet ~750K"},
        "rev_zero_label":    "$0",
    },
}

SCEN_ORDER = ["bear", "base", "bull", "ultra_bull"]


def parse_args():
    if len(sys.argv) != 2 or sys.argv[1].lower() not in CONFIG:
        print(f"usage: python charts/young_company.py <{'|'.join(CONFIG)}>",
              file=sys.stderr)
        sys.exit(2)
    return sys.argv[1].lower()


def load(ticker):
    d = yaml.safe_load((REPO / "data" / f"{ticker}.yml").read_text())
    assert d["dcf_type"] == "young_company", \
        f"{ticker}: dcf_type={d['dcf_type']}, expected young_company"
    rpu_key = "rev_per_aircraft" if ticker == "joby" else "rev_per_truck"
    scenarios = {}
    for k in SCEN_ORDER:
        s = d["scenarios"][k]
        scenarios[k] = {
            "rev":       s["dcf_path"]["rev_path"],     # 10 absolute $B
            "op_margin": s["dcf_path"]["op_margin"],     # decimal
            "wacc":      s["dcf_path"]["wacc_path"],
            "raises":    s["chart_data"]["raises"],
            "price":     s["chart_data"]["raise_prices"],
            "s2c":       s["dcf_metrics"]["s2c"],
            "mature_share":         s["dcf_metrics"]["tam_share"] / 100,
            "rev_per_unit":         s["chart_data"][rpu_key],
            "tam_competitor_share": s["chart_data"]["tam_competitor_share"],
            "color":     COLORS[k],
            "label":     s["short_label"],
        }
    return d, scenarios


def style_ax(ax):
    ax.spines["left"].set_color(MUTED)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(colors=MUTED)
    ax.grid(axis="y", color=RULE, linewidth=0.4, zorder=0)
    ax.set_axisbelow(True)


def today_marker(ax, x):
    ax.axvline(x, color=DIM, linewidth=0.4, linestyle=":", zorder=1)


# ─── Chart 1 — Revenue ramp (log scale) ──────────────────────────────────────
def chart_revenue(scn, cfg, out):
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.13, right=0.93, top=0.84, bottom=0.18)

    fy_all = cfg["fy_hist"] + FY_PROJ
    fy_short = [s[2:] for s in fy_all]
    n_hist = len(cfg["fy_hist"])
    rev_hist_plot = [max(r, 0.001) for r in cfg["rev_history"]]

    ax.plot(range(n_hist), rev_hist_plot, color=ACCENT, marker="o", markersize=4,
            linewidth=1.6, zorder=3, markerfacecolor=ACCENT, markeredgecolor="white")
    if cfg["rev_history"][0] < 0.001:
        ax.text(0, 0.0008, cfg["rev_zero_label"], fontsize=6.5, color=MUTED,
                ha="center", va="top")

    x_proj = list(range(n_hist - 1, n_hist + 10))
    for k in SCEN_ORDER:
        s = scn[k]
        rev_p = [cfg["rev_history"][-1]] + s["rev"]
        ax.plot(x_proj, rev_p, color=s["color"], linewidth=1.4, linestyle="--",
                marker="o", markersize=2.5, markerfacecolor=s["color"],
                markeredgecolor="white", markeredgewidth=0.5, zorder=3)
        ax.text(x_proj[-1] + 0.15, s["rev"][-1], f'{s["label"]} {s["rev"][-1]:.0f}',
                color=s["color"], fontsize=7, va="center", ha="left", fontweight="medium")

    today_marker(ax, n_hist - 0.5)
    ax.set_yscale("log")
    ax.set_ylim(0.0005, 80)
    ax.set_yticks([0.001, 0.01, 0.1, 1, 10])
    ax.set_yticklabels(["$1M", "$10M", "$100M", "$1B", "$10B"])
    ax.set_xticks(range(len(fy_all)))
    ax.set_xticklabels(fy_short, fontsize=7)
    ax.set_xlim(-0.5, len(fy_all) + 1.6)
    style_ax(ax)
    ax.set_title("Revenue ($, log scale) — history + scenarios to FY36",
                 fontsize=9, color=INK, loc="left", pad=8, fontweight="semibold")
    plt.savefig(f"{out}/01_revenue.png", dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close()


# ─── Chart 2 — Path to profitability (operating margin) ──────────────────────
def chart_path_to_profitability(scn, cfg, out):
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.13, right=0.93, top=0.84, bottom=0.18)

    ax.axhline(0, color=DIM, linewidth=0.5, linestyle="-", zorder=1, alpha=0.5)
    ax.axhline(cfg["peer_y"], color=ACCENT_SOFT, linewidth=0.4, linestyle=":", zorder=1)
    # JOBY drew peer text near the bottom; AUR near the top. Match per-ticker.
    peer_y_label = -95 if cfg["peer_y"] == 15 else cfg["peer_y"] + 2
    ax.text(0.5, peer_y_label, cfg["peer_text"], fontsize=6.5, color=MUTED, ha="left")

    x = list(range(10))
    for k in SCEN_ORDER:
        s = scn[k]
        margins = [max(m * 100, -100) for m in s["op_margin"]]
        ax.plot(x, margins, color=s["color"], linewidth=1.5,
                marker="o", markersize=3, markerfacecolor=s["color"],
                markeredgecolor="white", markeredgewidth=0.5, zorder=3)
        ax.text(9 + 0.15, s["op_margin"][-1] * 100,
                f'{s["label"]} {s["op_margin"][-1] * 100:.0f}%',
                color=s["color"], fontsize=7, va="center", ha="left", fontweight="medium")

    ax.set_xticks(x)
    ax.set_xticklabels([s[2:] for s in FY_PROJ], fontsize=7)
    ax.set_xlim(-0.4, 10.8)
    ax.set_ylim(-110, 50)
    ax.set_yticks([-100, -80, -60, -40, -20, 0, 20, 40])
    ax.set_yticklabels([f"{v}%" for v in [-100, -80, -60, -40, -20, 0, 20, 40]])
    style_ax(ax)
    ax.set_title("Path to profitability — operating margin (FY27→FY36)",
                 fontsize=9, color=INK, loc="left", pad=8, fontweight="semibold")
    plt.savefig(f"{out}/02_path_to_profit.png", dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close()


# ─── Chart 3 — Cash runway + dilution (dual axis) ────────────────────────────
def _cash_path(s, cfg):
    cash = cfg["cash_history"][-1]
    prev_rev = cfg["rev_history"][-1]
    out = [cash]
    for i in range(10):
        rev = s["rev"][i]
        delta = rev - prev_rev
        nopat = rev * s["op_margin"][i]   # no tax (NOLs)
        reinv = delta / s["s2c"]
        fcf = nopat - reinv
        cash = cash + s["raises"][i] + fcf
        out.append(cash)
        prev_rev = rev
    return out


def _shares_path(s, cfg):
    shares = cfg["shares_history"][-1]
    out = [shares]
    for i in range(10):
        new = (s["raises"][i] * 1000 / s["price"][i]) if s["price"][i] > 0 else 0
        shares += new
        out.append(shares)
    return out


def chart_cash_dilution(scn, cfg, out):
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.12, right=0.85, top=0.84, bottom=0.18)
    x = list(range(11))

    for k in SCEN_ORDER:
        s = scn[k]
        ax.plot(x, _cash_path(s, cfg), color=s["color"], linewidth=1.5,
                linestyle="--", marker="o", markersize=2.5, markerfacecolor=s["color"],
                markeredgecolor="white", markeredgewidth=0.5, zorder=3)

    style_ax(ax)
    ax.set_ylim(0, 5)
    ax.set_yticks([0, 1, 2, 3, 4, 5])
    ax.set_yticklabels(["$0", "$1B", "$2B", "$3B", "$4B", "$5B"])
    ax.set_ylabel("Cash + investments", fontsize=7.5, color=ACCENT, labelpad=4)

    ax2 = ax.twinx()
    for k in SCEN_ORDER:
        s = scn[k]
        ax2.plot(x, _shares_path(s, cfg), color=s["color"], linewidth=1.0,
                 linestyle=":", marker="s", markersize=2, markerfacecolor=s["color"],
                 markeredgecolor="white", markeredgewidth=0.4, zorder=2, alpha=0.75)
    # Right-axis range follows shares history scale (joby ~900-1500, aur ~1800-3600)
    sh = cfg["shares_history"][-1]
    if sh < 1500:
        ax2.set_ylim(900, 1600); ax2.set_yticks([900, 1100, 1300, 1500])
        ax2.set_yticklabels(["900M", "1.1K", "1.3K", "1.5K"])
    else:
        ax2.set_ylim(1800, 3600); ax2.set_yticks([1800, 2200, 2600, 3000, 3400])
        ax2.set_yticklabels(["1.8K", "2.2K", "2.6K", "3.0K", "3.4K"])
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_color(MUTED)
    ax2.spines["left"].set_visible(False)
    ax2.tick_params(colors=MUTED, axis="y")
    ax2.set_ylabel("Shares (M, dotted)", fontsize=7.5, color=INK, labelpad=4)

    today_marker(ax, 0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(["26"] + [s[2:] for s in FY_PROJ], fontsize=7)
    ax.set_xlim(-0.4, 10.4)
    ax.set_title("Cash runway + dilution (FY26→FY36)", fontsize=9,
                 color=INK, loc="left", pad=8, fontweight="semibold")
    plt.savefig(f"{out}/03_cash_dilution.png", dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close()


# ─── Chart 4 — Fleet/unit growth (log scale) ─────────────────────────────────
def chart_fleet(scn, cfg, out):
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.13, right=0.93, top=0.84, bottom=0.18)

    def fleet_from_rev(rev_path, rpu_path):
        # rev[i] $B; rev_per_unit $M or $K — both produce unit count via div.
        return [(r * 1000) / p for r, p in zip(rev_path, rpu_path)]

    ax.plot([0, 1, 2], cfg["fleet_history"], color=ACCENT, linewidth=1.8,
            marker="o", markersize=4, markerfacecolor=ACCENT,
            markeredgecolor="white", markeredgewidth=0.6, zorder=3)

    x_proj = list(range(2, 13))
    for k in SCEN_ORDER:
        s = scn[k]
        fleet = fleet_from_rev(s["rev"], s["rev_per_unit"])
        # AUR's rev_per_unit is $K/year → values are unit counts;
        # JOBY's rev_per_aircraft is $M/year → divide gives different magnitude.
        # Both per-ticker builders used the same formula (rev * 1000 / rpu) and
        # produced visually comparable trajectories.
        ax.plot(x_proj, [cfg["fleet_anchor"]] + fleet, color=s["color"], linewidth=1.4,
                linestyle="--", marker="o", markersize=2.5, markerfacecolor=s["color"],
                markeredgecolor="white", markeredgewidth=0.5, zorder=3)
        end = fleet[-1]
        if end >= 10000:
            unit = f"{end / 1000:.0f}K"
        elif end >= 1000:
            unit = f"{end / 1000:.1f}K"
        else:
            unit = f"{end:.0f}"
        ax.text(x_proj[-1] + 0.15, end, f'{s["label"]} {unit}', color=s["color"],
                fontsize=7, va="center", ha="left", fontweight="medium")

    if cfg["fleet_reference"]:
        ref = cfg["fleet_reference"]
        ax.axhline(ref["value"], color=DIM, linewidth=0.4, linestyle=":", zorder=1)
        ax.text(12.5, ref["value"] * 1.07, ref["label"],
                fontsize=6, color=MUTED, ha="right")

    today_marker(ax, 2.5)
    ax.set_yscale("log")
    # JOBY range: 0.5..10000; AUR range: 1..2M (for the ref line).
    if cfg["fleet_reference"]:
        ax.set_ylim(1, 2_000_000)
        ax.set_yticks([10, 100, 1000, 10000, 100000, 1000000])
        ax.set_yticklabels(["10", "100", "1K", "10K", "100K", "1M"])
    else:
        ax.set_ylim(0.5, 10000)
        ax.set_yticks([1, 10, 100, 1000, 10000])
        ax.set_yticklabels(["1", "10", "100", "1K", "10K"])

    fy_all = cfg["fy_hist"] + FY_PROJ
    ax.set_xticks(range(13))
    ax.set_xticklabels([s[2:] for s in fy_all], fontsize=7)
    ax.set_xlim(-0.5, 13.6)
    style_ax(ax)
    ax.set_title(cfg["fleet_chart_title"], fontsize=9, color=INK, loc="left",
                 pad=8, fontweight="semibold")
    plt.savefig(f"{out}/04_fleet.png", dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close()


# ─── Chart 5 — Valuation: today's mkt cap ÷ year-10 revenue ─────────────────
def chart_valuation(scn, cfg, data, out):
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.13, right=0.93, top=0.84, bottom=0.28)
    mkt_cap = data["market"]["market_cap_billion"]

    labels = ["Bear FY36", "Base FY36", "Bull FY36", "UltBull FY36"]
    multiples = [mkt_cap / scn[k]["rev"][-1] for k in SCEN_ORDER]
    colors = [scn[k]["color"] for k in SCEN_ORDER]
    bars = ax.bar(labels, multiples, color=colors, width=0.55, zorder=2)
    for i, m in enumerate(multiples):
        ax.text(i, m + 0.15, f"{m:.1f}×", ha="center", va="bottom",
                fontsize=9, color=colors[i], fontweight="semibold")

    ax.axhline(cfg["valn_anchor_y"], color=DIM, linewidth=0.5, linestyle=":", zorder=1)
    ax.text(2.55, cfg["valn_anchor_y"] + 0.2, cfg["valn_anchor_text"],
            fontsize=6.5, color=MUTED, ha="right")

    style_ax(ax)
    ax.set_ylim(0, max(9, max(multiples) * 1.2))
    ax.set_yticks([0, 2, 4, 6, 8])
    ax.set_yticklabels(["0×", "2×", "4×", "6×", "8×"])
    ax.tick_params(axis="x", labelsize=7)
    ax.set_title(f"Today's ${mkt_cap:g}B mkt cap as P/S on FY36 revenue",
                 fontsize=8.5, color=INK, loc="left", pad=8, fontweight="semibold")
    fig.text(0.13, 0.05, cfg["valn_caption"], fontsize=6.5, color=MUTED, ha="left")
    plt.savefig(f"{out}/05_valuation.png", dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close()


# ─── Chart 6 — TAM positioning at FY36 ───────────────────────────────────────
def chart_tam(scn, cfg, data, out):
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.13, right=0.93, top=0.84, bottom=0.20)

    tam = data["chart_reference"]["tam_billion"]
    short_pct = []
    company_share = []
    competitor_share = []
    for k in SCEN_ORDER:
        s = scn[k]
        short_pct.append(f"{s['label']}\n{s['mature_share'] * 100:.1f}%")
        company_share.append(s["rev"][-1])
        competitor_share.append(s["tam_competitor_share"])
    remaining = [tam - a - b for a, b in zip(company_share, competitor_share)]

    y_pos = [0, 1, 2, 3]
    bar_h = 0.55
    colors = [scn[k]["color"] for k in SCEN_ORDER]
    for i in range(4):
        ax.barh(y_pos[i], company_share[i], height=bar_h, color=colors[i], zorder=2)
        ax.barh(y_pos[i], competitor_share[i], height=bar_h, left=company_share[i],
                color=ACCENT_SOFT, zorder=2)
        ax.barh(y_pos[i], remaining[i], height=bar_h,
                left=company_share[i] + competitor_share[i],
                color=DIM, zorder=2, alpha=0.5)

    for i in range(4):
        if company_share[i] > 10:
            ax.text(company_share[i] / 2, y_pos[i], f"${company_share[i]:.0f}B",
                    ha="center", va="center", color="white", fontsize=7.5,
                    fontweight="medium")
        ax.text(company_share[i] + competitor_share[i] / 2, y_pos[i],
                f"${competitor_share[i]:.0f}B",
                ha="center", va="center", color="white", fontsize=7, alpha=0.9)
        if remaining[i] > (40 if tam >= 200 else 30):
            ax.text(company_share[i] + competitor_share[i] + remaining[i] / 2, y_pos[i],
                    f"${remaining[i]:.0f}B",
                    ha="center", va="center", color="white", fontsize=7, alpha=0.9)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(short_pct, fontsize=8, color=TEXT)
    # X-axis range adapts to TAM (JOBY 250, AUR 160).
    ax.set_xlim(0, tam + (tam * 0.04))
    if tam >= 200:
        ticks = [0, 50, 100, 150, 200, 250]
    else:
        ticks = [0, 40, 80, 120, 160]
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"${v}B" for v in ticks], fontsize=7.5)
    ax.spines["bottom"].set_color(MUTED)
    ax.spines["left"].set_visible(False)
    ax.tick_params(colors=MUTED, length=0)
    ax.set_title(cfg["tam_title"], fontsize=8.5, color=INK,
                 loc="left", pad=8, fontweight="semibold")

    leg_a, leg_b, leg_c = cfg["tam_legend"]
    fig.text(0.13, 0.03, leg_a, color=ACCENT, fontsize=7, fontweight="medium")
    fig.text(0.22, 0.03, leg_b, color=ACCENT_SOFT, fontsize=7)
    fig.text(0.42, 0.03, leg_c, color=DIM, fontsize=7)
    plt.savefig(f"{out}/06_tam.png", dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close()


def main():
    ticker = parse_args()
    cfg = CONFIG[ticker]
    data, scn = load(ticker)
    out = REPO / "charts" / ticker
    out.mkdir(parents=True, exist_ok=True)
    chart_revenue(scn, cfg, str(out))
    chart_path_to_profitability(scn, cfg, str(out))
    chart_cash_dilution(scn, cfg, str(out))
    chart_fleet(scn, cfg, str(out))
    chart_valuation(scn, cfg, data, str(out))
    chart_tam(scn, cfg, data, str(out))
    print(f"{ticker}: 6 charts -> {out.relative_to(REPO)}/")


if __name__ == "__main__":
    main()
