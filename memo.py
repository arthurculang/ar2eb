"""
memo.py · v001 · 2026-05-18_07-00
AR2EB investment memo PDF generator (parameterized, single-file).

Usage:
    python memo.py <ticker>      # e.g. python memo.py joby

Reads from /data/<ticker>.yml as the single source of truth for all
ticker-specific data. Dispatches on `dcf_type` for layout and math
differences between Young-Company DCF (Damodaran), Mature-Company DCF,
and Mature-Company DCF with SOTP framing.

Produces a 5-page landscape legal (14" × 8.5") PDF:
  · Page 1: qualitative narrative (central question, thesis, scenarios,
    forward-value chart, weighting rationale)
  · Page 2: scenario narratives (4-column layout, full narrative per scenario)
  · Page 3: business snapshot (six matplotlib-rendered charts, ticker-specific
    chart suite at charts/<ticker>/)
  · Page 4: quantitative model (assumptions, DCF table, equity build,
    future fair value, pushback, falsification triggers)
  · Page 5: disclaimers + glossary

Design system (per memo-spec v020):
  · Inter throughout (sans); JetBrains Mono for numbers/data/version stamps
  · Single accent (desaturated indigo) on eyebrows; semantic red/green on upside
  · Restraint over decoration; whitespace is content; tabular numbers right-aligned

Schema versioning: /data/<ticker>.yml is schema v002 (locked 2026-05-18).
Generator versioning: this file replaces the four chartfix14 per-ticker
generators (joby/aur/lth/zm). All four produce visually-equivalent PDFs.
"""

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth

import sys
import yaml
from pathlib import Path

# ═════════════════════════════════════════════════════════════════════════════
# DATA LOADING — single source of truth: /data/{ticker}.yml
# ═════════════════════════════════════════════════════════════════════════════
def parse_args():
    if len(sys.argv) != 2:
        print("Usage: python memo.py <ticker>", file=sys.stderr)
        print("       e.g. python memo.py joby", file=sys.stderr)
        sys.exit(1)
    return sys.argv[1].lower()

def load_data(ticker):
    yml_path = Path(__file__).parent / "data" / f"{ticker}.yml"
    if not yml_path.exists():
        raise FileNotFoundError(f"Data file not found: {yml_path}")
    with open(yml_path) as f:
        data = yaml.safe_load(f)
    prob_sum = sum(s['probability'] for s in data['scenarios'].values())
    if abs(prob_sum - 1.0) > 0.001:
        raise ValueError(f"{ticker}: probabilities sum to {prob_sum}, not 1.0")
    return data

TICKER = parse_args()
DATA = load_data(TICKER)
DCF_TYPE = DATA['dcf_type']

# ═════════════════════════════════════════════════════════════════════════════
# DCF-TYPE DISPATCH — handles per-type display + math differences
# ═════════════════════════════════════════════════════════════════════════════
def subtitle_for(dcf_type):
    return {
        'young_company':        'Young-Company DCF (Damodaran)',
        'mature_company':       'Mature-Company DCF',
        'mature_company_sotp':  'Mature-Company DCF (SOTP)',
    }[dcf_type]

def format_masthead_extras(data):
    m = data['market']
    parts = [f"${m['market_cap_billion']:.1f}B mkt cap"]
    sh = m['shares_outstanding_million']
    sh_str = f"{sh/1000:.2f}B sh" if sh >= 1000 else f"{sh:.0f}M sh"
    parts.append(sh_str)
    cash = m['cash_billion']
    debt = m['net_debt_billion']
    if debt > 0:
        parts.append(f"${cash:.2f}B cash, ${debt:.2f}B net debt")
    else:
        parts.append(f"${cash:.1f}B cash, zero debt" if cash >= 1
                     else f"${cash:.2f}B cash, no debt")
    parts.extend(data['market'].get('extras', []))
    return "   ·   ".join(parts)

def ribbon_metrics(sc, dcf_type):
    """Reads from flattened scenario dict (dcf_metrics fields are at top level)."""
    if dcf_type == 'young_company':
        return [
            ('TAM',    f"{sc['tam_share']:.1f}%"),
            ('P(fail)',f"{sc['p_fail']:.0f}%"),
            ('S2C',    f"{sc['s2c']:.1f}"),
            ('Prob',   f"{sc['probability']*100:.0f}%"),
        ]
    elif dcf_type == 'mature_company':
        return [
            ('CAGR',   f"{sc['cagr_5y']:+.1f}%"),
            ('WACC',   f"{sc['wacc']*100:.1f}%"),
            ('SLB',    f"${sc['slb_total_5y']:.1f}B"),
            ('Prob',   f"{sc['probability']*100:.0f}%"),
        ]
    elif dcf_type == 'mature_company_sotp':
        return [
            ('CAGR',   f"{sc['cagr_5y']:+.1f}%"),
            ('WACC',   f"{sc['wacc']*100:.1f}%"),
            ('Anth',   f"${sc['anthropic_stake']:.0f}B"),
            ('Prob',   f"{sc['probability']*100:.0f}%"),
        ]
    raise ValueError(f"Unknown dcf_type: {dcf_type}")

def dcf_period_years(dcf_type):
    """Length of explicit DCF horizon in years."""
    return 10 if dcf_type == 'young_company' else 5

def dcf_year_labels(dcf_type):
    """FY labels for the DCF horizon."""
    if dcf_type == 'young_company':
        return [f"FY{27+i}" for i in range(10)]
    else:
        return [f"FY{26+i}" for i in range(5)]

def assumptions_rows(sc, dcf_type, data):
    """Page 4 ASSUMPTIONS block rows."""
    if dcf_type == 'young_company':
        tam = data.get('chart_reference', {}).get('tam_billion', 0)
        return [
            (f"TAM Year-10 ($B)",         f"{tam:.0f}"),
            ("Mature share (%)",          f"{sc['tam_share']:.1f}"),
            ("Mature op margin (%)",      f"{sc['op_margin'][-1]*100:.0f}"),
            ("Sales-to-capital",          f"{sc['s2c']:.1f}"),
            ("Terminal WACC (%)",         f"{sc['wacc_path'][-1]*100:.1f}"),
            ("Terminal growth (%)",       f"{sc['term_g']*100:.1f}"),
            ("P(failure) (%)",            f"{sc['p_fail']}"),
            ("Scenario probability (%)",  f"{sc['probability']*100:.0f}"),
        ]
    elif dcf_type == 'mature_company':
        return [
            ("5y revenue CAGR (%)",       f"{sc['cagr_5y']:+.1f}"),
            ("Year-5 op margin (%)",      f"{sc['op_margin'][-1]*100:.1f}"),
            ("WACC (%)",                  f"{sc['wacc']*100:.1f}"),
            ("Terminal growth (%)",       f"{sc['term_g']*100:.1f}"),
            ("5y SLB total ($B)",         f"{sc['slb_total_5y']:.2f}"),
            ("Starting revenue ($B)",     f"{sc['rev_b']:.2f}"),
            ("Scenario probability (%)",  f"{sc['probability']*100:.0f}"),
        ]
    elif dcf_type == 'mature_company_sotp':
        return [
            ("5y revenue CAGR (%)",       f"{sc['cagr_5y']:+.1f}"),
            ("Year-5 op margin (%)",      f"{sc['op_margin'][-1]*100:.1f}"),
            ("WACC (%)",                  f"{sc['wacc']*100:.1f}"),
            ("Terminal growth (%)",       f"{sc['term_g']*100:.1f}"),
            ("Anthropic stake ($B)",      f"{sc['anthropic_stake']:.1f}"),
            ("Starting revenue ($B)",     f"{sc['rev_b']:.2f}"),
            ("Scenario probability (%)",  f"{sc['probability']*100:.0f}"),
        ]
    raise ValueError(f"Unknown dcf_type: {dcf_type}")

def equity_build_rows(sc, dcf_type):
    """Page 4 EQUITY BUILD section. Format: (label, value, kind) where kind is normal|subtotal|total."""
    if dcf_type == 'young_company':
        return [
            ("Operating EV",          f"${sc['op_ev']:.2f}B",         "normal"),
            ("+ Cash & investments",  f"${sc['cash']:.2f}B",          "normal"),
            ("= Equity value",        f"${sc['total_equity']:.2f}B",  "subtotal"),
            ("Raised over period",    f"${sc['raise_total']:.2f}B",   "normal"),
            ("Dilution by FY36",      f"+{sc['dilution_pct']}%",      "normal"),
            ("FY36 shares (M)",       f"{sc['final_shares']:,}",      "normal"),
            ("DCF per share",         f"${sc['dcf_per_share']:.2f}",  "subtotal"),
            (f"× (1−P_fail) [{100-sc['p_fail']}%]",
                                      f"${(1-sc['p_fail']/100)*sc['dcf_per_share']:.2f}", "normal"),
            (f"+ P_fail × distress [{sc['p_fail']}% × ${sc['distress']:.2f}]",
                                      f"${sc['p_fail']/100 * sc['distress']:.2f}", "normal"),
            ("= Expected per share",  f"${sc['expected_per_share']:.2f}",  "total"),
        ]
    elif dcf_type == 'mature_company':
        rows = [
            ("Operating EV",          f"${sc['op_ev']:.2f}B",         "normal"),
            ("+ Cash & investments",  f"${sc['cash']:.2f}B",          "normal"),
        ]
        if sc.get('net_debt', 0) > 0:
            rows.append(("− Net debt",            f"${sc['net_debt']:.2f}B",      "normal"))
        rows.extend([
            ("= Equity value",        f"${sc['total_equity']:.2f}B",  "subtotal"),
            ("FY30 shares (M)",       f"{sc['final_shares']:,}",      "normal"),
            ("= Expected per share",  f"${sc['expected_per_share']:.2f}",  "total"),
        ])
        return rows
    elif dcf_type == 'mature_company_sotp':
        # Label the special-assets row from the YAML (e.g. "Anthropic stake" for ZM)
        sa_label = "+ Anthropic stake" if 'anthropic_stake' in sc else "+ Special assets"
        rows = [
            ("Operating EV",          f"${sc['op_ev']:.2f}B",            "normal"),
            ("+ Cash & investments",  f"${sc['cash']:.2f}B",             "normal"),
            (sa_label,                f"${sc.get('special_assets', 0):.2f}B", "normal"),
        ]
        if sc.get('net_debt', 0) > 0:
            rows.append(("− Net debt",            f"${sc['net_debt']:.2f}B",         "normal"))
        rows.extend([
            ("= Equity value",        f"${sc['total_equity']:.2f}B",     "subtotal"),
            ("FY30 shares (M)",       f"{sc['final_shares']:,}",         "normal"),
            ("= Expected per share",  f"${sc['expected_per_share']:.2f}",  "total"),
        ])
        return rows
    raise ValueError(f"Unknown dcf_type: {dcf_type}")


# ── Font registration ────────────────────────────────────────────────────────
# Path translation (migration prompt v005 §4): sandbox paths → repo paths,
# resolved relative to this file so the generator runs from any CWD.
_REPO = Path(__file__).parent
FONT_DIR = str(_REPO / "public" / "assets" / "fonts")
JBM_DIR = str(_REPO / "public" / "assets" / "fonts")  # Inter + JBM flattened into one dir

pdfmetrics.registerFont(TTFont("Inter",     f"{FONT_DIR}/Inter-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Inter-Med", f"{FONT_DIR}/Inter-Medium.ttf"))
pdfmetrics.registerFont(TTFont("Inter-SB",  f"{FONT_DIR}/Inter-SemiBold.ttf"))
pdfmetrics.registerFont(TTFont("Inter-Bold", f"{FONT_DIR}/Inter-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Inter-It",  f"{FONT_DIR}/Inter-Italic.ttf"))
pdfmetrics.registerFont(TTFont("Mono",      f"{JBM_DIR}/JetBrainsMono-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Mono-Bold", f"{JBM_DIR}/JetBrainsMono-Bold.ttf"))

# ── Page: landscape legal ────────────────────────────────────────────────────
PAGE_W = 14.0 * inch       # 1008
PAGE_H = 8.5 * inch        # 612
MARGIN_L = 1.0 * inch      # 72
MARGIN_R = 1.0 * inch
MARGIN_T = 0.55 * inch     # 40
MARGIN_B = 0.55 * inch     # 40 — bumped to fit 3-line footer with disclaimer
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R   # 864

# Three columns
GUTTER = 16
COL_W = (CONTENT_W - 3 * GUTTER) / 4       # 4-column layout per spec §6c.11
COL_XS = [MARGIN_L + i * (COL_W + GUTTER) for i in range(4)]

# ── Palette: true neutrals + one accent + semantic only ──────────────────────
PAPER = HexColor("#fafafa")        # off-white neutral
INK = HexColor("#18181b")          # zinc-900
TEXT = HexColor("#3f3f46")         # zinc-700
MUTED = HexColor("#71717a")        # zinc-500
DIM = HexColor("#a1a1aa")          # zinc-400
RULE = HexColor("#e4e4e7")         # zinc-200
RULE_STRONG = HexColor("#18181b")  # ink, for thick rules

ACCENT = HexColor("#1e3a8a")       # indigo-900 — desaturated blue, used surgically

# Semantic finance — only where they carry meaning
POS = HexColor("#15803d")          # green-700
NEG = HexColor("#b91c1c")          # red-700

# Unified logo per spec §6c.15 — updated with new tagline baked into asset
# (1990x459 cropped; "LONG HORIZONS · STRUCTURAL SHIFTS · IMAGINATION" replaces prior tagline)
LOGO_UNIFIED = str(_REPO / "public" / "assets" / "ar2eb-logo-v3-cropped.png")
LOGO_COLORFUL = LOGO_UNIFIED  # back-compat alias for existing references
LOGO_MONO = LOGO_UNIFIED
# Aspect ratios (width / height) derived from source files
LOGO_UNIFIED_AR  = 1990 / 459   # ≈ 4.34 — boxed AR2EB + Long-Horizons tagline mark (v3)
LOGO_COLORFUL_AR = LOGO_UNIFIED_AR  # back-compat alias
LOGO_MONO_AR     = LOGO_UNIFIED_AR  # back-compat alias
# Backward-compatibility alias; some sections still reference LOGO_PATH
LOGO_PATH = LOGO_COLORFUL
CHARTS_DIR = str(_REPO / "charts" / TICKER)
# v999__refactored is a non-canonical sentinel for Setup-phase compare runs:
# it never collides with real versions and keeps the immutable canonical
# PDFs pristine. The real version-stamp convention is a workflow decision
# (migration prompt v005 step 7) — surfaced separately, not codified here.
OUT_PATH = str(_REPO / "public" / "memos" / f"{TICKER}-memo__v999__refactored.pdf")
SPOT = DATA['spot']
c = canvas.Canvas(OUT_PATH, pagesize=(PAGE_W, PAGE_H))


# ═════════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════════
def fill_bg():
    c.setFillColor(PAPER)
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)


def text(x, y, s, font="Inter", size=9, color=INK, anchor="left"):
    c.setFont(font, size)
    c.setFillColor(color)
    if anchor == "left":
        c.drawString(x, y, s)
    elif anchor == "right":
        c.drawRightString(x, y, s)
    elif anchor == "center":
        c.drawCentredString(x, y, s)


def hline(x1, x2, y, color=RULE, width=0.4):
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.line(x1, y, x2, y)


def wrap_text(s, font, size, max_w):
    words = s.split()
    lines, current = [], ""
    for word in words:
        cand = current + " " + word if current else word
        if stringWidth(cand, font, size) <= max_w:
            current = cand
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_paragraph(x, y, s, font="Inter", size=9, color=TEXT,
                   max_w=None, line_height=None):
    if max_w is None:
        max_w = CONTENT_W
    if line_height is None:
        line_height = size * 1.5
    for line in wrap_text(s, font, size, max_w):
        text(x, y, line, font=font, size=size, color=color)
        y -= line_height
    return y


def draw_paragraph_with_indent(x, y, s, first_line_indent=0,
                                font="Inter", size=9, color=TEXT,
                                max_w=None, line_height=None):
    """Like draw_paragraph but first line is indented (e.g., after an inline label).
    The first line of body text starts at x + first_line_indent and may be shorter
    than max_w by that amount; subsequent lines wrap to the full max_w from x."""
    if max_w is None:
        max_w = CONTENT_W
    if line_height is None:
        line_height = size * 1.5

    # First line: shorter by indent
    words = s.split()
    first_line_words = []
    first_max = max_w - first_line_indent
    while words:
        cand = " ".join(first_line_words + [words[0]])
        if stringWidth(cand, font, size) <= first_max:
            first_line_words.append(words.pop(0))
        else:
            break
    first_line = " ".join(first_line_words)
    text(x + first_line_indent, y, first_line,
         font=font, size=size, color=color)
    y -= line_height

    # Remaining wraps at full width from x
    remaining = " ".join(words)
    if remaining:
        y = draw_paragraph(x, y, remaining,
                           font=font, size=size, color=color,
                           max_w=max_w, line_height=line_height)
    return y


def eyebrow(x, y, label, color=ACCENT):
    """Section eyebrow — small caps, semibold, accent color."""
    text(x, y, label, font="Inter-SB", size=7, color=color)


def cagr(path):
    p = 1.0
    for g in path:
        p *= (1 + g)
    return p ** (1/len(path)) - 1


def avg(path):
    return sum(path) / len(path)


def page_footer(page_label, show_disclaimer_pointer=True):
    fy = MARGIN_B - 12
    hline(MARGIN_L, PAGE_W - MARGIN_R, fy + 18, color=RULE)
    # Disclaimer line — most prominent footer info
    if show_disclaimer_pointer:
        disclaimer_text = "NOT INVESTMENT ADVICE  ·  Not from a registered investment advisor  ·  AI-assisted analysis  ·  Author may hold positions  ·  See full disclaimers, page 5"
    else:
        # On page 3 itself, the disclaimers ARE here — no need to point elsewhere
        disclaimer_text = "NOT INVESTMENT ADVICE  ·  Not from a registered investment advisor  ·  AI-assisted analysis  ·  Author may hold positions"
    text(MARGIN_L, fy + 6, disclaimer_text,
         font="Inter-SB", size=6.5, color=INK)
    # Version stamp + page label below
    text(MARGIN_L, fy - 4,
         "v006 · 2026-05-17_14-00 · derived from joby-dcf-valuation__v007__2026-05-17_14-00.jsx (canonical)",
         font="Mono", size=6, color=MUTED)
    text(PAGE_W - MARGIN_R, fy - 4,
         f"Alameda Research 2: Electric Boogaloo (AR2EB)  ·  arthur@culang.co  ·  {page_label}",
         font="Inter", size=6, color=MUTED, anchor="right")


# ═════════════════════════════════════════════════════════════════════════════
# SCENARIOS — flattened from /data/{ticker}.yml for backward compatibility
# Existing code expects flat fields: sc["rev_path"], sc["tam_share"], etc.
# YAML structure nests these under dcf_path/dcf_metrics/chart_data — we flatten
# at load time so downstream rendering code works unchanged.
# ═════════════════════════════════════════════════════════════════════════════
def _flatten_scenario(name, sc, spot):
    """Merge dcf_path + dcf_metrics + top-level fields into single flat dict."""
    flat = {
        "label": sc["label"],
        "headline": sc["headline"],
        "narrative": sc["narrative"],
        "probability": sc["probability"],
        "probability_rationale": sc["probability_rationale"],
        "expected_per_share": sc["expected_per_share"],
    }
    # Derived: price (alias of expected_per_share), upside
    flat["price"] = sc["expected_per_share"]
    flat["upside"] = (sc["expected_per_share"] / spot - 1) * 100
    # Spread DCF metrics + path into flat dict
    flat.update(sc.get("dcf_metrics", {}))
    flat.update(sc.get("dcf_path", {}))
    # Keep chart_data nested — chart builders read it that way
    flat["chart_data"] = sc.get("chart_data", {})
    return flat

SCENARIOS = {
    name: _flatten_scenario(name, sc, SPOT)
    for name, sc in DATA["scenarios"].items()
}

# ── Probability-weighted expected fair value ────────────────────────────────
# Each scenario's `probability` field weights the scenarios. Computed once
# here and used on both Page 1 and Page 3.
def _prob_weighted_today():
    return sum(s["probability"] * s["expected_per_share"] for s in SCENARIOS.values())

def _prob_weighted_at_year(T):
    # weighted(T) = Σ p_i × expected_per_share_i × (1 + terminal_WACC_i)^T
    return sum(
        s["probability"] * s["expected_per_share"] * (1 + s["wacc_path"][-1])**T
        for s in SCENARIOS.values()
    )

PW_EXPECTED = _prob_weighted_today()
PW_UPSIDE = (PW_EXPECTED / SPOT - 1) * 100
PW_YEARS = [5, 10, 15, 20]
PW_FFV = [(T, _prob_weighted_at_year(T)) for T in PW_YEARS]

# Sanity check: probabilities sum to 1.0
_p_sum = sum(s["probability"] for s in SCENARIOS.values())
assert abs(_p_sum - 1.0) < 0.001, f"Probabilities sum to {_p_sum}, not 1.0"

GLOSSARY = [
    ("eVTOL",
     "Electric Vertical Take-Off and Landing aircraft. Joby's S4 is a 5-seat, 6-rotor design with ~100-mile range."),
    ("Type Certification",
     "FAA approval to operate a new aircraft design commercially. Joby is in Stage 4 (final) of 4-stage process."),
    ("eIPP",
     "eVTOL Integration Pilot Program. White House-backed initiative letting Joby fly in US states pre-Type Cert."),
    ("Dubai RTA",
     "Roads & Transport Authority. Awarded Joby exclusive eVTOL air-taxi rights in Dubai through 2032."),
    ("Toyota partnership",
     "$894M total investment. Joint manufacturing program at Dayton, Ohio facility for production scale."),
    ("Blade",
     "Helicopter-based mobility business acquired in 2024 — gives Joby existing routes (NYC-airport) for early ops."),
]


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 1 — QUALITATIVE
# ═════════════════════════════════════════════════════════════════════════════
fill_bg()
y = PAGE_H - MARGIN_T

# ── Masthead with logo (Page 1 uses colorful Boogaloo brand mark) ──────────
LOGO_W = 200  # spec §6c.12: re-tuned for new unified-logo AR
LOGO_H = LOGO_W / LOGO_COLORFUL_AR  # ≈ 74pt, preserves aspect ratio
# Draw logo on the left
c.drawImage(LOGO_COLORFUL, MARGIN_L, y - LOGO_H,
            width=LOGO_W, height=LOGO_H, mask='auto')

# Right side: research title information vertically arranged inside logo height
right_x = MARGIN_L + LOGO_W + 40
right_end = PAGE_W - MARGIN_R

# Top eyebrow — small caps, prominent disclaimer
text(right_x, y - 6,
     "INTERNAL RESEARCH  ·  MEMO  ·  NOT INVESTMENT ADVICE  ·  AI-ASSISTED",
     font="Inter-SB", size=7, color=ACCENT)
text(right_end, y - 6, "16 May 2026  ·  the qualitative",
     font="Inter", size=7.5, color=MUTED, anchor="right")

# Middle: Company name + price (vertically centered to logo)
mid_y = y - LOGO_H / 2 - 4
text(right_x, mid_y, DATA['company'],
     font="Inter-SB", size=18, color=INK)
text(right_end, mid_y, f"${SPOT:.2f}",
     font="Mono-Bold", size=18, color=INK, anchor="right")

# Subtitle row — near bottom of logo
sub_y = y - LOGO_H + 2
text(right_x, sub_y, f"{DATA['exchange']} : {DATA['ticker']}   ·   {subtitle_for(DCF_TYPE)}",
     font="Inter", size=8.5, color=MUTED)
text(right_end, sub_y, format_masthead_extras(DATA),
     font="Inter", size=8.5, color=MUTED, anchor="right")

# Advance past masthead block
y -= LOGO_H + 10
hline(MARGIN_L, PAGE_W - MARGIN_R, y, color=RULE_STRONG, width=0.6)
y -= 16

# ── Two-column layout (per memo-spec §6c.9): central question + PW block live in
# the LEFT column; chart extends vertically across the full column band on the right.
# Define columns FIRST so wrap_text() can use LEFT_W consistently throughout.
LEFT_W = CONTENT_W * 0.56
RIGHT_X = MARGIN_L + LEFT_W + 24
RIGHT_W = CONTENT_W - LEFT_W - 24
COL_TOP = y  # top of the two-column band — chart top aligns here

# ── Central question + thesis paragraph ─────────────────────────────────────
eyebrow(MARGIN_L, y, "THE CENTRAL QUESTION")
y -= 16

# Display headline — paired framing from YAML
question = DATA['central_question'].strip()
q_lines = wrap_text(question, "Inter", 14, LEFT_W)
for line in q_lines:
    text(MARGIN_L, y, line, font="Inter", size=14, color=INK)
    y -= 17
y -= 2

thesis = DATA['thesis'].strip()
y = draw_paragraph(MARGIN_L, y, thesis, font="Inter", size=9, color=TEXT,
                   max_w=LEFT_W, line_height=11.5)
y -= 10

# ═════════════════════════════════════════════════════════════════════════════
# PROBABILITY-WEIGHTED EXPECTED VALUE — full block with visual + commentary
# ═════════════════════════════════════════════════════════════════════════════
eyebrow(MARGIN_L, y, "PROBABILITY-WEIGHTED EXPECTED VALUE")
y -= 28

# Layout: left half = headline numbers + forward years + commentary
#         right half = contribution bar chart
BLOCK_TOP = COL_TOP  # spec §6c.9: chart top aligns with central question (left column top), not below
# Column dimensions moved earlier (see top of this section)

# ── LEFT: headline expected value ─────────────────────────────────
pw_color = POS if PW_EXPECTED >= SPOT else NEG
pw_sign = "+" if PW_UPSIDE >= 0 else ""

# Spec §6c.8: label x position derived from rendered width of the big number,
# not a fixed offset. Prevents overlap on tickers with wider expected values (e.g. $159.83).
_big_text = f"${PW_EXPECTED:.2f}"
text(MARGIN_L, y, _big_text, font="Mono-Bold", size=28, color=INK)
_big_w = pdfmetrics.stringWidth(_big_text, "Mono-Bold", 28)
_label_x = MARGIN_L + _big_w + 14  # 14pt buffer between big number and label
text(_label_x, y, "expected fair value today",
     font="Inter", size=10, color=MUTED)
text(_label_x, y - 14, f"{pw_sign}{PW_UPSIDE:.1f}% vs spot ${SPOT:.2f}",
     font="Mono", size=10, color=pw_color)

y -= 38

# Forward compounded value table — text complement to the chart's multiplier labels
text(MARGIN_L, y, "FORWARD COMPOUNDED VALUE",
     font="Inter-SB", size=7.5, color=MUTED)
y -= 14

ffv_col_w = LEFT_W / 4
for i, (T, val) in enumerate(PW_FFV):
    x = MARGIN_L + ffv_col_w * i
    mult = val / SPOT
    mc = POS if val >= SPOT else NEG
    text(x, y, f"+{T}y",
         font="Inter-SB", size=8, color=MUTED)
    text(x, y - 14, f"${val:,.2f}",
         font="Mono", size=12, color=INK)
    text(x, y - 27, f"{mult:.2f}× spot",
         font="Mono", size=8, color=mc)

y -= 34

# Analytical commentary — the heft
text(MARGIN_L, y, "WEIGHTING RATIONALE",
     font="Inter-SB", size=7.5, color=MUTED)
y -= 12

# Per-scenario justifications — loaded from YAML
rationales = [(r['label'], r['body']) for r in DATA['weighting_rationale']]
for label, body in rationales:
    # Render label inline as bold accent prefix, then continue body
    text(MARGIN_L, y, label, font="Inter-SB", size=8, color=ACCENT)
    label_w = stringWidth(label + "  ", "Inter-SB", 8)
    # Render body as a paragraph starting after the label; subsequent lines wrap to left margin
    y_after = draw_paragraph_with_indent(
        MARGIN_L, y, body,
        first_line_indent=label_w,
        font="Inter", size=8, color=TEXT,
        max_w=LEFT_W, line_height=10.5)
    y = y_after - 2

y -= 2

# Decomposition insight — computed from scenario weights (not hardcoded)
PW_BULL_CONTRIB = SCENARIOS['bull']['probability'] * SCENARIOS['bull']['expected_per_share']
PW_ULTRA_CONTRIB = SCENARIOS['ultra_bull']['probability'] * SCENARIOS['ultra_bull']['expected_per_share']
PW_TAIL_CONTRIB = PW_BULL_CONTRIB + PW_ULTRA_CONTRIB
PW_TAIL_PCT = PW_TAIL_CONTRIB / PW_EXPECTED * 100
_bull_pct = int(round(SCENARIOS['bull']['probability'] * 100))
_ultra_pct = int(round(SCENARIOS['ultra_bull']['probability'] * 100))
_combined_pct = _bull_pct + _ultra_pct
_spot_vs_pw = abs((SPOT / PW_EXPECTED - 1) * 100)
_spot_position = "above" if SPOT > PW_EXPECTED else "below"
insight = (f"Bull ({_bull_pct}%) + Ultra Bull ({_ultra_pct}%) together contribute "
           f"${PW_TAIL_CONTRIB:.2f} — {PW_TAIL_PCT:.0f}% of the ${PW_EXPECTED:.2f} expected value "
           f"despite {_combined_pct}% combined probability. "
           f"Today's spot (${SPOT:.2f}) sits {_spot_vs_pw:.0f}% {_spot_position} the weighted expected; "
           f"forward-weighted value crosses spot between +5y and +10y.")
y = draw_paragraph(MARGIN_L, y, insight,
                   font="Inter", size=8.5, color=TEXT,
                   max_w=LEFT_W, line_height=11)

# ── RIGHT: forward-value path chart with historical price ─────────────────────
# X-axis: historical period (since IPO) on the left + 20-year projection on the right.
# Y-axis: log scale; bounds adapt to data.
# Historical (gray, thin): actual market price quarterly closes from IPO to today.
# Today (bold black dot): current spot.
# Projection lines: each scenario's fair-value compounded path at terminal WACC.
# Weighted line (thick black): probability-weighted expected value path.
# Multiplier labels (#.##×) at +5/+10/+15/+20y on each line, vs spot.
# NOTE: Historical prices are approximate quarterly closes from analyst memory,
# included for shape only. Replace with actual data feed for distribution.
import math

# Historical prices loaded from YAML; final (0, spot) point appended at runtime
HIST_PRICE = [(p[0], p[1]) for p in DATA['historical_prices']['points']] + [(0.0, SPOT)]
X_MIN = DATA['historical_prices']['x_min']
X_MAX = 20.0   # years projected forward
IPO_MARKER = DATA['historical_prices']['ipo_marker']

y_chart_top = BLOCK_TOP + 6
y_chart_bot = y + 8
chart_h = y_chart_top - y_chart_bot
chart_w = RIGHT_W

# Title
text(RIGHT_X, y_chart_top + 4,
     "PRICE + PROJECTIONS  ·  HISTORICAL THROUGH PROBABILITY-WEIGHTED FORWARD",
     font="Inter-SB", size=7.5, color=MUTED)

# Plot area
plot_left = RIGHT_X + 28
plot_right = RIGHT_X + chart_w - 60  # spec §6c.10: extra padding for multiplier-in-label
plot_bot = y_chart_bot + 16
plot_top = y_chart_top - 22

# ── Forward paths (computed early so y_max can adapt) ─────────────
def scenario_path(sc):
    base = sc["expected_per_share"]
    wacc = sc["wacc_path"][-1]
    return [(t, base * (1 + wacc) ** t) for t in range(21)]

bear_path = scenario_path(SCENARIOS["bear"])
base_path = scenario_path(SCENARIOS["base"])
bull_path = scenario_path(SCENARIOS["bull"])
ultra_bull_path = scenario_path(SCENARIOS["ultra_bull"])

def weighted_at(t):
    return sum(
        s["probability"] * s["expected_per_share"] * (1 + s["wacc_path"][-1]) ** t
        for s in SCENARIOS.values()
    )
weighted_path = [(t, weighted_at(t)) for t in range(21)]

# ── Benchmark reference lines (per memo-spec §6c.5) ───────────────
# Starting at spot today, compounded forward at constant annual rates.
# Rates per memo-spec §6c.5: 4.5%/yr (10-yr Treasury current range) and
# 8.5%/yr (S&P 500 forward consensus nominal). Reference benchmarks for
# "what could you have done with this money instead" framing — visually
# subordinate to scenario lines (dotted, neutral gray, lighter weight).
TREASURY_RATE = 0.045
EQUITY_RATE = 0.085
treasury_path = [(t, SPOT * (1 + TREASURY_RATE) ** t) for t in range(21)]
equity_path = [(t, SPOT * (1 + EQUITY_RATE) ** t) for t in range(21)]

# Y range — log scale, y_max auto-computed from max forward value at +20y.
# Spec rule (memo-spec §7): y_max = max(200, max_fwd × 1.5) where max_fwd is the
# highest forward value across bear/base/bull/weighted at the +20y horizon.
# This prevents endpoint clipping that would compress scenarios visually at the top.
# ── y_min: data-adaptive lower bound (per memo-spec §6c.6) ────────
# If any scenario has non-positive values (e.g. LTH bear implied bankruptcy),
# keep y_min low so the wipeout is visible. Otherwise, lift y_min toward the
# min positive value to compress empty space and give visible scenarios more
# vertical spread.
_all_path_vals = []
for _p in (bear_path, base_path, bull_path, weighted_path, treasury_path, equity_path):
    _all_path_vals.extend(v for _, v in _p)
_all_path_vals.extend(v for _, v in HIST_PRICE)
_has_neg = any(v <= 0 for v in _all_path_vals)
if _has_neg:
    y_min = 0.10
else:
    _min_pos = min(v for v in _all_path_vals if v > 0)
    # Spec §6c.6: y_min = largest log-decade ≤ min positive value
    _y_min_raw = 10 ** math.floor(math.log10(_min_pos))
    y_min = max(0.10, min(100.0, _y_min_raw))

_max_fwd = max(
    bear_path[-1][1], base_path[-1][1], bull_path[-1][1], ultra_bull_path[-1][1], weighted_path[-1][1],
    treasury_path[-1][1], equity_path[-1][1]  # include benchmarks per §6c.5 + ultra_bull
)
# Round up to a nice "ceiling" value for the chart's top edge
import math as _m
if _max_fwd <= 180:
    y_max = 200.0
elif _max_fwd <= 900:
    y_max = 1000.0
elif _max_fwd <= 1800:
    y_max = 2000.0
elif _max_fwd <= 9000:
    y_max = 10000.0
else:
    # Generic fallback: 1.5× ceiling rounded to nearest power of 10
    y_max = 10 ** _m.ceil(_m.log10(_max_fwd * 1.5))
log_min, log_max = math.log10(y_min), math.log10(y_max)

def y_pixel(val):
    v = max(min(val, y_max), y_min)
    return plot_bot + (math.log10(v) - log_min) / (log_max - log_min) * (plot_top - plot_bot)

def x_pixel(t):
    """Map year offset (X_MIN to X_MAX) to pixel."""
    return plot_left + ((t - X_MIN) / (X_MAX - X_MIN)) * (plot_right - plot_left)

# Y-axis tick labels + gridlines
for tick_val in [0.10, 1.0, 10.0, 100.0, 1000.0, 10000.0]:
    if tick_val > y_max or tick_val < y_min:
        continue  # skip ticks outside chart range
    ty = y_pixel(tick_val)
    text(plot_left - 4, ty - 2,
         f"${tick_val:.2f}" if tick_val < 1 else f"${tick_val:.0f}",
         font="Mono", size=6, color=MUTED, anchor="right")
    c.setStrokeColor(RULE)
    c.setLineWidth(0.3)
    c.line(plot_left, ty, plot_right, ty)

# X-axis baseline + tick marks
c.setStrokeColor(RULE)
c.setLineWidth(0.5)
c.line(plot_left, plot_bot, plot_right, plot_bot)
x_ticks = [(-5, "-5y"), (-2, "-2y"), (0, "today"), (5, "+5y"), (10, "+10y"), (15, "+15y"), (20, "+20y")]
for t, label in x_ticks:
    tx = x_pixel(t)
    text(tx, plot_bot - 9, label,
         font="Mono", size=6, color=MUTED, anchor="center")

# Vertical line at "today" separating history from projection
c.setStrokeColor(MUTED)
c.setDash(1, 2)
c.setLineWidth(0.4)
c.line(x_pixel(0), plot_bot, x_pixel(0), plot_top)
c.setDash()

# Spot reference line — dashed horizontal
spot_y_px = y_pixel(SPOT)
c.setStrokeColor(MUTED)
c.setDash(2, 2)
c.setLineWidth(0.6)
c.line(plot_left, spot_y_px, plot_right, spot_y_px)
c.setDash()
text(plot_right - 2, spot_y_px + 2,
     f"spot ${SPOT:.2f}",
     font="Mono", size=6.5, color=MUTED, anchor="right")

# ── Historical price line ──────────────────────────────────────────
c.setStrokeColor(TEXT)
c.setLineWidth(0.9)
p = c.beginPath()
p.moveTo(x_pixel(HIST_PRICE[0][0]), y_pixel(HIST_PRICE[0][1]))
for t, v in HIST_PRICE[1:]:
    p.lineTo(x_pixel(t), y_pixel(v))
c.drawPath(p, stroke=1, fill=0)

# Historical label at IPO point
ipo_t, ipo_v = HIST_PRICE[0]
text(x_pixel(ipo_t) + 2, y_pixel(ipo_v) + 4,
     IPO_MARKER,
     font="Inter", size=5.5, color=MUTED)

# Today's spot price marker — prominent dot
c.setFillColor(INK)
c.circle(x_pixel(0), y_pixel(SPOT), 2.6, fill=1, stroke=0)

# ── Forward projection paths ──────────────────────────────────────
# (scenario paths moved to before chart definition — see y_max block above)

def draw_path(path, color, line_width=0.8):
    c.setStrokeColor(color)
    c.setLineWidth(line_width)
    p = c.beginPath()
    p.moveTo(x_pixel(path[0][0]), y_pixel(path[0][1]))
    for t, v in path[1:]:
        p.lineTo(x_pixel(t), y_pixel(v))
    c.drawPath(p, stroke=1, fill=0)

# Benchmark lines drawn first (subordinate visual weight per §6c.5)
# Light gray, dotted, thin — should read as background reference, not foreground signal
BENCHMARK = colors.Color(0.55, 0.55, 0.55)  # neutral gray
c.setDash(1, 2)  # dotted
draw_path(treasury_path, BENCHMARK, line_width=0.5)
draw_path(equity_path, BENCHMARK, line_width=0.5)
c.setDash()  # reset to solid

# Ultra-bull line drawn with distinctive deep-purple color (trial — JOBY only)
ULTRA_BULL = colors.Color(0.46, 0.16, 0.65)  # deep purple — tail-of-tails signifier
draw_path(bear_path, NEG, line_width=0.7)
draw_path(base_path, ACCENT, line_width=0.7)
draw_path(bull_path, POS, line_width=0.7)
draw_path(ultra_bull_path, ULTRA_BULL, line_width=0.7)
draw_path(weighted_path, INK, line_width=2.0)

# Anchor markers at t=0 (each scenario's starting fair value, distinct from spot)
for sc_key, color in [("bear", NEG), ("base", ACCENT), ("bull", POS), ("ultra_bull", ULTRA_BULL)]:
    s = SCENARIOS[sc_key]
    c.setFillColor(color)
    c.circle(x_pixel(0), y_pixel(s["expected_per_share"]), 1.6, fill=1, stroke=0)
c.setFillColor(INK)
c.circle(x_pixel(0), y_pixel(PW_EXPECTED), 2.2, fill=1, stroke=0)

# ── Multiplier labels (#.##× vs spot) at anchor years ─────────────
# Place labels just above each line's data point at +5/+10/+15/+20y.
# Bear labels go BELOW the line (since it sits at the bottom and other labels stay above).
def annotate_multipliers(path, color, position="above"):
    dy = 4 if position == "above" else -7
    for t, v in path:
        if t in [5, 10, 15]:  # drop +20y per §6c.7 — series label conveys endpoint multiplier
            mult = v / SPOT
            text(x_pixel(t), y_pixel(v) + dy,
                 f"{mult:.2f}×",
                 font="Mono", size=5.5, color=color, anchor="center")

annotate_multipliers(bull_path, POS, "above")
annotate_multipliers(ultra_bull_path, ULTRA_BULL, "above")
annotate_multipliers(weighted_path, INK, "above")
annotate_multipliers(base_path, ACCENT, "below")
annotate_multipliers(bear_path, NEG, "below")

# End-of-line scenario labels (at t=20)
BENCHMARK_LABEL = colors.Color(0.45, 0.45, 0.45)  # slightly darker than line for legibility
# Spec §6c.10: end-of-line labels embed the +20y multiplier rather than as a
# separate annotation. Single text string avoids overlap with the series label.
def _mx(v): return v / SPOT
end_labels = [
    (bear_path[-1][1], f"Bear  {_mx(bear_path[-1][1]):.2f}×",     NEG),
    (base_path[-1][1], f"Base  {_mx(base_path[-1][1]):.2f}×",     ACCENT),
    (weighted_path[-1][1], f"Weighted  {_mx(weighted_path[-1][1]):.2f}×", INK),
    (bull_path[-1][1], f"Bull  {_mx(bull_path[-1][1]):.2f}×",     POS),
    (ultra_bull_path[-1][1], f"Ultra Bull  {_mx(ultra_bull_path[-1][1]):.2f}×", ULTRA_BULL),
    (treasury_path[-1][1], f"Tsy 4.5%  {_mx(treasury_path[-1][1]):.2f}×",  BENCHMARK_LABEL),
    (equity_path[-1][1],   f"S&P 8.5%  {_mx(equity_path[-1][1]):.2f}×",  BENCHMARK_LABEL),
]
end_labels.sort(key=lambda e: e[0])
# Spec rule (memo-spec §7): enforce minimum vertical separation between endpoint
# labels so adjacent scenarios with similar end values (e.g. LTH Weighted vs Base)
# don't render text on top of each other. Adjust labels upward from sorted-bottom
# order so they stack cleanly along the right edge.
MIN_LABEL_SEP_PT = 8.0
label_positions = []
prev_y = None
for val, lbl, col in end_labels:
    raw_y = y_pixel(val) - 2
    if prev_y is not None and raw_y - prev_y < MIN_LABEL_SEP_PT:
        raw_y = prev_y + MIN_LABEL_SEP_PT
    label_positions.append((raw_y, lbl, col))
    prev_y = raw_y
for ly, label, color in label_positions:
    text(plot_right + 4, ly, label, font="Inter-SB", size=6.5, color=color)

# Bottom of block
y = y_chart_bot - 4
hline(MARGIN_L, PAGE_W - MARGIN_R, y, color=RULE)
y -= 16


# ─────────────────────────────────────────────────────────────────────────────
# Scenario column — qualitative
# ─────────────────────────────────────────────────────────────────────────────
def draw_scenario_summary(y_top, col_x, sc):
    """Compact scenario card for Page 1 — label, price, upside, ribbon, one-line headline.
    Full narratives live on Page 2."""
    y = y_top

    # Header row: label (left) + price (right)
    text(col_x, y, sc["label"].upper(),
         font="Inter-SB", size=11, color=INK)
    text(col_x + COL_W, y, f"${sc['price']:.2f}",
         font="Mono-Bold", size=18, color=INK, anchor="right")

    # Upside %
    up_color = POS if sc["upside"] >= 0 else NEG
    sign = "+" if sc["upside"] >= 0 else ""
    text(col_x + COL_W, y - 14, f"{sign}{sc['upside']:.1f}%  vs spot",
         font="Mono", size=8.5, color=up_color, anchor="right")

    y -= 28

    # Two-line metrics ribbon — dispatched per dcf_type (per spec §6c.11)
    rm = ribbon_metrics(sc, DCF_TYPE)
    metric_l1 = f"{rm[0][0]}  {rm[0][1]}    {rm[1][0]}  {rm[1][1]}"
    metric_l2 = f"{rm[2][0]}  {rm[2][1]}     {rm[3][0]}  {rm[3][1]}"
    text(col_x, y,    metric_l1, font="Mono", size=7, color=MUTED)
    text(col_x, y-10, metric_l2, font="Mono", size=7, color=MUTED)

    y -= 18
    hline(col_x, col_x + COL_W, y, color=RULE)
    y -= 12

    # Headline — one-line preview, full narrative on Page 2
    # Per spec §6c.11: 10pt headlines fit better in 4-column narrower cards
    h_lines = wrap_text(sc["headline"], "Inter-Med", 10, COL_W)
    for line in h_lines:
        text(col_x, y, line, font="Inter-Med", size=10, color=INK)
        y -= 13

    return y


def draw_scenario_narrative(y_top, col_x, sc):
    """Full scenario card for Page 2 — label, price, headline, full narrative paragraphs."""
    y = y_top

    # Header row: label (left) + price (right) — same as Page 1 for visual rhyme
    text(col_x, y, sc["label"].upper(),
         font="Inter-SB", size=11, color=INK)
    text(col_x + COL_W, y, f"${sc['price']:.2f}",
         font="Mono-Bold", size=18, color=INK, anchor="right")

    up_color = POS if sc["upside"] >= 0 else NEG
    sign = "+" if sc["upside"] >= 0 else ""
    text(col_x + COL_W, y - 14, f"{sign}{sc['upside']:.1f}%  vs spot",
         font="Mono", size=8.5, color=up_color, anchor="right")

    y -= 28

    # Probability emphasized here — that's the through-line on Page 2
    prob_line = f"Probability  {sc['probability']*100:.0f}%"
    text(col_x, y, prob_line, font="Mono", size=8, color=ACCENT)

    y -= 14
    hline(col_x, col_x + COL_W, y, color=RULE)
    y -= 20

    # Headline
    # Per spec §6c.11: 12pt headlines fit better in 4-column narrower cards on P2 too
    h_lines = wrap_text(sc["headline"], "Inter-Med", 12, COL_W)
    for line in h_lines:
        text(col_x, y, line, font="Inter-Med", size=12, color=INK)
        y -= 16
    y -= 8

    # WHY THIS PROBABILITY — fleshed-out rationale paragraph
    if "probability_rationale" in sc:
        text(col_x, y, f"WHY {int(sc['probability']*100)}%",
             font="Inter-SB", size=7, color=MUTED)
        y -= 9
        y = draw_paragraph(col_x, y, sc["probability_rationale"],
                           font="Inter", size=7, color=TEXT,
                           max_w=COL_W, line_height=9.5)
        y -= 6
        hline(col_x, col_x + COL_W * 0.3, y + 2, color=RULE, width=0.5)
        y -= 6

    # WHAT HAPPENS — scenario narrative
    text(col_x, y, "WHAT HAPPENS",
         font="Inter-SB", size=7, color=MUTED)
    y -= 9

    # Narrative paragraphs — 7pt for 4-column layout per spec §6c.11
    narrative_to_render = sc["narrative"][:-1] if len(sc["narrative"]) > 2 else sc["narrative"]
    for para in narrative_to_render:
        y = draw_paragraph(col_x, y, para,
                           font="Inter", size=7, color=TEXT,
                           max_w=COL_W, line_height=9.5)
        y -= 4

    return y


# Draw three scenario summary cards from same y_top — no narratives on Page 1
scenario_y_top = y
y_bottoms = []
for i, key in enumerate(["bear", "base", "bull", "ultra_bull"]):
    y_b = draw_scenario_summary(scenario_y_top, COL_XS[i], SCENARIOS[key])
    y_bottoms.append(y_b)
y = min(y_bottoms)


page_footer("page 1 of 5")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 2 — SCENARIO NARRATIVES (new in v005 — moved off Page 1 for breathing room)
# ═════════════════════════════════════════════════════════════════════════════
c.showPage()
fill_bg()
y = PAGE_H - MARGIN_T

# Standard masthead (same as Page 3/4 — smaller logo, eyebrow above name)
disc_y = y
text(MARGIN_L, disc_y, "INTERNAL RESEARCH",
     font="Inter-SB", size=7.5, color=ACCENT)
text(MARGIN_L + 116, disc_y, "·  MEMO  ·  NOT INVESTMENT ADVICE  ·  AI-ASSISTED",
     font="Inter", size=7.5, color=MUTED)
text(PAGE_W - MARGIN_R, disc_y, "16 May 2026  ·  the narratives",
     font="Inter", size=7.5, color=MUTED, anchor="right")

# Logo + title — Pages 2-5 use the restrained AR2EB monogram
LOGO_W_NARR = 110
LOGO_H_NARR = LOGO_W_NARR / LOGO_MONO_AR  # ≈ 19pt — short clean typographic mark
c.drawImage(LOGO_MONO, MARGIN_L, y - LOGO_H_NARR - 16,
            width=LOGO_W_NARR, height=LOGO_H_NARR, mask='auto')

title_x = MARGIN_L + LOGO_W_NARR + 14
title_y = y - LOGO_H_NARR / 2 - 19
text(title_x, title_y, DATA['company'],
     font="Inter-SB", size=15, color=INK)
title_w_p2 = stringWidth(DATA['company'], "Inter-SB", 15)
text(title_x + title_w_p2 + 8, title_y, "scenario narratives",
     font="Inter", size=12, color=MUTED)

y -= LOGO_H_NARR + 22

# Probability strip — restate weights at top for context
text(MARGIN_L, y, "PROBABILITY WEIGHTS",
     font="Inter-SB", size=8, color=MUTED)
y -= 14

prob_strip = (f"Bear {int(SCENARIOS['bear']['probability']*100)}%     "
              f"Base {int(SCENARIOS['base']['probability']*100)}%     "
              f"Bull {int(SCENARIOS['bull']['probability']*100)}%     "
              f"Ultra Bull {int(SCENARIOS['ultra_bull']['probability']*100)}%     ·     "
              f"Weighted expected ${PW_EXPECTED:.2f} ({pw_sign}{PW_UPSIDE:.1f}% vs spot)")
text(MARGIN_L, y, prob_strip,
     font="Mono", size=9, color=INK)

y -= 22
hline(MARGIN_L, PAGE_W - MARGIN_R, y, color=RULE_STRONG, width=0.6)
y -= 22

# Three scenario columns with full narratives
narrative_y_top = y
y_bottoms_p2 = []
for i, key in enumerate(["bear", "base", "bull", "ultra_bull"]):
    y_b = draw_scenario_narrative(narrative_y_top, COL_XS[i], SCENARIOS[key])
    y_bottoms_p2.append(y_b)
y = min(y_bottoms_p2)

page_footer("page 2 of 5")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 2 — BUSINESS SNAPSHOT (six charts) — NEW in v009
# ═════════════════════════════════════════════════════════════════════════════
c.showPage()
fill_bg()
y = PAGE_H - MARGIN_T

# Masthead — Pages 2-5 use the restrained AR2EB monogram
LOGO_W_P_SNAP = 150
LOGO_H_P_SNAP = LOGO_W_P_SNAP / LOGO_MONO_AR  # ≈ 26pt
# Position logo near top of masthead band; will be visually compact
c.drawImage(LOGO_MONO, MARGIN_L, y - LOGO_H_P_SNAP - 22,
            width=LOGO_W_P_SNAP, height=LOGO_H_P_SNAP, mask='auto')

right_x_snap = MARGIN_L + LOGO_W_P_SNAP + 28
right_end_snap = PAGE_W - MARGIN_R

text(right_x_snap, y - 4,
     "INTERNAL RESEARCH  ·  MEMO  ·  NOT INVESTMENT ADVICE  ·  AI-ASSISTED",
     font="Inter-SB", size=7, color=ACCENT)
text(right_end_snap, y - 4, "16 May 2026  ·  the snapshot",
     font="Inter", size=7.5, color=MUTED, anchor="right")

mid_y_snap = y - 22
text(right_x_snap, mid_y_snap, DATA['company'],
     font="Inter-SB", size=15, color=INK)
zm_w_snap = stringWidth(DATA['company'], "Inter-SB", 15)
text(right_x_snap + zm_w_snap + 8, mid_y_snap, "business snapshot",
     font="Inter", size=12, color=MUTED)

# Subtitle: data scope
sub_y_snap = y - 42
text(right_x_snap, sub_y_snap,
     DATA['page3']['subtitle'],
     font="Inter", size=8.5, color=MUTED)

y -= 56
hline(MARGIN_L, PAGE_W - MARGIN_R, y, color=RULE_STRONG, width=0.6)
y -= 18

# ── 3 × 2 chart grid ─────────────────────────────────────────────────────────
# Each chart: 280pt × 190pt, with 12pt horizontal gap and 20pt vertical gap
CHART_W = 280
CHART_H = 190
CHART_GAP_X = 12
CHART_GAP_Y = 16

# Center the 3-col grid in the content area
total_grid_w = 3 * CHART_W + 2 * CHART_GAP_X
grid_x_start = MARGIN_L + (CONTENT_W - total_grid_w) / 2
chart_x_positions = [
    grid_x_start,
    grid_x_start + CHART_W + CHART_GAP_X,
    grid_x_start + 2 * (CHART_W + CHART_GAP_X),
]

# Row 1 starts at y, row 2 at y - CHART_H - CHART_GAP_Y
row1_y_top = y
row2_y_top = y - CHART_H - CHART_GAP_Y

# Charts laid out as:
#   Row 1: revenue · segments · margins
#   Row 2: net cash · EV/Revenue · geographic
chart_layout = [
    # (row, col, filename)
    (0, 0, "01_revenue.png"),
    (0, 1, "02_path_to_profit.png"),
    (0, 2, "03_cash_dilution.png"),
    (1, 0, "04_fleet.png"),
    (1, 1, "05_valuation.png"),
    (1, 2, "06_tam.png"),
]

for row, col, fname in chart_layout:
    chart_path = f"{CHARTS_DIR}/{fname}"
    cx = chart_x_positions[col]
    cy_top = row1_y_top if row == 0 else row2_y_top
    cy_bottom = cy_top - CHART_H
    c.drawImage(chart_path, cx, cy_bottom,
                width=CHART_W, height=CHART_H,
                preserveAspectRatio=True, anchor='c', mask='auto')

# Caption line at the bottom — caveats and data provenance
y = row2_y_top - CHART_H - 10
text(MARGIN_L, y,
     DATA['page3']['sources'],
     font="Inter", size=7, color=MUTED)

page_footer("page 3 of 5")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 3 — QUANTITATIVE (show your work)
# ═════════════════════════════════════════════════════════════════════════════
c.showPage()
fill_bg()
y = PAGE_H - MARGIN_T

# Mono logo (smaller, restrained) — Pages 2-5
LOGO_W_P2 = 150
LOGO_H_P2 = LOGO_W_P2 / LOGO_MONO_AR  # ≈ 26pt
c.drawImage(LOGO_MONO, MARGIN_L, y - LOGO_H_P2 - 22,
            width=LOGO_W_P2, height=LOGO_H_P2, mask='auto')

right_x = MARGIN_L + LOGO_W_P2 + 28
right_end = PAGE_W - MARGIN_R

# Top eyebrow with disclaimer (continued)
text(right_x, y - 4,
     "INTERNAL RESEARCH  ·  MEMO  ·  NOT INVESTMENT ADVICE  ·  AI-ASSISTED",
     font="Inter-SB", size=7, color=ACCENT)
text(right_end, y - 4, "16 May 2026  ·  the quantitative",
     font="Inter", size=7.5, color=MUTED, anchor="right")

# Mid: Company name + "show your work"
mid_y = y - 22
text(right_x, mid_y, DATA['company'],
     font="Inter-SB", size=15, color=INK)
zm_w = stringWidth(DATA['company'], "Inter-SB", 15)
text(right_x + zm_w + 8, mid_y, "show your work",
     font="Inter", size=12, color=MUTED)

# Bottom: recap prices + prob-weighted expected
recap_y = y - 42
pw_sign_top = "+" if PW_UPSIDE >= 0 else ""
recap = (f"Bear  ${SCENARIOS['bear']['expected_per_share']:.2f}     "
         f"Base  ${SCENARIOS['base']['expected_per_share']:.2f}     "
         f"Bull  ${SCENARIOS['bull']['expected_per_share']:.2f}     "
         f"·     Weighted  ${PW_EXPECTED:.2f}  ({pw_sign_top}{PW_UPSIDE:.1f}%)")
text(right_end, recap_y, recap,
     font="Mono", size=10, color=INK, anchor="right")

y -= 56
hline(MARGIN_L, PAGE_W - MARGIN_R, y, color=RULE_STRONG, width=0.6)
y -= 16


# ─────────────────────────────────────────────────────────────────────────────
# Quant scenario column — design system compliant
# Currency symbol in header; cells are bare numbers.
# Headers semibold + narrow rule below. Body rows whitespace-separated.
# No filled backgrounds for totals — semibold + rule above.
# ─────────────────────────────────────────────────────────────────────────────
def draw_scenario_quant(y_top, col_x, sc):
    y = y_top

    # Scenario header
    text(col_x, y, sc["label"].upper(),
         font="Inter-SB", size=10, color=INK)
    text(col_x + COL_W, y, f"${sc['expected_per_share']:.2f}",
         font="Mono-Bold", size=14, color=INK, anchor="right")
    y -= 16
    hline(col_x, col_x + COL_W, y, color=RULE)
    y -= 16

    # — ASSUMPTIONS (dispatched per dcf_type) —
    eyebrow(col_x, y, "ASSUMPTIONS")
    y -= 10
    hline(col_x, col_x + COL_W, y, color=RULE)
    y -= 12

    asm_rows = assumptions_rows(sc, DCF_TYPE, DATA)
    for lab, val in asm_rows:
        text(col_x, y, lab, font="Inter", size=7.5, color=TEXT)
        text(col_x + COL_W, y, val,
             font="Mono", size=7.5, color=INK, anchor="right")
        y -= 10
    y -= 4

    # — N-YEAR DCF (compact) — N = 10 for Young, 5 for Mature
    n_years = dcf_period_years(DCF_TYPE)
    eyebrow(col_x, y, f"{n_years}-YEAR DCF  ·  $B")
    y -= 10
    hline(col_x, col_x + COL_W, y, color=RULE)
    y -= 11

    # Column positions inside scenario column
    col_yr_x = col_x
    col_rev_x = col_x + COL_W - 145
    col_marg_x = col_x + COL_W - 100
    col_fcf_x = col_x + COL_W - 55
    col_pv_x = col_x + COL_W

    # Header
    text(col_yr_x, y, "FY", font="Inter-SB", size=6.5, color=MUTED)
    text(col_rev_x, y, "Rev", font="Inter-SB", size=6.5, color=MUTED, anchor="right")
    text(col_marg_x, y, "Margin", font="Inter-SB", size=6.5, color=MUTED, anchor="right")
    text(col_fcf_x, y, "FCF", font="Inter-SB", size=6.5, color=MUTED, anchor="right")
    text(col_pv_x, y, "PV FCF", font="Inter-SB", size=6.5, color=MUTED, anchor="right")
    hline(col_x, col_x + COL_W, y - 3, color=RULE)
    y -= 10

    # FY labels + revenue display differ per dcf_type:
    # Young-Company: rev_path[i] IS revenue in $B
    # Mature-Company: rev_path[i] is growth rate; compute compounded revenue from rev_b
    fy_labels = dcf_year_labels(DCF_TYPE)
    if DCF_TYPE == 'young_company':
        rev_display = [sc['rev_path'][i] for i in range(n_years)]
    else:
        rev_display = []
        running = sc['rev_b']
        for i in range(n_years):
            running = running * (1 + sc['rev_path'][i])
            rev_display.append(running)

    for i in range(n_years):
        text(col_yr_x, y, fy_labels[i],
             font="Inter", size=6.5, color=TEXT)
        text(col_rev_x, y, f"{rev_display[i]:.2f}",
             font="Mono", size=6.5, color=INK, anchor="right")
        text(col_marg_x, y, f"{sc['op_margin'][i]*100:+.0f}%",
             font="Mono", size=6.5, color=INK, anchor="right")
        fcf_color = NEG if sc['fcf'][i] < 0 else INK
        text(col_fcf_x, y, f"{sc['fcf'][i]:+.2f}",
             font="Mono", size=6.5, color=fcf_color, anchor="right")
        text(col_pv_x, y, f"{sc['pv_fcf'][i]:+.2f}",
             font="Mono", size=6.5, color=INK, anchor="right")
        y -= 9

    # Subtotal
    y -= 1
    hline(col_x, col_x + COL_W, y + 3, color=RULE)
    text(col_x, y, "Σ PV explicit FCF",
         font="Inter-Med", size=7, color=INK)
    text(col_pv_x, y, f"{sc['sum_pv_fcf']:+.2f}",
         font="Mono-Bold", size=7, color=INK, anchor="right")
    y -= 10

    text(col_x, y, f"+ PV terminal (g {sc['term_g']*100:.1f}%)",
         font="Inter", size=7, color=TEXT)
    text(col_pv_x, y, f"{sc['pv_terminal']:.2f}",
         font="Mono", size=7, color=INK, anchor="right")
    y -= 11

    # — SUM OF PARTS → PER SHARE (dispatched per dcf_type) —
    eyebrow(col_x, y, "EQUITY BUILD  ·  $B & per share")
    y -= 10
    hline(col_x, col_x + COL_W, y, color=RULE)
    y -= 12

    sop_rows = equity_build_rows(sc, DCF_TYPE)
    for lab, val, kind in sop_rows:
        if kind == "subtotal":
            hline(col_x, col_x + COL_W, y + 9, color=RULE)
            font_l = "Inter-Med"
            font_n = "Mono-Bold"
            sz = 7
            color = INK
        elif kind == "total":
            hline(col_x, col_x + COL_W, y + 10, color=RULE_STRONG, width=0.6)
            font_l = "Inter-SB"
            font_n = "Mono-Bold"
            sz = 8.5
            color = INK
        else:
            font_l = "Inter"
            font_n = "Mono"
            sz = 7
            color = TEXT

        text(col_x, y, lab, font=font_l, size=sz, color=color)
        text(col_x + COL_W, y, val, font=font_n, size=sz, color=color, anchor="right")

        y -= 10 if kind != "total" else 12

    # — FUTURE FAIR VALUE (if scenario plays out) —
    # Variant B: terminal WACC, compounded against failure-haircut-weighted
    # expected_per_share. Compact horizontal layout: 4 year columns × 3 rows.
    y -= 2
    eyebrow(col_x, y, "FUTURE FAIR VALUE  ·  IF SCENARIO PLAYS OUT")
    y -= 8
    hline(col_x, col_x + COL_W, y, color=RULE)
    y -= 10

    terminal_wacc = sc['wacc_path'][-1]
    today_value = sc['expected_per_share']
    col_step = COL_W / 4
    years = [5, 10, 15, 20]

    for i, T in enumerate(years):
        x = col_x + col_step * (i + 0.5)
        text(x, y, f"+{T}y",
             font="Inter-SB", size=6.5, color=MUTED, anchor="center")
    y -= 9
    for i, T in enumerate(years):
        x = col_x + col_step * (i + 0.5)
        future_val = today_value * ((1 + terminal_wacc) ** T)
        text(x, y, f"${future_val:,.2f}",
             font="Mono", size=7, color=INK, anchor="center")
    y -= 9
    for i, T in enumerate(years):
        x = col_x + col_step * (i + 0.5)
        future_val = today_value * ((1 + terminal_wacc) ** T)
        multiple = future_val / SPOT
        if today_value <= 0:
            mult_color = "#b91c1c"
        elif future_val >= SPOT:
            mult_color = "#15803d"
        else:
            mult_color = "#b91c1c"
        text(x, y, f"{multiple:.2f}×",
             font="Mono", size=6.5, color=mult_color, anchor="center")
    y -= 4

    return y


# Draw three quant columns from same y_top
quant_y_top = y
quant_y_bottoms = []
for i, key in enumerate(["bear", "base", "bull", "ultra_bull"]):
    y_b = draw_scenario_quant(quant_y_top, COL_XS[i], SCENARIOS[key])
    quant_y_bottoms.append(y_b)
y = min(quant_y_bottoms)

# Page 3 ends after quant. Prob-weighted expected is shown in the top recap
# strip (alongside Bear/Base/Bull). Methodology lives in the JSX header.

page_footer("page 4 of 5")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 3 — DISCLAIMERS + GLOSSARY (back matter)
# ═════════════════════════════════════════════════════════════════════════════
c.showPage()
fill_bg()
y = PAGE_H - MARGIN_T

# Mono logo (smaller, restrained) — Pages 2-5
LOGO_W_P3 = 150
LOGO_H_P3 = LOGO_W_P3 / LOGO_MONO_AR  # ≈ 26pt
c.drawImage(LOGO_MONO, MARGIN_L, y - LOGO_H_P3 - 22,
            width=LOGO_W_P3, height=LOGO_H_P3, mask='auto')

right_x = MARGIN_L + LOGO_W_P3 + 28
right_end = PAGE_W - MARGIN_R

text(right_x, y - 4,
     "INTERNAL RESEARCH  ·  MEMO  ·  NOT INVESTMENT ADVICE  ·  AI-ASSISTED",
     font="Inter-SB", size=7, color=ACCENT)
text(right_end, y - 4, "16 May 2026  ·  the back matter",
     font="Inter", size=7.5, color=MUTED, anchor="right")

mid_y = y - 22
text(right_x, mid_y, DATA['company'],
     font="Inter-SB", size=15, color=INK)
zm_w_p3 = stringWidth(DATA['company'], "Inter-SB", 15)
text(right_x + zm_w_p3 + 8, mid_y, "supporting analysis · disclaimers · glossary",
     font="Inter", size=12, color=MUTED)

recap_y = y - 42
text(right_end, recap_y,
     f"Bear  ${SCENARIOS['bear']['expected_per_share']:.2f}     Base  ${SCENARIOS['base']['expected_per_share']:.2f}     Bull  ${SCENARIOS['bull']['expected_per_share']:.2f}",
     font="Mono", size=9, color=MUTED, anchor="right")

y -= 56
hline(MARGIN_L, PAGE_W - MARGIN_R, y, color=RULE_STRONG, width=0.6)
y -= 16


# ── Pushback section — 2-line compact ──────────────────────────────────────
eyebrow(MARGIN_L, y, "PUSHBACK  ·  WHY THE BASE CASE IS TOO HARSH")
y -= 9
hline(MARGIN_L, PAGE_W - MARGIN_R, y, color=RULE)
y -= 12

pushback = [(p['label'], p['body']) for p in DATA['appendix']['pushback']]

pb_y_top = y
pb_row_h = 36  # was 22 — increase to fit wrapped body text
for idx, (lead, body) in enumerate(pushback):
    col = idx % 3
    row = idx // 3
    px = COL_XS[col]
    py = pb_y_top - row * pb_row_h

    text(px, py, f"{idx+1}", font="Mono-Bold", size=8, color=MUTED)
    text(px + 12, py, lead, font="Inter-SB", size=7.5, color=INK)
    # Wrap body text to column width
    body_lines = wrap_text(body, "Inter", 7, COL_W - 14)
    for li, line in enumerate(body_lines):
        text(px + 12, py - 9 - li * 9, line,
             font="Inter", size=7, color=TEXT)

y = pb_y_top - 2 * pb_row_h - 6


# ── Falsification triggers ──────────────────────────────────────────────────
eyebrow(MARGIN_L, y, "FALSIFICATION TRIGGERS")
y -= 9
hline(MARGIN_L, PAGE_W - MARGIN_R, y, color=RULE)
y -= 13

triggers = [(t['label'], t['body']) for t in DATA['appendix']['triggers']]

trigger_lines_max = 0
for col_idx, (lead, body) in enumerate(triggers):
    tx = COL_XS[col_idx]
    text(tx, y, lead, font="Inter-SB", size=8, color=INK)
    body_lines = wrap_text(body, "Inter", 7.5, COL_W)
    trigger_lines_max = max(trigger_lines_max, len(body_lines))
    for li, line in enumerate(body_lines):
        text(tx, y - 10 - li * 10, line,
             font="Inter", size=7.5, color=TEXT)

y -= 10 + trigger_lines_max * 10 + 14


# ── Full DISCLAIMERS — 3 cols × 2 rows, generous treatment ─────────────────
eyebrow(MARGIN_L, y, "DISCLAIMERS  ·  PLEASE READ BEFORE USING THIS DOCUMENT")
y -= 10
hline(MARGIN_L, PAGE_W - MARGIN_R, y, color=RULE)
y -= 16

DISCLAIMERS_FULL = [
    ("Not investment advice.",
     "This document is produced for entertainment and educational purposes only by an individual amateur investor. \"Alameda Research 2: Electric Boogaloo\" is the unincorporated personal concept of one person and is not a registered investment management entity. Nothing herein constitutes investment advice, a recommendation, or a solicitation to buy or sell any security."),
    ("Not a professional.",
     "The author is not a registered investment advisor, broker-dealer, CFA charterholder, certified financial planner, or licensed financial professional of any kind. The author has no formal training in equity research or capital markets. No fiduciary relationship is created by reading this document."),
    ("AI-assisted analysis.",
     "Substantial portions of this analysis were produced with the assistance of large language models. LLMs are known to fabricate facts, miscalculate numbers, hallucinate sources, and present incorrect information with high apparent confidence. Every figure, claim, and projection in this document should be independently verified before acting on it."),
    ("Forward-looking statements.",
     "Scenarios, valuations, projections, and any forward-looking statements involve substantial assumptions and uncertainty. Actual results may differ materially from those projected. Past performance is not indicative of future results. The model is a model; reality is not."),
    ("Author may hold positions.",
     "The author may own, intend to acquire, or hold short exposure to $JOBY or related securities at any time. Positions may change without notice and without an update to this document. Do not assume the author's positions match the tone of the analysis."),
    ("Do your own research.",
     "Do not make investment decisions on the basis of this document. Consult a licensed financial professional and read the company's official SEC filings (10-K, 10-Q, 8-K, proxy) before forming any investment view. If you wouldn't trust your retirement to a chatbot, don't trust this either."),
]

disc_row_h = 86
disc_y_top = y

for idx, (lead, body) in enumerate(DISCLAIMERS_FULL):
    col = idx % 3
    row = idx // 3
    dx = COL_XS[col]
    dy = disc_y_top - row * disc_row_h

    text(dx, dy, lead, font="Inter-SB", size=9, color=INK)
    body_y = dy - 14
    body_lines = wrap_text(body, "Inter", 8, COL_W)
    for li, line in enumerate(body_lines):
        text(dx, body_y - li * 11, line,
             font="Inter", size=8, color=TEXT)

y = disc_y_top - 2 * disc_row_h - 12


# ── Glossary on page 3 ─────────────────────────────────────────────────────
eyebrow(MARGIN_L, y, "GLOSSARY  ·  CONCEPTS REFERENCED IN THE NARRATIVE")
y -= 10
hline(MARGIN_L, PAGE_W - MARGIN_R, y, color=RULE)
y -= 14

gloss_row_h = 22
gloss_y_top = y

for idx, (term, defn) in enumerate(GLOSSARY):
    col = idx % 3
    row = idx // 3
    gx = COL_XS[col]
    gy = gloss_y_top - row * gloss_row_h

    text(gx, gy, term, font="Inter-SB", size=8, color=INK)
    term_w = stringWidth(term, "Inter-SB", 8)
    text(gx + term_w + 4, gy, "—", font="Inter", size=7.5, color=DIM)
    def_x = gx + term_w + 13
    def_avail = COL_W - (term_w + 13)
    # Wrap definition: line 1 fits after term/em-dash; line 2 (if needed) starts at col x
    def_lines = wrap_text(defn, "Inter", 7.5, def_avail)
    if def_lines:
        text(def_x, gy, def_lines[0], font="Inter", size=7.5, color=TEXT)
        # If wrap needed: remaining text on next line at column x (full col width)
        if len(def_lines) > 1:
            rest = " ".join(def_lines[1:])
            rest_lines = wrap_text(rest, "Inter", 7.5, COL_W)
            text(gx, gy - 10, rest_lines[0], font="Inter", size=7.5, color=TEXT)

page_footer("page 5 of 5", show_disclaimer_pointer=False)

c.save()
print(f"PDF saved to {OUT_PATH}")
