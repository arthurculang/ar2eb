"""
charts/young_company.py · v001 · 2026-05-18_08-00
Young-Company DCF chart builder (parameterized).

Usage:
    python charts/young_company.py <ticker>

Reads /data/<ticker>.yml. Produces 6 matplotlib charts at
/home/claude/<ticker>_charts/, matching the canonical Page 3 layout for
Damodaran young-company DCF tickers (JOBY, AUR).
"""

import os
import sys
import yaml
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path

# ── Font registration ──────────────────────────────────────────────────────
FONT_DIR = '/home/claude/fonts/ttf'
for f in os.listdir(FONT_DIR):
    if f.endswith('.ttf'):
        fm.fontManager.addfont(os.path.join(FONT_DIR, f))

plt.rcParams['font.family'] = 'Inter'
plt.rcParams['font.size'] = 9
plt.rcParams['axes.labelsize'] = 9
plt.rcParams['axes.titlesize'] = 10
plt.rcParams['xtick.labelsize'] = 8.5
plt.rcParams['ytick.labelsize'] = 8.5
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False
plt.rcParams['axes.linewidth'] = 0.5
plt.rcParams['xtick.major.width'] = 0.5
plt.rcParams['ytick.major.width'] = 0.5
plt.rcParams['xtick.major.size'] = 3
plt.rcParams['ytick.major.size'] = 3

# ── Palette ────────────────────────────────────────────────────────────────
INK = '#0a0a0a'
TEXT = '#1f2937'
MUTED = '#6b7280'
DIM = '#9ca3af'
RULE = '#e5e7eb'
ACCENT = '#1e3a8a'
ACCENT_SOFT = '#94a3b8'
BEAR = '#b91c1c'
BASE = '#1e3a8a'
BULL = '#15803d'
ULTRA_BULL = '#7629a6'
SCENARIO_COLORS = {'bear': BEAR, 'base': BASE, 'bull': BULL, 'ultra_bull': ULTRA_BULL}

FIG_W, FIG_H = 3.5, 2.4
DPI = 200

# ── Data loading ───────────────────────────────────────────────────────────
def parse_args():
    if len(sys.argv) != 2:
        print("Usage: python charts/young_company.py <ticker>", file=sys.stderr)
        sys.exit(1)
    return sys.argv[1].lower()

def load_data(ticker):
    data_dir = Path(__file__).parent.parent / "data"
    yml_path = data_dir / f"{ticker}.yml"
    if not yml_path.exists():
        yml_path = Path(__file__).parent / f"{ticker}.yml"
    if not yml_path.exists():
        raise FileNotFoundError(f"Data file not found for {ticker}")
    with open(yml_path) as f:
        return yaml.safe_load(f)

TICKER = parse_args()
DATA = load_data(TICKER)
assert DATA['dcf_type'] == 'young_company', \
    f"{TICKER} is {DATA['dcf_type']}; this builder is for young_company only"

OUT = f'/home/claude/{TICKER}_charts'
Path(OUT).mkdir(exist_ok=True)

# Pull reference data from YAML
CR = DATA['chart_reference']
fy_hist = CR['rev_history_years']
fy_proj = [f'FY{27+i}' for i in range(10)]
fy_all = fy_hist + fy_proj
fy_short = [s[2:] for s in fy_all]

rev_hist = CR['history_revenue']
cash_hist = CR['history_cash']
shares_hist = CR['history_shares']
op_margin_hist = CR['history_op_margin_pct']
fleet_hist = CR['history_fleet']
SPOT = DATA['spot']
MARKET_CAP = DATA['market']['market_cap_billion']
UNIT_LABEL = CR['unit_label']
TAM_BILLION = CR['tam_billion']
CHART5_TITLE = CR['chart5_title']
CHART5_CAPTION = CR['chart5_caption']
CHART6_TITLE = CR['chart6_title']
CHART6_LEGEND = CR['chart6_legend']
MATURE_PEER_ANCHOR_TEXT = CR['mature_peer_anchor_text']

# Build SCENARIOS dict from YAML scenarios
SCENARIOS = {}
for name, sc in DATA['scenarios'].items():
    SCENARIOS[name] = {
        'rev':       sc['dcf_path']['rev_path'],
        'op_margin': sc['dcf_path']['op_margin'],
        'raises':    sc['chart_data']['raises'],
        'price':     sc['chart_data']['raise_prices'],
        's2c':       sc['dcf_metrics']['s2c'],
        'wacc':      sc['dcf_path']['wacc_path'],
        'mature_share': sc['dcf_metrics']['tam_share'] / 100,
        'color':     SCENARIO_COLORS[name],
        'label':     sc['short_label'],
        'rev_per_unit': sc['chart_data']['rev_per_unit'],
        'tam_competitor_share': sc['chart_data']['tam_competitor_share'],
    }

# ── Helpers ────────────────────────────────────────────────────────────────
def style_ax(ax):
    for spine in ax.spines.values():
        spine.set_color(MUTED)
    ax.tick_params(colors=MUTED, length=3)
    ax.grid(False)
    ax.set_facecolor('white')

def today_marker(ax, x):
    ax.axvline(x, color=DIM, linewidth=0.4, linestyle=':', alpha=0.8, zorder=0)

def compute_cash_path(scn):
    cash = cash_hist[-1]
    path = []
    for i in range(10):
        cash += scn['raises'][i]
        burn = -scn['rev'][i] * scn['op_margin'][i]
        cash -= burn
        path.append(max(0, cash))
    return path

def compute_shares_path(scn):
    sh = shares_hist[-1]
    path = []
    for i in range(10):
        if scn['raises'][i] > 0 and scn['price'][i] > 0:
            sh += (scn['raises'][i] * 1000) / scn['price'][i]
        path.append(sh)
    return path

# ── CHART 1: Revenue ramp (log scale) ──────────────────────────────────────
def chart_revenue():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.16, right=0.95, top=0.85, bottom=0.18)
    x_hist = range(len(fy_hist))
    x_proj = range(len(fy_hist) - 1, len(fy_all))
    ax.plot(x_hist, rev_hist, color=ACCENT_SOFT, linewidth=1.5, marker='o',
            markersize=3.5, markerfacecolor=ACCENT_SOFT, markeredgecolor='white',
            markeredgewidth=0.5, zorder=3)
    for key in ['bear', 'base', 'bull', 'ultra_bull']:
        scn = SCENARIOS[key]
        proj = [rev_hist[-1]] + scn['rev']
        ax.plot(x_proj, proj, color=scn['color'], linewidth=1.0, linestyle='--',
                marker='o', markersize=2.5, markerfacecolor=scn['color'],
                markeredgecolor='white', markeredgewidth=0.4, alpha=0.95, zorder=2)
        endpoint = scn['rev'][-1]
        ax.annotate(f"{scn['label']} {endpoint:.0f}", xy=(x_proj[-1], endpoint),
                    xytext=(4, 0), textcoords='offset points', fontsize=7,
                    color=scn['color'], va='center', fontweight='semibold')
    today_marker(ax, len(fy_hist) - 1)
    ax.set_yscale('log')
    ax.set_ylim(0.0005, 100)
    ax.set_yticks([0.001, 0.01, 0.1, 1, 10])
    ax.set_yticklabels(['$1M', '$10M', '$100M', '$1B', '$10B'])
    ax.set_xticks(range(len(fy_all)))
    ax.set_xticklabels(fy_short, fontsize=7.5)
    style_ax(ax)
    ax.set_title('Revenue ($, log scale) — history + scenarios to FY36',
                 fontsize=9, color=INK, loc='left', pad=8, fontweight='semibold')
    plt.savefig(f'{OUT}/01_revenue.png', dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()

# ── CHART 2: Path to profitability ─────────────────────────────────────────
def chart_path_to_profitability():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.14, right=0.95, top=0.85, bottom=0.18)
    x_proj = list(range(10))
    for key in ['bear', 'base', 'bull', 'ultra_bull']:
        scn = SCENARIOS[key]
        margins_pct = [m * 100 for m in scn['op_margin']]
        ax.plot(x_proj, margins_pct, color=scn['color'], linewidth=1.0, linestyle='--',
                marker='o', markersize=2.5, markerfacecolor=scn['color'],
                markeredgecolor='white', markeredgewidth=0.4, alpha=0.95, zorder=2)
        endpoint_pct = margins_pct[-1]
        ax.annotate(f"{scn['label']} {endpoint_pct:.0f}%",
                    xy=(x_proj[-1], endpoint_pct), xytext=(4, 0),
                    textcoords='offset points', fontsize=7, color=scn['color'],
                    va='center', fontweight='semibold')
    ax.axhline(0, color=MUTED, linewidth=0.3, alpha=0.5)
    ax.axhline(15, color=DIM, linewidth=0.4, linestyle=':', alpha=0.8, zorder=0)
    ax.text(0.5, 13, 'Aerospace + operator peer median ~15%',
            fontsize=6.5, color=MUTED, ha='left')
    ax.set_xticks(range(10))
    ax.set_xticklabels([f"{27+i}" for i in range(10)], fontsize=7.5)
    ax.set_yticks([-100, -80, -60, -40, -20, 0, 20, 40])
    ax.set_yticklabels(['-100%', '-80%', '-60%', '-40%', '-20%', '0%', '20%', '40%'])
    ax.set_ylim(-110, 50)
    style_ax(ax)
    ax.set_title('Path to profitability — operating margin (FY27→FY36)',
                 fontsize=9, color=INK, loc='left', pad=8, fontweight='semibold')
    plt.savefig(f'{OUT}/02_path_to_profit.png', dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()

# ── CHART 3: Cash runway + dilution (dual y-axis) ──────────────────────────
def chart_cash_dilution():
    fig, ax1 = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.14, right=0.86, top=0.85, bottom=0.18)
    x_proj = list(range(11))
    for key in ['bear', 'base', 'bull', 'ultra_bull']:
        scn = SCENARIOS[key]
        cash_path = [cash_hist[-1]] + compute_cash_path(scn)
        ax1.plot(x_proj, cash_path, color=scn['color'], linewidth=1.0, linestyle='--',
                 marker='o', markersize=2.5, markerfacecolor=scn['color'],
                 markeredgecolor='white', markeredgewidth=0.4, alpha=0.95, zorder=2)
    ax1.set_ylabel('Cash + investments', color=ACCENT, fontsize=8, labelpad=2)
    ax1.tick_params(axis='y', colors=ACCENT)
    ax1.set_xticks(range(11))
    ax1.set_xticklabels(['26'] + [f"{27+i}" for i in range(10)], fontsize=7.5)
    ax1.set_yticks([0, 1, 2, 3, 4, 5])
    ax1.set_yticklabels(['$0', '$1B', '$2B', '$3B', '$4B', '$5B'])
    ax1.set_ylim(0, 5)
    ax2 = ax1.twinx()
    for key in ['bear', 'base', 'bull', 'ultra_bull']:
        scn = SCENARIOS[key]
        sh_path = [shares_hist[-1]] + compute_shares_path(scn)
        ax2.plot(x_proj, sh_path, color=scn['color'], linewidth=0.6, linestyle=':',
                 alpha=0.6, zorder=1)
    ax2.set_ylabel('Shares (M, dotted)', color=MUTED, fontsize=8, labelpad=2)
    ax2.tick_params(axis='y', colors=MUTED)
    style_ax(ax1)
    for spine in ax2.spines.values():
        spine.set_color(MUTED)
    ax2.spines['top'].set_visible(False)
    ax2.grid(False)
    ax1.set_title('Cash runway + dilution (FY26→FY36)', fontsize=9,
                  color=INK, loc='left', pad=8, fontweight='semibold')
    plt.savefig(f'{OUT}/03_cash_dilution.png', dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()

# ── CHART 4: Unit growth ───────────────────────────────────────────────────
def chart_fleet():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.16, right=0.95, top=0.85, bottom=0.18)
    def fleet_from_rev(rev_path, rev_per_unit_path):
        return [(r * 1000) / p for r, p in zip(rev_path, rev_per_unit_path)]

    if any(f > 0 for f in fleet_hist):
        x_hist_safe = list(range(len(fleet_hist)))
        ax.plot(x_hist_safe, fleet_hist, color=ACCENT_SOFT, linewidth=1.5,
                marker='o', markersize=3.5, markerfacecolor=ACCENT_SOFT,
                markeredgecolor='white', markeredgewidth=0.5, zorder=3)

    x_proj = list(range(len(fy_hist) - 1, len(fy_all)))
    for key in ['bear', 'base', 'bull', 'ultra_bull']:
        scn = SCENARIOS[key]
        fleet = fleet_from_rev(scn['rev'], scn['rev_per_unit'])
        anchor = fleet_hist[-1] if fleet_hist[-1] > 0 else 1
        proj = [anchor] + fleet
        ax.plot(x_proj, proj, color=scn['color'], linewidth=1.0, linestyle='--',
                marker='o', markersize=2.5, markerfacecolor=scn['color'],
                markeredgecolor='white', markeredgewidth=0.4, alpha=0.95, zorder=2)
        endpoint = fleet[-1]
        endpoint_str = f"{endpoint/1000:.1f}K" if endpoint >= 1000 else f"{endpoint:.0f}"
        ax.annotate(f"{scn['label']} {endpoint_str}",
                    xy=(x_proj[-1], endpoint), xytext=(4, 0),
                    textcoords='offset points', fontsize=7, color=scn['color'],
                    va='center', fontweight='semibold')
    today_marker(ax, len(fy_hist) - 1)
    ax.set_yscale('log')
    ax.set_ylim(1, 1_000_000)
    ax.set_yticks([1, 10, 100, 1000, 10000, 100000, 1000000])
    ax.set_yticklabels(['1', '10', '100', '1K', '10K', '100K', '1M'])
    ax.set_xticks(range(len(fy_all)))
    ax.set_xticklabels(fy_short, fontsize=7.5)
    style_ax(ax)
    ax.set_title(f'{UNIT_LABEL} deployed (log scale)',
                 fontsize=9, color=INK, loc='left', pad=8, fontweight='semibold')
    plt.savefig(f'{OUT}/04_fleet.png', dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()

# ── CHART 5: Valuation multiples ───────────────────────────────────────────
def chart_valuation():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.13, right=0.95, top=0.84, bottom=0.18)
    scenarios_data = []
    for name in ['bear', 'base', 'bull', 'ultra_bull']:
        scn = SCENARIOS[name]
        endpoint = scn['rev'][-1]
        multiple = MARKET_CAP / endpoint if endpoint > 0 else 0
        scenarios_data.append((f"{scn['label']} FY36", multiple, scn['color']))
    labels = [s[0] for s in scenarios_data]
    multiples = [s[1] for s in scenarios_data]
    colors = [s[2] for s in scenarios_data]
    bars = ax.bar(range(len(labels)), multiples, color=colors, width=0.55, zorder=2)
    for bar, mult in zip(bars, multiples):
        ax.text(bar.get_x() + bar.get_width()/2, mult + 0.15, f'{mult:.1f}×',
                ha='center', va='bottom', fontsize=8, color=INK)
    ax.text(2.55, 4.2, MATURE_PEER_ANCHOR_TEXT,
            fontsize=6.5, color=MUTED, ha='right')
    style_ax(ax)
    ax.set_ylim(0, 8)
    ax.set_yticks([0, 2, 4, 6, 8])
    ax.set_yticklabels(['0×', '2×', '4×', '6×', '8×'])
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=7.5)
    ax.set_title(CHART5_TITLE,
                 fontsize=9, color=INK, loc='left', pad=8, fontweight='semibold')
    fig.text(0.5, 0.02, CHART5_CAPTION,
             fontsize=6.5, color=MUTED, ha='center')
    plt.savefig(f'{OUT}/05_valuation.png', dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()

# ── CHART 6: TAM positioning (stacked horizontal bars) ─────────────────────
def chart_tam():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.18, right=0.95, top=0.83, bottom=0.20)
    tam = TAM_BILLION
    scenarios_text = []
    company_shares = []
    competitor_shares = []
    order = ['ultra_bull', 'bull', 'base', 'bear']
    for name in order:
        scn = SCENARIOS[name]
        share_pct = scn['mature_share'] * 100
        scenarios_text.append(f"{scn['label']}\n{share_pct:.1f}%")
        company_shares.append(scn['rev'][-1])
        competitor_shares.append(scn['tam_competitor_share'])
    remaining = [tam - a - c for a, c in zip(company_shares, competitor_shares)]
    y_pos = list(range(len(order) - 1, -1, -1))
    bar_h = 0.6
    bar_colors = [SCENARIO_COLORS[k] for k in order]
    for i in range(4):
        ax.barh(y_pos[i], company_shares[i], height=bar_h, color=bar_colors[i],
                edgecolor='white', linewidth=0.5)
        ax.barh(y_pos[i], competitor_shares[i], height=bar_h, left=company_shares[i],
                color=ACCENT_SOFT, edgecolor='white', linewidth=0.5)
        ax.barh(y_pos[i], remaining[i], height=bar_h,
                left=company_shares[i] + competitor_shares[i],
                color=RULE, edgecolor='white', linewidth=0.5)
    for i in range(4):
        if company_shares[i] > 10:
            ax.text(company_shares[i]/2, y_pos[i], f'${company_shares[i]:.0f}B',
                    ha='center', va='center', fontsize=6.5, color='white', fontweight='semibold')
        else:
            ax.text(company_shares[i] + 1, y_pos[i], f'${company_shares[i]:.0f}B',
                    ha='left', va='center', fontsize=6.5, color=bar_colors[i], fontweight='semibold')
        ax.text(company_shares[i] + competitor_shares[i]/2, y_pos[i],
                f'${competitor_shares[i]:.0f}B',
                ha='center', va='center', fontsize=6.5, color='white')
        ax.text(company_shares[i] + competitor_shares[i] + remaining[i]/2, y_pos[i],
                f'${remaining[i]:.0f}B',
                ha='center', va='center', fontsize=6.5, color=MUTED)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(scenarios_text, fontsize=7)
    if tam >= 200:
        ax.set_xticks([0, 50, 100, 150, 200, 250])
    else:
        ax.set_xticks([0, 40, 80, 120, 160])
    ax.set_xticklabels([f'${v}B' for v in ax.get_xticks()])
    ax.set_xlim(0, tam)
    style_ax(ax)
    ax.set_title(CHART6_TITLE,
                 fontsize=9, color=INK, loc='left', pad=8, fontweight='semibold')
    legend_text = f"{CHART6_LEGEND[0]}  ·  {CHART6_LEGEND[1]}  ·  {CHART6_LEGEND[2]}"
    fig.text(0.5, 0.04, legend_text, fontsize=6.5, color=MUTED, ha='center')
    plt.savefig(f'{OUT}/06_tam.png', dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()


if __name__ == '__main__':
    chart_revenue()
    chart_path_to_profitability()
    chart_cash_dilution()
    chart_fleet()
    chart_valuation()
    chart_tam()
    print(f"Charts generated for {TICKER.upper()} → {OUT}/")
