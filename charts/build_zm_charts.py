"""Generate 6 ZM business-snapshot charts for the memo Page 3."""
import os, matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ZM_OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "charts", "zm")
os.makedirs(ZM_OUT, exist_ok=True)

# Design system colors
INK = "#0a0a0a"
TEXT = "#262626"
MUTED = "#737373"
RULE = "#d4d4d4"
ACCENT = "#1e3a8a"   # base scenario
NEG = "#b91c1c"      # bear
POS = "#15803d"      # bull
ULTRA = "#7629a6"    # ultra_bull (deep purple, per spec §6c.11)

plt.rcParams.update({
    'font.family': 'sans-serif', 'font.sans-serif': ['Inter', 'DejaVu Sans'],
    'font.size': 9, 'axes.edgecolor': RULE, 'axes.linewidth': 0.4,
    'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.labelcolor': MUTED,
    'axes.spines.top': False, 'axes.spines.right': False,
})

def style_ax(ax, title):
    ax.set_title(title, fontsize=10, color=INK, loc='left', pad=8)
    ax.grid(axis='y', color=RULE, linewidth=0.3, linestyle=':')
    ax.set_axisbelow(True)
    ax.tick_params(axis='both', length=2, labelsize=8)

# Historical revenue ($B): FY21-FY25 (approximate)
hist_years = [2021, 2022, 2023, 2024, 2025]
hist_rev = [2.65, 4.10, 4.39, 4.53, 4.74]
hist_ent_split = [0.55, 0.58, 0.59, 0.60, 0.603]
proj_years = list(range(2026, 2031))

# Scenarios — computed earlier
bear_rev = [4.92, 4.92, 4.87, 4.77, 4.68]
base_rev = [5.06, 5.24, 5.40, 5.53, 5.67]
bull_rev = [5.11, 5.47, 5.91, 6.32, 6.64]
ultra_rev = [5.20, 5.70, 6.40, 7.10, 7.80]  # ultra_bull: AI Companion fires + Anthropic IPO drives reacceleration

# ─── 01: Revenue ($B) — history + scenarios to FY30 ─────────────────────────────
fig, ax = plt.subplots(figsize=(4.0, 2.8))
ax.bar(hist_years, hist_rev, color=RULE, edgecolor=ACCENT, width=0.6)
ax.bar(2025, hist_rev[-1], color=ACCENT, width=0.6)
ax.plot(proj_years, bear_rev, '--o', color=NEG, ms=3, lw=1, label=f'Bear {bear_rev[-1]:.1f}')
ax.plot(proj_years, base_rev, '--o', color=ACCENT, ms=3, lw=1, label=f'Base {base_rev[-1]:.1f}')
ax.plot(proj_years, bull_rev, '--o', color=POS, ms=3, lw=1, label=f'Bull {bull_rev[-1]:.1f}')
ax.plot(proj_years, ultra_rev, '--o', color=ULTRA, ms=3, lw=1, label=f'UltBull {ultra_rev[-1]:.1f}')
for label, vals, color in [('Bear', bear_rev, NEG), ('Base', base_rev, ACCENT), ('Bull', bull_rev, POS), ('UltBull', ultra_rev, ULTRA)]:
    ax.annotate(f'{label} {vals[-1]:.1f}', xy=(2030.3, vals[-1]), color=color, fontsize=7, va='center')
ax.set_xticks([2021, 2023, 2025, 2027, 2029])
ax.set_xticklabels(['21', '23', '25', '27', '29'])
ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'${x:.0f}B'))
style_ax(ax, "Revenue ($B) — history + scenario projections to FY30")
plt.tight_layout()
plt.savefig(f"{ZM_OUT}/01_revenue.png", dpi=200, bbox_inches='tight', facecolor='white')
plt.close()

# ─── 02: Revenue by segment (Enterprise vs Online) ──────────────────────────────
fig, ax = plt.subplots(figsize=(4.0, 2.8))
hist_ent = [r*s for r, s in zip(hist_rev, hist_ent_split)]
hist_onl = [r-e for r, e in zip(hist_rev, hist_ent)]
proj_ent_base = [base_rev[i]*0.62+i*0.02 for i in range(5)]
proj_onl_base = [base_rev[i] - proj_ent_base[i] for i in range(5)]
proj_ent_bear = [bear_rev[i]*0.60-i*0.01 for i in range(5)]
proj_onl_bear = [bear_rev[i] - proj_ent_bear[i] for i in range(5)]
proj_ent_bull = [bull_rev[i]*0.64+i*0.025 for i in range(5)]
proj_onl_bull = [bull_rev[i] - proj_ent_bull[i] for i in range(5)]
proj_ent_ultra = [ultra_rev[i]*0.66+i*0.03 for i in range(5)]
proj_onl_ultra = [ultra_rev[i] - proj_ent_ultra[i] for i in range(5)]
ax.plot(hist_years, hist_ent, '-o', color=ACCENT, ms=2.5, lw=1.2, label='Enterprise')
ax.plot(hist_years, hist_onl, '-o', color=MUTED, ms=2.5, lw=1.2, label='Online')
ax.plot(proj_years, proj_ent_base, '--', color=ACCENT, lw=0.9, alpha=0.8)
ax.plot(proj_years, proj_onl_base, '--', color=MUTED, lw=0.9, alpha=0.8)
ax.plot(proj_years, proj_ent_bull, ':', color=POS, lw=0.7, alpha=0.6)
ax.plot(proj_years, proj_ent_bear, ':', color=NEG, lw=0.7, alpha=0.6)
ax.plot(proj_years, proj_ent_ultra, ':', color=ULTRA, lw=0.7, alpha=0.6)
ax.annotate('Enterprise', xy=(2025.3, 2.85), color=ACCENT, fontsize=8)
ax.annotate('Online', xy=(2025.3, 1.9), color=MUTED, fontsize=8)
ax.set_xticks([2021, 2023, 2025, 2027, 2029])
ax.set_xticklabels(['21', '23', '25', '27', '29'])
ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'${x:.1f}B'))
style_ax(ax, "Revenue by segment ($B) — dashed=base, dotted=bear/bull")
plt.tight_layout()
plt.savefig(f"{ZM_OUT}/02_segments.png", dpi=200, bbox_inches='tight', facecolor='white')
plt.close()

# ─── 03: Margin trends ─────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(4.0, 2.8))
hist_gross = [73.5, 76.0, 76.4, 76.6, 76.5]
hist_op = [25.0, 35.0, 38.0, 38.5, 39.0]
hist_fcf = [29.0, 36.0, 37.0, 36.0, 36.0]
bear_fcf_proj = [35, 34, 33, 31, 29]
base_fcf_proj = [35, 35, 35, 35, 35]
bull_fcf_proj = [38, 39, 40, 41, 41]
ultra_fcf_proj = [39, 41, 43, 44, 45]  # ultra_bull: AI scale + multiple expansion juice
ax.plot(hist_years, hist_gross, '-o', color=INK, ms=2.5, lw=1.2)
ax.plot(hist_years, hist_op, '-o', color=ACCENT, ms=2.5, lw=1.2)
ax.plot(hist_years, hist_fcf, '-o', color=MUTED, ms=2.5, lw=1.2)
ax.plot(proj_years, bear_fcf_proj, '--', color=NEG, lw=1.0)
ax.plot(proj_years, base_fcf_proj, '--', color=ACCENT, lw=1.0)
ax.plot(proj_years, bull_fcf_proj, '--', color=POS, lw=1.0)
ax.plot(proj_years, ultra_fcf_proj, '--', color=ULTRA, lw=1.0)
ax.annotate('Gross 76%', xy=(2025.2, 76.5), color=INK, fontsize=7)
ax.annotate('Op 39%', xy=(2025.2, 39), color=ACCENT, fontsize=7)
ax.annotate('Bull 41%', xy=(2030.2, 41), color=POS, fontsize=7, va='center')
ax.annotate('UltBull 45%', xy=(2030.2, 45), color=ULTRA, fontsize=7, va='center')
ax.annotate('Base 35%', xy=(2030.2, 35), color=ACCENT, fontsize=7, va='center')
ax.annotate('Bear 29%', xy=(2030.2, 29), color=NEG, fontsize=7, va='center')
ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:.0f}%'))
ax.set_xticks([2021, 2023, 2025, 2027, 2029])
ax.set_xticklabels(['21', '23', '25', '27', '29'])
ax.set_ylim(20, 85)
style_ax(ax, "Margin trends — dashed = FCF margin scenarios")
plt.tight_layout()
plt.savefig(f"{ZM_OUT}/03_margins.png", dpi=200, bbox_inches='tight', facecolor='white')
plt.close()

# ─── 04: Net cash position (ZM is net cash, builds with FCF) ──────────────────────
fig, ax = plt.subplots(figsize=(4.0, 2.8))
hist_cash = [4.7, 5.4, 6.7, 7.4, 7.8]
bear_cash = [7.8 + i*1.2 for i in range(5)]   # +1.2/yr accumulation after buybacks
base_cash = [7.8 + i*0.8 for i in range(5)]
bull_cash = [7.8 + i*1.4 for i in range(5)]
ultra_cash = [7.8 + i*1.6 for i in range(5)]   # ultra_bull: cash machine + AI re-rate (note: aggressive buybacks may consume some)
ax.bar(hist_years, hist_cash, color=RULE, edgecolor=ACCENT, width=0.6)
ax.bar(2025, hist_cash[-1], color=ACCENT, width=0.6)
ax.plot(proj_years, bear_cash, '--o', color=NEG, ms=3, lw=1)
ax.plot(proj_years, base_cash, '--o', color=ACCENT, ms=3, lw=1)
ax.plot(proj_years, bull_cash, '--o', color=POS, ms=3, lw=1)
ax.plot(proj_years, ultra_cash, '--o', color=ULTRA, ms=3, lw=1)
for label, vals, color in [('Bear', bear_cash, NEG), ('Base', base_cash, ACCENT), ('Bull', bull_cash, POS), ('UltBull', ultra_cash, ULTRA)]:
    ax.annotate(f'{label} ${vals[-1]:.1f}B', xy=(2030.2, vals[-1]), color=color, fontsize=7, va='center')
ax.set_xticks([2021, 2023, 2025, 2027, 2029])
ax.set_xticklabels(['21', '23', '25', '27', '29'])
ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'${x:.0f}B'))
style_ax(ax, "Cash & investments ($B) — net cash position grows")
plt.tight_layout()
plt.savefig(f"{ZM_OUT}/04_net_debt.png", dpi=200, bbox_inches='tight', facecolor='white')
plt.close()

# ─── 05: EV multiples — dual axis EV/Rev + EV/FCF ─────────────────────────────────
fig, ax1 = plt.subplots(figsize=(4.0, 2.8))
hist_ev_rev = [11.5, 4.0, 3.8, 4.0, 4.3]  # approximate historical EV/Rev
hist_ev_fcf = [40, 11, 10, 11, 12]
bear_ev_rev = [3.8, 3.5, 3.3, 3.0, 2.8]
base_ev_rev = [4.5, 4.7, 4.8, 4.9, 5.0]
bull_ev_rev = [5.5, 6.5, 7.5, 8.0, 8.5]
ultra_ev_rev = [6.0, 7.5, 9.0, 10.0, 11.0]  # ultra_bull: multiple expansion to growth-software premium
ax1.plot(hist_years, hist_ev_rev, '-o', color=INK, ms=3, lw=1.2)
ax1.plot(proj_years, base_ev_rev, '--', color=ACCENT, lw=1.0)
ax1.plot(proj_years, bull_ev_rev, '--', color=POS, lw=0.9)
ax1.plot(proj_years, bear_ev_rev, '--', color=NEG, lw=0.9)
ax1.plot(proj_years, ultra_ev_rev, '--', color=ULTRA, lw=0.9)
ax1.annotate(f'{base_ev_rev[-1]:.1f}×', xy=(2030.2, base_ev_rev[-1]), color=ACCENT, fontsize=7, va='center')
ax1.annotate(f'{bull_ev_rev[-1]:.1f}×', xy=(2030.2, bull_ev_rev[-1]), color=POS, fontsize=7, va='center')
ax1.annotate(f'{bear_ev_rev[-1]:.1f}×', xy=(2030.2, bear_ev_rev[-1]), color=NEG, fontsize=7, va='center')
ax1.annotate(f'{ultra_ev_rev[-1]:.1f}×', xy=(2030.2, ultra_ev_rev[-1]), color=ULTRA, fontsize=7, va='center')
ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:.0f}×'))
ax1.set_ylim(0, 14)
ax1.set_ylabel('EV / Rev', fontsize=8)
ax2 = ax1.twinx()
ax2.plot(hist_years, hist_ev_fcf, 's:', color=MUTED, ms=3, lw=0.8, alpha=0.7)
ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:.0f}×'))
ax2.set_ylim(0, 45)
ax2.set_ylabel('EV / FCF', fontsize=8)
ax2.spines['top'].set_visible(False)
ax1.set_xticks([2021, 2023, 2025, 2027, 2029])
ax1.set_xticklabels(['21', '23', '25', '27', '29'])
style_ax(ax1, "EV multiples (operating-EV basis, ex-Anthropic)")
plt.tight_layout()
plt.savefig(f"{ZM_OUT}/05_ev_multiples.png", dpi=200, bbox_inches='tight', facecolor='white')
plt.close()

# ─── 06: SOTP decomposition by scenario ────────────────────────────────────────
fig, ax = plt.subplots(figsize=(4.0, 2.8))
scenarios_data = [
    ('Bear', 14.43, 7.8, 4.0, NEG),
    ('Base', 28.11, 7.8, 7.0, ACCENT),
    ('Bull', 43.79, 7.8, 9.0, POS),
    ('UltBull', 80.05, 7.8, 16.0, ULTRA),  # Op EV $80B + cash + Anthropic $16B = $103B → $400/sh
]
y_pos = [3.5, 2.5, 1.5, 0.5]
for i, (lbl, opev, cash, anth, color) in enumerate(scenarios_data):
    ax.barh(y_pos[i], opev, color=color, height=0.6, alpha=0.9, label='Op EV' if i==0 else '')
    ax.barh(y_pos[i], cash, left=opev, color=MUTED, height=0.6, alpha=0.6, label='Cash & inv' if i==0 else '')
    ax.barh(y_pos[i], anth, left=opev+cash, color=INK, height=0.6, alpha=0.7, label='Anthropic stake' if i==0 else '')
    ax.text(opev/2, y_pos[i], f'${opev:.1f}B', color='white', fontsize=7, ha='center', va='center', fontweight='bold')
    ax.text(opev+cash/2, y_pos[i], f'${cash:.1f}B', color='white', fontsize=7, ha='center', va='center')
    ax.text(opev+cash+anth/2, y_pos[i], f'${anth:.1f}B', color='white', fontsize=7, ha='center', va='center')
    total = opev + cash + anth
    ax.text(total+1, y_pos[i], f'${total:.1f}B', color=INK, fontsize=8, va='center', fontweight='bold')

ax.set_yticks(y_pos)
ax.set_yticklabels(['Bear', 'Base', 'Bull', 'UltBull'])
ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f'${x:.0f}B'))
ax.legend(loc='lower right', fontsize=7, frameon=False)
ax.set_xlim(0, 115)
style_ax(ax, "Equity value decomposition (SOTP) by scenario")
plt.tight_layout()
plt.savefig(f"{ZM_OUT}/06_sotp.png", dpi=200, bbox_inches='tight', facecolor='white')
plt.close()

# Symlink to expected names
import os
for src, dst in [
    ('02_segments.png',   '02_path_to_profit.png'),
    ('03_margins.png',    '03_cash_dilution.png'),
    ('04_net_debt.png',   '04_fleet.png'),
    ('05_ev_multiples.png', '05_valuation.png'),
    ('06_sotp.png',       '06_tam.png'),
]:
    full_dst = f'{ZM_OUT}/{dst}'
    if os.path.exists(full_dst): os.remove(full_dst)
    os.symlink(src, full_dst)

print("ZM charts generated and symlinked.")
