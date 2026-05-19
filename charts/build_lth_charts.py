"""
$LTH Business Snapshot — chart generator (Variant A)
Six charts: revenue, segments, margins, net debt, EV multiples, club count by format.

Per spec §7 Variant A: 5-year forward projections.
The "geographic mix" slot is repurposed as "Club count by format" since LTH's
geographic mix isn't a meaningful breakdown (US-only operator); club format
(luxury vs standard) is the more analytically useful breakdown.

Canonical source: lth-dcf-valuation__v001__2026-05-16_19-30.jsx
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

OUT = str(Path(__file__).parent.parent / 'charts' / 'lth')
Path(OUT).mkdir(parents=True, exist_ok=True)

FIG_W, FIG_H = 3.5, 2.4
DPI = 200

fy_hist = ['FY21', 'FY22', 'FY23', 'FY24', 'FY25']
fy_proj = ['FY26', 'FY27', 'FY28', 'FY29', 'FY30']
fy_all = fy_hist + fy_proj
fy_short = [s[2:] for s in fy_all]

rev_hist = [1.318, 1.822, 2.217, 2.621, 2.995]
ent_hist = [907, 1276, 1551, 1853, 2118]
onl_hist = [380, 524, 638, 740, 845]
gross_hist = [29.4, 35.6, 37.8, 38.4, 39.0]
op_hist = [2.5, 9.2, 12.5, 15.5, 18.0]
fcf_hist = [-8.3, -7.5, -4.9, 10.4, 6.9]
debt_hist = [1.51, 1.62, 1.51, 1.34, 1.29]
ev_ev_rev_hist = [None, 5.8, 4.7, 3.8, 3.2]
ev_ev_ebitda_hist = [None, 28.0, 16.5, 12.5, 10.5]
club_hist_yr = ['FY23', 'FY24', 'FY25']
clubs_lux_hist = [22, 30, 42]
clubs_std_hist = [149, 144, 148]

SCENARIOS = {
    'bear': {
        'rev_growth':   [0.11, 0.06, 0.04, 0.03, 0.02],
        'fcf_margin':   [0.04, 0.05, 0.04, 0.03, 0.02],
        'op_margin':    [0.175, 0.170, 0.160, 0.150, 0.140],
        'gross_margin': [0.380, 0.375, 0.370, 0.365, 0.360],
        'mem_growth':   [0.10, 0.06, 0.04, 0.03, 0.02],
        'inc_growth':   [0.14, 0.06, 0.04, 0.03, 0.02],
        'slb':          [0.40, 0.25, 0.15, 0.10, 0.05],
        'buybacks':     [0.0, 0.0, 0.0, 0.0, 0.0],
        'wacc': 0.110, 'term_g': 0.015,
        'color': BEAR, 'label': 'Bear',
    },
    'base': {
        'rev_growth':   [0.11, 0.09, 0.08, 0.06, 0.05],
        'fcf_margin':   [0.07, 0.08, 0.08, 0.08, 0.08],
        'op_margin':    [0.180, 0.185, 0.188, 0.190, 0.190],
        'gross_margin': [0.385, 0.388, 0.390, 0.390, 0.390],
        'mem_growth':   [0.10, 0.09, 0.08, 0.07, 0.06],
        'inc_growth':   [0.14, 0.09, 0.08, 0.06, 0.04],
        'slb':          [0.40, 0.40, 0.35, 0.30, 0.25],
        'buybacks':     [0.0, 0.0, 0.10, 0.15, 0.15],
        'wacc': 0.095, 'term_g': 0.025,
        'color': BASE, 'label': 'Base',
    },
    'bull': {
        'rev_growth':   [0.12, 0.11, 0.10, 0.09, 0.07],
        'fcf_margin':   [0.09, 0.11, 0.12, 0.13, 0.14],
        'op_margin':    [0.185, 0.195, 0.205, 0.215, 0.220],
        'gross_margin': [0.390, 0.395, 0.400, 0.405, 0.410],
        'mem_growth':   [0.11, 0.10, 0.09, 0.08, 0.07],
        'inc_growth':   [0.15, 0.13, 0.12, 0.11, 0.08],
        'slb':          [0.40, 0.40, 0.40, 0.40, 0.40],
        'buybacks':     [0.0, 0.10, 0.20, 0.30, 0.40],
        'wacc': 0.080, 'term_g': 0.030,
        'color': BULL, 'label': 'Bull',
    },
    'ultra_bull': {
        # Per spec §6c.11 — tail-of-tails: 250+ clubs by 2030 + ARPU $6,500 + 15x re-rate
        'rev_growth':   [0.13, 0.12, 0.12, 0.11, 0.09],
        'fcf_margin':   [0.11, 0.13, 0.14, 0.15, 0.16],
        'op_margin':    [0.195, 0.210, 0.220, 0.230, 0.240],
        'gross_margin': [0.395, 0.405, 0.415, 0.420, 0.425],
        'mem_growth':   [0.12, 0.11, 0.10, 0.09, 0.08],
        'inc_growth':   [0.16, 0.15, 0.14, 0.13, 0.10],
        'slb':          [0.40, 0.40, 0.40, 0.40, 0.40],
        'buybacks':     [0.0, 0.15, 0.30, 0.40, 0.50],
        'wacc': 0.075, 'term_g': 0.035,
        'color': ULTRA_BULL, 'label': 'UltBull',
    },
}


def project_revenue(scn):
    rev = 2.995
    out = [rev]
    for g in scn['rev_growth']:
        rev = rev * (1 + g)
        out.append(rev)
    return out


def project_segment(scn):
    mem, inc = 2118, 845
    mem_out, inc_out = [mem], [inc]
    for gm, gi in zip(scn['mem_growth'], scn['inc_growth']):
        mem = mem * (1 + gm)
        inc = inc * (1 + gi)
        mem_out.append(mem)
        inc_out.append(inc)
    return mem_out, inc_out


def project_net_debt(scn):
    """Net debt: starts at FY25 $1.29B. Debt paid down by FCF (which includes SLB).
    LTH's stated strategy: SLB proceeds offset new-club capex; FCF after SLB
    flows to debt paydown. Some buybacks in years 3+.
    """
    debt = 1.29
    out = [debt]
    rev = 2.995
    for i in range(5):
        rev = rev * (1 + scn['rev_growth'][i])
        fcf = rev * scn['fcf_margin'][i]
        debt = debt - fcf + scn['buybacks'][i]
        debt = max(debt, 0)
        out.append(debt)
    return out


def project_margins(scn):
    return (
        [gross_hist[-1]] + [m * 100 for m in scn['gross_margin']],
        [op_hist[-1]]    + [m * 100 for m in scn['op_margin']],
        [fcf_hist[-1]]   + [m * 100 for m in scn['fcf_margin']],
    )


def project_ev_multiples(scn):
    # Anchor projections at HISTORICAL FY25 values (3.2× EV/Rev, 10.5× EV/EBITDA)
    # rather than a "today" snapshot. The current multiples are higher (~3.7× / ~13.5×)
    # due to LTH's spring 2026 price runup ($26 → $33.61), but plotting that creates
    # a visual discontinuity. Use the FY25 close as the anchor for continuity.
    anchor_ev_rev = ev_ev_rev_hist[-1]      # 3.2×
    anchor_ev_ebitda = ev_ev_ebitda_hist[-1] # 10.5×
    term_fcf_mult = 1.0 / (scn['wacc'] - scn['term_g'])
    fcf_to_ebitda_ratio = {'bear': 0.10, 'base': 0.30, 'bull': 0.50, 'ultbull': 0.65}[scn['label'].lower()]
    term_ev_ebitda = term_fcf_mult * fcf_to_ebitda_ratio
    term_ebitda_margin = scn['op_margin'][-1] + 0.08
    term_ev_rev = term_ev_ebitda * term_ebitda_margin
    rev_out = [anchor_ev_rev]
    ebitda_out = [anchor_ev_ebitda]
    for i in range(5):
        t = (i + 1) / 5.0
        rev_out.append(anchor_ev_rev * (1 - t) + term_ev_rev * t)
        ebitda_out.append(anchor_ev_ebitda * (1 - t) + term_ev_ebitda * t)
    return rev_out, ebitda_out


def style_ax(ax):
    ax.spines['left'].set_color(MUTED)
    ax.spines['bottom'].set_color(MUTED)
    ax.tick_params(colors=MUTED)
    ax.grid(axis='y', color=RULE, linewidth=0.4, zorder=0)
    ax.set_axisbelow(True)


def today_marker(ax, x):
    ax.axvline(x, color=DIM, linewidth=0.4, linestyle=':', zorder=1)


def chart_revenue():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.11, right=0.93, top=0.84, bottom=0.18)
    bars = ax.bar(range(len(fy_hist)), rev_hist, color=ACCENT_SOFT, width=0.62, zorder=2)
    bars[-1].set_color(ACCENT)
    for i, val in enumerate(rev_hist):
        ax.text(i, val + 0.07, f'{val:.1f}', ha='center', va='bottom',
                fontsize=7, color=TEXT)
    n_hist = len(fy_hist)
    proj_x = list(range(n_hist - 1, n_hist + 5))
    for key in ['bear', 'base', 'bull', 'ultra_bull']:
        scn = SCENARIOS[key]
        proj_y = project_revenue(scn)
        ax.plot(proj_x, proj_y, color=scn['color'], linewidth=1.4,
                linestyle='--', marker='o', markersize=2.5,
                markerfacecolor=scn['color'], markeredgecolor='white',
                markeredgewidth=0.6, zorder=3)
        ax.text(proj_x[-1] + 0.12, proj_y[-1], f'{scn["label"]} {proj_y[-1]:.1f}',
                color=scn['color'], fontsize=7, va='center', ha='left',
                fontweight='medium')
    today_marker(ax, n_hist - 0.5)
    ax.set_xticks(list(range(n_hist + 5)))
    ax.set_xticklabels(fy_short, fontsize=7.5)
    ax.set_xlim(-0.5, n_hist + 5 + 1.5)
    ax.set_ylim(0, max(rev_hist) * 1.8)
    style_ax(ax)
    ax.set_title('Revenue ($B) — history + scenario projections to FY30',
                 fontsize=9, color=INK, loc='left', pad=8, fontweight='semibold')
    plt.savefig(f'{OUT}/01_revenue.png', dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()


def chart_segments():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.14, right=0.93, top=0.84, bottom=0.18)
    n_hist = len(fy_hist)
    hist_x = list(range(n_hist))
    ax.plot(hist_x, ent_hist, color=ACCENT, linewidth=1.8, marker='o', markersize=3.5,
            markerfacecolor=ACCENT, markeredgecolor='white', markeredgewidth=0.6, zorder=4)
    ax.plot(hist_x, onl_hist, color=ACCENT_SOFT, linewidth=1.4, marker='o', markersize=3,
            markerfacecolor=ACCENT_SOFT, markeredgecolor='white', markeredgewidth=0.6, zorder=3)
    proj_x = list(range(n_hist - 1, n_hist + 5))
    for key in ['bear', 'base', 'bull', 'ultra_bull']:
        scn = SCENARIOS[key]
        mem_p, inc_p = project_segment(scn)
        ax.plot(proj_x, mem_p, color=scn['color'], linewidth=1.4, linestyle='--',
                marker='o', markersize=2.5, markerfacecolor=scn['color'],
                markeredgecolor='white', markeredgewidth=0.6, zorder=3)
        ax.plot(proj_x, inc_p, color=scn['color'], linewidth=0.9, linestyle=':',
                alpha=0.7, zorder=2)
        ax.text(proj_x[-1] + 0.12, mem_p[-1], f'{scn["label"]} {mem_p[-1]/1000:.1f}K',
                color=scn['color'], fontsize=7, va='center', ha='left', fontweight='medium')
    ax.text(-0.18, ent_hist[0], 'Membership', color=ACCENT,
            fontsize=7.5, va='center', ha='right', fontweight='medium')
    ax.text(-0.18, onl_hist[0], 'In-center', color=MUTED,
            fontsize=7.5, va='center', ha='right', fontweight='medium')
    today_marker(ax, n_hist - 0.5)
    ax.set_xticks(list(range(n_hist + 5)))
    ax.set_xticklabels(fy_short, fontsize=7.5)
    ax.set_xlim(-2.0, n_hist + 5 + 1.5)
    ax.set_ylim(200, 3800)
    ax.set_yticks([500, 1000, 2000, 3000])
    ax.set_yticklabels(['0.5K', '1K', '2K', '3K'])
    style_ax(ax)
    ax.set_title('Revenue by segment ($M) — dashed Membership, dotted In-center',
                 fontsize=8.5, color=INK, loc='left', pad=8, fontweight='semibold')
    plt.savefig(f'{OUT}/02_segments.png', dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()


def chart_margins():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.13, right=0.93, top=0.84, bottom=0.18)
    n_hist = len(fy_hist)
    hist_x = list(range(n_hist))
    ax.plot(hist_x, gross_hist, color=INK, linewidth=1.6, marker='o', markersize=3,
            markerfacecolor=INK, markeredgecolor='white', markeredgewidth=0.6, zorder=4)
    ax.plot(hist_x, op_hist, color=ACCENT, linewidth=1.6, marker='o', markersize=3,
            markerfacecolor=ACCENT, markeredgecolor='white', markeredgewidth=0.6, zorder=3)
    ax.plot(hist_x, fcf_hist, color=ACCENT_SOFT, linewidth=1.4, marker='o', markersize=3,
            markerfacecolor=ACCENT_SOFT, markeredgecolor='white', markeredgewidth=0.6, zorder=2)
    proj_x = list(range(n_hist - 1, n_hist + 5))
    for key in ['bear', 'base', 'bull', 'ultra_bull']:
        scn = SCENARIOS[key]
        _, _, fcf_p = project_margins(scn)
        ax.plot(proj_x, fcf_p, color=scn['color'], linewidth=1.3, linestyle='--',
                marker='o', markersize=2.5, markerfacecolor=scn['color'],
                markeredgecolor='white', markeredgewidth=0.5, zorder=3)
        ax.text(proj_x[-1] + 0.12, fcf_p[-1], f'{scn["label"]} {fcf_p[-1]:.0f}%',
                color=scn['color'], fontsize=7, va='center', ha='left', fontweight='medium')
    proj_x_only = list(range(n_hist, n_hist + 5))
    ax.plot([n_hist - 1] + proj_x_only, [gross_hist[-1]] + [39.0] * 5,
            color=INK, linewidth=0.7, linestyle=':', alpha=0.5, zorder=2)
    ax.plot([n_hist - 1] + proj_x_only, [op_hist[-1]] + [19.0] * 5,
            color=ACCENT, linewidth=0.7, linestyle=':', alpha=0.5, zorder=2)
    ax.text(n_hist - 1 + 0.12, gross_hist[-1] + 1.5, 'Gross 39%',
            color=INK, fontsize=6.5, va='center', ha='left')
    ax.text(n_hist - 1 + 0.12, op_hist[-1] + 1.5, 'Op 18%',
            color=ACCENT, fontsize=6.5, va='center', ha='left')
    today_marker(ax, n_hist - 0.5)
    ax.set_xticks(list(range(n_hist + 5)))
    ax.set_xticklabels(fy_short, fontsize=7.5)
    ax.set_xlim(-0.4, n_hist + 5 + 1.6)
    ax.set_ylim(-15, 50)
    ax.set_yticks([-10, 0, 10, 20, 30, 40, 50])
    ax.set_yticklabels(['-10%', '0%', '10%', '20%', '30%', '40%', '50%'])
    style_ax(ax)
    ax.set_title('Margin trends — dashed = FCF margin scenarios',
                 fontsize=9, color=INK, loc='left', pad=8, fontweight='semibold')
    plt.savefig(f'{OUT}/03_margins.png', dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()


def chart_net_debt():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.12, right=0.93, top=0.84, bottom=0.18)
    n_hist = len(fy_hist)
    bars = ax.bar(range(n_hist), debt_hist, color=ACCENT_SOFT, width=0.6, zorder=2)
    bars[-1].set_color(ACCENT)
    for i, val in enumerate(debt_hist):
        ax.text(i, val + 0.04, f'{val:.1f}', ha='center', va='bottom',
                fontsize=7, color=TEXT)
    proj_x = list(range(n_hist - 1, n_hist + 5))
    for key in ['bear', 'base', 'bull', 'ultra_bull']:
        scn = SCENARIOS[key]
        debt_p = project_net_debt(scn)
        ax.plot(proj_x, debt_p, color=scn['color'], linewidth=1.4, linestyle='--',
                marker='o', markersize=2.5, markerfacecolor=scn['color'],
                markeredgecolor='white', markeredgewidth=0.6, zorder=3)
        ax.text(proj_x[-1] + 0.12, debt_p[-1], f'{scn["label"]} {debt_p[-1]:.1f}',
                color=scn['color'], fontsize=7, va='center', ha='left', fontweight='medium')
    today_marker(ax, n_hist - 0.5)
    ax.set_xticks(list(range(n_hist + 5)))
    ax.set_xticklabels(fy_short, fontsize=7.5)
    ax.set_xlim(-0.5, n_hist + 5 + 1.6)
    ax.set_ylim(0, 2.0)
    ax.set_yticks([0, 0.5, 1.0, 1.5, 2.0])
    ax.set_yticklabels(['$0', '$0.5B', '$1B', '$1.5B', '$2B'])
    style_ax(ax)
    ax.set_title('Net financial debt ($B) — debt paydown via FCF (incl. SLB)',
                 fontsize=8.5, color=INK, loc='left', pad=8, fontweight='semibold')
    plt.savefig(f'{OUT}/04_net_debt.png', dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()


def chart_ev_multiples():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.13, right=0.83, top=0.84, bottom=0.18)
    n_hist = len(fy_hist)
    valid = [(i, v) for i, v in enumerate(ev_ev_rev_hist) if v is not None]
    ax.plot([i for i, _ in valid], [v for _, v in valid],
            color=ACCENT, linewidth=1.6, marker='o', markersize=3.5,
            markerfacecolor=ACCENT, markeredgecolor='white',
            markeredgewidth=0.6, zorder=3)
    proj_x = list(range(n_hist - 1, n_hist + 5))
    for key in ['bear', 'base', 'bull', 'ultra_bull']:
        scn = SCENARIOS[key]
        ev_rev_p, _ = project_ev_multiples(scn)
        ax.plot(proj_x, ev_rev_p, color=scn['color'], linewidth=1.3, linestyle='--',
                marker='o', markersize=2, markerfacecolor=scn['color'],
                markeredgecolor='white', markeredgewidth=0.5, zorder=2)
        ax.text(proj_x[-1] + 0.12, ev_rev_p[-1], f'{ev_rev_p[-1]:.1f}×',
                color=scn['color'], fontsize=7, va='center', ha='left', fontweight='medium')
    style_ax(ax)
    ax.set_ylim(0, 8)
    ax.set_yticks([0, 2, 4, 6, 8])
    ax.set_yticklabels(['0×', '2×', '4×', '6×', '8×'])
    ax.set_ylabel('EV / Revenue', fontsize=7.5, color=ACCENT, labelpad=4)
    ax2 = ax.twinx()
    fcf_hist_x = [i for i, v in enumerate(ev_ev_ebitda_hist) if v is not None]
    fcf_hist_y = [v for v in ev_ev_ebitda_hist if v is not None]
    ax2.plot(fcf_hist_x, fcf_hist_y, color=INK, linewidth=1.4, marker='s', markersize=3,
             markerfacecolor=INK, markeredgecolor='white', markeredgewidth=0.6, zorder=3, alpha=0.85)
    for key in ['bear', 'base', 'bull', 'ultra_bull']:
        scn = SCENARIOS[key]
        _, ev_ebitda_p = project_ev_multiples(scn)
        ax2.plot(proj_x, ev_ebitda_p, color=scn['color'], linewidth=1.0, linestyle=':',
                 marker='s', markersize=2, markerfacecolor=scn['color'],
                 markeredgecolor='white', markeredgewidth=0.4, zorder=2, alpha=0.85)
    ax2.set_ylim(0, 35)
    ax2.set_yticks([0, 10, 20, 30])
    ax2.set_yticklabels(['0×', '10×', '20×', '30×'])
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_color(MUTED)
    ax2.spines['left'].set_visible(False)
    ax2.tick_params(colors=MUTED, axis='y')
    ax2.set_ylabel('EV / EBITDA', fontsize=7.5, color=INK, labelpad=4)
    today_marker(ax, n_hist - 0.5)
    ax.set_xticks(list(range(n_hist + 5)))
    ax.set_xticklabels(fy_short, fontsize=7.5)
    ax.set_xlim(-0.4, n_hist + 5 + 1.4)
    ax.set_title('EV multiples — dual axis (Rev left, EBITDA right)',
                 fontsize=8.5, color=INK, loc='left', pad=8, fontweight='semibold')
    fig.text(0.13, 0.05, 'Solid line = EV/Rev (left). Square markers + dotted = EV/EBITDA (right).',
             fontsize=6, color=MUTED, ha='left')
    plt.savefig(f'{OUT}/05_ev_multiples.png', dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()


def chart_clubs():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0.20, right=0.95, top=0.84, bottom=0.18)
    luxury_proj = {
        'bear': 42 + 5*7,
        'base': 42 + 5*11,
        'bull': 42 + 5*13,
        'ultra_bull': 42 + 5*15,
    }
    std_proj = 148
    years = ['FY23', 'FY24', 'FY25', 'FY30E']
    y_pos = list(range(4))
    bar_h = 0.55
    for i in range(3):
        ax.barh(y_pos[i], clubs_lux_hist[i], height=bar_h, color=BULL, alpha=1.0, zorder=2)
        ax.barh(y_pos[i], clubs_std_hist[i], height=bar_h, left=clubs_lux_hist[i],
                color=ACCENT_SOFT, alpha=1.0, zorder=2)
    avg_lux = sum(luxury_proj.values()) / 4
    ax.barh(y_pos[3], avg_lux, height=bar_h, color=BULL, alpha=0.55, zorder=2)
    ax.barh(y_pos[3], std_proj, height=bar_h, left=avg_lux,
            color=ACCENT_SOFT, alpha=0.55, zorder=2)
    for i in range(3):
        ax.text(clubs_lux_hist[i]/2, y_pos[i], f'{clubs_lux_hist[i]}',
                ha='center', va='center', color='white', fontsize=7.5, fontweight='medium')
        ax.text(clubs_lux_hist[i] + clubs_std_hist[i]/2, y_pos[i], f'{clubs_std_hist[i]}',
                ha='center', va='center', color='white', fontsize=7.5)
    ax.text(avg_lux/2, y_pos[3], f'{int(avg_lux)}',
            ha='center', va='center', color='white', fontsize=7.5, fontweight='medium')
    ax.text(avg_lux + std_proj/2, y_pos[3], f'{std_proj}',
            ha='center', va='center', color='white', fontsize=7.5)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(years, fontsize=9, color=TEXT)
    ax.set_xlim(0, 260)
    ax.set_xticks([])
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_color(MUTED)
    ax.tick_params(colors=MUTED, length=0)
    ax.set_title('Club count by format — Luxury vs Standard',
                 fontsize=9, color=INK, loc='left', pad=8, fontweight='semibold')
    fig.text(0.20, 0.04,
             'FY30E: scenario average. Luxury clubs are the growth engine; +5-13 added per year.',
             fontsize=6.5, color=MUTED, ha='left')
    fig.text(0.55, 0.95, 'Luxury', color=BULL, fontsize=7, ha='left', fontweight='medium')
    fig.text(0.70, 0.95, 'Standard', color=ACCENT_SOFT, fontsize=7, ha='left', fontweight='medium')
    plt.savefig(f'{OUT}/06_clubs.png', dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()


if __name__ == '__main__':
    chart_revenue()
    chart_segments()
    chart_margins()
    chart_net_debt()
    chart_ev_multiples()
    chart_clubs()
    print('Charts generated:')
    for f in sorted(os.listdir(OUT)):
        print(' ', f)
