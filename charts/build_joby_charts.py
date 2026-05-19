"""
$JOBY Business Snapshot — chart generator
Variant B (young-company) charts per tearsheet-spec__v002 §7.

Six charts:
  1. Revenue ramp (log scale) — history + 3 scenario projections to FY36
  2. Path to profitability — operating margin evolution chart
  3. Cash runway + dilution — cumulative cash vs share count
  4. Fleet/unit growth — eVTOL aircraft deployment trajectory
  5. Valuation multiples — Market Cap / Year-10 Revenue
  6. TAM positioning — scenario-specific share of $250B global UAM TAM at FY36

Canonical source: joby-dcf-valuation__v001__2026-05-17_01-00.jsx
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

OUT = str(Path(__file__).parent.parent / 'charts' / 'joby')
Path(OUT).mkdir(parents=True, exist_ok=True)

FIG_W, FIG_H = 3.5, 2.4
DPI = 200

# ── Data mirror from aur-dcf-valuation__v001 ───────────────────────────────
fy_hist = ['FY24', 'FY25', 'FY26']
fy_proj = ['FY27','FY28','FY29','FY30','FY31','FY32','FY33','FY34','FY35','FY36']
fy_all = fy_hist + fy_proj
fy_short = [s[2:] for s in fy_all]

# Historical (annual)
rev_hist = [0.000136, 0.053, 0.110]  # $B; FY24 $136K, FY25 $53M, FY26 $110M guidance
cash_hist = [1.10, 1.40, 2.50]    # FY24-FY26 cash (post Feb 2026 raise)
shares_hist = [710, 800, 984]      # M shares
op_margin_hist = [None, -1750.0, -800.0]  # FY25 had ~$930M op loss on $53M rev

SCENARIOS = {
    'bear': {
        'rev':       [0.150, 0.250, 0.400, 0.600, 0.800, 0.950, 1.100, 1.250, 1.400, 1.500],
        'op_margin': [-3.0, -2.0, -1.2, -0.60, -0.20, 0.00, 0.02, 0.04, 0.05, 0.05],
        'raises':    [0.50, 0.75, 0.75, 0.50, 0.25, 0.00, 0.00, 0.00, 0.00, 0.00],
        'price':     [8.00, 6.50, 5.00, 4.00, 3.50, 0.00, 0.00, 0.00, 0.00, 0.00],
        's2c': 0.8,
        'wacc':      [0.140, 0.135, 0.130, 0.125, 0.120, 0.115, 0.110, 0.105, 0.100, 0.095],
        'mature_share': 0.006,
        'color': BEAR,
        'label': 'Bear',
    },
    'base': {
        'rev':       [0.180, 0.400, 0.900, 1.600, 2.500, 3.500, 4.500, 5.500, 6.300, 7.000],
        'op_margin': [-2.5, -1.2, -0.50, -0.10, 0.05, 0.08, 0.10, 0.12, 0.13, 0.13],
        'raises':    [0.50, 0.75, 1.00, 0.75, 0.50, 0.25, 0.00, 0.00, 0.00, 0.00],
        'price':     [10.00, 11.00, 12.00, 14.00, 16.00, 18.00, 0.00, 0.00, 0.00, 0.00],
        's2c': 1.2,
        'wacc':      [0.130, 0.125, 0.120, 0.115, 0.110, 0.105, 0.100, 0.095, 0.090, 0.085],
        'mature_share': 0.028,
        'color': BASE,
        'label': 'Base',
    },
    'bull': {
        'rev':       [0.200, 0.500, 1.200, 2.500, 4.500, 7.500, 11.00, 15.00, 18.00, 20.00],
        'op_margin': [-2.0, -0.80, -0.20, 0.05, 0.12, 0.18, 0.22, 0.25, 0.27, 0.28],
        'raises':    [0.30, 0.50, 0.75, 0.50, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        'price':     [12.00, 16.00, 22.00, 30.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        's2c': 1.6,
        'wacc':      [0.120, 0.115, 0.110, 0.105, 0.100, 0.095, 0.090, 0.085, 0.080, 0.075],
        'mature_share': 0.080,
        'color': BULL,
        'label': 'Bull',
    },
    'ultra_bull': {
        # Per spec §6c.11 — tail-of-tails: global UAM dominance + SaaS-take-rate model
        'rev':       [0.250, 0.700, 1.800, 3.800, 7.000, 11.50, 17.00, 23.00, 28.00, 32.00],
        'op_margin': [-1.8, -0.60, -0.10, 0.10, 0.18, 0.24, 0.28, 0.30, 0.32, 0.34],
        'raises':    [0.30, 0.50, 0.50, 0.30, 0.20, 0.00, 0.00, 0.00, 0.00, 0.00],
        'price':     [16.00, 28.00, 50.00, 80.00, 120.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        's2c': 1.8,
        'wacc':      [0.110, 0.105, 0.100, 0.095, 0.090, 0.085, 0.080, 0.075, 0.072, 0.070],
        'mature_share': 0.160,
        'color': ULTRA_BULL,
        'label': 'UltBull',  # short for chart labels at small font
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
    cash = 2.50
    out = [cash]
    prev_rev = 0.110  # FY26 starting revenue $110M
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
    shares = 984
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

    # Mature peer-set anchor at ~15% (right side)
    ax.axhline(15, color=ACCENT_SOFT, linewidth=0.4, linestyle=':', zorder=1)
    ax.text(0.5, -95, 'Aerospace + operator peer median ~15%',
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

    ax2.set_ylim(900, 1600)
    ax2.set_yticks([900, 1100, 1300, 1500])
    ax2.set_yticklabels(['900M', '1.1K', '1.3K', '1.5K'])
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


# ── CHART 4: Fleet/unit growth — eVTOL aircraft deployment ────────────────
def chart_fleet():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.13, right=0.93, top=0.84, bottom=0.18)

    # Inferred aircraft trajectory: revenue / revenue per aircraft (annual)
    # Each aircraft generates roughly $4-6M/yr at maturity (6 flights/day, $200/seat avg)
    # Lower in early years (ramp), higher at scale
    def fleet_from_rev(rev_path, rev_per_aircraft_path):
        # rev_i in $B; rev per aircraft in $M
        return [(r * 1000) / p for r, p in zip(rev_path, rev_per_aircraft_path)]

    rev_per_aircraft = {  # $M/year per aircraft
        'bear': [3.0, 3.2, 3.5, 3.7, 4.0, 4.2, 4.4, 4.5, 4.5, 4.5],
        'base': [3.5, 3.8, 4.0, 4.2, 4.5, 4.8, 5.0, 5.0, 5.0, 5.0],
        'bull': [4.0, 4.3, 4.5, 4.8, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
        'ultra_bull': [4.5, 4.8, 5.0, 5.2, 5.5, 5.5, 5.5, 5.5, 5.5, 5.5],
    }

    # Historical fleet: JOBY had only prototypes through FY25; first conforming aircraft Q1'26
    # ~5 aircraft by EOY 2026 (production ramping)
    fleet_hist_x = [0, 1, 2]
    fleet_hist = [1, 2, 5]  # FY24, FY25, FY26 estimate

    ax.plot(fleet_hist_x, fleet_hist, color=ACCENT, linewidth=1.8,
            marker='o', markersize=4, markerfacecolor=ACCENT,
            markeredgecolor='white', markeredgewidth=0.6, zorder=3)

    x_proj = list(range(2, 13))
    for key in ['bear', 'base', 'bull', 'ultra_bull']:
        scn = SCENARIOS[key]
        fleet = fleet_from_rev(scn['rev'], rev_per_aircraft[key])
        ax.plot(x_proj, [5] + fleet, color=scn['color'], linewidth=1.4,
                linestyle='--', marker='o', markersize=2.5,
                markerfacecolor=scn['color'], markeredgecolor='white',
                markeredgewidth=0.5, zorder=3)
        end = fleet[-1]
        if end >= 1000:
            unit = f'{end/1000:.1f}K'
        else:
            unit = f'{end:.0f}'
        ax.text(x_proj[-1] + 0.15, end, f'{scn["label"]} {unit}',
                color=scn['color'], fontsize=7, va='center', ha='left',
                fontweight='medium')

    # No capacity reference line — chart shows cumulative fleet, but
    # "500/yr" capacity is annual production, so reference would mislead.

    today_marker(ax, 2.5)

    ax.set_yscale('log')
    ax.set_ylim(0.5, 10000)
    ax.set_yticks([1, 10, 100, 1000, 10000])
    ax.set_yticklabels(['1', '10', '100', '1K', '10K'])

    ax.set_xticks(range(13))
    ax.set_xticklabels(fy_short, fontsize=7)
    ax.set_xlim(-0.5, 13.6)

    style_ax(ax)
    ax.set_title('eVTOL aircraft deployed (log scale)', fontsize=9,
                 color=INK, loc='left', pad=8, fontweight='semibold')

    plt.savefig(f'{OUT}/04_fleet.png', dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()


# ── CHART 5: Valuation — Market cap / Year-10 revenue ─────────────────────
def chart_valuation():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.13, right=0.93, top=0.84, bottom=0.28)

    scenarios = ['Bear FY36', 'Base FY36', 'Bull FY36', 'UltBull FY36']
    multiples = [10.3/1.5, 10.3/7.0, 10.3/20.0, 10.3/32.0]
    colors = [BEAR, BASE, BULL, ULTRA_BULL]

    bars = ax.bar(scenarios, multiples, color=colors, width=0.55, zorder=2)
    for i, m in enumerate(multiples):
        ax.text(i, m + 0.15, f'{m:.1f}×', ha='center', va='bottom',
                fontsize=9, color=colors[i], fontweight='semibold')

    ax.axhline(3, color=DIM, linewidth=0.5, linestyle=':', zorder=1)
    ax.text(2.55, 3.2, 'Mature aerospace P/S ~2-4×',
            fontsize=6.5, color=MUTED, ha='right')

    style_ax(ax)
    ax.set_ylim(0, 9)
    ax.set_yticks([0, 2, 4, 6, 8])
    ax.set_yticklabels(['0×', '2×', '4×', '6×', '8×'])
    ax.tick_params(axis='x', labelsize=7)
    ax.set_title('Today\'s $10.3B mkt cap as P/S on FY36 revenue',
                 fontsize=8.5, color=INK, loc='left', pad=8, fontweight='semibold')

    fig.text(0.13, 0.05,
             'Bear=very stretched (6.9×), base=full (1.5×), bull/ultbull=cheap (0.5×/0.3×).',
             fontsize=6.5, color=MUTED, ha='left')

    plt.savefig(f'{OUT}/05_valuation.png', dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()


# ── CHART 6: TAM positioning at FY36 ──────────────────────────────────────
def chart_tam():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.13, right=0.93, top=0.84, bottom=0.20)

    # Total TAM: $250B global UAM passenger + cargo 2036 (Morgan Stanley curve interpolation)
    tam = 250
    scenarios = ['Bear\n0.6%', 'Base\n2.8%', 'Bull\n8.0%', 'UltBull\n16%']
    joby_shares = [1.5, 7.0, 20.0, 40.0]  # JOBY's revenue ($B) at FY36
    # Competitors: Archer, Vertical, EHang, Boeing/Airbus, Chinese, etc.
    competitor_shares = [40.0, 60.0, 70.0, 75.0]
    remaining = [tam - a - c for a, c in zip(joby_shares, competitor_shares)]

    y_pos = [0, 1, 2, 3]
    bar_h = 0.55

    for i in range(4):
        ax.barh(y_pos[i], joby_shares[i], height=bar_h, color=[BEAR, BASE, BULL, ULTRA_BULL][i],
                zorder=2)
        ax.barh(y_pos[i], competitor_shares[i], height=bar_h, left=joby_shares[i],
                color=ACCENT_SOFT, zorder=2)
        ax.barh(y_pos[i], remaining[i], height=bar_h, left=joby_shares[i]+competitor_shares[i],
                color=DIM, zorder=2, alpha=0.5)

    for i in range(4):
        if joby_shares[i] > 10:
            ax.text(joby_shares[i]/2, y_pos[i], f'${joby_shares[i]:.0f}B',
                    ha='center', va='center', color='white', fontsize=7.5,
                    fontweight='medium')
        ax.text(joby_shares[i] + competitor_shares[i]/2, y_pos[i], f'${competitor_shares[i]:.0f}B',
                ha='center', va='center', color='white', fontsize=7, alpha=0.9)
        if remaining[i] > 40:
            ax.text(joby_shares[i] + competitor_shares[i] + remaining[i]/2, y_pos[i],
                    f'${remaining[i]:.0f}B',
                    ha='center', va='center', color='white', fontsize=7, alpha=0.9)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(scenarios, fontsize=8, color=TEXT)
    ax.set_xlim(0, 260)
    ax.set_xticks([0, 50, 100, 150, 200, 250])
    ax.set_xticklabels(['$0B', '$50B', '$100B', '$150B', '$200B', '$250B'], fontsize=7.5)
    ax.spines['bottom'].set_color(MUTED)
    ax.spines['left'].set_visible(False)
    ax.tick_params(colors=MUTED, length=0)

    ax.set_title('$250B global UAM TAM (FY36) — Joby\'s share by scenario',
                 fontsize=8.5, color=INK, loc='left', pad=8, fontweight='semibold')

    fig.text(0.13, 0.03, 'JOBY', color=ACCENT, fontsize=7, fontweight='medium')
    fig.text(0.22, 0.03, 'Competitors', color=ACCENT_SOFT, fontsize=7)
    fig.text(0.42, 0.03, 'Other UAM (cargo, etc.)', color=DIM, fontsize=7)

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
