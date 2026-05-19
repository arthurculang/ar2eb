"""
$AUR Business Snapshot — chart generator
Variant B (young-company) charts per tearsheet-spec__v002 §7.

Six charts:
  1. Revenue ramp (log scale) — history + 3 scenario projections to FY36
  2. Path to profitability — operating margin evolution chart (the single most important chart)
  3. Cash runway + dilution — cumulative cash vs share count
  4. Fleet/unit growth — driverless truck deployment trajectory
  5. Valuation multiples — Market Cap / Year-10 Revenue
  6. TAM positioning — scenario-specific share of $160B US TAM at FY36

Design system: Inter, indigo accent, semantic red/green, no chartjunk.
Canonical source: aur-dcf-valuation__v001__2026-05-16_18-30.jsx
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path

FONT_DIR = str(Path(__file__).parent.parent / 'public' / 'assets' / 'fonts')
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
ULTRA_BULL = '#7629a6'  # Deep purple per spec §6c.11

OUT = str(Path(__file__).parent.parent / 'charts' / 'aur')
Path(OUT).mkdir(parents=True, exist_ok=True)

FIG_W, FIG_H = 3.5, 2.4
DPI = 200

# ── Data mirror from aur-dcf-valuation__v001 ───────────────────────────────
fy_hist = ['FY24', 'FY25', 'FY26']
fy_proj = ['FY27','FY28','FY29','FY30','FY31','FY32','FY33','FY34','FY35','FY36']
fy_all = fy_hist + fy_proj
fy_short = [s[2:] for s in fy_all]

# Historical (annual)
rev_hist = [0.000, 0.003, 0.004]  # $B
cash_hist = [1.22, 1.45, 1.28]    # FY24-FY26 cash + investments
shares_hist = [1733, 1943, 1956]  # M shares
op_margin_hist = [None, -300.0, -200.0]  # crude approximation; FY25 had $-901M op loss on $3M rev

SCENARIOS = {
    'bear': {
        'rev':       [0.015, 0.040, 0.080, 0.150, 0.300, 0.600, 1.000, 1.500, 2.000, 2.500],
        'op_margin': [-8.0, -4.0, -2.0, -1.0, -0.50, -0.20, -0.10, 0.00, 0.05, 0.08],
        'raises':    [0.50, 0.75, 0.75, 0.75, 0.75, 0.50, 0.25, 0.00, 0.00, 0.00],
        'price':     [5.00, 4.00, 3.50, 3.00, 2.50, 2.00, 1.75, 0.00, 0.00, 0.00],
        's2c': 1.2,
        'wacc':      [0.140, 0.140, 0.135, 0.130, 0.125, 0.120, 0.115, 0.110, 0.105, 0.100],
        'mature_share': 0.015,
        'color': BEAR,
        'label': 'Bear',
    },
    'base': {
        'rev':       [0.030, 0.100, 0.250, 0.600, 1.200, 2.500, 4.500, 7.000, 9.500, 12.00],
        'op_margin': [-6.0, -2.5, -1.0, -0.40, -0.10, 0.05, 0.10, 0.15, 0.18, 0.20],
        'raises':    [0.50, 0.75, 1.00, 1.00, 0.75, 0.50, 0.00, 0.00, 0.00, 0.00],
        'price':     [7.00, 7.50, 8.00, 9.00, 10.00, 12.00, 0.00, 0.00, 0.00, 0.00],
        's2c': 1.5,
        'wacc':      [0.120, 0.120, 0.115, 0.110, 0.105, 0.100, 0.095, 0.090, 0.090, 0.085],
        'mature_share': 0.075,
        'color': BASE,
        'label': 'Base',
    },
    'bull': {
        'rev':       [0.040, 0.180, 0.500, 1.200, 2.500, 5.000, 10.00, 18.00, 27.00, 36.00],
        'op_margin': [-5.0, -1.5, -0.30, 0.05, 0.15, 0.22, 0.28, 0.32, 0.34, 0.35],
        'raises':    [0.30, 0.50, 0.75, 0.75, 0.50, 0.00, 0.00, 0.00, 0.00, 0.00],
        'price':     [9.00, 12.00, 15.00, 18.00, 22.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        's2c': 1.8,
        'wacc':      [0.110, 0.110, 0.105, 0.100, 0.095, 0.090, 0.085, 0.080, 0.080, 0.075],
        'mature_share': 0.225,
        'color': BULL,
        'label': 'Bull',
    },
    'ultra_bull': {
        # Per spec §6c.11 — tail-of-tails: dominant US autonomous + software-take-rate
        'rev':       [0.050, 0.250, 0.750, 1.800, 3.500, 6.500, 12.00, 22.00, 32.00, 42.00],
        'op_margin': [-4.0, -1.0, -0.10, 0.10, 0.20, 0.28, 0.34, 0.38, 0.40, 0.42],
        'raises':    [0.30, 0.50, 0.50, 0.50, 0.20, 0.00, 0.00, 0.00, 0.00, 0.00],
        'price':     [11.00, 16.00, 25.00, 40.00, 60.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        's2c': 2.0,
        'wacc':      [0.105, 0.100, 0.095, 0.090, 0.085, 0.080, 0.075, 0.070, 0.070, 0.065],
        'mature_share': 0.275,
        'color': ULTRA_BULL,
        'label': 'UltBull',
    },
}

def style_ax(ax):
    ax.spines['left'].set_color(MUTED)
    ax.spines['bottom'].set_color(MUTED)
    ax.tick_params(colors=MUTED)
    ax.grid(axis='y', color=RULE, linewidth=0.4, zorder=0)
    ax.set_axisbelow(True)

def today_marker(ax, x):
    ax.axvline(x, color=DIM, linewidth=0.4, linestyle=':', zorder=1)

# Compute derived series
def compute_cash_path(scn):
    cash = 1.28
    out = [cash]
    prev_rev = 0.004
    for i in range(10):
        rev = scn['rev'][i]
        delta = rev - prev_rev
        op_inc = rev * scn['op_margin'][i]
        nopat = op_inc  # no tax (NOLs)
        reinv = delta / scn['s2c']
        fcf = nopat - reinv
        cash = cash + scn['raises'][i] + fcf
        out.append(cash)
        prev_rev = rev
    return out

def compute_shares_path(scn):
    shares = 1956
    out = [shares]
    for i in range(10):
        new = (scn['raises'][i] * 1000 / scn['price'][i]) if scn['price'][i] > 0 else 0
        shares += new
        out.append(shares)
    return out

def compute_op_margin_path(scn):
    return [None, -300.0, -200.0] + [m*100 for m in scn['op_margin']]


# ── CHART 1: Revenue ramp (log scale) ──────────────────────────────────────
def chart_revenue():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.13, right=0.93, top=0.84, bottom=0.18)

    # Historical: bars are too small to show on log; use markers
    x_hist = list(range(len(fy_hist)))
    # Plot tiny historical revenue with markers, replacing $0 with 0.001 for visibility on log scale
    rev_hist_plot = [max(r, 0.001) for r in rev_hist]
    ax.plot(x_hist, rev_hist_plot, color=ACCENT, marker='o', markersize=4,
            linewidth=1.6, zorder=3, markerfacecolor=ACCENT, markeredgecolor='white')
    # Label "$0" for FY24
    ax.text(0, 0.0008, '$0', fontsize=6.5, color=MUTED, ha='center', va='top')

    # Projections
    x_proj = list(range(len(fy_hist)-1, len(fy_hist)+10))
    for key in ['bear', 'base', 'bull', 'ultra_bull']:
        scn = SCENARIOS[key]
        rev_p = [rev_hist[-1]] + scn['rev']
        ax.plot(x_proj, rev_p, color=scn['color'], linewidth=1.4,
                linestyle='--', marker='o', markersize=2.5,
                markerfacecolor=scn['color'], markeredgecolor='white',
                markeredgewidth=0.5, zorder=3)
        # Endpoint label
        ax.text(x_proj[-1] + 0.15, scn['rev'][-1], f'{scn["label"]} {scn["rev"][-1]:.0f}',
                color=scn['color'], fontsize=7, va='center', ha='left',
                fontweight='medium')

    today_marker(ax, len(fy_hist) - 0.5)

    ax.set_yscale('log')
    ax.set_ylim(0.0005, 80)
    ax.set_yticks([0.001, 0.01, 0.1, 1, 10])
    ax.set_yticklabels(['$1M', '$10M', '$100M', '$1B', '$10B'])

    ax.set_xticks(range(len(fy_all)))
    ax.set_xticklabels(fy_short, fontsize=7)
    ax.set_xlim(-0.5, len(fy_all) + 1.6)

    style_ax(ax)
    ax.set_title('Revenue ($, log scale) — history + scenarios to FY36',
                 fontsize=9, color=INK, loc='left', pad=8, fontweight='semibold')

    plt.savefig(f'{OUT}/01_revenue.png', dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()


# ── CHART 2: Path to profitability (operating margin evolution) ────────────
def chart_path_to_profitability():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.13, right=0.93, top=0.84, bottom=0.18)

    # Historical margins are huge negative (op loss vs tiny revenue). Don't plot them on this chart.
    # Focus on FY27 onwards. Use linear scale capped at -100% to +50%.

    # Reference: break-even line at 0
    ax.axhline(0, color=DIM, linewidth=0.5, linestyle='-', zorder=1, alpha=0.5)

    # Mature peer-set anchor at ~20% (right side)
    ax.axhline(20, color=ACCENT_SOFT, linewidth=0.4, linestyle=':', zorder=1)
    ax.text(0.5, 22, 'Mature tech-auto peer median ~20%',
            fontsize=6.5, color=MUTED, ha='left')

    x = list(range(10))
    for key in ['bear', 'base', 'bull', 'ultra_bull']:
        scn = SCENARIOS[key]
        # Clip to chart range
        margins = [max(m * 100, -100) for m in scn['op_margin']]
        ax.plot(x, margins, color=scn['color'], linewidth=1.5,
                marker='o', markersize=3, markerfacecolor=scn['color'],
                markeredgecolor='white', markeredgewidth=0.5, zorder=3)
        # Endpoint label
        ax.text(9 + 0.15, scn['op_margin'][-1]*100, f'{scn["label"]} {scn["op_margin"][-1]*100:.0f}%',
                color=scn['color'], fontsize=7, va='center', ha='left',
                fontweight='medium')

    ax.set_xticks(x)
    ax.set_xticklabels([s[2:] for s in fy_proj], fontsize=7)
    ax.set_xlim(-0.4, 10.8)
    ax.set_ylim(-110, 50)
    ax.set_yticks([-100, -80, -60, -40, -20, 0, 20, 40])
    ax.set_yticklabels([f'{v}%' for v in [-100, -80, -60, -40, -20, 0, 20, 40]])

    style_ax(ax)
    ax.set_title('Path to profitability — operating margin (FY27→FY36)',
                 fontsize=9, color=INK, loc='left', pad=8, fontweight='semibold')

    plt.savefig(f'{OUT}/02_path_to_profit.png', dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()


# ── CHART 3: Cash runway + dilution (dual axis) ───────────────────────────
def chart_cash_dilution():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.12, right=0.85, top=0.84, bottom=0.18)

    x = list(range(11))  # FY26 + 10 years

    # Left axis: cash position ($B)
    for key in ['bear', 'base', 'bull', 'ultra_bull']:
        scn = SCENARIOS[key]
        cash = compute_cash_path(scn)
        ax.plot(x, cash, color=scn['color'], linewidth=1.5,
                linestyle='--', marker='o', markersize=2.5,
                markerfacecolor=scn['color'], markeredgecolor='white',
                markeredgewidth=0.5, zorder=3)

    style_ax(ax)
    ax.set_ylim(0, 5)
    ax.set_yticks([0, 1, 2, 3, 4, 5])
    ax.set_yticklabels(['$0', '$1B', '$2B', '$3B', '$4B', '$5B'])
    ax.set_ylabel('Cash + investments', fontsize=7.5, color=ACCENT, labelpad=4)

    # Right axis: share count (M)
    ax2 = ax.twinx()
    for key in ['bear', 'base', 'bull', 'ultra_bull']:
        scn = SCENARIOS[key]
        shares = compute_shares_path(scn)
        ax2.plot(x, shares, color=scn['color'], linewidth=1.0,
                 linestyle=':', marker='s', markersize=2,
                 markerfacecolor=scn['color'], markeredgecolor='white',
                 markeredgewidth=0.4, zorder=2, alpha=0.75)
        # No inline labels — they collide with right-axis ticks. Rely on color coding.

    ax2.set_ylim(1800, 3600)
    ax2.set_yticks([1800, 2200, 2600, 3000, 3400])
    ax2.set_yticklabels(['1.8K', '2.2K', '2.6K', '3.0K', '3.4K'])
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_color(MUTED)
    ax2.spines['left'].set_visible(False)
    ax2.tick_params(colors=MUTED, axis='y')
    ax2.set_ylabel('Shares (M, dotted)', fontsize=7.5, color=INK, labelpad=4)

    today_marker(ax, 0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(['26'] + [s[2:] for s in fy_proj], fontsize=7)
    ax.set_xlim(-0.4, 10.4)

    ax.set_title('Cash runway + dilution (FY26→FY36)', fontsize=9,
                 color=INK, loc='left', pad=8, fontweight='semibold')

    plt.savefig(f'{OUT}/03_cash_dilution.png', dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()


# ── CHART 4: Fleet/unit growth — driverless truck deployment ──────────────
def chart_fleet():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.13, right=0.93, top=0.84, bottom=0.18)

    # Inferred fleet trajectory from revenue paths.
    # rev in $B, rev per truck in $K → trucks (in thousands) = rev * 1000 / rev_per_truck = rev_$M / rpt_$K
    # Result is in thousands of trucks. Multiply by 1000 to get actual trucks.
    def fleet_from_rev(rev_path, rpt_path):
        # rev[i] is $B; rpt is $K per truck
        # trucks_i = (rev_i in $) / (rpt_i in $) = (rev_i * 1e9) / (rpt_i * 1e3)
        return [(r * 1e9) / (p * 1e3) for r, p in zip(rev_path, rpt_path)]

    rev_per_truck = {
        'bear': [100, 110, 120, 130, 140, 150, 155, 160, 160, 165],
        'base': [120, 135, 150, 165, 180, 195, 205, 215, 220, 225],
        'bull': [150, 175, 200, 225, 240, 250, 250, 250, 250, 250],
        'ultra_bull': [180, 210, 240, 260, 275, 280, 280, 280, 280, 280],
    }

    # Historical fleet (publicly stated): ~6 trucks EOY 2024, ~20 EOY 2025, ~50 EOY Q1 2026
    fleet_hist_x = [0, 1, 2]
    fleet_hist = [6, 20, 50]

    ax.plot(fleet_hist_x, fleet_hist, color=ACCENT, linewidth=1.8,
            marker='o', markersize=4, markerfacecolor=ACCENT,
            markeredgecolor='white', markeredgewidth=0.6, zorder=3)

    x_proj = list(range(2, 13))
    for key in ['bear', 'base', 'bull', 'ultra_bull']:
        scn = SCENARIOS[key]
        fleet = fleet_from_rev(scn['rev'], rev_per_truck[key])
        # Anchor projection at FY26 historical fleet of 50, connect to first projection
        ax.plot(x_proj, [50] + fleet, color=scn['color'], linewidth=1.4,
                linestyle='--', marker='o', markersize=2.5,
                markerfacecolor=scn['color'], markeredgecolor='white',
                markeredgewidth=0.5, zorder=3)
        # Endpoint label
        end = fleet[-1]
        if end >= 10000:
            unit = f'{end/1000:.0f}K'
        elif end >= 1000:
            unit = f'{end/1000:.1f}K'
        else:
            unit = f'{end:.0f}'
        ax.text(x_proj[-1] + 0.15, end, f'{scn["label"]} {unit}',
                color=scn['color'], fontsize=7, va='center', ha='left',
                fontweight='medium')

    # Reference line: total US Class 8 long-haul fleet ~750K trucks
    ax.axhline(750000, color=DIM, linewidth=0.4, linestyle=':', zorder=1)
    ax.text(12.5, 800000, 'US Class 8 long-haul fleet ~750K',
            fontsize=6, color=MUTED, ha='right')

    today_marker(ax, 2.5)

    ax.set_yscale('log')
    ax.set_ylim(1, 2000000)
    ax.set_yticks([10, 100, 1000, 10000, 100000, 1000000])
    ax.set_yticklabels(['10', '100', '1K', '10K', '100K', '1M'])

    ax.set_xticks(range(13))
    ax.set_xticklabels(fy_short, fontsize=7)
    ax.set_xlim(-0.5, 13.6)

    style_ax(ax)
    ax.set_title('Driverless trucks deployed (log scale)', fontsize=9,
                 color=INK, loc='left', pad=8, fontweight='semibold')

    plt.savefig(f'{OUT}/04_fleet.png', dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()


# ── CHART 5: Valuation — Market cap / Year-10 revenue ─────────────────────
def chart_valuation():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.13, right=0.93, top=0.84, bottom=0.28)

    scenarios = ['Bear FY36', 'Base FY36', 'Bull FY36', 'UltBull FY36']
    multiples = [15.1/2.5, 15.1/12, 15.1/36, 15.1/42]
    colors = [BEAR, BASE, BULL, ULTRA_BULL]

    bars = ax.bar(scenarios, multiples, color=colors, width=0.55, zorder=2)
    for i, m in enumerate(multiples):
        ax.text(i, m + 0.15, f'{m:.1f}×', ha='center', va='bottom',
                fontsize=9, color=colors[i], fontweight='semibold')

    ax.axhline(4, color=DIM, linewidth=0.5, linestyle=':', zorder=1)
    ax.text(2.55, 4.2, 'Mature peer P/S ~3-5×',
            fontsize=6.5, color=MUTED, ha='right')

    style_ax(ax)
    ax.set_ylim(0, 8)
    ax.set_yticks([0, 2, 4, 6, 8])
    ax.set_yticklabels(['0×', '2×', '4×', '6×', '8×'])
    ax.tick_params(axis='x', labelsize=7)
    ax.set_title('Today\'s $15.1B mkt cap as P/S on FY36 revenue',
                 fontsize=8.5, color=INK, loc='left', pad=8, fontweight='semibold')

    fig.text(0.13, 0.05,
             'Bear=stretched (6×), base=fair (1.3×), bull/ultbull=cheap (0.4×/0.4×).',
             fontsize=6.5, color=MUTED, ha='left')

    plt.savefig(f'{OUT}/05_valuation.png', dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()


# ── CHART 6: TAM positioning at FY36 ──────────────────────────────────────
def chart_tam():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.13, right=0.93, top=0.84, bottom=0.20)

    # Total TAM: $160B US autonomous trucking 2035 (McKinsey)
    # Show each scenario's AUR share + other players + remaining TAM
    tam = 160
    scenarios = ['Bear\n1.5%', 'Base\n7.5%', 'Bull\n22.5%', 'UltBull\n27.5%']
    aur_shares = [2.5, 12.0, 36.0, 44.0]  # AUR's revenue ($B) at FY36
    competitor_shares = [25.0, 35.0, 50.0, 55.0]  # Kodiak + PlusAI + Waabi + Others combined
    remaining = [tam - a - c for a, c in zip(aur_shares, competitor_shares)]

    y_pos = [0, 1, 2, 3]
    bar_h = 0.55

    # Stacked horizontal bars
    for i in range(4):
        ax.barh(y_pos[i], aur_shares[i], height=bar_h, color=[BEAR, BASE, BULL, ULTRA_BULL][i],
                zorder=2)
        ax.barh(y_pos[i], competitor_shares[i], height=bar_h, left=aur_shares[i],
                color=ACCENT_SOFT, zorder=2)
        ax.barh(y_pos[i], remaining[i], height=bar_h, left=aur_shares[i]+competitor_shares[i],
                color=DIM, zorder=2, alpha=0.5)

    # In-bar labels
    for i in range(4):
        # AUR share — value
        if aur_shares[i] > 6:
            ax.text(aur_shares[i]/2, y_pos[i], f'${aur_shares[i]:.0f}B',
                    ha='center', va='center', color='white', fontsize=7.5,
                    fontweight='medium')
        # Competitors
        ax.text(aur_shares[i] + competitor_shares[i]/2, y_pos[i], f'${competitor_shares[i]:.0f}B',
                ha='center', va='center', color='white', fontsize=7, alpha=0.9)
        # Non-autonomous
        if remaining[i] > 30:
            ax.text(aur_shares[i] + competitor_shares[i] + remaining[i]/2, y_pos[i],
                    f'${remaining[i]:.0f}B',
                    ha='center', va='center', color='white', fontsize=7, alpha=0.9)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(scenarios, fontsize=8, color=TEXT)
    ax.set_xlim(0, 165)
    ax.set_xticks([0, 40, 80, 120, 160])
    ax.set_xticklabels(['$0B', '$40B', '$80B', '$120B', '$160B'], fontsize=7.5)
    ax.spines['bottom'].set_color(MUTED)
    ax.spines['left'].set_visible(False)
    ax.tick_params(colors=MUTED, length=0)

    ax.set_title('$160B US autonomous trucking TAM (FY36) — Aurora\'s share by scenario',
                 fontsize=8.5, color=INK, loc='left', pad=8, fontweight='semibold')

    # Legend — shorter labels to prevent overlap
    fig.text(0.13, 0.03, 'AUR', color=ACCENT, fontsize=7, fontweight='medium')
    fig.text(0.20, 0.03, 'Competitors', color=ACCENT_SOFT, fontsize=7)
    fig.text(0.42, 0.03, 'Non-autonomous (legacy)', color=DIM, fontsize=7)

    plt.savefig(f'{OUT}/06_tam.png', dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()


if __name__ == '__main__':
    chart_revenue()
    chart_path_to_profitability()
    chart_cash_dilution()
    chart_fleet()
    chart_valuation()
    chart_tam()
    print('Charts generated:')
    for f in sorted(os.listdir(OUT)):
        print(' ', f)
