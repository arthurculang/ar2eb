/* AR2EB — PDF-only memo component.
 *
 * JSX as layout source of truth. Reads ?ticker=<slug> from print.html and
 * renders the per-page components. As Phase 2 ports pages, they are added
 * to <MemoPDF>; once all five live here, memo.py is retired.
 *
 * Render harness: public/print.html?ticker=<slug>
 * Renderer:       scripts/render_memo_pdf.py
 *
 * Units: pt (1pt = 1/72in). CSS @page is 14in x 8.5in landscape, matching
 * memo.py's PAGE_W / PAGE_H. memo.py constants translate 1:1 to pt here.
 */

const PALETTE = {
  paper:       '#fafafa',
  ink:         '#18181b',  // zinc-900
  text:        '#3f3f46',  // zinc-700
  muted:       '#71717a',  // zinc-500
  dim:         '#a1a1aa',  // zinc-400
  rule:        '#e4e4e7',  // zinc-200
  ruleStrong:  '#18181b',
  accent:      '#1e3a8a',  // indigo-900
};

const FONT_SANS = "'Inter', system-ui, sans-serif";
const FONT_MONO = "'JetBrains Mono', ui-monospace, monospace";

// Inter-SemiBold (weight 600) per-glyph advance widths, in em, extracted from
// public/assets/fonts/Inter-SemiBold.ttf (rounded UP — conservative). Used to
// size chart margins to the actual rendered label widths so long series labels
// never clip at the SVG edge (spec §3.5: layout bounds compute from data).
const _INTER_SB_EM = {" ":0.252,"!":0.322,"\"":0.523,"#":0.644,"$":0.651,"%":1.005,"&":0.663,"'":0.326,"(":0.374,")":0.374,"*":0.54,"+":0.673,",":0.319,"-":0.466,".":0.319,"/":0.379,"0":0.66,"1":0.423,"2":0.624,"3":0.637,"4":0.667,"5":0.613,"6":0.64,"7":0.577,"8":0.641,"9":0.64,":":0.319,";":0.33,"<":0.673,"=":0.673,">":0.673,"?":0.544,"@":1.0,"A":0.728,"B":0.66,"C":0.737,"D":0.723,"E":0.606,"F":0.588,"G":0.75,"H":0.746,"I":0.277,"J":0.58,"K":0.704,"L":0.566,"M":0.923,"N":0.76,"O":0.769,"P":0.646,"Q":0.773,"R":0.653,"S":0.651,"T":0.661,"U":0.736,"V":0.728,"W":1.021,"X":0.72,"Y":0.714,"Z":0.653,"[":0.374,"\\":0.379,"]":0.374,"^":0.482,"_":0.47,"`":0.352,"a":0.575,"b":0.625,"c":0.583,"d":0.625,"e":0.592,"f":0.389,"g":0.626,"h":0.613,"i":0.262,"j":0.262,"k":0.57,"l":0.262,"m":0.901,"n":0.612,"o":0.609,"p":0.625,"q":0.625,"r":0.397,"s":0.55,"t":0.354,"u":0.613,"v":0.587,"w":0.84,"x":0.569,"y":0.589,"z":0.566,"{":0.455,"|":0.359,"}":0.455,"~":0.673,"×":0.673,"·":0.319,"—":1.0,"–":0.5,"’":0.294,"“":0.507,"”":0.502,"→":0.955};

// Estimate the rendered width (in SVG user units) of `str` set in Inter-SemiBold
// at `fontSizePt`. CRITICAL: inside a viewBox'd <svg>, a `font-size` given in
// `pt` is resolved to px (×96/72) and that px value is then treated as user
// units — so every `pt` chart font renders 1.333× larger than its number in
// the user-coordinate system the plot box is laid out in. We bake that factor
// in here. Ignores kerning (which only shrinks real width), so the estimate is
// a safe upper bound. `letterSpacingEm` accounts for SVG letter-spacing.
function estSvgTextWidth(str, fontSizePt, letterSpacingEm = 0) {
  const PT_TO_USER = 96 / 72;
  let em = 0;
  for (const ch of str) em += (_INTER_SB_EM[ch] !== undefined ? _INTER_SB_EM[ch] : 1.021);
  return (em + letterSpacingEm * str.length) * fontSizePt * PT_TO_USER;
}

// Greedy word-wrap for an SVG <text>: split `str` into lines each ≤ maxWidthUser
// user-units wide when set in Inter at fontSizePt (via estSvgTextWidth, which
// already folds in the pt→user 1.333× blow-up). Long single words aren't broken.
function wrapSvgText(str, maxWidthUser, fontSizePt, letterSpacingEm = 0) {
  const words = String(str).split(/\s+/).filter(Boolean);
  const lines = [];
  let cur = '';
  for (const w of words) {
    const trial = cur ? cur + ' ' + w : w;
    if (!cur || estSvgTextWidth(trial, fontSizePt, letterSpacingEm) <= maxWidthUser) {
      cur = trial;
    } else {
      lines.push(cur); cur = w;
    }
  }
  if (cur) lines.push(cur);
  return lines;
}

// "Nice" axis step for ~`target` ticks across a numeric range, at ANY magnitude
// (1/2/5 × 10^k). Replaces fixed thresholds (`yMax > 6 ? 2`) that exploded into
// hundreds of gridlines once mega-cap $100B–$1T values entered the mature charts.
function niceStep(range, target = 6) {
  if (!(range > 0)) return 1;
  const raw = range / target;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const n = raw / mag;
  return (n < 1.5 ? 1 : n < 3 ? 2 : n < 7 ? 5 : 10) * mag;
}

// Width (SVG user units) of a JetBrains-Mono string at `pt` — the chart axis
// font. Mono advance ≈ 0.6em; folds in the same pt→user 1.333× as estSvgTextWidth.
function monoTextWidth(str, pt) {
  return String(str).length * 0.6 * pt * (96 / 72);
}

// ── Helpers ────────────────────────────────────────────────────────────
function getTickerSlug() {
  const params = new URLSearchParams(location.search);
  return (params.get('ticker') || '').toLowerCase();
}

function findMemo(slug) {
  if (!window.AR2EB_DATA || !window.AR2EB_DATA.MEMOS) return null;
  return window.AR2EB_DATA.MEMOS.find(m => m.slug === slug) || null;
}

function fmtDollars(n, decimals = 2) {
  return '$' + n.toFixed(decimals);
}

// "May 16, 2026" → "16 May 2026" (matches memo.py's date stamp style).
function fmtDayMonthYear(isoDate) {
  const d = new Date(isoDate + 'T00:00:00Z');
  const month = d.toLocaleString('en-GB', { month: 'long', timeZone: 'UTC' });
  return `${d.getUTCDate()} ${month} ${d.getUTCFullYear()}`;
}

// ── DCF display logic — ported from memo.py for compute-from-inputs parity.
// Mirrors assumptions_rows() and equity_build_rows() per dcf_type so the
// JSX computes its own display rather than receiving pre-formatted rows.

function dcfYearLabels(dcfType, n) {
  // Young: FY27 → FY36 (10y); Mature: FY26 → FY30 (5y).
  const start = dcfType === 'young_company' ? 27 : 26;
  return Array.from({ length: n }, (_, i) => `FY${start + i}`);
}

function dcfRevenueDisplay(scn, dcfType, n) {
  // Young rev_path is absolute $B; Mature is growth rates compounded from rev_b.
  const p = scn.dcfPath;
  if (dcfType === 'young_company') {
    return p.rev_path.slice(0, n);
  }
  const out = [];
  let r = p.rev_b;
  for (let i = 0; i < n; i++) {
    r = r * (1 + p.rev_path[i]);
    out.push(r);
  }
  return out;
}

function assumptionsRows(scn, dcfType, tamBillion) {
  const probPct = (scn.probability * 100).toFixed(0);
  if (dcfType === 'private_prevaluation') {
    const e = scn.exitTerms;
    const exitStr = e.exitPostMoneyBillion >= 1000
      ? `$${(e.exitPostMoneyBillion / 1000).toFixed(2)}T` : `$${e.exitPostMoneyBillion.toFixed(0)}B`;
    return [
      ['Exit kind',               e.kind.replace(/_/g, ' ')],
      ['Exit year',               String(e.exitYear)],
      ['Exit post-money',         exitStr],
      ['Per-share at exit ($)',   e.exitPerShareNominal.toLocaleString()],
      ['Years to exit',           e.yearsToExit.toFixed(1)],
      ['Venture WACC (%)',        (e.ventureWacc * 100).toFixed(0)],
      ['Dilution to exit (%)',    `+${e.dilutionPctFromToday}`],
      ['P(total loss) (%)',       ((e.pTotalLoss || 0) * 100).toFixed(0)],
      ['Scenario probability (%)', probPct],
    ];
  }
  const m = scn.dcfMetrics;
  const p = scn.dcfPath;
  if (dcfType === 'young_company') {
    return [
      ['TAM Year-10 ($B)',        (tamBillion || 0).toFixed(0)],
      ['Mature share (%)',        m.tam_share.toFixed(1)],
      ['Mature op margin (%)',    (p.op_margin[p.op_margin.length - 1] * 100).toFixed(0)],
      ['Sales-to-capital',        m.s2c.toFixed(1)],
      ['Terminal WACC (%)',       (p.wacc_path[p.wacc_path.length - 1] * 100).toFixed(1)],
      ['Terminal growth (%)',     (p.term_g * 100).toFixed(1)],
      ['P(failure) (%)',          String(m.p_fail)],
      ['Scenario probability (%)', probPct],
    ];
  }
  if (dcfType === 'mature_company') {
    const sign = m.cagr_5y >= 0 ? '+' : '';
    // Ticker-specific diagnostic row: LTH = SLB total, ISRG = installed
    // base, exit-multiple names also surface the terminal multiple.
    let diagRow;
    if (m.slb_total_5y !== undefined) {
      diagRow = ['5y SLB total ($B)', m.slb_total_5y.toFixed(2)];
    } else if (m.installed_base_fy30 !== undefined) {
      diagRow = ['Installed base FY30', m.installed_base_fy30.toLocaleString()];
    } else if (m.take_rate_basis !== undefined) {
      diagRow = ['Take rate (bp)', m.take_rate_basis.toFixed(0)];
    } else if (m.anthropic_stake !== undefined) {
      diagRow = ['Anthropic stake ($B)', m.anthropic_stake.toFixed(1)];
    } else {
      // Non-redundant default — the 5y CAGR is already row 1, so show terminal FCF instead.
      diagRow = ['Terminal FCF ($B)', `$${p.fcf[p.fcf.length - 1].toFixed(2)}B`];
    }
    const rows = [
      ['5y revenue CAGR (%)',     `${sign}${m.cagr_5y.toFixed(1)}`],
      ['Year-5 op margin (%)',    (p.op_margin[p.op_margin.length - 1] * 100).toFixed(1)],
      ['WACC (%)',                (m.wacc * 100).toFixed(1)],
      ['Terminal growth (%)',     (p.term_g * 100).toFixed(1)],
      diagRow,
      ['Starting revenue ($B)',   p.rev_b.toFixed(2)],
      ['Scenario probability (%)', probPct],
    ];
    // If the diagnostic is an exit-multiple ticker, swap terminal-growth for
    // the exit multiple (more informative than a display-only term_g).
    if (m.exit_fcf_multiple !== undefined) {
      rows[3] = ['Exit FCF multiple (×)', m.exit_fcf_multiple.toFixed(0)];
    }
    return rows;
  }
  // mature_company_sotp
  const signS = m.cagr_5y >= 0 ? '+' : '';
  return [
    ['5y revenue CAGR (%)',     `${signS}${m.cagr_5y.toFixed(1)}`],
    ['Year-5 op margin (%)',    (p.op_margin[p.op_margin.length - 1] * 100).toFixed(1)],
    ['WACC (%)',                (m.wacc * 100).toFixed(1)],
    // Real-estate / cap-rate SOTP names (marked by special_label, e.g. HHH) value
    // the terminal on an exit multiple, not a Gordon growth. Gated on special_label
    // so COIN — which carries exit_fcf_multiple but has always shown term_g — is
    // byte-identical.
    (m.special_label && m.exit_fcf_multiple !== undefined
      ? ['Exit FCF multiple (×)', m.exit_fcf_multiple.toFixed(0)]
      : ['Terminal growth (%)',   (p.term_g * 100).toFixed(1)]),
    // Special-asset label is data-driven (ZM: Anthropic stake; HHH: Vantage).
    (m.special_label
      ? [`${m.special_label} ($B)`, (p.special_assets ?? 0).toFixed(1)]
      : ['Anthropic stake ($B)',    (m.anthropic_stake ?? 0).toFixed(1)]),
    ['Starting revenue ($B)',   p.rev_b.toFixed(2)],
    ['Scenario probability (%)', probPct],
  ];
}

function equityBuildRows(scn, dcfType) {
  if (dcfType === 'private_prevaluation') {
    // Exit-payout PV walk: nominal exit → discount → loss/haircut → expected.
    const e = scn.exitTerms;
    const ipoHc = e.ipoUnderperformanceHaircutPct || 0;
    const pLoss = (e.pTotalLoss || 0) * 100;
    const rows = [
      ['Per-share at exit (nominal)', `$${e.exitPerShareNominal.toLocaleString()}`, 'normal'],
      [`÷ (1+${(e.ventureWacc * 100).toFixed(0)}%)^${e.yearsToExit.toFixed(1)}`,
        `$${e.pvPerShare.toFixed(2)}`, 'subtotal'],
    ];
    if (ipoHc) rows.push([`× (1−IPO haircut ${ipoHc}%)`,
      `$${(e.pvPerShare * (1 - ipoHc / 100)).toFixed(2)}`, 'normal']);
    if (pLoss) rows.push([`× (1−P_loss ${pLoss.toFixed(0)}%)`, '', 'normal']);
    rows.push(['= Expected PV per share', `$${scn.expectedPerShare.toFixed(2)}`, 'total']);
    return rows;
  }
  const p = scn.dcfPath;
  if (dcfType === 'young_company') {
    return [
      ['Operating EV',           `$${p.op_ev.toFixed(2)}B`,        'normal'],
      ['+ Cash & investments',   `$${p.cash.toFixed(2)}B`,         'normal'],
      ['= Equity value',         `$${p.total_equity.toFixed(2)}B`, 'subtotal'],
      ['Raised over period',     `$${p.raise_total.toFixed(2)}B`,  'normal'],
      ['Dilution by FY36',       `+${p.dilution_pct}%`,            'normal'],
      ['FY36 shares (M)',        p.final_shares.toLocaleString(),  'normal'],
      ['DCF per share',          `$${p.dcf_per_share.toFixed(2)}`, 'subtotal'],
      [`× (1−P_fail) [${100 - scn.dcfMetrics.p_fail}%]`,
        `$${((1 - scn.dcfMetrics.p_fail / 100) * p.dcf_per_share).toFixed(2)}`, 'normal'],
      [`+ P_fail × distress [${scn.dcfMetrics.p_fail}% × $${p.distress.toFixed(2)}]`,
        `$${(scn.dcfMetrics.p_fail / 100 * p.distress).toFixed(2)}`, 'normal'],
      ['= Expected per share',   `$${scn.expectedPerShare.toFixed(2)}`, 'total'],
    ];
  }
  if (dcfType === 'mature_company') {
    const rows = [
      ['Operating EV',           `$${p.op_ev.toFixed(2)}B`,        'normal'],
      ['+ Cash & investments',   `$${p.cash.toFixed(2)}B`,         'normal'],
    ];
    if ((p.net_debt || 0) > 0) {
      rows.push(['− Total debt', `$${p.net_debt.toFixed(2)}B`,     'normal']);
    }
    rows.push(
      ['= Equity value',         `$${p.total_equity.toFixed(2)}B`, 'subtotal'],
      ['FY30 shares (M)',        p.final_shares.toLocaleString(),  'normal'],
      ['= Expected per share',   `$${scn.expectedPerShare.toFixed(2)}`, 'total'],
    );
    return rows;
  }
  // mature_company_sotp — special-asset label is data-driven (ZM: Anthropic; HHH: Vantage).
  const saLabel = scn.dcfMetrics.special_label ? ('+ ' + scn.dcfMetrics.special_label)
    : (scn.dcfMetrics.anthropic_stake != null ? '+ Anthropic stake' : '+ Special assets');
  const rowsS = [
    ['Operating EV',             `$${p.op_ev.toFixed(2)}B`,        'normal'],
    ['+ Cash & investments',     `$${p.cash.toFixed(2)}B`,         'normal'],
    [saLabel,                    `$${(p.special_assets || 0).toFixed(2)}B`, 'normal'],
  ];
  if ((p.net_debt || 0) > 0) {
    rowsS.push(['− Total debt',  `$${p.net_debt.toFixed(2)}B`,     'normal']);
  }
  rowsS.push(
    ['= Equity value',           `$${p.total_equity.toFixed(2)}B`, 'subtotal'],
    ['FY30 shares (M)',          p.final_shares.toLocaleString(),  'normal'],
    ['= Expected per share',     `$${scn.expectedPerShare.toFixed(2)}`, 'total'],
  );
  return rowsS;
}

// ── Shared building blocks ─────────────────────────────────────────────
function Eyebrow({ children, color = PALETTE.accent }) {
  return (
    <div style={{
      fontFamily: FONT_SANS,
      fontWeight: 600,
      fontSize: '7pt',
      letterSpacing: '0.04em',
      textTransform: 'uppercase',
      color,
    }}>
      {children}
    </div>
  );
}

function Rule({ strong = false, width = 0.4 }) {
  return (
    <div style={{
      height: 0,
      borderTop: `${strong ? 0.6 : width}pt solid ${strong ? PALETTE.ruleStrong : PALETTE.rule}`,
      margin: '0',
    }} />
  );
}

function PageFooter({ memo, pageLabel, showDisclaimerPointer = true }) {
  const stamp = memo.print.stamp;
  const disclaimer = showDisclaimerPointer
    ? `NOT INVESTMENT ADVICE  ·  Not from a registered investment advisor  ·  AI-assisted analysis  ·  Author may hold positions  ·  See full disclaimers, page ${memoTotalPages(memo)}`
    : "NOT INVESTMENT ADVICE  ·  Not from a registered investment advisor  ·  AI-assisted analysis  ·  Author may hold positions";
  const footerStamp = `v${stamp.footerVersion} · ${stamp.footerTimestamp} · derived from ${stamp.canonicalJsx} (canonical)`;
  return (
    // Anchor at bottom: 0 so the masked band extends to the very edge of
    // the page (no leak zone below the footer). Inner padding-bottom of
    // 0.15in places the disclaimer line visually where it was before;
    // padding-left/right of 1in match memo.py's MARGIN_L/R. Background
    // covers full width so any content reaching into the bottom band is
    // hidden, not just content inside the 1in margin column.
    // Spec §3.5 A: footer band must mask any overflowing content all the
    // way to the page edge — otherwise long glossary/disclaimer/narrative
    // entries (e.g. NAUT, ZM v022 Page 5) leak below the disclaimer line.
    <div className="memo-footer" style={{
      position: 'absolute',
      left: 0,
      right: 0,
      bottom: 0,
      background: PALETTE.paper,
      paddingTop: '4pt',
      paddingBottom: '0.15in',
      paddingLeft: '1in',
      paddingRight: '1in',
    }}>
      <div style={{
        borderTop: `0.4pt solid ${PALETTE.rule}`,
        paddingTop: '6pt',
      }}>
        <div style={{
          fontFamily: FONT_SANS,
          fontWeight: 600,
          fontSize: '6.5pt',
          color: PALETTE.ink,
        }}>
          {disclaimer}
        </div>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginTop: '8pt',
        }}>
          <div style={{
            fontFamily: FONT_MONO,
            fontSize: '6pt',
            color: PALETTE.muted,
          }}>
            {footerStamp}
          </div>
          <div style={{
            fontFamily: FONT_SANS,
            fontSize: '6pt',
            color: PALETTE.muted,
          }}>
            Alameda Research 2: Electric Boogaloo (AR2EB)  ·  arthur@culang.co  ·  ar2eb.com  ·  {pageLabel}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Section header (eyebrow + horizontal rule) ─────────────────────────
function SectionHeader({ label, marginTop = '12pt', marginBottom = '12pt' }) {
  return (
    <div style={{ marginTop, marginBottom }}>
      <Eyebrow>{label}</Eyebrow>
      <div style={{ marginTop: '4pt' }}>
        <Rule />
      </div>
    </div>
  );
}

// ── 3-column grid for back-matter sections ─────────────────────────────
function ThreeColGrid({ items, renderItem, rowGap = '12pt' }) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(3, 1fr)',
      columnGap: '16pt',
      rowGap,
    }}>
      {items.map((item, i) => (
        <div key={i}>{renderItem(item, i)}</div>
      ))}
    </div>
  );
}

// ── Reusable page header (logo + eyebrow + company + recap strip). The
// `compact` mode trims internal margins so Page 4 (4-column quant grid)
// fits without overflow. Page 5 uses the default (slightly airier). ──
function PageHeader({ memo, suffix, label, recapWeighted = false, compact = false }) {
  const bear = memo.scenarios.find(s => s.key === 'bear');
  const base = memo.scenarios.find(s => s.key === 'base');
  const bull = memo.scenarios.find(s => s.key === 'bull');
  const w = memo.print.weighted;
  const wSign = w.upsidePct >= 0 ? '+' : '';
  const recap = recapWeighted
    ? `Bear  ${fmtDollars(bear.price)}     Base  ${fmtDollars(base.price)}     `
      + `Bull  ${fmtDollars(bull.price)}     ·     `
      + `Weighted  ${fmtDollars(w.expected)}  (${wSign}${w.upsidePct.toFixed(1)}%)`
    : `Bear  ${fmtDollars(bear.price)}     Base  ${fmtDollars(base.price)}     `
      + `Bull  ${fmtDollars(bull.price)}`;
  const padTop = compact ? '12pt' : '22pt';
  const gap1 = compact ? '8pt' : '12pt';
  const gap2 = compact ? '4pt' : '8pt';
  const ruleMargin = compact ? '8pt' : '14pt';
  return (
    <>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '28pt',
                    paddingTop: padTop }}>
        <img src="assets/ar2eb-logo-v3-cropped.png" alt=""
             style={{ width: '150pt', height: 'auto', flexShrink: 0 }} />
        <div style={{ flex: 1 }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'baseline',
          }}>
            <Eyebrow>
              INTERNAL RESEARCH  ·  MEMO  ·  NOT INVESTMENT ADVICE  ·  AI-ASSISTED
            </Eyebrow>
            <div style={{
              fontFamily: FONT_SANS,
              fontSize: '7.5pt',
              color: PALETTE.muted,
            }}>
              {fmtDayMonthYear(memo.publishedISO)}  ·  {label}
            </div>
          </div>
          <div style={{
            marginTop: gap1,
            display: 'flex',
            alignItems: 'baseline',
            gap: '8pt',
          }}>
            <div style={{
              fontFamily: FONT_SANS,
              fontWeight: 600,
              fontSize: '15pt',
              color: PALETTE.ink,
              lineHeight: 1.0,
            }}>
              {memo.company}
            </div>
            <div style={{
              fontFamily: FONT_SANS,
              fontSize: '12pt',
              color: PALETTE.muted,
              lineHeight: 1.0,
            }}>
              {suffix}
            </div>
          </div>
          <div style={{
            marginTop: gap2,
            textAlign: 'right',
            fontFamily: FONT_MONO,
            fontSize: recapWeighted ? '10pt' : '9pt',
            color: recapWeighted ? PALETTE.ink : PALETTE.muted,
          }}>
            {recap}
          </div>
        </div>
      </div>

      <div style={{ marginTop: ruleMargin }}>
        <Rule strong />
      </div>
    </>
  );
}

// ── Page 1 — Headline (qualitative + probability-weighted answer) ──────
// Two-column layout: LEFT (~56%) is text — central question, thesis,
// the big expected value, forward-compounded table, weighting rationale,
// and decomposition insight. RIGHT (~44%) is the forward-value chart.
// Below: 4-column scenario summary cards. Footer.

// Private-company chart: funding-round history (left of today) + exit-scenario
// fan (right of today), log Y. Each scenario draws a dashed line from today's
// last mark to its (years_to_exit, exit_per_share_nominal) endpoint.
function PrivateValueChart({ memo, widthPt = 415, heightPt = 290 }) {
  const NEG = '#b91c1c', POS = '#15803d';
  const mark = memo.spot.price;
  const fh = memo.print.fundingHistory;
  const scn = memo.print.scenarios;
  const scnList = scnKeysFor(memo);
  const SCN_C = {
    ultra_bear: '#5b1010', bear: '#b91c1c', base: '#1e3a8a',
    bull: '#15803d', ultra_bull: '#762aa6',
  };
  const xMin = fh.xMin;
  const xMax = Math.max(...scnList.map(k => scn[k].exitTerms.yearsToExit)) + 0.5;
  const allY = [
    ...fh.rounds.map(r => r.ps), mark,
    ...scnList.map(k => scn[k].exitTerms.exitPerShareNominal),
  ].filter(v => v > 0);
  const yLo = Math.pow(10, Math.floor(Math.log10(Math.min(...allY))));
  const yHi = Math.pow(10, Math.ceil(Math.log10(Math.max(...allY))));
  const plotL = 34, plotR = widthPt - 70, plotT = 22, plotB = heightPt - 20;
  const x = t => plotL + (t - xMin) / (xMax - xMin) * (plotR - plotL);
  const y = v => {
    const c = Math.max(yLo, Math.min(yHi, v));
    return plotB + (Math.log10(c) - Math.log10(yLo)) / (Math.log10(yHi) - Math.log10(yLo)) * (plotT - plotB);
  };
  const yTicks = [];
  for (let e = Math.log10(yLo); e <= Math.log10(yHi) + 0.001; e++) yTicks.push(Math.pow(10, e));
  const todayX = x(0);
  const histPts = [...fh.rounds.map(r => [r.x, r.ps]), [0, mark]];
  const pathD = pts => pts.map(([t, v], i) => `${i === 0 ? 'M' : 'L'} ${x(t).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  // End-label declutter (min 9pt vertical separation).
  const ends = scnList.map(k => {
    const e = scn[k].exitTerms;
    return { k, t: e.yearsToExit, v: e.exitPerShareNominal, c: SCN_C[k], lab: scn[k].shortLabel };
  }).sort((a, b) => a.v - b.v);
  let prevY = null;
  const endPos = ends.map(e => {
    let py = y(e.v) + 2;
    if (prevY !== null && prevY - py < 9) py = prevY - 9;
    prevY = py;
    return { ...e, py };
  });

  return (
    <svg width={`${widthPt}pt`} height={`${heightPt}pt`} viewBox={`0 0 ${widthPt} ${heightPt}`} style={{ display: 'block' }}>
      <text x={plotL} y={12} fontFamily={FONT_SANS} fontWeight={600} fontSize="7.5pt"
            fill={PALETTE.muted} letterSpacing="0.04em">
        FUNDING ROUNDS  ·  LAST MARK  ·  EXIT-SCENARIO FAN (PV at exit, $/sh)
      </text>
      {yTicks.map(t => (
        <g key={`y${t}`}>
          <line x1={plotL} x2={plotR} y1={y(t)} y2={y(t)} stroke={PALETTE.rule} strokeWidth="0.3" />
          <text x={plotL - 4} y={y(t) + 2} fontFamily={FONT_MONO} fontSize="6pt" fill={PALETTE.muted} textAnchor="end">
            {t < 1 ? `$${t.toFixed(2)}` : `$${t.toFixed(0)}`}
          </text>
        </g>
      ))}
      {/* today divider */}
      <line x1={todayX} x2={todayX} y1={plotT} y2={plotB} stroke={PALETTE.muted} strokeWidth="0.4" strokeDasharray="1,2" />
      <text x={todayX} y={plotB + 9} fontFamily={FONT_MONO} fontSize="6pt" fill={PALETTE.muted} textAnchor="middle">today</text>
      {/* last-mark reference */}
      <line x1={plotL} x2={plotR} y1={y(mark)} y2={y(mark)} stroke={PALETTE.muted} strokeWidth="0.6" strokeDasharray="2,2" />
      <text x={plotL + 2} y={y(mark) - 2} fontFamily={FONT_MONO} fontSize="6.5pt" fill={PALETTE.muted}>last mark ${mark.toFixed(0)}</text>
      {/* funding history line + round markers */}
      <path d={pathD(histPts)} stroke={PALETTE.text} strokeWidth="0.9" fill="none" />
      {fh.rounds.map(r => (
        <g key={r.name}>
          <circle cx={x(r.x)} cy={y(r.ps)} r="1.6" fill={PALETTE.ink} />
          <text x={x(r.x)} y={y(r.ps) - 4} fontFamily={FONT_SANS} fontSize="5pt" fill={PALETTE.muted} textAnchor="middle">
            {r.name.replace('Series ', '')}
          </text>
        </g>
      ))}
      <circle cx={todayX} cy={y(mark)} r="2.6" fill={PALETTE.ink} />
      {/* exit-scenario fan */}
      {scnList.map(k => {
        const e = scn[k].exitTerms;
        return <path key={k} d={pathD([[0, mark], [e.yearsToExit, e.exitPerShareNominal]])}
                     stroke={SCN_C[k]} strokeWidth="0.9" fill="none" strokeDasharray="3,2" />;
      })}
      {scnList.map(k => {
        const e = scn[k].exitTerms;
        return <circle key={`e${k}`} cx={x(e.yearsToExit)} cy={y(e.exitPerShareNominal)} r="1.6" fill={SCN_C[k]} />;
      })}
      {endPos.map(e => (
        <text key={`l${e.k}`} x={plotR + 3} y={e.py} fontFamily={FONT_MONO} fontSize="5.5pt" fill={e.c}>
          {e.lab} ${e.v >= 1000 ? (e.v/1000).toFixed(1)+'k' : e.v.toFixed(0)}
        </text>
      ))}
    </svg>
  );
}

function ForwardValueChart({ memo, widthPt = 415, heightPt = 290 }) {
  const NEG = '#b91c1c';
  const POS = '#15803d';
  const ULTRA = '#762aa6';                   // deep purple — tail signifier
  const BENCH = 'rgb(140,140,140)';          // benchmark gray
  const BENCH_LBL = 'rgb(115,115,115)';
  const spot = memo.spot.price;
  const hist = memo.historicalPrices;
  const printScn = memo.print.scenarios;
  const w = memo.print.weighted;
  const X_MIN = hist.xMin;
  const X_MAX = 20.0;

  // Scenario forward paths: expected_per_share × (1 + terminal WACC)^t for t=0..20.
  // Dynamically computed per-scenario so tickers with ultra_bear get an
  // additional line plotted. SCN_PATH_META keys map to JSX color tokens
  // declared above (NEG/POS/ULTRA/etc) and per-line stroke widths.
  const path = (key) => {
    const s = printScn[key];
    const wacc = s.dcfPath.wacc_path[s.dcfPath.wacc_path.length - 1];
    return Array.from({ length: 21 }, (_, t) => [t, s.expectedPerShare * Math.pow(1 + wacc, t)]);
  };
  const scnList = scnKeysFor(memo);
  const scnPaths = Object.fromEntries(scnList.map(k => [k, path(k)]));
  // Legacy aliases — preserved so the rest of this big component (label
  // sorting, multiplier annotations) doesn't need broader refactoring.
  // Missing-scenario lookups are guarded; e.g. tickers without ultra_bear
  // skip rendering the ultraBearP line.
  const ultraBearP = scnPaths.ultra_bear;
  const bearP  = scnPaths.bear;
  const baseP  = scnPaths.base;
  const bullP  = scnPaths.bull;
  const ultraP = scnPaths.ultra_bull;

  const weightedAt = (t) =>
    Object.values(printScn).reduce((acc, s) => {
      const wacc = s.dcfPath.wacc_path[s.dcfPath.wacc_path.length - 1];
      return acc + s.probability * s.expectedPerShare * Math.pow(1 + wacc, t);
    }, 0);
  const weightedP = Array.from({ length: 21 }, (_, t) => [t, weightedAt(t)]);

  // Benchmarks
  const TSY = 0.045, EQ = 0.085;
  const tsyP = Array.from({ length: 21 }, (_, t) => [t, spot * Math.pow(1 + TSY, t)]);
  const eqP  = Array.from({ length: 21 }, (_, t) => [t, spot * Math.pow(1 + EQ, t)]);

  // Y-range: data-adaptive. memo.py rules:
  // - y_min: 0.10 if any value <= 0, else largest log-decade <= min positive.
  // - y_max: bucketed ceiling based on max forward across all scenarios+benchmarks.
  const allVals = [
    ...Object.values(scnPaths).flat(), ...weightedP,
    ...tsyP, ...eqP, ...hist.points, [0, spot],
  ].map(p => p[1]);
  const hasNeg = allVals.some(v => v <= 0);
  let yMin;
  if (hasNeg) {
    yMin = 0.10;
  } else {
    const minPos = Math.min(...allVals.filter(v => v > 0));
    const raw = Math.pow(10, Math.floor(Math.log10(minPos)));
    yMin = Math.max(0.10, Math.min(100.0, raw));
  }
  const maxFwd = Math.max(
    ...scnList.map(k => scnPaths[k][20][1]),
    weightedP[20][1], tsyP[20][1], eqP[20][1]
  );
  let yMax;
  if (maxFwd <= 180) yMax = 200;
  else if (maxFwd <= 900) yMax = 1000;
  else if (maxFwd <= 1800) yMax = 2000;
  else if (maxFwd <= 9000) yMax = 10000;
  else yMax = Math.pow(10, Math.ceil(Math.log10(maxFwd * 1.5)));
  const logMin = Math.log10(yMin);
  const logMax = Math.log10(yMax);

  // End-of-line series labels. SCN_LABEL_META maps each scenario key to its
  // rendered label + color; built dynamically from scnList so tickers with
  // ultra_bear/ultra_bull get the extra lines and others skip cleanly. Defined
  // before the plot box so the RIGHT margin can be sized to the widest label.
  const SCN_LABEL_META = {
    ultra_bear: { name: 'Ultra Bear', color: SCN_COLORS.ultra_bear },
    bear:       { name: 'Bear',       color: NEG },
    base:       { name: 'Base',       color: PALETTE.accent },
    bull:       { name: 'Bull',       color: POS },
    ultra_bull: { name: 'Ultra Bull', color: ULTRA },
  };
  const endLabels = [
    ...scnList.map(k => {
      const p = scnPaths[k];
      const m = SCN_LABEL_META[k];
      return [p[20][1], `${m.name}  ${(p[20][1] / spot).toFixed(2)}×`, m.color];
    }),
    [weightedP[20][1], `Weighted  ${(weightedP[20][1] / spot).toFixed(2)}×`, PALETTE.ink],
    [tsyP[20][1],      `Tsy 4.5%  ${(tsyP[20][1] / spot).toFixed(2)}×`,  BENCH_LBL],
    [eqP[20][1],       `S&P 8.5%  ${(eqP[20][1] / spot).toFixed(2)}×`,   BENCH_LBL],
  ].sort((a, b) => a[0] - b[0]);

  // Plot area within SVG. Padding lets Y labels (left) + end-of-line series
  // labels (right) live outside the plot. The RIGHT margin is data-driven:
  // wide enough for the WIDEST end label at its render size so nothing clips
  // at the SVG edge (spec §3.5). Floored at the original 60 so short-label
  // charts stay byte-identical to the prior baseline.
  const LABEL_FS = 6.5, LABEL_GAP = 4, LABEL_PAD = 3;
  const maxLabelW = endLabels.reduce(
    (mx, [, lbl]) => Math.max(mx, estSvgTextWidth(lbl, LABEL_FS)), 0);
  const plotLeft = 32;
  const plotRight = widthPt - Math.max(60, LABEL_GAP + maxLabelW + LABEL_PAD);
  const plotTop = 24;
  const plotBot = heightPt - 18;

  const x = (t) => plotLeft + (t - X_MIN) / (X_MAX - X_MIN) * (plotRight - plotLeft);
  const y = (v) => {
    const clamped = Math.max(yMin, Math.min(yMax, v));
    return plotBot + (Math.log10(clamped) - logMin) / (logMax - logMin) * (plotTop - plotBot);
  };
  const pathD = (pts) => pts.map(([t, v], i) => `${i === 0 ? 'M' : 'L'} ${x(t).toFixed(2)},${y(v).toFixed(2)}`).join(' ');

  const yTicks = [0.10, 1.0, 10.0, 100.0, 1000.0, 10000.0].filter(t => t >= yMin && t <= yMax);
  const xTicks = [
    [-5, '-5y'], [-2, '-2y'], [0, 'today'],
    [5, '+5y'], [10, '+10y'], [15, '+15y'], [20, '+20y'],
  ].filter(([t]) => t >= X_MIN && t <= X_MAX);   // drop ticks off-plot on recent IPOs (X_MIN > -5)

  // End-of-line labels with min-vertical-separation enforcement (endLabels +
  // SCN_LABEL_META are built above, before the plot box).
  // Bottom-up stacking; ensure at least 8pt vertical separation.
  const MIN_SEP = 8;
  const labelPositions = [];
  let prevY = null;
  for (const [val, lbl, col] of endLabels) {
    let py = y(val) + 2;
    if (prevY !== null && prevY - py < MIN_SEP) py = prevY - MIN_SEP;
    labelPositions.push([py, lbl, col]);
    prevY = py;
  }

  // Multiplier annotations at +5/+10/+15. Bear/base annotations go below the
  // line (since bear tends to sit lowest); others go above.
  const annotate = (pts, color, pos) => {
    const dy = pos === 'above' ? -4 : 8;
    // Suppress the ×-annotation on a wiped-out scenario (rounds to 0.00×) — the
    // repeated "0.00×" overprinted on NAUT's floored lines; the end-label suffices.
    return pts.filter(([t, v]) => [5, 10, 15].includes(t) && Math.abs(v / spot) >= 0.005).map(([t, v]) => (
      <text key={`${color}-${t}-${pos}`}
            x={x(t)} y={y(v) + dy}
            fontFamily={FONT_MONO} fontSize="5.5pt" fill={color}
            textAnchor="middle">
        {(v / spot).toFixed(2)}×
      </text>
    ));
  };

  const histPoints = [...hist.points, [0, spot]];
  const todayX = x(0);

  // Title spans the full SVG width (it sits above the plot, clear of the y-axis
  // labels). It's longer than the box at 7.5pt, so compress-to-fit only when it
  // would otherwise overflow the SVG edge — keeps the size/hierarchy intact and
  // can never clip, for any title string.
  const TITLE = 'PRICE + PROJECTIONS  ·  HISTORICAL THROUGH PROBABILITY-WEIGHTED FORWARD';
  const TITLE_FS = 7.5, TITLE_LS = 0.04;
  const titleAvail = widthPt - plotLeft - LABEL_PAD;
  const titleFit = estSvgTextWidth(TITLE, TITLE_FS, TITLE_LS) > titleAvail;

  return (
    <svg width={`${widthPt}pt`} height={`${heightPt}pt`}
         viewBox={`0 0 ${widthPt} ${heightPt}`}
         style={{ display: 'block' }}>
      {/* Title — compressed to the box width only when it would overflow. */}
      <text x={plotLeft} y={12}
            fontFamily={FONT_SANS} fontWeight={600} fontSize={`${TITLE_FS}pt`}
            fill={PALETTE.muted} letterSpacing={`${TITLE_LS}em`}
            {...(titleFit ? { textLength: titleAvail, lengthAdjust: 'spacingAndGlyphs' } : {})}>
        {TITLE}
      </text>

      {/* Y-axis gridlines + tick labels */}
      {yTicks.map(t => (
        <g key={`yt-${t}`}>
          <line x1={plotLeft} x2={plotRight} y1={y(t)} y2={y(t)}
                stroke={PALETTE.rule} strokeWidth="0.3" />
          <text x={plotLeft - 4} y={y(t) + 2}
                fontFamily={FONT_MONO} fontSize="6pt" fill={PALETTE.muted}
                textAnchor="end">
            {t < 1 ? `$${t.toFixed(2)}` : `$${t.toFixed(0)}`}
          </text>
        </g>
      ))}

      {/* X-axis baseline + ticks */}
      <line x1={plotLeft} x2={plotRight} y1={plotBot} y2={plotBot}
            stroke={PALETTE.rule} strokeWidth="0.5" />
      {xTicks.map(([t, lbl]) => (
        <text key={`xt-${t}`} x={x(t)} y={plotBot + 9}
              fontFamily={FONT_MONO} fontSize="6pt" fill={PALETTE.muted}
              textAnchor="middle">
          {lbl}
        </text>
      ))}

      {/* "Today" divider line (dashed vertical) */}
      <line x1={todayX} x2={todayX} y1={plotTop} y2={plotBot}
            stroke={PALETTE.muted} strokeWidth="0.4" strokeDasharray="1,2" />

      {/* Spot reference line (dashed horizontal) */}
      <line x1={plotLeft} x2={plotRight} y1={y(spot)} y2={y(spot)}
            stroke={PALETTE.muted} strokeWidth="0.6" strokeDasharray="2,2" />
      <text x={plotRight - 2} y={y(spot) - 2}
            fontFamily={FONT_MONO} fontSize="6.5pt" fill={PALETTE.muted}
            textAnchor="end">
        spot ${spot.toFixed(2)}
      </text>

      {/* Historical price line */}
      <path d={pathD(histPoints)} stroke={PALETTE.text} strokeWidth="0.9" fill="none" />
      <text x={x(hist.points[0][0]) + 2} y={y(hist.points[0][1]) - 4}
            fontFamily={FONT_SANS} fontSize="5.5pt" fill={PALETTE.muted}>
        {hist.ipoMarker}
      </text>

      {/* Today's spot marker */}
      <circle cx={todayX} cy={y(spot)} r="2.6" fill={PALETTE.ink} />

      {/* Benchmark lines (dotted, light) */}
      <path d={pathD(tsyP)} stroke={BENCH} strokeWidth="0.5" fill="none" strokeDasharray="1,2" />
      <path d={pathD(eqP)}  stroke={BENCH} strokeWidth="0.5" fill="none" strokeDasharray="1,2" />

      {/* Scenario paths — one per scenario in the ticker. */}
      {scnList.map(k => (
        <path key={`p-${k}`}
              d={pathD(scnPaths[k])}
              stroke={SCN_LABEL_META[k].color}
              strokeWidth="0.7" fill="none" />
      ))}
      {/* Weighted line — thickest, ink */}
      <path d={pathD(weightedP)} stroke={PALETTE.ink} strokeWidth="2.0" fill="none" />

      {/* Anchor markers at t=0 for each scenario */}
      {scnList.map(k => (
        <circle key={`a-${k}`}
                cx={todayX}
                cy={y(printScn[k].expectedPerShare)}
                r="1.6"
                fill={SCN_LABEL_META[k].color} />
      ))}
      <circle cx={todayX} cy={y(w.expected)} r="2.2" fill={PALETTE.ink} />

      {/* Multiplier annotations at +5/+10/+15. Above the line for the
          upside scenarios, below for downside; weighted is above. */}
      {bullP   && annotate(bullP, POS, 'above')}
      {ultraP  && annotate(ultraP, ULTRA, 'above')}
      {annotate(weightedP, PALETTE.ink, 'above')}
      {baseP   && annotate(baseP, PALETTE.accent, 'below')}
      {bearP   && annotate(bearP, NEG, 'below')}
      {ultraBearP && annotate(ultraBearP, SCN_COLORS.ultra_bear, 'below')}

      {/* End-of-line labels — x reserves LABEL_GAP past the plot edge; the
          plot's right margin was sized so these never reach the SVG edge. */}
      {labelPositions.map(([py, lbl, col], i) => (
        <text key={`end-${i}`} x={plotRight + LABEL_GAP} y={py}
              fontFamily={FONT_SANS} fontWeight={600} fontSize={`${LABEL_FS}pt`}
              fill={col}>
          {lbl}
        </text>
      ))}
    </svg>
  );
}

// Ribbon metrics for Page 1 scenario summary cards — same dispatch as memo.py.
function ribbonMetrics(scnPrint, dcfType) {
  const pct = (scnPrint.probability * 100).toFixed(0);
  if (dcfType === 'private_prevaluation') {
    // Private exit-scenario ribbon: exit valuation / years to exit / venture
    // WACC / probability (the analog of the public DCF ribbon).
    const e = scnPrint.exitTerms;
    return [
      ['Exit',  `$${e.exitPostMoneyBillion >= 1000 ? (e.exitPostMoneyBillion/1000).toFixed(1)+'T' : e.exitPostMoneyBillion.toFixed(0)+'B'}`],
      ['Yrs',   e.yearsToExit.toFixed(1)],
      ['WACC',  `${(e.ventureWacc * 100).toFixed(0)}%`],
      ['Prob',  `${pct}%`],
    ];
  }
  const m = scnPrint.dcfMetrics;
  if (dcfType === 'young_company') {
    return [
      ['TAM',     `${m.tam_share.toFixed(1)}%`],
      ['P(fail)', `${m.p_fail.toFixed(0)}%`],
      ['S2C',     m.s2c.toFixed(1)],
      ['Prob',    `${pct}%`],
    ];
  }
  // Mature tickers share CAGR + WACC + Prob; the 3rd slot is the
  // ticker-specific diagnostic metric. Dispatch on whichever key is present
  // so a new mature ticker only needs its own metric in the YAML, not a JSX
  // branch: LTH = slb_total_5y, ZM = anthropic_stake, ISRG = installed_base_fy30.
  const cagrCell = ['CAGR', `${m.cagr_5y >= 0 ? '+' : ''}${m.cagr_5y.toFixed(1)}%`];
  const waccCell = ['WACC', `${(m.wacc * 100).toFixed(1)}%`];
  const probCell = ['Prob', `${pct}%`];
  let thirdCell;
  if (m.slb_total_5y !== undefined) {
    thirdCell = ['SLB', `$${m.slb_total_5y.toFixed(1)}B`];
  } else if (m.installed_base_fy30 !== undefined) {
    thirdCell = ['Base', `${(m.installed_base_fy30 / 1000).toFixed(1)}K`];
  } else if (m.take_rate_basis !== undefined) {
    thirdCell = ['Take', `${m.take_rate_basis.toFixed(0)}bp`];
  } else if (m.anthropic_stake !== undefined) {
    thirdCell = ['Anth', `$${m.anthropic_stake.toFixed(0)}B`];
  } else {
    // Generic fallback: surface the exit multiple if set, else CAGR repeats.
    thirdCell = m.exit_fcf_multiple !== undefined
      ? ['Exit', `${m.exit_fcf_multiple.toFixed(0)}×`]
      : ['CAGR', `${m.cagr_5y >= 0 ? '+' : ''}${m.cagr_5y.toFixed(1)}%`];
  }
  return [cagrCell, waccCell, thirdCell, probCell];
}

function Page1Headline({ memo }) {
  const NEG = '#b91c1c';
  const POS = '#15803d';
  // 5-scenario memos carry a 5th weighting-rationale line + an extra card
  // column; tighten the left-column type a touch so the central question and
  // thesis don't have to be hand-trimmed to clear the footer band. 4-scenario
  // memos render exactly as before.
  const five = memo.scenarios.length === 5;
  const qFont = five ? '11pt' : '12pt';
  const thesisLH = five ? 1.24 : 1.28;
  const isPriv = memo.print.dcfType === 'private_prevaluation';
  const spot = memo.spot.price;
  const refLabel = isPriv ? 'last mark' : 'spot';   // private compares to last round mark
  const w = memo.print.weighted;
  const wSign = w.upsidePct >= 0 ? '+' : '';
  const wColor = w.expected >= spot ? POS : NEG;

  // Decomposition insight — mirrors memo.py lines 615-629.
  const bullScn = memo.print.scenarios.bull;
  const ultraScn = memo.print.scenarios.ultra_bull;
  const bullContrib = bullScn.probability * bullScn.expectedPerShare;
  const ultraContrib = ultraScn.probability * ultraScn.expectedPerShare;
  const tailContrib = bullContrib + ultraContrib;
  const tailPct = tailContrib / w.expected * 100;
  const bullPct = Math.round(bullScn.probability * 100);
  const ultraPct = Math.round(ultraScn.probability * 100);
  const combinedPct = bullPct + ultraPct;
  const spotVsPw = Math.abs((spot / w.expected - 1) * 100);
  const spotPosition = spot > w.expected ? 'above' : 'below';
  const insight = isPriv
    ? `${memo.print.scenarios.bull.label} (${bullPct}%) + ${memo.print.scenarios.ultra_bull.label} (${ultraPct}%) `
      + `contribute $${tailContrib.toFixed(0)} — ${tailPct.toFixed(0)}% of the $${w.expected.toFixed(0)} weighted PV `
      + `despite ${combinedPct}% combined probability. The last round mark ($${spot.toFixed(0)}) sits `
      + `${spotVsPw.toFixed(0)}% ${spotPosition} the weighted PV, so secondary buyers paying through the mark are `
      + `roughly justified. The venture discount rate is the load-bearing input — see Page 4 sensitivity.`
    : `Bull (${bullPct}%) + Ultra Bull (${ultraPct}%) together contribute `
      + `$${tailContrib.toFixed(2)} — ${tailPct.toFixed(0)}% of the $${w.expected.toFixed(2)} expected value `
      + `despite ${combinedPct}% combined probability. `
      + `Today's spot ($${spot.toFixed(2)}) sits ${spotVsPw.toFixed(0)}% ${spotPosition} the weighted expected; `
      + `forward-weighted value crosses spot between +5y and +10y.`;

  return (
    <div className="memo-page">
      {/* Masthead — Page 1 uses a LARGER logo (200pt wide) with a 3-row
          info column to its right. */}
      <div style={{
        display: 'flex', alignItems: 'flex-start', gap: '40pt',
        paddingTop: '8pt',
      }}>
        <img src="assets/ar2eb-logo-v3-cropped.png" alt=""
             style={{ width: '200pt', height: 'auto', flexShrink: 0 }} />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column',
                      justifyContent: 'space-between', minHeight: '46pt' }}>
          {/* Top row: eyebrow + date */}
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            alignItems: 'baseline',
          }}>
            <Eyebrow>
              INTERNAL RESEARCH  ·  MEMO  ·  NOT INVESTMENT ADVICE  ·  AI-ASSISTED
            </Eyebrow>
            <div style={{
              fontFamily: FONT_SANS, fontSize: '7.5pt', color: PALETTE.muted,
            }}>
              {fmtDayMonthYear(memo.publishedISO)}  ·  the qualitative
            </div>
          </div>
          {/* Middle: company name + spot */}
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            alignItems: 'baseline',
          }}>
            <div style={{
              fontFamily: FONT_SANS, fontWeight: 600, fontSize: '18pt',
              color: PALETTE.ink, lineHeight: 1.0,
            }}>
              {memo.company}
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{
                fontFamily: FONT_MONO, fontWeight: 700, fontSize: '18pt',
                color: PALETTE.ink, lineHeight: 1.0,
              }}>
                ${spot.toFixed(2)}
              </div>
              {isPriv && (
                <div style={{ fontFamily: FONT_SANS, fontSize: '6.5pt', color: PALETTE.muted, marginTop: '1pt' }}>
                  last round mark · {memo.print.private.spotRound}
                </div>
              )}
            </div>
          </div>
          {/* Bottom: exchange/ticker/DCF type + masthead extras */}
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            alignItems: 'baseline',
          }}>
            <div style={{
              fontFamily: FONT_SANS, fontSize: '8.5pt', color: PALETTE.muted,
            }}>
              {memo.exchange} : {memo.ticker}   ·   {memo.dcfType}
            </div>
            <div style={{
              fontFamily: FONT_SANS, fontSize: '8.5pt', color: PALETTE.muted,
            }}>
              {memo.metrics.mktCap} mkt cap  ·  {memo.metrics.shares} sh  ·  {memo.metrics.cash}
            </div>
          </div>
        </div>
      </div>

      <div style={{ marginTop: '8pt' }}>
        <Rule strong />
      </div>

      {/* Two-column band */}
      <div style={{
        marginTop: '12pt',
        display: 'grid',
        gridTemplateColumns: '56fr 44fr',
        columnGap: '24pt',
      }}>
        {/* LEFT: central question + thesis + PW block */}
        <div>
          <Eyebrow>THE CENTRAL QUESTION</Eyebrow>
          <div style={{
            marginTop: '6pt',
            fontFamily: FONT_SANS, fontSize: qFont, color: PALETTE.ink,
            lineHeight: 1.2,
          }}>
            {memo.question}
          </div>

          <div style={{
            marginTop: '6pt',
            fontFamily: FONT_SANS, fontSize: '8pt', color: PALETTE.text,
            lineHeight: thesisLH,
          }}>
            {memo.thesis}
          </div>

          <div style={{ marginTop: '10pt' }}>
            <Eyebrow>PROBABILITY-WEIGHTED EXPECTED VALUE</Eyebrow>
          </div>

          <div style={{
            marginTop: '6pt',
            display: 'flex', alignItems: 'baseline', gap: '14pt',
          }}>
            <div style={{
              fontFamily: FONT_MONO, fontWeight: 700, fontSize: '24pt',
              color: PALETTE.ink, lineHeight: 1.0,
            }}>
              ${w.expected.toFixed(2)}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{
                fontFamily: FONT_SANS, fontSize: '9pt', color: PALETTE.muted,
              }}>
                expected fair value today
              </div>
              <div style={{
                marginTop: '3pt',
                fontFamily: FONT_MONO, fontSize: '9pt', color: wColor,
              }}>
                {wSign}{w.upsidePct.toFixed(1)}% vs {refLabel} ${spot.toFixed(2)}
              </div>
            </div>
          </div>

          {/* Forward compounded value table — public only (the forward
              compounding is meaningless for a private pre-exit company). */}
          {!isPriv && <>
          <div style={{
            marginTop: '10pt',
            fontFamily: FONT_SANS, fontWeight: 600, fontSize: '7.5pt',
            color: PALETTE.muted, letterSpacing: '0.04em',
            textTransform: 'uppercase',
          }}>
            FORWARD COMPOUNDED VALUE
          </div>
          <div style={{
            marginTop: '6pt',
            display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
          }}>
            {memo.compound.map(c => {
              const mc = c.value >= spot ? POS : NEG;
              return (
                <div key={c.y}>
                  <div style={{
                    fontFamily: FONT_SANS, fontWeight: 600, fontSize: '8pt',
                    color: PALETTE.muted,
                  }}>
                    +{c.y}y
                  </div>
                  <div style={{
                    marginTop: '2pt',
                    fontFamily: FONT_MONO, fontSize: '11pt', color: PALETTE.ink,
                  }}>
                    ${c.value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <div style={{
                    marginTop: '2pt',
                    fontFamily: FONT_MONO, fontSize: '8pt', color: mc,
                  }}>
                    {c.mult.toFixed(2)}× spot
                  </div>
                </div>
              );
            })}
          </div>
          </>}

          {/* Weighting rationale */}
          <div style={{
            marginTop: '8pt',
            fontFamily: FONT_SANS, fontWeight: 600, fontSize: '7.5pt',
            color: PALETTE.muted, letterSpacing: '0.04em',
            textTransform: 'uppercase',
          }}>
            WEIGHTING RATIONALE
          </div>
          <div style={{ marginTop: '3pt' }}>
            {memo.weightingRationale.map((r, i) => (
              <div key={i} style={{
                marginTop: i === 0 ? 0 : '2pt',
                fontFamily: FONT_SANS, fontSize: '7pt', color: PALETTE.text,
                lineHeight: 1.28,
              }}>
                <span style={{ fontWeight: 600, color: PALETTE.accent }}>
                  {r.label}
                </span>
                <span>  {r.body}</span>
              </div>
            ))}
          </div>

          {/* Decomposition insight */}
          <div style={{
            marginTop: '6pt',
            fontFamily: FONT_SANS, fontSize: '7.5pt', color: PALETTE.text,
            lineHeight: 1.3,
          }}>
            {insight}
          </div>
        </div>

        {/* RIGHT: forward-value chart (public) or funding+exit fan (private) */}
        <div>
          {memo.print.dcfType === 'private_prevaluation'
            ? <PrivateValueChart memo={memo} />
            : <ForwardValueChart memo={memo} />}
        </div>
      </div>

      {/* Section separator + scenario summary cards */}
      <div style={{ marginTop: memo.scenarios.length === 5 ? '4pt' : '6pt' }}><Rule /></div>

      {/* Scenario summary cards (compact — full narrative on Page 2).
          Column count tracks scenario count: 4 for the standard tickers,
          5 when a ticker carries ultra_bear. 5-col mode tightens typography
          AND the top margin — a 5-scenario Page 1 left column (thesis +
          PWEV + 5 weighting lines + decomposition) is tall enough that the
          card headlines can otherwise sit behind the footer band. */}
      <div style={{
        marginTop: memo.scenarios.length === 5 ? '4pt' : '8pt',
        display: 'grid',
        gridTemplateColumns: `repeat(${memo.scenarios.length}, 1fr)`,
        columnGap: memo.scenarios.length === 5 ? '10pt' : '16pt',
      }}>
        {memo.scenarios.map(scn => {
          const upside = (scn.price / spot - 1) * 100;
          const upSign = upside >= 0 ? '+' : '';
          const upColor = upside >= 0 ? POS : NEG;
          const scnPrint = memo.print.scenarios[scn.key === 'ultra' ? 'ultra_bull' : scn.key];
          const ribbon = ribbonMetrics(scnPrint, memo.print.dcfType);
          const l1 = `${ribbon[0][0]}  ${ribbon[0][1]}    ${ribbon[1][0]}  ${ribbon[1][1]}`;
          const l2 = `${ribbon[2][0]}  ${ribbon[2][1]}    ${ribbon[3][0]}  ${ribbon[3][1]}`;
          const isWide = memo.scenarios.length === 5;
          const F = {
            label:    isWide ? '9.5pt'  : '11pt',
            price:    isWide ? '14pt'   : '18pt',
            upside:   isWide ? '7pt'    : '8.5pt',
            ribbon:   isWide ? '6pt'    : '7pt',
            headline: isWide ? '8pt'    : '9.5pt',
          };
          return (
            <div key={scn.key}>
              <div style={{
                display: 'flex', justifyContent: 'space-between',
                alignItems: 'baseline',
              }}>
                <div style={{
                  fontFamily: FONT_SANS, fontWeight: 600, fontSize: F.label,
                  color: PALETTE.ink, letterSpacing: '0.02em',
                }}>
                  {scn.label}
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{
                    fontFamily: FONT_MONO, fontWeight: 700, fontSize: F.price,
                    color: PALETTE.ink, lineHeight: 1.0,
                  }}>
                    ${scn.price.toFixed(2)}
                  </div>
                  <div style={{
                    marginTop: '4pt',
                    fontFamily: FONT_MONO, fontSize: F.upside, color: upColor,
                  }}>
                    {upSign}{upside.toFixed(1)}%  vs spot
                  </div>
                </div>
              </div>
              <div style={{
                marginTop: '6pt',
                fontFamily: FONT_MONO, fontSize: F.ribbon, color: PALETTE.muted,
                lineHeight: 1.4,
              }}>
                <div>{l1}</div>
                <div>{l2}</div>
              </div>
              <div style={{ marginTop: '4pt' }}><Rule /></div>
              <div style={{
                marginTop: '6pt',
                fontFamily: FONT_SANS, fontWeight: 500, fontSize: F.headline,
                color: PALETTE.ink, lineHeight: 1.2,
              }}>
                {scn.headline}
              </div>
            </div>
          );
        })}
      </div>

      <PageFooter memo={memo} pageLabel={`page 1 of ${memoTotalPages(memo)}`} />
    </div>
  );
}

// ── Page 2 — Scenario narratives ───────────────────────────────────────
// 4-column layout. Each column: label + price + upside + probability +
// headline + "WHY x%" rationale + "WHAT HAPPENS" narrative paragraphs.
//
// Header is different from Pages 4/5: full-width eyebrow row on top,
// smaller (110pt) logo on the second row, then a PROBABILITY WEIGHTS
// strip — matches memo.py lines 1019-1059.
function Page2Narratives({ memo }) {
  const w = memo.print.weighted;
  const wSign = w.upsidePct >= 0 ? '+' : '';
  const NEG = '#b91c1c';
  const POS = '#15803d';
  // Build prob strip dynamically — tickers may have ultra_bear (5th column).
  const PROB_LABELS = {
    ultra_bear: 'Ultra Bear',
    bear:       'Bear',
    base:       'Base',
    bull:       'Bull',
    ultra:      'Ultra Bull',  // site key for ultra_bull
  };
  const probStrip = (
    memo.scenarios.map(s => `${PROB_LABELS[s.key]} ${s.prob}%`).join('     ')
    + `     ·     `
    + `Weighted expected $${w.expected.toFixed(2)} `
    + `(${wSign}${w.upsidePct.toFixed(1)}% vs spot)`
  );

  return (
    <div className="memo-page">
      {/* Top eyebrow row — full-width, eyebrow left + date right */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'baseline',
        paddingTop: '4pt',
      }}>
        <div>
          <span style={{
            fontFamily: FONT_SANS, fontWeight: 600, fontSize: '7.5pt',
            color: PALETTE.accent, letterSpacing: '0.04em',
            textTransform: 'uppercase',
          }}>
            INTERNAL RESEARCH
          </span>
          <span style={{
            fontFamily: FONT_SANS, fontSize: '7.5pt',
            color: PALETTE.muted, marginLeft: '8pt',
          }}>
            ·  MEMO  ·  NOT INVESTMENT ADVICE  ·  AI-ASSISTED
          </span>
        </div>
        <div style={{
          fontFamily: FONT_SANS, fontSize: '7.5pt', color: PALETTE.muted,
        }}>
          {fmtDayMonthYear(memo.publishedISO)}  ·  the narratives
        </div>
      </div>

      {/* Logo + title row — smaller (110pt) logo for Pages 2/3 */}
      <div style={{
        marginTop: '10pt',
        display: 'flex',
        alignItems: 'center',
        gap: '14pt',
      }}>
        <img src="assets/ar2eb-logo-v3-cropped.png" alt=""
             style={{ width: '110pt', height: 'auto', flexShrink: 0 }} />
        <div style={{
          display: 'flex',
          alignItems: 'baseline',
          gap: '8pt',
        }}>
          <div style={{
            fontFamily: FONT_SANS, fontWeight: 600, fontSize: '15pt',
            color: PALETTE.ink, lineHeight: 1.0,
          }}>
            {memo.company}
          </div>
          <div style={{
            fontFamily: FONT_SANS, fontSize: '12pt',
            color: PALETTE.muted, lineHeight: 1.0,
          }}>
            scenario narratives
          </div>
        </div>
      </div>

      {/* Probability weights strip */}
      <div style={{ marginTop: '12pt' }}>
        <div style={{
          fontFamily: FONT_SANS, fontWeight: 600, fontSize: '8pt',
          color: PALETTE.muted, letterSpacing: '0.04em',
          textTransform: 'uppercase',
        }}>
          PROBABILITY WEIGHTS
        </div>
        <div style={{
          marginTop: '6pt',
          fontFamily: FONT_MONO, fontSize: '9pt', color: PALETTE.ink,
        }}>
          {probStrip}
        </div>
      </div>

      <div style={{ marginTop: '10pt' }}>
        <Rule strong />
      </div>

      {/* Scenario narrative grid — column count tracks scenarios.length.
          5-col mode (ultra_bear present) tightens fonts so narratives fit
          in 20%-narrower columns without spilling past the page bottom. */}
      <div style={{
        marginTop: '12pt',
        display: 'grid',
        gridTemplateColumns: `repeat(${memo.scenarios.length}, 1fr)`,
        columnGap: memo.scenarios.length === 5 ? '10pt' : '16pt',
      }}>
        {memo.scenarios.map(scn => {
          // 5-col mode: tighter typography for narrower columns.
          const isWide = memo.scenarios.length === 5;
          const F = {
            label:    isWide ? '10pt'  : '11pt',
            price:    isWide ? '14pt'  : '18pt',
            upside:   isWide ? '8pt'   : '8.5pt',
            prob:     isWide ? '7.5pt' : '8pt',
            headline: isWide ? '9pt'   : '11pt',
            section:  isWide ? '6.5pt' : '7pt',
            body:     isWide ? '6.0pt' : '6.75pt',
            bodyLH:   isWide ? 1.25    : 1.28,
          };
          const upside = (scn.price / memo.spot.price - 1) * 100;
          const upSign = upside >= 0 ? '+' : '';
          const upColor = upside >= 0 ? POS : NEG;
          return (
            <div key={scn.key}>
              {/* Header row: label + price + upside */}
              <div style={{
                display: 'flex', justifyContent: 'space-between',
                alignItems: 'baseline',
              }}>
                <div style={{
                  fontFamily: FONT_SANS, fontWeight: 600, fontSize: F.label,
                  color: PALETTE.ink, letterSpacing: '0.02em',
                }}>
                  {scn.label}
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{
                    fontFamily: FONT_MONO, fontWeight: 700, fontSize: F.price,
                    color: PALETTE.ink, lineHeight: 1.0,
                  }}>
                    ${scn.price.toFixed(2)}
                  </div>
                  <div style={{
                    marginTop: '4pt',
                    fontFamily: FONT_MONO, fontSize: F.upside, color: upColor,
                  }}>
                    {upSign}{upside.toFixed(1)}%  vs spot
                  </div>
                </div>
              </div>

              {/* Probability emphasized */}
              <div style={{
                marginTop: isWide ? '8pt' : '10pt',
                fontFamily: FONT_MONO, fontSize: F.prob, color: PALETTE.accent,
              }}>
                Probability  {scn.prob}%
              </div>

              <div style={{ marginTop: '4pt' }}><Rule /></div>

              {/* Headline */}
              <div style={{
                marginTop: isWide ? '6pt' : '8pt',
                fontFamily: FONT_SANS, fontWeight: 500, fontSize: F.headline,
                color: PALETTE.ink, lineHeight: 1.15,
              }}>
                {scn.headline}
              </div>

              {/* WHY x% */}
              <div style={{
                marginTop: isWide ? '8pt' : '10pt',
                fontFamily: FONT_SANS, fontWeight: 600, fontSize: F.section,
                color: PALETTE.muted, letterSpacing: '0.04em',
                textTransform: 'uppercase',
              }}>
                WHY {scn.prob}%
              </div>
              <div style={{
                marginTop: '3pt',
                fontFamily: FONT_SANS, fontSize: F.body, color: PALETTE.text,
                lineHeight: F.bodyLH,
              }}>
                {scn.why}
              </div>

              {/* Mini-rule then WHAT HAPPENS */}
              <div style={{
                marginTop: '5pt',
                width: '30%',
                borderTop: `0.5pt solid ${PALETTE.rule}`,
              }} />
              <div style={{
                marginTop: '4pt',
                fontFamily: FONT_SANS, fontWeight: 600, fontSize: F.section,
                color: PALETTE.muted, letterSpacing: '0.04em',
                textTransform: 'uppercase',
              }}>
                WHAT HAPPENS
              </div>
              {scn.what.map((para, pi) => (
                <div key={pi} style={{
                  marginTop: pi === 0 ? '3pt' : '4pt',
                  fontFamily: FONT_SANS, fontSize: F.body, color: PALETTE.text,
                  lineHeight: F.bodyLH,
                }}>
                  {para}
                </div>
              ))}
            </div>
          );
        })}
      </div>

      <PageFooter memo={memo} pageLabel={`page 2 of ${memoTotalPages(memo)}`} />
    </div>
  );
}

// ── Page 3 — Business snapshot (6-chart grid) ──────────────────────────
// Each chart is 280pt × 190pt; 3-column × 2-row grid; per-dcf_type
// dispatch. Phase 2 ports them one at a time. Each chart computes from
// data.js inputs — no PNG embeds.

// --- Scenario colors (shared across charts) ---
const SCN_COLORS = {
  ultra_bear: '#5b1010',    // dark red — mirror of ultra_bull's deep purple
  bear:       '#b91c1c',
  base:       '#1e3a8a',
  bull:       '#15803d',
  ultra_bull: '#7629a6',
};

// Canonical scenario order — worst to best. Used everywhere that needs to
// iterate scenarios (Page 1 cards, Page 2 narratives, Page 4 quant grid,
// charts). Per-ticker visible set = SCN_ORDER ∩ keys-in-memo. ZM has all 5;
// JOBY/AUR/LTH/NAUT have the standard 4. New scenario types must be added
// here AND in scripts/build_site_data.py's SCEN_ORDER, AND any layouts that
// use `repeat(N, 1fr)` must derive N from scnKeysFor(memo).length.
const SCN_ORDER = ['ultra_bear', 'bear', 'base', 'bull', 'ultra_bull'];
function scnKeysFor(memo) {
  const scns = (memo.print && memo.print.scenarios) || {};
  return SCN_ORDER.filter(k => scns[k] !== undefined);
}

// Page 4 — Competitive landscape (§6d) renders only when the ticker carries
// a `competitive` block. Tickers without it stay at the original 5 pages;
// the footer page numbers below are computed so both cases render correctly.
function hasCompetitive(memo) {
  return !!(memo.print && memo.print.competitive);
}
// POCD scorecard (§14) is the last (back-matter) page — appended, so it never
// renumbers the earlier pages; it only grows the total by 1 when present.
function hasPOCD(memo) {
  return !!(memo.print && memo.print.pocd);
}
function memoTotalPages(memo) {
  return 5 + (hasCompetitive(memo) ? 1 : 0) + (hasPOCD(memo) ? 1 : 0);
}

// --- Chart primitives (shared by Page 3 charts) ---
//
// mkLinearScale / mkLogScale: return a function value→pixel. Following
// d3's idiom (domain, range), without pulling in d3.
const mkLinearScale = ([d0, d1], [r0, r1]) => (v) =>
  r0 + (v - d0) / (d1 - d0) * (r1 - r0);
const mkLogScale = ([d0, d1], [r0, r1]) => {
  const lo = Math.log10(d0), hi = Math.log10(d1);
  return (v) => {
    const cl = Math.max(d0, Math.min(d1, v));
    return r0 + (Math.log10(cl) - lo) / (hi - lo) * (r1 - r0);
  };
};

// Build a path "d" string from points + scales.
const pathD = (pts, xScale, yScale) =>
  pts.map(([t, v], i) =>
    `${i === 0 ? 'M' : 'L'} ${xScale(t).toFixed(2)},${yScale(v).toFixed(2)}`
  ).join(' ');

// Standard chart frame margins for the 280×190 slots on Page 3.
const CHART_MARGIN = { left: 26, right: 36, top: 16, bottom: 14 };

function ChartTitle({ children, x = 2, y = 10, maxWidth }) {
  // When a maxWidth is given and the title would overrun it, compress with
  // textLength (spec §3.5: titles size to the chart, never clip the SVG edge).
  const s = typeof children === 'string' ? children : '';
  const over = maxWidth && s && estSvgTextWidth(s, 7.5) > (maxWidth - x);
  return (
    <text x={x} y={y}
          fontFamily={FONT_SANS} fontWeight={600} fontSize="7.5pt"
          fill={PALETTE.ink}
          {...(over ? { textLength: maxWidth - x, lengthAdjust: 'spacingAndGlyphs' } : {})}>
      {children}
    </text>
  );
}

// Generic Y-axis gridlines + tick labels. `ticks` is [[value, label], ...].
function YGridTicks({ ticks, yScale, plotL, plotR }) {
  return ticks.map(([v, lbl]) => (
    <g key={`yt-${v}`}>
      <line x1={plotL} x2={plotR} y1={yScale(v)} y2={yScale(v)}
            stroke={PALETTE.rule} strokeWidth="0.3" />
      <text x={plotL - 3} y={yScale(v) + 2}
            fontFamily={FONT_MONO} fontSize="5.5pt" fill={PALETTE.muted}
            textAnchor="end">
        {lbl}
      </text>
    </g>
  ));
}

// X-axis tick labels. `ticks` is [[value, label], ...].
function XTicks({ ticks, xScale, plotB }) {
  return ticks.map(([v, lbl]) => (
    <text key={`xt-${v}`} x={xScale(v)} y={plotB + 8}
          fontFamily={FONT_MONO} fontSize="5pt" fill={PALETTE.muted}
          textAnchor="middle">
      {lbl}
    </text>
  ));
}

// --- Young-company Chart 1: revenue ramp (log scale) ---
// Historical FY24-FY26 anchor + 4 scenario projections FY27-FY36.
function YoungRevenueChart({ memo, widthPt = 280, heightPt = 190 }) {
  const ref = memo.page3.chartReference;
  const histYears = ref.historyYears;                    // e.g. [2024, 2025, 2026]
  const histRev = ref.historyRevenue;                    // e.g. [0, 0, 0.001] in $B
  const nHist = histYears.length;
  const scnKeys = scnKeysFor(memo);

  // FY labels e.g. "FY24"..."FY36" → render as 2-digit "24"..."36".
  const fyAll = [
    ...histYears.map(y => `FY${y - 2000}`),
    ...Array.from({ length: 10 }, (_, i) => `FY${27 + i}`),
  ];

  const m = CHART_MARGIN;
  const plotL = m.left, plotR = widthPt - m.right;
  const plotT = m.top, plotB = heightPt - m.bottom;

  // X scale: discrete year index 0..nHist+9, padded slightly.
  const xScale = mkLinearScale([-0.5, nHist + 9 + 1.6], [plotL, plotR]);

  // Y scale: log $B, fixed range matching memo.py (0.0005 → 80).
  const yLo = 0.0005, yHi = 80;
  const yScale = mkLogScale([yLo, yHi], [plotB, plotT]);

  // Y ticks at $1M / $10M / $100M / $1B / $10B (0.001..10 in $B).
  const yTicks = [
    [0.001, '$1M'], [0.01, '$10M'], [0.1, '$100M'],
    [1, '$1B'], [10, '$10B'],
  ];
  const xTicks = fyAll.map((fy, i) => [i, fy.slice(2)]);

  // Historical line.
  const histPlot = histRev.map((r, i) => [i, Math.max(r, 0.001)]);
  // Projection paths (each scenario: starts at last historical pt, runs to FY36).
  const projPts = (key) => {
    const rev = memo.print.scenarios[key].dcfPath.rev_path;
    return [[nHist - 1, Math.max(histRev[nHist - 1], yLo)],
            ...rev.map((r, i) => [nHist + i, Math.max(r, yLo)])];
  };
  const projEnd = (key) => {
    const rev = memo.print.scenarios[key].dcfPath.rev_path;
    return [nHist + 9, rev[rev.length - 1]];
  };
  const shortLabel = (key) => memo.print.scenarios[key].shortLabel;
  const showZeroAnchor = histRev[0] < 0.001;

  return (
    <svg width={`${widthPt}pt`} height={`${heightPt}pt`}
         viewBox={`0 0 ${widthPt} ${heightPt}`}
         style={{ display: 'block' }}>
      <ChartTitle>Revenue — history + scenarios to FY36 (log)</ChartTitle>
      <YGridTicks ticks={yTicks} yScale={yScale} plotL={plotL} plotR={plotR} />
      <XTicks ticks={xTicks} xScale={xScale} plotB={plotB} />

      {/* "Today" divider (between historical and projection) */}
      <line x1={xScale(nHist - 0.5)} x2={xScale(nHist - 0.5)}
            y1={plotT} y2={plotB}
            stroke={PALETTE.dim} strokeWidth="0.4" strokeDasharray="1,2" />

      {/* Historical line (solid, accent) */}
      <path d={pathD(histPlot, xScale, yScale)}
            stroke={PALETTE.accent} strokeWidth="1.4" fill="none" />
      {histPlot.map(([t, r]) => (
        <circle key={`h-${t}`} cx={xScale(t)} cy={yScale(r)} r="2.4"
                fill={PALETTE.accent} stroke="white" strokeWidth="0.6" />
      ))}
      {showZeroAnchor && (
        <text x={xScale(0)} y={yScale(0.0008) + 6}
              fontFamily={FONT_SANS} fontSize="5pt" fill={PALETTE.muted}
              textAnchor="middle">
          $0
        </text>
      )}

      {/* Scenario projection paths (dashed) + end-of-line labels */}
      {scnKeys.map(key => (
        <path key={`p-${key}`} d={pathD(projPts(key), xScale, yScale)}
              stroke={SCN_COLORS[key]} strokeWidth="1.1" fill="none"
              strokeDasharray="3,2" />
      ))}
      {scnKeys.map(key => {
        const [t, v] = projEnd(key);
        const py = yScale(Math.max(v, yLo));
        return (
          <g key={`pe-${key}`}>
            <circle cx={xScale(t)} cy={py} r="1.4"
                    fill={SCN_COLORS[key]} stroke="white" strokeWidth="0.4" />
            <text x={xScale(t) + 3} y={py + 2}
                  fontFamily={FONT_SANS} fontWeight={500} fontSize="5.5pt"
                  fill={SCN_COLORS[key]}>
              {shortLabel(key)} {v < 1 ? v.toFixed(2) : v.toFixed(0)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// Page 3 chart-aesthetic config is read from memo.page3.chartConfig
// (YAML page3_chart_config block). The pre-Phase 4 JSX hardcoded
// YOUNG_CHART_CFG / MATURE_CHART_CFG dicts here; those moved to YAML.

// --- Young-company Chart 4: fleet / unit growth (log scale) ---
function YoungFleetChart({ memo, widthPt = 280, heightPt = 190 }) {
  const cfg = memo.page3.chartConfig || {};
  const ref = memo.page3.chartReference;
  const scnKeys = scnKeysFor(memo);

  const fleetFromRev = (key) => {
    const rev = memo.print.scenarios[key].dcfPath.rev_path;
    const rpu = memo.print.scenarios[key].revPerUnit || [];
    return rpu.length === rev.length
      ? rev.map((r, i) => (r * 1000) / rpu[i])
      : rev.map(() => 0);
  };

  const fyAll = ['FY24', 'FY25', 'FY26', ...Array.from({ length: 10 }, (_, i) => `FY${27 + i}`)];
  const m = CHART_MARGIN;
  const plotL = m.left, plotR = widthPt - m.right;
  const plotT = m.top, plotB = heightPt - m.bottom;
  const xScale = mkLinearScale([-0.5, 13.6], [plotL, plotR]);

  const hasRef = !!cfg.fleetReference;
  const yLo = hasRef ? 1 : 0.5;
  const yHi = hasRef ? 2_000_000 : 10_000;
  const yScale = mkLogScale([yLo, yHi], [plotB, plotT]);
  const yTicks = hasRef
    ? [[10, '10'], [100, '100'], [1000, '1K'], [10000, '10K'],
       [100000, '100K'], [1000000, '1M']]
    : [[1, '1'], [10, '10'], [100, '100'], [1000, '1K'], [10000, '10K']];

  const xTicks = fyAll.map((fy, i) => [i, fy.slice(2)]);
  const shortLabel = (key) => memo.print.scenarios[key].shortLabel;
  const fmtUnits = (n) =>
    n >= 10000 ? `${(n / 1000).toFixed(0)}K` :
    n >= 1000  ? `${(n / 1000).toFixed(1)}K` :
                 `${n.toFixed(0)}`;
  const fleetHist = ref.historyFleet || [0, 0, 0];
  const fleetAnchor = cfg.fleetAnchor || fleetHist.at(-1) || 1;

  return (
    <svg width={`${widthPt}pt`} height={`${heightPt}pt`}
         viewBox={`0 0 ${widthPt} ${heightPt}`}
         style={{ display: 'block' }}>
      <ChartTitle>{cfg.fleetTitle || 'Fleet / unit growth (log)'}</ChartTitle>
      <YGridTicks ticks={yTicks} yScale={yScale} plotL={plotL} plotR={plotR} />
      <XTicks ticks={xTicks} xScale={xScale} plotB={plotB} />
      <line x1={xScale(2.5)} x2={xScale(2.5)} y1={plotT} y2={plotB}
            stroke={PALETTE.dim} strokeWidth="0.4" strokeDasharray="1,2" />

      {/* Historical fleet — drawn only when there's real data to show */}
      {fleetHist.some(v => v > 0) && (
        <>
          <path d={pathD(fleetHist.map((v, i) => [i, Math.max(v, yLo)]), xScale, yScale)}
                stroke={PALETTE.accent} strokeWidth="1.5" fill="none" />
          {fleetHist.map((v, i) =>
            v > 0 && (
              <circle key={`fh-${i}`} cx={xScale(i)} cy={yScale(v)} r="2.2"
                      fill={PALETTE.accent} stroke="white" strokeWidth="0.6" />
            )
          )}
        </>
      )}

      {cfg.fleetReference && (
        <>
          <line x1={plotL} x2={plotR}
                y1={yScale(cfg.fleetReference.value)} y2={yScale(cfg.fleetReference.value)}
                stroke={PALETTE.dim} strokeWidth="0.4" strokeDasharray="1,2" />
          <text x={plotR - 2} y={yScale(cfg.fleetReference.value) - 2}
                fontFamily={FONT_SANS} fontSize="5pt" fill={PALETTE.muted}
                textAnchor="end">
            {cfg.fleetReference.label}
          </text>
        </>
      )}

      {scnKeys.map(key => {
        const fleet = fleetFromRev(key);
        const pts = [[2, Math.max(fleetAnchor, yLo)],
                     ...fleet.map((v, i) => [3 + i, Math.max(v, yLo)])];
        const end = fleet[fleet.length - 1];
        return (
          <g key={`f-${key}`}>
            <path d={pathD(pts, xScale, yScale)}
                  stroke={SCN_COLORS[key]} strokeWidth="1.1" fill="none"
                  strokeDasharray="3,2" />
            {pts.map(([t, v], i) => (
              <circle key={`fp-${key}-${i}`} cx={xScale(t)} cy={yScale(v)} r="1.4"
                      fill={SCN_COLORS[key]} stroke="white" strokeWidth="0.4" />
            ))}
            <text x={xScale(12) + 3} y={yScale(Math.max(end, yLo)) + 2}
                  fontFamily={FONT_SANS} fontWeight={500} fontSize="5.5pt"
                  fill={SCN_COLORS[key]}>
              {shortLabel(key)} {fmtUnits(end)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// --- Young-company Chart 5: valuation (P/S on FY36 revenue) ---
function YoungValuationChart({ memo, widthPt = 280, heightPt = 190 }) {
  const cfg = memo.page3.chartConfig || {};
  const scnKeys = scnKeysFor(memo);
  const mktCap = memo.print.market.marketCapBillion;

  // P/S = today_mkt_cap / FY36 revenue per scenario.
  const ratios = scnKeys.map(k => ({
    key: k,
    label: memo.print.scenarios[k].shortLabel,
    mult: mktCap / memo.print.scenarios[k].dcfPath.rev_path.at(-1),
  }));

  const m = { left: 26, right: 22, top: 16, bottom: 30 };
  const plotL = m.left, plotR = widthPt - m.right;
  const plotT = m.top, plotB = heightPt - m.bottom;

  // Y axis: 0 → max(9, ratios×1.2), domain snapped to a round top tick. Ticks are
  // niceStep-derived, not a fixed 0/2/4/6/8 list — an ultra_bear's near-zero FY36
  // revenue puts its P/S at 50–120×, which left ~90% of the axis unscaled (spec §3.5).
  const maxR = Math.max(...ratios.map(r => r.mult));
  const rawMax = Math.max(9, maxR * 1.2);
  const yStep = niceStep(rawMax);
  const yMax = Math.ceil(rawMax / yStep) * yStep;
  const yScale = mkLinearScale([0, yMax], [plotB, plotT]);
  const yTicks = [];
  for (let i = 0; i * yStep <= yMax; i++) {
    const v = i * yStep;
    yTicks.push([v, `${v.toFixed(yStep < 1 ? 1 : 0)}×`]);
  }

  // Bars: equal spacing across plot width.
  const barW = (plotR - plotL) / (ratios.length + 1.5);
  const xCenter = (i) => plotL + (i + 1) * (plotR - plotL) / (ratios.length + 1);

  return (
    <svg width={`${widthPt}pt`} height={`${heightPt}pt`}
         viewBox={`0 0 ${widthPt} ${heightPt}`}
         style={{ display: 'block' }}>
      <ChartTitle maxWidth={widthPt}>{`$${mktCap.toFixed(2)}B mkt cap as P/S on FY36 rev`}</ChartTitle>
      <YGridTicks ticks={yTicks} yScale={yScale} plotL={plotL} plotR={plotR} />

      {/* Reference line for mature peer P/S */}
      <line x1={plotL} x2={plotR}
            y1={yScale(cfg.valnAnchorY)} y2={yScale(cfg.valnAnchorY)}
            stroke={PALETTE.dim} strokeWidth="0.5" strokeDasharray="1,2" />
      <text x={plotR - 2} y={yScale(cfg.valnAnchorY) - 2}
            fontFamily={FONT_SANS} fontSize="5pt" fill={PALETTE.muted}
            textAnchor="end">
        {cfg.valnAnchorText}
      </text>

      {/* Bars */}
      {ratios.map((r, i) => {
        const cx = xCenter(i);
        const top = yScale(r.mult);
        const baseY = yScale(0);
        return (
          <g key={r.key}>
            <rect x={cx - barW / 2} y={top} width={barW}
                  height={baseY - top}
                  fill={SCN_COLORS[r.key]} />
            <text x={cx} y={top - 4}
                  fontFamily={FONT_MONO} fontWeight={600} fontSize="7pt"
                  fill={SCN_COLORS[r.key]} textAnchor="middle">
              {r.mult.toFixed(1)}×
            </text>
            <text x={cx} y={plotB + 9}
                  fontFamily={FONT_SANS} fontSize="6pt" fill={PALETTE.text}
                  textAnchor="middle">
              {r.label}
            </text>
            <text x={cx} y={plotB + 17}
                  fontFamily={FONT_SANS} fontSize="5.5pt" fill={PALETTE.muted}
                  textAnchor="middle">
              FY36
            </text>
          </g>
        );
      })}

      {/* Caption — word-wrapped to the chart width and bottom-aligned so a long
          caption never clips the SVG right edge (spec §3.5: from data). Shrinks
          5pt→4pt if needed to keep it to ≤2 lines clear of the FY36 row. */}
      {(() => {
        const availW = widthPt - plotL - 2;
        let fs = 5, lines = wrapSvgText(cfg.valnCaption || '', availW, fs);
        while (lines.length > 2 && fs > 4) { fs -= 0.5; lines = wrapSvgText(cfg.valnCaption || '', availW, fs); }
        const lh = fs + 1.7;
        return lines.map((ln, i) => (
          <text key={`cap-${i}`} x={plotL} y={heightPt - 2 - (lines.length - 1 - i) * lh}
                fontFamily={FONT_SANS} fontSize={`${fs}pt`} fill={PALETTE.muted}>
            {ln}
          </text>
        ));
      })()}
    </svg>
  );
}

// --- Young-company Chart 6: TAM positioning at FY36 (horizontal stacked) ---
function YoungTamChart({ memo, widthPt = 280, heightPt = 190 }) {
  const cfg = memo.page3.chartConfig || {};
  const scnKeys = scnKeysFor(memo);
  const tam = memo.print.tamBillion;
  if (!tam) return null;

  // 4 rows. Each row split into: company share / competitor share / rest.
  const rows = scnKeys.map(k => {
    const s = memo.print.scenarios[k];
    const company = s.dcfPath.rev_path.at(-1);
    const competitor = s.chartData.tam_competitor_share || 0;
    const remaining = Math.max(0, tam - company - competitor);
    return {
      key: k,
      label: s.shortLabel,
      share: (s.dcfMetrics.tam_share || 0),
      company, competitor, remaining,
    };
  });

  const m = { left: 50, right: 14, top: 16, bottom: 30 };
  const plotL = m.left, plotR = widthPt - m.right;
  const plotT = m.top, plotB = heightPt - m.bottom;
  const xScale = mkLinearScale([0, tam * 1.04], [plotL, plotR]);

  // Y rows
  const rowH = (plotB - plotT) / rows.length;
  const rowY = (i) => plotT + (i + 0.5) * rowH;
  const barH = rowH * 0.5;

  const SOFT = '#94a3b8';
  const REM_FILL = '#9ca3af';

  // X ticks adapted to TAM size.
  const xTickVals = tam >= 200
    ? [0, 50, 100, 150, 200, 250]
    : tam >= 100 ? [0, 40, 80, 120, 160] : [0, 25, 50, 75];
  const xTicks = xTickVals.filter(v => v <= tam * 1.04).map(v => [v, `$${v}B`]);

  return (
    <svg width={`${widthPt}pt`} height={`${heightPt}pt`}
         viewBox={`0 0 ${widthPt} ${heightPt}`}
         style={{ display: 'block' }}>
      <ChartTitle maxWidth={widthPt}>{cfg.tamTitle}</ChartTitle>

      {/* X-axis labels along the bottom */}
      <XTicks ticks={xTicks} xScale={xScale} plotB={plotB} />

      {/* Rows */}
      {rows.map((r, i) => {
        const y = rowY(i);
        const yTop = y - barH / 2;
        const xCompanyEnd = xScale(r.company);
        const xCompetitorEnd = xScale(r.company + r.competitor);
        const xRemainingEnd = xScale(r.company + r.competitor + r.remaining);
        return (
          <g key={r.key}>
            {/* Y-axis row labels */}
            <text x={plotL - 4} y={y - 2}
                  fontFamily={FONT_SANS} fontWeight={500} fontSize="6.5pt"
                  fill={PALETTE.text} textAnchor="end">
              {r.label}
            </text>
            <text x={plotL - 4} y={y + 7}
                  fontFamily={FONT_MONO} fontSize="6pt" fill={PALETTE.muted}
                  textAnchor="end">
              {r.share.toFixed(1)}%
            </text>

            {/* Company share */}
            <rect x={plotL} y={yTop} width={xCompanyEnd - plotL} height={barH}
                  fill={SCN_COLORS[r.key]} />
            {r.company >= tam * 0.04 && (
              <text x={plotL + (xCompanyEnd - plotL) / 2} y={y + 2}
                    fontFamily={FONT_MONO} fontWeight={500} fontSize="5.5pt"
                    fill="white" textAnchor="middle">
                ${r.company.toFixed(0)}B
              </text>
            )}

            {/* Competitor share */}
            <rect x={xCompanyEnd} y={yTop} width={xCompetitorEnd - xCompanyEnd}
                  height={barH} fill={SOFT} />
            {r.competitor >= tam * 0.08 && (
              <text x={(xCompanyEnd + xCompetitorEnd) / 2} y={y + 2}
                    fontFamily={FONT_MONO} fontSize="5pt" fill="white"
                    textAnchor="middle">
                ${r.competitor.toFixed(0)}B
              </text>
            )}

            {/* Remaining */}
            <rect x={xCompetitorEnd} y={yTop} width={xRemainingEnd - xCompetitorEnd}
                  height={barH} fill={REM_FILL} opacity="0.55" />
            {r.remaining >= tam * 0.15 && (
              <text x={(xCompetitorEnd + xRemainingEnd) / 2} y={y + 2}
                    fontFamily={FONT_MONO} fontSize="5pt" fill="white"
                    textAnchor="middle">
                ${r.remaining.toFixed(0)}B
              </text>
            )}
          </g>
        );
      })}

      {/* Legend */}
      <g transform={`translate(${plotL}, ${heightPt - 8})`}>
        <rect x="0" y="-4" width="6" height="4" fill={PALETTE.accent} />
        <text x="9" y="0" fontFamily={FONT_SANS} fontSize="5.5pt"
              fontWeight={500} fill={PALETTE.accent}>
          {cfg.tamLegend[0]}
        </text>
        <rect x="40" y="-4" width="6" height="4" fill={SOFT} />
        <text x="49" y="0" fontFamily={FONT_SANS} fontSize="5.5pt"
              fill={PALETTE.text}>
          {cfg.tamLegend[1]}
        </text>
        <rect x="140" y="-4" width="6" height="4" fill={REM_FILL} opacity="0.55" />
        <text x="149" y="0" fontFamily={FONT_SANS} fontSize="5.5pt"
              fill={PALETTE.muted}>
          {cfg.tamLegend[2]}
        </text>
      </g>
    </svg>
  );
}
// LEFT axis: cumulative cash in $B (auto-fit range, not hardcoded — this
// was the §6c.6 axis-clipping bug that v002 surfaced).
// RIGHT axis: shares (M) — dotted lines, scaled separately.
// Cash path mirrors charts/young_company.py::_cash_path; shares path
// mirrors _shares_path. Both computed in JS from raw dcfPath inputs.

const cashPathSeries = (scn, startCash) => {
  // _cash_path: out[0] = startCash; per-year cash += raises[i] + fcf where
  // fcf = rev*op_margin - (rev - prev_rev)/s2c; prev_rev starts at 0 (young
  // company assumed pre-revenue at history end — matches memo.py's use of
  // cfg["rev_history"][-1] which is near-zero for the three young tickers).
  const { rev_path, op_margin } = scn.dcfPath;
  const s2c = scn.dcfMetrics.s2c;
  const raises = scn.chartData.raises;
  const out = [startCash];
  let cash = startCash, prevRev = 0;
  for (let i = 0; i < rev_path.length; i++) {
    const delta = rev_path[i] - prevRev;
    const nopat = rev_path[i] * op_margin[i];
    const reinv = s2c ? delta / s2c : 0;
    cash = cash + raises[i] + (nopat - reinv);
    out.push(cash);
    prevRev = rev_path[i];
  }
  return out;
};

const sharesPathSeries = (scn, startShares) => {
  const raises = scn.chartData.raises;
  const prices = scn.chartData.raise_prices;
  const out = [startShares];
  let shares = startShares;
  for (let i = 0; i < raises.length; i++) {
    const newSh = prices[i] > 0 ? (raises[i] * 1000 / prices[i]) : 0;
    shares += newSh;
    out.push(shares);
  }
  return out;
};

function YoungCashDilutionChart({ memo, widthPt = 280, heightPt = 190 }) {
  const scnKeys = scnKeysFor(memo);
  const startCash = memo.print.market.cashBillion;
  const startShares = memo.print.market.sharesOutstandingMillion;

  const cashByScn = Object.fromEntries(
    scnKeys.map(k => [k, cashPathSeries(memo.print.scenarios[k], startCash)])
  );
  const sharesByScn = Object.fromEntries(
    scnKeys.map(k => [k, sharesPathSeries(memo.print.scenarios[k], startShares)])
  );

  // 11 x positions: FY26 (start) + FY27-FY36 projection.
  const fyLabels = ['26', ...Array.from({ length: 10 }, (_, i) => `${27 + i}`)];

  // Margins — right side needs more room because shares labels live there.
  const m = { left: 26, right: 36, top: 16, bottom: 14 };
  const plotL = m.left, plotR = widthPt - m.right;
  const plotT = m.top, plotB = heightPt - m.bottom;

  const xScale = mkLinearScale([-0.4, 10.4], [plotL, plotR]);

  // LEFT Y axis (cash): auto-fit. Floor at 0 because cash<0 means equity
  // wipeout — the spec §6c.6 rule. Top: max observed + 10% headroom,
  // rounded up to a clean tick.
  const allCash = Object.values(cashByScn).flat();
  const cashMax = Math.max(...allCash);
  // Pick a clean ceiling (1, 2, 3, 5, 10 etc).
  const ceilCash = (v) => {
    if (v <= 1) return 1;
    if (v <= 2) return 2;
    if (v <= 3) return 3;
    if (v <= 5) return 5;
    if (v <= 10) return 10;
    return Math.ceil(v / 5) * 5;
  };
  const yMaxCash = ceilCash(cashMax * 1.05);
  const yScaleCash = mkLinearScale([0, yMaxCash], [plotB, plotT]);
  const cashTickStep = yMaxCash <= 2 ? 0.5 : yMaxCash <= 5 ? 1 : 2;
  const cashTickVals = [];
  for (let v = 0; v <= yMaxCash + 0.001; v += cashTickStep) cashTickVals.push(v);
  const cashTicks = cashTickVals.map(v => [
    v, v === 0 ? '$0' : v >= 1 ? `$${v.toFixed(0)}B` : `$${(v * 1000).toFixed(0)}M`,
  ]);

  // RIGHT Y axis (shares): auto-fit from start-shares × 0.9 to peak × 1.10.
  const allShares = Object.values(sharesByScn).flat();
  const sharesMax = Math.max(...allShares);
  const sharesLo = startShares * 0.85;
  const sharesHi = sharesMax * 1.10;
  const yScaleShares = mkLinearScale([sharesLo, sharesHi], [plotB, plotT]);
  // Clean tick step
  const sharesSpan = sharesHi - sharesLo;
  const sharesStep = sharesSpan > 2500 ? 500 : sharesSpan > 1000 ? 200 :
                     sharesSpan > 400 ? 100 : sharesSpan > 200 ? 50 : 25;
  const sharesTickVals = [];
  for (let v = Math.ceil(sharesLo / sharesStep) * sharesStep;
       v < sharesHi; v += sharesStep) sharesTickVals.push(v);
  const sharesTickLabel = (v) => v >= 1000 ? `${(v / 1000).toFixed(1)}K` : `${v.toFixed(0)}M`;

  const xTicks = fyLabels.map((l, i) => [i, l]);

  return (
    <svg width={`${widthPt}pt`} height={`${heightPt}pt`}
         viewBox={`0 0 ${widthPt} ${heightPt}`}
         style={{ display: 'block' }}>
      <ChartTitle>Cash + dilution (FY26 → FY36)</ChartTitle>

      {/* LEFT axis: cash gridlines + labels */}
      {cashTicks.map(([v, lbl]) => (
        <g key={`l-${v}`}>
          <line x1={plotL} x2={plotR} y1={yScaleCash(v)} y2={yScaleCash(v)}
                stroke={PALETTE.rule} strokeWidth="0.3" />
          <text x={plotL - 3} y={yScaleCash(v) + 2}
                fontFamily={FONT_MONO} fontSize="5.5pt" fill={PALETTE.accent}
                textAnchor="end">
            {lbl}
          </text>
        </g>
      ))}

      {/* RIGHT axis: shares labels (no gridlines — keep them quiet) */}
      {sharesTickVals.map(v => (
        <text key={`r-${v}`} x={plotR + 3} y={yScaleShares(v) + 2}
              fontFamily={FONT_MONO} fontSize="5.5pt" fill={PALETTE.muted}
              textAnchor="start">
          {sharesTickLabel(v)}
        </text>
      ))}

      <XTicks ticks={xTicks} xScale={xScale} plotB={plotB} />

      {/* "Today" divider at start of projection (between FY26 and FY27) */}
      <line x1={xScale(0.5)} x2={xScale(0.5)} y1={plotT} y2={plotB}
            stroke={PALETTE.dim} strokeWidth="0.4" strokeDasharray="1,2" />

      {/* Cash paths — dashed, scenario-colored */}
      {scnKeys.map(key => {
        const pts = cashByScn[key].map((v, i) => [i, Math.max(v, 0)]);
        return (
          <g key={`c-${key}`}>
            <path d={pathD(pts, xScale, yScaleCash)}
                  stroke={SCN_COLORS[key]} strokeWidth="1.2" fill="none"
                  strokeDasharray="3,2" />
            {pts.map(([t, v], i) => (
              <circle key={`cp-${key}-${i}`} cx={xScale(t)} cy={yScaleCash(v)}
                      r="1.4" fill={SCN_COLORS[key]} stroke="white"
                      strokeWidth="0.4" />
            ))}
          </g>
        );
      })}

      {/* Shares paths — dotted, lighter opacity to keep cash dominant */}
      {scnKeys.map(key => {
        const pts = sharesByScn[key].map((v, i) => [i, v]);
        return (
          <g key={`s-${key}`} opacity="0.75">
            <path d={pathD(pts, xScale, yScaleShares)}
                  stroke={SCN_COLORS[key]} strokeWidth="0.7" fill="none"
                  strokeDasharray="1,2" />
            {pts.map(([t, v], i) => (
              <rect key={`sp-${key}-${i}`} x={xScale(t) - 0.9}
                    y={yScaleShares(v) - 0.9} width="1.8" height="1.8"
                    fill={SCN_COLORS[key]} stroke="white" strokeWidth="0.3" />
            ))}
          </g>
        );
      })}

      {/* Axis-direction hints — just below the title band so they don't
          collide with the title text on either side. */}
      <text x={plotL} y={plotT - 2}
            fontFamily={FONT_SANS} fontSize="5pt" fill={PALETTE.accent}>
        Cash + investments ↓
      </text>
      <text x={plotR} y={plotT - 2}
            fontFamily={FONT_SANS} fontSize="5pt" fill={PALETTE.muted}
            textAnchor="end">
        ↓ Shares (M, dotted)
      </text>
    </svg>
  );
}

// Mature-company aesthetic config (segments, chart6 dispatch) is read
// from memo.page3.chartConfig (YAML page3_chart_config).

const projectMatureRev = (revB, growthPath) => {
  let r = revB;
  return growthPath.map(g => (r *= 1 + g));
};

function MatureRevenueChart({ memo, widthPt = 280, heightPt = 190 }) {
  const ref = memo.page3.chartReference;
  const histYears = ref.historyYears;
  const histRev = ref.historyRevenue;
  const nHist = histYears.length;
  const scnKeys = scnKeysFor(memo);
  const revB = memo.print.scenarios.base.dcfPath.rev_b;
  const projByScn = Object.fromEntries(scnKeys.map(k =>
    [k, projectMatureRev(revB, memo.print.scenarios[k].dcfPath.rev_path)]));

  const totalX = nHist + 5;
  const fyAll = [
    ...histYears.map(y => `${y - 2000}`),
    ...Array.from({ length: 5 }, (_, i) => `${26 + i}`),
  ];
  const m = CHART_MARGIN;
  const plotR = widthPt - m.right;
  const plotT = m.top, plotB = heightPt - m.bottom;
  const allVals = [...histRev, ...Object.values(projByScn).flat()];
  // Domain top snaps to a round tick so the last gridline lands ON the axis top —
  // the old `v <= yMax + step*0.5` loop could draw a tick above the domain, whose
  // unclamped extrapolation put a gridline + label through the chart title.
  const rawMax = Math.max(...allVals) * 1.1;
  const yStep = niceStep(rawMax);
  const yMax = Math.ceil(rawMax / yStep) * yStep;
  const yScale = mkLinearScale([0, yMax], [plotB, plotT]);
  const yTicks = [];
  for (let i = 0; i * yStep <= yMax; i++) {
    const v = i * yStep;
    yTicks.push([v, `$${v.toFixed(yStep < 1 ? 1 : 0)}B`]);
  }
  // Left margin sized to the widest y-label so $100B–$1T labels never clip (spec §3.5).
  const plotL = Math.max(m.left,
    Math.ceil(Math.max(...yTicks.map(([, l]) => monoTextWidth(l, 5.5)))) + 5);
  const xScale = mkLinearScale([-0.5, totalX + 0.5], [plotL, plotR]);
  const shortLabel = (k) => memo.print.scenarios[k].shortLabel;

  return (
    <svg width={`${widthPt}pt`} height={`${heightPt}pt`}
         viewBox={`0 0 ${widthPt} ${heightPt}`}
         style={{ display: 'block' }}>
      <ChartTitle>Revenue ($B) — history + scenarios to FY30</ChartTitle>
      <YGridTicks ticks={yTicks} yScale={yScale} plotL={plotL} plotR={plotR} />
      {fyAll.map((fy, i) => (
        <text key={`xt-${i}`} x={xScale(i)} y={plotB + 8}
              fontFamily={FONT_MONO} fontSize="5pt" fill={PALETTE.muted}
              textAnchor="middle">{fy}</text>
      ))}
      <line x1={xScale(nHist - 0.5)} x2={xScale(nHist - 0.5)} y1={plotT} y2={plotB}
            stroke={PALETTE.dim} strokeWidth="0.4" strokeDasharray="1,2" />
      {histRev.map((v, i) => {
        const x = xScale(i);
        const y0 = yScale(0), yv = yScale(v);
        const barW = (plotR - plotL) / totalX * 0.55;
        const isLatest = i === nHist - 1;
        return (
          <g key={`hb-${i}`}>
            <rect x={x - barW / 2} y={yv} width={barW} height={y0 - yv}
                  fill={isLatest ? PALETTE.accent : '#94a3b8'} />
            <text x={x} y={yv - 2}
                  fontFamily={FONT_MONO} fontSize="5.5pt" fill={PALETTE.text}
                  textAnchor="middle">{v.toFixed(1)}</text>
          </g>
        );
      })}
      {scnKeys.map(k => {
        const pts = [[nHist - 1, histRev[nHist - 1]],
                     ...projByScn[k].map((v, i) => [nHist + i, v])];
        const endV = projByScn[k].at(-1);
        return (
          <g key={`p-${k}`}>
            <path d={pathD(pts, xScale, yScale)}
                  stroke={SCN_COLORS[k]} strokeWidth="1.2" fill="none"
                  strokeDasharray="3,2" />
            {pts.map(([t, v], i) => (
              <circle key={`pp-${k}-${i}`} cx={xScale(t)} cy={yScale(v)} r="1.4"
                      fill={SCN_COLORS[k]} stroke="white" strokeWidth="0.4" />
            ))}
            <text x={xScale(nHist + 4) + 3} y={yScale(endV) + 2}
                  fontFamily={FONT_SANS} fontWeight={500} fontSize="5.5pt"
                  fill={SCN_COLORS[k]}>
              {shortLabel(k)} {endV.toFixed(1)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function MatureSegmentsChart({ memo, widthPt = 280, heightPt = 190 }) {
  const cfg = memo.page3.chartConfig || {};
  const ref = memo.page3.chartReference;
  const histYears = ref.historyYears;
  const nHist = histYears.length;
  let segA, segB;
  if (ref.historyEntRevenueM) {
    // LTH variant — segments tracked in $M directly.
    segA = ref.historyEntRevenueM;
    segB = ref.historyOnlRevenueM || [];
  } else if (cfg.histEntSplit) {
    // ZM variant — derive Enterprise from total × split coefficient.
    const rev = ref.historyRevenue;
    segA = rev.map((r, i) => r * (cfg.histEntSplit[i] || 0.6) * 1000);
    segB = rev.map((r, i) => (r * 1000) - segA[i]);
  } else {
    segA = []; segB = [];
  }

  const m = CHART_MARGIN;
  const plotR = widthPt - m.right;
  const plotT = m.top, plotB = heightPt - m.bottom;
  // Magnitude-aware axis: display $B once a segment reaches $1B (1,000 $M), else $M;
  // niceStep keeps the tick count ~6 at any scale. (The old fixed step capped at 1,000
  // and exploded into ~130 gridlines at mega-cap $100B+ segment revenue — spec §3.5.)
  // Domain top snaps to a round tick so no gridline extrapolates into the title band.
  const rawMax = Math.max(...segA, ...segB) * 1.15;
  const yStep = niceStep(rawMax);
  const yMax = Math.ceil(rawMax / yStep) * yStep;
  const yScale = mkLinearScale([0, yMax], [plotB, plotT]);
  const useB = yMax >= 1000;
  const unit = useB ? 'B' : 'M';
  const div = useB ? 1000 : 1;
  const yTicks = [];
  for (let i = 0; i * yStep <= yMax; i++) {
    const v = i * yStep;
    yTicks.push([v, `$${(v / div).toFixed(yStep / div < 1 ? 1 : 0)}${unit}`]);
  }
  // Left margin sized to the widest y-label so labels never clip (spec §3.5).
  const plotL = Math.max(m.left,
    Math.ceil(Math.max(...yTicks.map(([, l]) => monoTextWidth(l, 5.5)))) + 5);
  const xScale = mkLinearScale([-0.5, nHist - 0.5], [plotL, plotR]);
  const xTicks = histYears.map((y, i) => [i, `${y - 2000}`]);

  return (
    <svg width={`${widthPt}pt`} height={`${heightPt}pt`}
         viewBox={`0 0 ${widthPt} ${heightPt}`}
         style={{ display: 'block' }}>
      <ChartTitle>{`Revenue by segment ($${unit})`}</ChartTitle>
      <YGridTicks ticks={yTicks} yScale={yScale} plotL={plotL} plotR={plotR} />
      <XTicks ticks={xTicks} xScale={xScale} plotB={plotB} />
      <path d={pathD(segA.map((v, i) => [i, v]), xScale, yScale)}
            stroke={PALETTE.accent} strokeWidth="1.6" fill="none" />
      {segA.map((v, i) => (
        <circle key={`a-${i}`} cx={xScale(i)} cy={yScale(v)} r="2"
                fill={PALETTE.accent} stroke="white" strokeWidth="0.5" />
      ))}
      <path d={pathD(segB.map((v, i) => [i, v]), xScale, yScale)}
            stroke={PALETTE.muted} strokeWidth="1.2" fill="none" />
      {segB.map((v, i) => (
        <circle key={`b-${i}`} cx={xScale(i)} cy={yScale(v)} r="1.6"
                fill={PALETTE.muted} stroke="white" strokeWidth="0.4" />
      ))}
      <text x={xScale(0) + 4} y={yScale(segA[0]) - 4}
            fontFamily={FONT_SANS} fontWeight={500} fontSize="6pt"
            fill={PALETTE.accent}>{cfg.segmentA || 'Primary'}</text>
      <text x={xScale(0) + 4} y={yScale(segB[0]) - 4}
            fontFamily={FONT_SANS} fontSize="6pt" fill={PALETTE.muted}>
        {cfg.segmentB || 'Secondary'}
      </text>
    </svg>
  );
}

function MatureMarginsChart({ memo, widthPt = 280, heightPt = 190 }) {
  const ref = memo.page3.chartReference;
  const histYears = ref.historyYears;
  const nHist = histYears.length;
  const scnKeys = scnKeysFor(memo);
  const histOp = (ref.historyOpMargin || []).map(v => v);

  // Defensive: with no historyOpMargin the scenario fan would anchor at 0% and
  // the whole pre-projection history would read as a flat zero. Surface the gap
  // explicitly instead (mirrors MatureEvMultiplesChart). The validator now makes
  // this field a hard requirement for mature/SOTP, so this is belt-and-suspenders.
  if (histOp.length === 0) {
    return (
      <svg width={`${widthPt}pt`} height={`${heightPt}pt`}
           viewBox={`0 0 ${widthPt} ${heightPt}`}
           style={{ display: 'block' }}>
        <ChartTitle>Op margin — history + scenarios</ChartTitle>
        <text x={widthPt / 2} y={heightPt / 2}
              fontFamily={FONT_MONO} fontSize="7pt" fill={PALETTE.muted}
              textAnchor="middle">(no op-margin history)</text>
      </svg>
    );
  }

  const m = CHART_MARGIN;
  const plotL = m.left, plotR = widthPt - m.right;
  const plotT = m.top, plotB = heightPt - m.bottom;
  const totalX = nHist + 5;
  const xScale = mkLinearScale([-0.5, totalX + 0.5], [plotL, plotR]);
  const allMargins = [
    ...histOp,
    ...scnKeys.flatMap(k => memo.print.scenarios[k].dcfPath.op_margin.map(d => d * 100)),
  ];
  const yMin = Math.min(0, Math.floor(Math.min(...allMargins) / 10) * 10);
  const yMax = Math.ceil(Math.max(...allMargins) / 10) * 10 + 5;
  const yScale = mkLinearScale([yMin, yMax], [plotB, plotT]);
  const yTicks = [];
  for (let v = yMin; v <= yMax; v += 10) yTicks.push([v, `${v}%`]);
  const fyAll = [
    ...histYears.map(y => `${y - 2000}`),
    ...Array.from({ length: 5 }, (_, i) => `${26 + i}`),
  ];
  const xTicks = fyAll.map((fy, i) => [i, fy]);
  const shortLabel = (k) => memo.print.scenarios[k].shortLabel;

  return (
    <svg width={`${widthPt}pt`} height={`${heightPt}pt`}
         viewBox={`0 0 ${widthPt} ${heightPt}`}
         style={{ display: 'block' }}>
      <ChartTitle>Op margin — history + scenarios</ChartTitle>
      <YGridTicks ticks={yTicks} yScale={yScale} plotL={plotL} plotR={plotR} />
      <XTicks ticks={xTicks} xScale={xScale} plotB={plotB} />
      <line x1={plotL} x2={plotR} y1={yScale(0)} y2={yScale(0)}
            stroke={PALETTE.dim} strokeWidth="0.4" opacity="0.6" />
      <line x1={xScale(nHist - 0.5)} x2={xScale(nHist - 0.5)} y1={plotT} y2={plotB}
            stroke={PALETTE.dim} strokeWidth="0.4" strokeDasharray="1,2" />
      {histOp.length > 0 && (
        <>
          <path d={pathD(histOp.map((v, i) => [i, v]), xScale, yScale)}
                stroke={PALETTE.accent} strokeWidth="1.6" fill="none" />
          {histOp.map((v, i) => (
            <circle key={`h-${i}`} cx={xScale(i)} cy={yScale(v)} r="2"
                    fill={PALETTE.accent} stroke="white" strokeWidth="0.5" />
          ))}
        </>
      )}
      {/* Endpoint labels collide when the fan is compressed — a one-time
          impairment year (ILMN −91%, COIN −85%) drives the data-derived axis
          floor far down, squeezing the scenarios into a thin band. Spread any
          overlapping labels vertically; the dashed lines stay at true value.
          Only triggers on genuine overlap, so well-spaced tickers are unchanged. */}
      {(() => {
        const LBL_GAP = 7.2;  // pt — ~1.3× the 5.5pt label cap height
        const lab = scnKeys.map(k => ({
          k, y: yScale(memo.print.scenarios[k].dcfPath.op_margin.at(-1) * 100) + 2,
        })).sort((a, b) => a.y - b.y);
        for (let i = 1; i < lab.length; i++)
          if (lab[i].y - lab[i - 1].y < LBL_GAP) lab[i].y = lab[i - 1].y + LBL_GAP;
        const overflow = lab.length ? lab[lab.length - 1].y - plotB : 0;
        if (overflow > 0) lab.forEach(o => (o.y -= overflow));
        const labelY = Object.fromEntries(lab.map(o => [o.k, o.y]));
        return scnKeys.map(k => {
          const margins = memo.print.scenarios[k].dcfPath.op_margin.map(d => d * 100);
          const pts = [[nHist - 1, histOp.at(-1) || 0],
                       ...margins.map((v, i) => [nHist + i, v])];
          const endV = margins.at(-1);
          return (
            <g key={`m-${k}`}>
              <path d={pathD(pts, xScale, yScale)}
                    stroke={SCN_COLORS[k]} strokeWidth="1.2" fill="none"
                    strokeDasharray="3,2" />
              <text x={xScale(nHist + 4) + 3} y={labelY[k]}
                    fontFamily={FONT_SANS} fontWeight={500} fontSize="5.5pt"
                    fill={SCN_COLORS[k]}>
                {shortLabel(k)} {endV.toFixed(0)}%
              </text>
            </g>
          );
        });
      })()}
    </svg>
  );
}

function MatureBalanceChart({ memo, widthPt = 280, heightPt = 190 }) {
  const ref = memo.page3.chartReference;
  const histYears = ref.historyYears;
  const nHist = histYears.length;
  const histND = ref.historyNetDebt;
  const isDebtChart = !!histND;

  const m = CHART_MARGIN;
  const plotR = widthPt - m.right;
  const plotT = m.top, plotB = heightPt - m.bottom;

  let vals, title;
  if (isDebtChart) {
    vals = histND; title = 'Net financial debt ($B) — history';
  } else if (ref.historyFcf) {
    vals = ref.historyFcf; title = 'Free cash flow ($B) — history';
  } else {
    vals = [memo.print.market.cashBillion]; title = 'Net cash ($B)';
  }
  // Domain always spans 0 with headroom on the SPAN (a bare max×1.2 flips sign on
  // all-negative FCF history — TEM/TWST/NVCR — pushing yScale(0) off-canvas), and
  // both ends snap to tick multiples so ticks are round and stay inside the plot.
  const hi = Math.max(0, ...vals);
  const lo = Math.min(0, ...vals);
  const span = (hi - lo) || 1;
  const yStep = niceStep(span);
  const yMax = Math.ceil((hi + 0.15 * span) / yStep) * yStep;
  const yMin = Math.floor(lo / yStep) * yStep;
  const yScale = mkLinearScale([yMin, yMax], [plotB, plotT]);
  const yTicks = [];
  for (let i = 0; i <= Math.round((yMax - yMin) / yStep); i++) {
    const v = yMin + i * yStep;
    yTicks.push([v, `$${v.toFixed(yStep < 1 ? 1 : 0)}B`]);
  }
  const plotL = Math.max(m.left,
    Math.ceil(Math.max(...yTicks.map(([, l]) => monoTextWidth(l, 5.5)))) + 5);
  const xScale = mkLinearScale([-0.5, nHist - 0.5], [plotL, plotR]);
  const xTicks = histYears.map((y, i) => [i, `${y - 2000}`]);

  return (
    <svg width={`${widthPt}pt`} height={`${heightPt}pt`}
         viewBox={`0 0 ${widthPt} ${heightPt}`}
         style={{ display: 'block' }}>
      <ChartTitle>{title}</ChartTitle>
      <YGridTicks ticks={yTicks} yScale={yScale} plotL={plotL} plotR={plotR} />
      <XTicks ticks={xTicks} xScale={xScale} plotB={plotB} />
      {vals.map((v, i) => {
        const x = xScale(i);
        const y0 = yScale(0), yv = yScale(v);
        const barW = (plotR - plotL) / nHist * 0.55;
        return (
          <g key={`b-${i}`}>
            <rect x={x - barW / 2} y={Math.min(y0, yv)} width={barW}
                  height={Math.abs(y0 - yv)} fill={PALETTE.accent} />
            <text x={x} y={Math.min(y0, yv) - 2}
                  fontFamily={FONT_MONO} fontSize="5.5pt" fill={PALETTE.text}
                  textAnchor="middle">{v.toFixed(1)}</text>
          </g>
        );
      })}
    </svg>
  );
}

function MatureEvMultiplesChart({ memo, widthPt = 280, heightPt = 190 }) {
  const ref = memo.page3.chartReference;
  const histYears = ref.historyYears;
  const nHist = histYears.length;
  const evRev = (ref.historyEvRev || []).map(v => v == null ? null : v);
  const haveData = evRev.some(v => v != null);

  const m = CHART_MARGIN;
  const plotL = m.left, plotR = widthPt - m.right;
  const plotT = m.top, plotB = heightPt - m.bottom;
  const xScale = mkLinearScale([-0.5, nHist - 0.5], [plotL, plotR]);

  if (!haveData) {
    return (
      <svg width={`${widthPt}pt`} height={`${heightPt}pt`}
           viewBox={`0 0 ${widthPt} ${heightPt}`}
           style={{ display: 'block' }}>
        <ChartTitle>EV / Revenue — historical</ChartTitle>
        <text x={widthPt / 2} y={heightPt / 2}
              fontFamily={FONT_MONO} fontSize="7pt" fill={PALETTE.muted}
              textAnchor="middle">(no EV history data)</text>
      </svg>
    );
  }
  const validVals = evRev.filter(v => v != null);
  // niceStep, matching the Revenue/FCF/segment charts — the old fixed `yMax>8 ? 2 : 1`
  // ladder drew ~25 near-touching labels on high-multiple names like SHOP (spec §3.5).
  const rawMax = Math.max(...validVals) * 1.2;
  const yStep = niceStep(rawMax);
  const yMax = Math.ceil(rawMax / yStep) * yStep;
  const yScale = mkLinearScale([0, yMax], [plotB, plotT]);
  const yTicks = [];
  for (let i = 0; i * yStep <= yMax; i++) {
    const v = i * yStep;
    yTicks.push([v, `${v.toFixed(yStep < 1 ? 1 : 0)}×`]);
  }
  const xTicks = histYears.map((y, i) => [i, `${y - 2000}`]);
  const linePts = evRev.map((v, i) => [i, v]).filter(([, v]) => v != null);

  return (
    <svg width={`${widthPt}pt`} height={`${heightPt}pt`}
         viewBox={`0 0 ${widthPt} ${heightPt}`}
         style={{ display: 'block' }}>
      <ChartTitle>EV / Revenue — historical</ChartTitle>
      <YGridTicks ticks={yTicks} yScale={yScale} plotL={plotL} plotR={plotR} />
      <XTicks ticks={xTicks} xScale={xScale} plotB={plotB} />
      <path d={pathD(linePts, xScale, yScale)}
            stroke={PALETTE.accent} strokeWidth="1.6" fill="none" />
      {linePts.map(([t, v]) => (
        <g key={`ev-${t}`}>
          <circle cx={xScale(t)} cy={yScale(v)} r="2"
                  fill={PALETTE.accent} stroke="white" strokeWidth="0.5" />
          <text x={xScale(t)} y={yScale(v) - 4}
                fontFamily={FONT_MONO} fontSize="5.5pt" fill={PALETTE.text}
                textAnchor="middle">{v.toFixed(1)}×</text>
        </g>
      ))}
    </svg>
  );
}

function MatureTerminalChart({ memo, widthPt = 280, heightPt = 190 }) {
  const cfg = memo.page3.chartConfig || {};
  const m = { left: 30, right: 24, top: 16, bottom: 16 };
  const plotL = m.left, plotR = widthPt - m.right;
  const plotT = m.top, plotB = heightPt - m.bottom;

  // ISRG installed-base chart: historical da Vinci systems (FY21-25) + a
  // per-scenario projection to FY30 (each scenario's dcfMetrics
  // .installed_base_fy30). Surfaces the razor-blade engine — the installed
  // base is the denominator that drives recurring revenue.
  if (cfg.chart6Type === 'isrgInstalledBase') {
    const ref = memo.page3.chartReference;
    const yrs = ref.historyYears || [];
    const hist = ref.historyInstalledBase || [];
    const scnKeys = scnKeysFor(memo);
    const totalX = yrs.length + 4;   // history + 5 projected years (FY26-30)
    const xScale = mkLinearScale([-0.5, totalX + 0.5], [plotL, plotR]);
    const fy30 = scnKeys.map(k => memo.print.scenarios[k].dcfMetrics.installed_base_fy30 || 0);
    const yMax = Math.max(...hist, ...fy30) * 1.1;
    const yScale = mkLinearScale([0, yMax], [plotB, plotT]);
    const yTicks = [0, 5000, 10000, 15000, 20000, 25000]
      .filter(v => v <= yMax).map(v => [v, `${(v / 1000).toFixed(0)}K`]);
    const allLabels = [...yrs.map(y => String(y).slice(2)), '26', '27', '28', '29', '30'];
    const xTicks = allLabels.map((l, i) => [i, l]);
    const lastHistX = yrs.length - 1;
    const lastHistY = hist[hist.length - 1];

    return (
      <svg width={`${widthPt}pt`} height={`${heightPt}pt`}
           viewBox={`0 0 ${widthPt} ${heightPt}`}
           style={{ display: 'block' }}>
        <ChartTitle>{cfg.chart6Title}</ChartTitle>
        <YGridTicks ticks={yTicks} yScale={yScale} plotL={plotL} plotR={plotR} />
        <XTicks ticks={xTicks} xScale={xScale} plotB={plotB} />
        {/* Historical installed base (solid ink) */}
        <path d={pathD(hist.map((v, i) => [i, v]), xScale, yScale)}
              stroke={PALETTE.ink} strokeWidth="1.6" fill="none" />
        {/* Per-scenario projection from last history point to FY30 */}
        {scnKeys.map((k, i) => (
          <path key={`ib-${k}`}
                d={pathD([[lastHistX, lastHistY], [totalX, fy30[i]]], xScale, yScale)}
                stroke={SCN_COLORS[k]} strokeWidth="1.0" fill="none"
                strokeDasharray="3,2" />
        ))}
        {/* End-of-line scenario labels at FY30 */}
        {scnKeys.map((k, i) => (
          <text key={`ibl-${k}`}
                x={xScale(totalX) + 2} y={yScale(fy30[i]) + 2}
                fontFamily={FONT_MONO} fontSize="5pt" fill={SCN_COLORS[k]}>
            {(fy30[i] / 1000).toFixed(1)}K
          </text>
        ))}
        <text x={plotL + 4} y={yScale(hist[0]) - 4}
              fontFamily={FONT_SANS} fontSize="6pt" fill={PALETTE.muted}>
          da Vinci systems
        </text>
        {cfg.chart6Footer && (
          <text x={plotL} y={heightPt - 4}
                fontFamily={FONT_SANS} fontSize="5.5pt" fill={PALETTE.muted}>
            {cfg.chart6Footer}
          </text>
        )}
      </svg>
    );
  }

  if (cfg.chart6Type === 'lthClubs') {
    const ref = memo.page3.chartReference;
    const yrs = ref.clubHistoryYears || [];
    const luxury = ref.clubHistoryLuxury || [];
    const standard = ref.clubHistoryStandard || [];
    const totalX = yrs.length + 5;
    const xScale = mkLinearScale([-0.5, totalX - 0.5], [plotL, plotR]);
    const yMax = Math.max(...standard, ...luxury) * 1.2 + 60;
    const yScale = mkLinearScale([0, yMax], [plotB, plotT]);
    const yTicks = [0, 50, 100, 150, 200].filter(v => v <= yMax).map(v => [v, `${v}`]);
    const allLabels = [...yrs.map(y => y.slice(2)), '26', '27', '28', '29', '30'];
    const xTicks = allLabels.map((l, i) => [i, l]);
    // Per-scenario FY30 luxury-club endpoints come from each scenario's
    // chart_data.luxury_club_count_fy30 in the yml (compute-from-data, spec §3.5 —
    // the old hardcoded dict had drifted from the authored values AND lacked
    // ultra_bear, whose NaN path silently dropped the fifth fan line).
    const luxFY30 = Object.fromEntries(scnKeysFor(memo).map(k =>
      [k, memo.print.scenarios[k].chartData?.luxury_club_count_fy30]));
    const stdFY30 = ref.clubStandardProjFy30 || standard.at(-1);

    return (
      <svg width={`${widthPt}pt`} height={`${heightPt}pt`}
           viewBox={`0 0 ${widthPt} ${heightPt}`}
           style={{ display: 'block' }}>
        <ChartTitle>{cfg.chart6Title}</ChartTitle>
        <YGridTicks ticks={yTicks} yScale={yScale} plotL={plotL} plotR={plotR} />
        <XTicks ticks={xTicks} xScale={xScale} plotB={plotB} />
        <path d={pathD([...standard.map((v, i) => [i, v]),
                       [yrs.length + 4, stdFY30]], xScale, yScale)}
              stroke={PALETTE.muted} strokeWidth="1.4" fill="none" />
        <path d={pathD(luxury.map((v, i) => [i, v]), xScale, yScale)}
              stroke={PALETTE.accent} strokeWidth="1.6" fill="none" />
        {scnKeysFor(memo).filter(k => luxFY30[k] != null).map(k => (
          <path key={`lx-${k}`}
                d={pathD([[yrs.length - 1, luxury.at(-1)],
                          [yrs.length + 4, luxFY30[k]]], xScale, yScale)}
                stroke={SCN_COLORS[k]} strokeWidth="1.0" fill="none"
                strokeDasharray="3,2" />
        ))}
        <text x={plotL + 4} y={yScale(standard[0]) - 4}
              fontFamily={FONT_SANS} fontSize="6pt" fill={PALETTE.muted}>
          Standard
        </text>
        <text x={plotL + 4} y={yScale(luxury[0]) - 4}
              fontFamily={FONT_SANS} fontWeight={500} fontSize="6pt"
              fill={PALETTE.accent}>
          Luxury
        </text>
      </svg>
    );
  }

  // ZM SOTP equity decomposition
  const scnKeys = scnKeysFor(memo);
  const rows = scnKeys.map(k => {
    const s = memo.print.scenarios[k];
    const opEv = Math.max(0, s.dcfPath.op_ev);
    const netCash = (s.dcfPath.cash || 0) - (s.dcfPath.net_debt || 0);   // signed: +cash / −debt
    const anth = s.dcfPath.special_assets || 0;
    return { key: k, label: s.shortLabel, opEv, netCash, anth,
             equity: Math.max(0, opEv + netCash + anth) };
  });
  // Bar extent = the rightmost of (Op EV, equity): net-cash rows end at equity;
  // net-debt rows build to Op EV, then a red bar cuts back to the equity point.
  const maxTotal = Math.max(...rows.map(r => Math.max(r.opEv, r.equity))) * 1.05;
  // Left margin sized to the widest right-anchored scenario label so "UltBear"/
  // "UltBull" never clip the SVG left edge (spec §3.5: bounds compute from data).
  const eqL = Math.max(plotL, Math.ceil(Math.max(...rows.map(r => estSvgTextWidth(r.label, 6.5)))) + 6);
  const xScale = mkLinearScale([0, maxTotal], [eqL, plotR]);
  const rowH = (plotB - plotT) / rows.length;
  const barH = rowH * 0.5;
  const rowY = (i) => plotT + (i + 0.5) * rowH;

  return (
    <svg width={`${widthPt}pt`} height={`${heightPt}pt`}
         viewBox={`0 0 ${widthPt} ${heightPt}`}
         style={{ display: 'block' }}>
      <ChartTitle>{cfg.chart6Title}</ChartTitle>
      {rows.map((r, i) => {
        const y = rowY(i);
        const yTop = y - barH / 2;
        const opX = xScale(r.opEv);
        // Segments: net-cash rows = Op EV (color) + net cash (gray) + special
        // assets (light); net-debt rows = equity (color) + a red −net-debt bar.
        const segs = [];
        if (r.netCash >= 0) {
          const cashX = xScale(r.opEv + r.netCash);
          const anthX = xScale(r.opEv + r.netCash + r.anth);
          segs.push({ x: eqL, w: opX - eqL, fill: SCN_COLORS[r.key] });
          segs.push({ x: opX, w: cashX - opX, fill: '#94a3b8' });
          segs.push({ x: cashX, w: anthX - cashX, fill: '#9ca3af', op: 0.6 });
        } else {
          const eqX = xScale(r.equity);
          segs.push({ x: eqL, w: eqX - eqL, fill: SCN_COLORS[r.key] });
          segs.push({ x: eqX, w: opX - eqX, fill: '#dc2626', op: 0.5 });
        }
        return (
          <g key={r.key}>
            <text x={eqL - 4} y={y + 2}
                  fontFamily={FONT_SANS} fontWeight={500} fontSize="6.5pt"
                  fill={SCN_COLORS[r.key]} textAnchor="end">
              {r.label}
            </text>
            {segs.map((s, j) => (
              <rect key={j} x={s.x} y={yTop} width={Math.max(0, s.w)} height={barH}
                    fill={s.fill} opacity={s.op} />
            ))}
            <text x={xScale(Math.max(r.opEv, r.equity)) + 3} y={y + 2}
                  fontFamily={FONT_MONO} fontSize="6pt" fill={PALETTE.text}>
              ${r.equity.toFixed(0)}B
            </text>
          </g>
        );
      })}
      <text x={eqL} y={heightPt - 4}
            fontFamily={FONT_SANS} fontSize="5.5pt" fill={PALETTE.muted}>
        {cfg.chart6Footer || 'Op EV  ·  cash  ·  special assets'}
      </text>
    </svg>
  );
}

// --- Young-company Chart 2: path to profitability (op margin) ---
// 10 projected years FY27-FY36, op margin %, linear Y -100% to +50% with
// a zero line + a horizontal peer-median reference. Peer text + y level
// from memo.page3.chartConfig (YAML page3_chart_config).
function YoungProfitabilityChart({ memo, widthPt = 280, heightPt = 190 }) {
  const scnKeys = scnKeysFor(memo);
  const cfg = memo.page3.chartConfig || {};
  const peer = {
    peerY: cfg.peerY ?? 20,
    peerText: cfg.peerText || 'Peer median',
  };
  const fyProj = Array.from({ length: 10 }, (_, i) => `FY${27 + i}`);

  const m = CHART_MARGIN;
  const plotL = m.left, plotR = widthPt - m.right;
  const plotT = m.top, plotB = heightPt - m.bottom;

  const xScale = mkLinearScale([-0.4, 10.8], [plotL, plotR]);
  // Y: -110% to +50% linear, matching memo.py. Plot in % units (not decimals).
  const yScale = mkLinearScale([-110, 50], [plotB, plotT]);

  const yTickVals = [-100, -80, -60, -40, -20, 0, 20, 40];
  const yTicks = yTickVals.map(v => [v, `${v}%`]);
  const xTicks = fyProj.map((fy, i) => [i, fy.slice(2)]);

  // Margins clamped to ≥ -100% (matches memo.py max(m*100, -100)).
  const marginPts = (key) =>
    memo.print.scenarios[key].dcfPath.op_margin.map((m, i) =>
      [i, Math.max(m * 100, -100)]);
  const endMargin = (key) => {
    const arr = memo.print.scenarios[key].dcfPath.op_margin;
    return arr[arr.length - 1] * 100;
  };
  const shortLabel = (key) => memo.print.scenarios[key].shortLabel;

  // Peer text label position: JOBY (peerY=15) drew text near the bottom in
  // legacy; others near the line itself. Mirror that here.
  const peerLabelY = peer.peerY === 15 ? -95 : peer.peerY + 4;

  return (
    <svg width={`${widthPt}pt`} height={`${heightPt}pt`}
         viewBox={`0 0 ${widthPt} ${heightPt}`}
         style={{ display: 'block' }}>
      <ChartTitle>Path to profitability — op margin (FY27→FY36)</ChartTitle>
      <YGridTicks ticks={yTicks} yScale={yScale} plotL={plotL} plotR={plotR} />
      <XTicks ticks={xTicks} xScale={xScale} plotB={plotB} />

      {/* Zero line — slightly more prominent than gridlines */}
      <line x1={plotL} x2={plotR} y1={yScale(0)} y2={yScale(0)}
            stroke={PALETTE.dim} strokeWidth="0.5" opacity="0.6" />

      {/* Peer median reference (dotted) */}
      <line x1={plotL} x2={plotR} y1={yScale(peer.peerY)} y2={yScale(peer.peerY)}
            stroke="#94a3b8" strokeWidth="0.4" strokeDasharray="1,2" />
      <text x={plotL + 4} y={yScale(peerLabelY) + 2}
            fontFamily={FONT_SANS} fontSize="5.5pt" fill={PALETTE.muted}>
        {peer.peerText}
      </text>

      {/* Scenario lines (solid, with markers) */}
      {scnKeys.map(key => (
        <g key={`m-${key}`}>
          <path d={pathD(marginPts(key), xScale, yScale)}
                stroke={SCN_COLORS[key]} strokeWidth="1.3" fill="none" />
          {marginPts(key).map(([t, v], i) => (
            <circle key={`pt-${key}-${i}`} cx={xScale(t)} cy={yScale(v)} r="1.6"
                    fill={SCN_COLORS[key]} stroke="white" strokeWidth="0.4" />
          ))}
        </g>
      ))}

      {/* End-of-line labels (final margin %) */}
      {scnKeys.map(key => {
        const v = endMargin(key);
        return (
          <text key={`e-${key}`}
                x={xScale(9) + 4} y={yScale(v) + 2}
                fontFamily={FONT_SANS} fontWeight={500} fontSize="5.5pt"
                fill={SCN_COLORS[key]}>
            {shortLabel(key)} {v.toFixed(0)}%
          </text>
        );
      })}
    </svg>
  );
}

// Private Page 3: ARR build (history) + exit-valuation distribution (one bar
// per scenario, height = exit post-money, labelled with probability). Far less
// chart surface than the public 6-grid, and honest about what data exists.
function PrivateArrChart({ memo, widthPt = 415, heightPt = 188 }) {
  const ref = memo.page3.chartReference;
  const yrs = ref.historyYears || [];
  const arr = ref.historyArrBillion || [];
  const m = { left: 38, right: 20, top: 20, bottom: 22 };
  const plotL = m.left, plotR = widthPt - m.right, plotT = m.top, plotB = heightPt - m.bottom;
  const yMax = Math.max(...arr) * 1.2 || 1;
  const xScale = mkLinearScale([-0.5, yrs.length - 0.5], [plotL, plotR]);
  const yScale = mkLinearScale([0, yMax], [plotB, plotT]);
  const bw = (plotR - plotL) / yrs.length * 0.55;
  return (
    <svg width={`${widthPt}pt`} height={`${heightPt}pt`} viewBox={`0 0 ${widthPt} ${heightPt}`} style={{ display: 'block' }}>
      <ChartTitle>{(memo.page3.chartConfig || {}).arrTitle || 'ARR build (run-rate $B)'}</ChartTitle>
      <line x1={plotL} x2={plotR} y1={plotB} y2={plotB} stroke={PALETTE.rule} strokeWidth="0.5" />
      {arr.map((v, i) => (
        <g key={i}>
          <rect x={xScale(i) - bw / 2} y={yScale(v)} width={bw} height={plotB - yScale(v)} fill={PALETTE.accent} />
          <text x={xScale(i)} y={yScale(v) - 3} fontFamily={FONT_MONO} fontSize="6.5pt" fill={PALETTE.ink} textAnchor="middle">${v.toFixed(1)}</text>
          <text x={xScale(i)} y={plotB + 10} fontFamily={FONT_MONO} fontSize="6pt" fill={PALETTE.muted} textAnchor="middle">{String(yrs[i]).slice(2)}</text>
        </g>
      ))}
    </svg>
  );
}

function PrivateExitDistChart({ memo, widthPt = 415, heightPt = 188 }) {
  const scn = memo.print.scenarios;
  const keys = scnKeysFor(memo);
  const SCN_C = { ultra_bear: '#5b1010', bear: '#b91c1c', base: '#1e3a8a', bull: '#15803d', ultra_bull: '#762aa6' };
  const m = { left: 38, right: 20, top: 20, bottom: 30 };
  const plotL = m.left, plotR = widthPt - m.right, plotT = m.top, plotB = heightPt - m.bottom;
  const vals = keys.map(k => scn[k].exitTerms.exitPostMoneyBillion);
  const yMax = Math.max(...vals) * 1.15;
  const xScale = mkLinearScale([-0.5, keys.length - 0.5], [plotL, plotR]);
  const yScale = mkLinearScale([0, yMax], [plotB, plotT]);
  const bw = (plotR - plotL) / keys.length * 0.6;
  return (
    <svg width={`${widthPt}pt`} height={`${heightPt}pt`} viewBox={`0 0 ${widthPt} ${heightPt}`} style={{ display: 'block' }}>
      <ChartTitle>{(memo.page3.chartConfig || {}).exitFanTitle || 'Exit valuation distribution (post-money $B)'}</ChartTitle>
      <line x1={plotL} x2={plotR} y1={plotB} y2={plotB} stroke={PALETTE.rule} strokeWidth="0.5" />
      {keys.map((k, i) => {
        const e = scn[k].exitTerms;
        const lab = e.exitPostMoneyBillion >= 1000 ? `$${(e.exitPostMoneyBillion/1000).toFixed(1)}T` : `$${e.exitPostMoneyBillion.toFixed(0)}B`;
        return (
          <g key={k}>
            <rect x={xScale(i) - bw / 2} y={yScale(e.exitPostMoneyBillion)} width={bw}
                  height={plotB - yScale(e.exitPostMoneyBillion)} fill={SCN_C[k]} />
            <text x={xScale(i)} y={yScale(e.exitPostMoneyBillion) - 3} fontFamily={FONT_MONO} fontSize="6.5pt" fill={PALETTE.ink} textAnchor="middle">{lab}</text>
            <text x={xScale(i)} y={plotB + 10} fontFamily={FONT_SANS} fontSize="6pt" fill={SCN_C[k]} textAnchor="middle">{scn[k].shortLabel}</text>
            <text x={xScale(i)} y={plotB + 19} fontFamily={FONT_MONO} fontSize="5.5pt" fill={PALETTE.muted} textAnchor="middle">{(scn[k].probability*100).toFixed(0)}%</text>
          </g>
        );
      })}
    </svg>
  );
}

function Page3Snapshot({ memo }) {
  if (memo.print.dcfType === 'private_prevaluation') {
    return (
      <div className="memo-page">
        <PageHeader memo={memo} suffix="business snapshot" label="the snapshot" compact />
        <div style={{ marginTop: '8pt', fontFamily: FONT_SANS, fontSize: '8pt', color: PALETTE.muted }}>
          {memo.page3.subtitle}
        </div>
        <div style={{ marginTop: '16pt', display: 'flex', flexDirection: 'column', gap: '10pt', alignItems: 'center' }}>
          <PrivateArrChart memo={memo} />
          <PrivateExitDistChart memo={memo} />
        </div>
        <div style={{ marginTop: '12pt', fontFamily: FONT_SANS, fontSize: '7pt', color: PALETTE.muted }}>
          {memo.page3.sources}
        </div>
        <PageFooter memo={memo} pageLabel={`page 3 of ${memoTotalPages(memo)}`} />
      </div>
    );
  }
  const isYoung = memo.print.dcfType === 'young_company';

  // Six chart slots — 3 columns × 2 rows. Phase 2 ports them one at a time;
  // un-ported slots show a placeholder so the layout stays representative.
  const placeholder = (slot, title) => (
    <div style={{
      width: '280pt', height: '190pt',
      border: `0.5pt dashed ${PALETTE.dim}`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: FONT_MONO, fontSize: '7pt', color: PALETTE.muted,
    }}>
      {slot}. {title} (pending)
    </div>
  );

  const slots = isYoung ? [
    <YoungRevenueChart memo={memo} />,
    <YoungProfitabilityChart memo={memo} />,
    <YoungCashDilutionChart memo={memo} />,
    <YoungFleetChart memo={memo} />,
    <YoungValuationChart memo={memo} />,
    <YoungTamChart memo={memo} />,
  ] : [
    <MatureRevenueChart memo={memo} />,
    <MatureSegmentsChart memo={memo} />,
    <MatureMarginsChart memo={memo} />,
    <MatureBalanceChart memo={memo} />,
    <MatureEvMultiplesChart memo={memo} />,
    <MatureTerminalChart memo={memo} />,
  ];

  return (
    <div className="memo-page">
      <PageHeader memo={memo} suffix="business snapshot"
                  label="the snapshot" compact />

      {/* Page 3 subtitle (data scope, fiscal years, sources strip) */}
      <div style={{
        marginTop: '8pt',
        fontFamily: FONT_SANS, fontSize: '8pt', color: PALETTE.muted,
      }}>
        {memo.page3.subtitle}
      </div>

      {/* 3 × 2 chart grid */}
      <div style={{
        marginTop: '12pt',
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 280pt)',
        gridTemplateRows: 'repeat(2, 190pt)',
        columnGap: '12pt',
        rowGap: '16pt',
        justifyContent: 'center',
      }}>
        {slots.map((slot, i) => <div key={i}>{slot}</div>)}
      </div>

      {/* Sources caption */}
      <div style={{
        marginTop: '12pt',
        fontFamily: FONT_SANS, fontSize: '7pt', color: PALETTE.muted,
      }}>
        {memo.page3.sources}
      </div>

      <PageFooter memo={memo} pageLabel={`page 3 of ${memoTotalPages(memo)}`} />
    </div>
  );
}

// ── Page 4 — Quantitative (show your work) ─────────────────────────────
function ScenarioQuantColumn({ memo, scenarioKey }) {
  const print = memo.print;
  const scn = print.scenarios[scenarioKey];
  const dcfType = print.dcfType;
  const isPriv = dcfType === 'private_prevaluation';
  const n = print.dcfPeriodYears;
  // DCF-table fields are public-equity only; private scenarios have no
  // operating-cash-flow path (they carry exit_terms instead).
  const fyLabels = isPriv ? [] : dcfYearLabels(dcfType, n);
  const rev = isPriv ? [] : dcfRevenueDisplay(scn, dcfType, n);
  const margins = isPriv ? [] : scn.dcfPath.op_margin;
  const fcf = isPriv ? [] : scn.dcfPath.fcf;
  const pvFcf = isPriv ? [] : scn.dcfPath.pv_fcf;
  const sumPv = isPriv ? 0 : scn.dcfPath.sum_pv_fcf;
  const pvTerm = isPriv ? 0 : scn.dcfPath.pv_terminal;
  const termG = isPriv ? 0 : scn.dcfPath.term_g;
  const waccTerm = isPriv ? 0 : scn.dcfPath.wacc_path[scn.dcfPath.wacc_path.length - 1];
  const asm = assumptionsRows(scn, dcfType, print.tamBillion);
  const eb = equityBuildRows(scn, dcfType);
  const expected = scn.expectedPerShare;
  const NEG = '#b91c1c';
  const POS = '#15803d';

  // Column-internal positions (memo.py uses 4 numeric columns + label).
  const cell = {
    fontFamily: FONT_MONO, fontSize: '6.5pt', color: PALETTE.ink,
    textAlign: 'right',
  };
  const cellLabel = {
    fontFamily: FONT_SANS, fontSize: '6.5pt', color: PALETTE.text,
  };
  const headerCell = {
    fontFamily: FONT_SANS, fontWeight: 600, fontSize: '6.5pt',
    color: PALETTE.muted, textAlign: 'right',
  };

  // Section helper for in-column headings. Tight margins so the 5-section
  // column (header / assumptions / DCF / equity / future-value) fits on
  // one page — memo.py uses ~22pt total per section header; CSS Grid
  // gives 22pt at 4/4 margins.
  // 5-scenario columns are ~20% narrower and (for young_company) carry a
  // 10-row DCF table — tighten section margins and row line-heights so the
  // column fits the page without trimming narrative. 4-scenario memos are
  // untouched.
  const tight = scnKeysFor(memo).length === 5;
  const dcfRowLH = tight ? '8.3pt' : '9pt';
  const SectionEyebrow = ({ children }) => (
    <div style={{ marginTop: tight ? '3pt' : '4pt', marginBottom: tight ? '3pt' : '4pt' }}>
      <Eyebrow>{children}</Eyebrow>
      <div style={{ marginTop: '2pt' }}><Rule /></div>
    </div>
  );

  return (
    <div>
      {/* Scenario header */}
      <div style={{ display: 'flex', justifyContent: 'space-between',
                    alignItems: 'baseline', paddingBottom: '4pt' }}>
        <div style={{
          fontFamily: FONT_SANS, fontWeight: 600, fontSize: '10pt',
          color: PALETTE.ink, letterSpacing: '0.02em',
        }}>
          {scn.label.toUpperCase()}
        </div>
        <div style={{
          fontFamily: FONT_MONO, fontWeight: 700, fontSize: '14pt',
          color: PALETTE.ink,
        }}>
          ${expected.toFixed(2)}
        </div>
      </div>
      <Rule />

      {/* Assumptions */}
      <SectionEyebrow>ASSUMPTIONS</SectionEyebrow>
      {asm.map(([lab, val], i) => (
        <div key={i} style={{
          display: 'flex', justifyContent: 'space-between',
          lineHeight: '9.5pt',
        }}>
          <span style={cellLabel}>{lab}</span>
          <span style={{ ...cell, fontFamily: FONT_MONO }}>{val}</span>
        </div>
      ))}

      {/* DCF table — public-equity only (private has no operating cash flows) */}
      {!isPriv && <>
      <SectionEyebrow>{n}-YEAR DCF  ·  $B</SectionEyebrow>
      <div style={{
        display: 'grid',
        gridTemplateColumns: '28pt 1fr 1fr 1fr 1fr',
        columnGap: '4pt',
        rowGap: '0',
      }}>
        <div style={{ ...headerCell, textAlign: 'left' }}>FY</div>
        <div style={headerCell}>Rev</div>
        <div style={headerCell}>Margin</div>
        <div style={headerCell}>FCF</div>
        <div style={headerCell}>PV FCF</div>
      </div>
      <div style={{ marginTop: '2pt' }}><Rule /></div>
      <div style={{
        display: 'grid',
        gridTemplateColumns: '28pt 1fr 1fr 1fr 1fr',
        columnGap: '4pt',
        rowGap: '0',
        marginTop: '3pt',
      }}>
        {fyLabels.map((fy, i) => {
          const fcfColor = fcf[i] < 0 ? NEG : PALETTE.ink;
          const marginSign = margins[i] >= 0 ? '+' : '';
          const fcfSign = fcf[i] >= 0 ? '+' : '';
          const pvSign = pvFcf[i] >= 0 ? '+' : '';
          return (
            <React.Fragment key={fy}>
              <div style={{ fontFamily: FONT_SANS, fontSize: '6.5pt',
                            color: PALETTE.text, lineHeight: dcfRowLH }}>{fy}</div>
              <div style={{ ...cell, lineHeight: dcfRowLH }}>{rev[i].toFixed(2)}</div>
              <div style={{ ...cell, lineHeight: dcfRowLH }}>
                {marginSign}{(margins[i] * 100).toFixed(0)}%
              </div>
              <div style={{ ...cell, color: fcfColor, lineHeight: dcfRowLH }}>
                {fcfSign}{fcf[i].toFixed(2)}
              </div>
              <div style={{ ...cell, lineHeight: dcfRowLH }}>
                {pvSign}{pvFcf[i].toFixed(2)}
              </div>
            </React.Fragment>
          );
        })}
      </div>

      {/* DCF subtotals */}
      <div style={{ marginTop: '4pt' }}><Rule /></div>
      <div style={{ display: 'flex', justifyContent: 'space-between',
                    marginTop: '4pt' }}>
        <span style={{ fontFamily: FONT_SANS, fontSize: '7pt',
                       fontWeight: 500, color: PALETTE.ink }}>
          Σ PV explicit FCF
        </span>
        <span style={{ fontFamily: FONT_MONO, fontSize: '7pt',
                       fontWeight: 700, color: PALETTE.ink }}>
          {sumPv >= 0 ? '+' : ''}{sumPv.toFixed(2)}
        </span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between',
                    marginTop: '2pt' }}>
        <span style={{ fontFamily: FONT_SANS, fontSize: '7pt', color: PALETTE.text }}>
          + PV terminal (g {(termG * 100).toFixed(1)}%)
        </span>
        <span style={{ fontFamily: FONT_MONO, fontSize: '7pt', color: PALETTE.ink }}>
          {pvTerm.toFixed(2)}
        </span>
      </div>
      </>}

      {/* Equity build (public) / Exit-PV build (private) */}
      <SectionEyebrow>{isPriv ? 'EXIT → PV PER SHARE' : 'EQUITY BUILD  ·  $B & per share'}</SectionEyebrow>
      {eb.map(([lab, val, kind], i) => {
        const baseStyle = { display: 'flex', justifyContent: 'space-between' };
        if (kind === 'subtotal') {
          return (
            <React.Fragment key={i}>
              <div style={{ marginBottom: '2pt' }}><Rule /></div>
              <div style={{ ...baseStyle, lineHeight: '9.5pt' }}>
                <span style={{ fontFamily: FONT_SANS, fontSize: '7pt',
                               fontWeight: 500, color: PALETTE.ink }}>{lab}</span>
                <span style={{ fontFamily: FONT_MONO, fontSize: '7pt',
                               fontWeight: 700, color: PALETTE.ink }}>{val}</span>
              </div>
            </React.Fragment>
          );
        }
        if (kind === 'total') {
          return (
            <React.Fragment key={i}>
              <div style={{ marginTop: '2pt', marginBottom: '3pt' }}>
                <Rule strong />
              </div>
              <div style={{ ...baseStyle, lineHeight: '12pt' }}>
                <span style={{ fontFamily: FONT_SANS, fontSize: '8.5pt',
                               fontWeight: 600, color: PALETTE.ink }}>{lab}</span>
                <span style={{ fontFamily: FONT_MONO, fontSize: '8.5pt',
                               fontWeight: 700, color: PALETTE.ink }}>{val}</span>
              </div>
            </React.Fragment>
          );
        }
        return (
          <div key={i} style={{ ...baseStyle, lineHeight: '10pt' }}>
            <span style={{ fontFamily: FONT_SANS, fontSize: '7pt', color: PALETTE.text }}>{lab}</span>
            <span style={{ fontFamily: FONT_MONO, fontSize: '7pt', color: PALETTE.text }}>{val}</span>
          </div>
        );
      })}

      {/* Private: discount-rate sensitivity (the load-bearing input). Shows
          how the scenario's PV moves with the venture WACC. */}
      {isPriv ? (() => {
        const e = scn.exitTerms;
        const nom = e.exitPerShareNominal * (1 - (e.lpHaircutPct || 0) / 100);
        const ipoHc = 1 - (e.ipoUnderperformanceHaircutPct || 0) / 100;
        const pLoss = e.pTotalLoss || 0;
        const rates = [0.15, 0.18, 0.22, 0.25];
        return (
          <>
            <SectionEyebrow>PV SENSITIVITY TO DISCOUNT RATE</SectionEyebrow>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', textAlign: 'center' }}>
              {rates.map(r => (
                <div key={`r-${r}`} style={{ ...headerCell, textAlign: 'center' }}>{(r*100).toFixed(0)}%</div>
              ))}
              {rates.map(r => {
                const pv = nom / Math.pow(1 + r, e.yearsToExit);
                const exp = (1 - pLoss) * pv * ipoHc;
                const hot = Math.abs(r - e.ventureWacc) < 0.005;
                return (
                  <div key={`rv-${r}`} style={{
                    fontFamily: FONT_MONO, fontSize: '7pt',
                    color: hot ? PALETTE.accent : PALETTE.ink,
                    fontWeight: hot ? 700 : 400,
                    textAlign: 'center', marginTop: '2pt',
                  }}>
                    ${exp.toFixed(0)}
                  </div>
                );
              })}
            </div>
          </>
        );
      })() : (<>
      <SectionEyebrow>FUTURE FAIR VALUE  ·  IF SCENARIO PLAYS OUT</SectionEyebrow>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        textAlign: 'center',
      }}>
        {[5, 10, 15, 20].map(T => (
          <div key={`y-${T}`} style={{ ...headerCell, textAlign: 'center' }}>
            +{T}y
          </div>
        ))}
        {[5, 10, 15, 20].map(T => {
          const fv = expected * Math.pow(1 + waccTerm, T);
          return (
            <div key={`v-${T}`} style={{
              fontFamily: FONT_MONO, fontSize: '7pt', color: PALETTE.ink,
              textAlign: 'center', marginTop: '2pt',
            }}>
              ${fv.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          );
        })}
        {[5, 10, 15, 20].map(T => {
          const fv = expected * Math.pow(1 + waccTerm, T);
          const mult = fv / memo.spot.price;
          const color = (expected <= 0 || fv < memo.spot.price) ? NEG : POS;
          return (
            <div key={`m-${T}`} style={{
              fontFamily: FONT_MONO, fontSize: '6.5pt', color,
              textAlign: 'center',
            }}>
              {mult.toFixed(2)}×
            </div>
          );
        })}
      </div>
      </>)}
    </div>
  );
}

// ── Page 4 — Competitive landscape (§6d). Two lenses keyed off
// competitive.lens: Power Audit (mature/FCF++/megacap) and Power Origination
// (moonshots/private). Renders only when memo.print.competitive is present;
// otherwise the memo stays 5 pages. Helmer's 7 Powers is the spine. ──
const POWER_ORDER = ['scaleEconomies', 'networkEconomies', 'counterPositioning',
                     'switchingCosts', 'branding', 'corneredResource', 'processPower'];
const POWER_LABEL = {
  scaleEconomies: 'Scale Economies', networkEconomies: 'Network Economies',
  counterPositioning: 'Counter-Positioning', switchingCosts: 'Switching Costs',
  branding: 'Branding', corneredResource: 'Cornered Resource',
  processPower: 'Process Power',
};
const VERDICT_COLOR = { leading: '#15803d', even: PALETTE.muted, lagging: '#b91c1c' };
// camelize a snake_case *value* (list-item string values aren't camelized upstream)
const _camelVal = s => (s || '').replace(/_([a-z])/g, (_, x) => x.toUpperCase());

function PowerBar({ score }) {
  return (
    <div style={{ display: 'flex', gap: '2pt' }}>
      {[0, 1, 2].map(i => (
        <div key={i} style={{
          width: '14pt', height: '5pt', borderRadius: '1pt',
          background: i < score ? PALETTE.accent : PALETTE.rule,
        }} />
      ))}
    </div>
  );
}

function Page4Competitive({ memo }) {
  const c = memo.print.competitive;
  const origination = c.lens === 'power_origination';
  const lensLabel = origination ? 'Power Origination' : 'Power Audit';
  const dom = _camelVal(c.dominantPower);
  const maxT = Math.max(0.01, ...((c.rivals || []).map(x => x.shareTerminal || 0)));
  return (
    <div className="memo-page">
      <PageHeader memo={memo} suffix="7 Powers · the moat, scored"
                  label="the competitive landscape" />

      {/* Arena + lens badge */}
      <div style={{ display: 'flex', justifyContent: 'space-between',
                    alignItems: 'flex-start', marginTop: '8pt', gap: '14pt' }}>
        <div style={{ fontFamily: FONT_SANS, fontSize: '8.5pt', color: PALETTE.text,
                      lineHeight: 1.4, flex: 1 }}>
          <span style={{ fontWeight: 700, color: PALETTE.ink }}>Arena.&nbsp;</span>{c.arena}
        </div>
        <div style={{ flexShrink: 0, textAlign: 'right' }}>
          <div style={{ fontFamily: FONT_MONO, fontSize: '7pt', fontWeight: 700,
                        color: PALETTE.accent, letterSpacing: '0.04em' }}>
            {lensLabel.toUpperCase()}
          </div>
          <div style={{ fontFamily: FONT_SANS, fontSize: '6.5pt', color: PALETTE.muted }}>
            {origination
              ? `origination window: ${c.window || '—'}`
              : `dominant-power durability: ${c.durability || '—'}`}
          </div>
        </div>
      </div>

      {/* Two columns: 7-Powers scorecard (left) + rivals/falsifiers (right) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.15fr 1fr',
                    gap: '20pt', marginTop: '12pt' }}>
        {/* LEFT — 7 Powers scorecard */}
        <div>
          <SectionHeader label={origination ? 'POWER ORIGINATION · 7 POWERS' : 'POWER AUDIT · 7 POWERS'}
                         marginTop="0" marginBottom="8pt" />
          {POWER_ORDER.map(k => {
            const p = (c.powers || {})[k] || { score: 0, note: '' };
            const isDom = k === dom;
            return (
              <div key={k} style={{ display: 'flex', gap: '8pt',
                                    alignItems: 'flex-start', marginBottom: '7pt' }}>
                <div style={{ width: '150pt', flexShrink: 0 }}>
                  <div style={{ fontFamily: FONT_SANS, fontSize: '7.5pt',
                                fontWeight: isDom ? 700 : 600,
                                color: isDom ? PALETTE.accent : PALETTE.ink }}>
                    {POWER_LABEL[k]}
                    {isDom && <span style={{ fontFamily: FONT_MONO, fontSize: '6pt',
                                             fontWeight: 700, color: PALETTE.accent }}>
                      {'  ◂ thesis leans here'}</span>}
                  </div>
                  <div style={{ marginTop: '2pt' }}><PowerBar score={p.score} /></div>
                </div>
                <div style={{ flex: 1, fontFamily: FONT_SANS, fontSize: '7pt',
                              color: PALETTE.text, lineHeight: 1.35 }}>{p.note}</div>
              </div>
            );
          })}
        </div>

        {/* RIGHT — rivals + falsifiers, lens-dependent */}
        <div>
          {origination ? (
            <>
              <SectionHeader label="THE RACE · NAMED RIVALS" marginTop="0" marginBottom="8pt" />
              {(c.rivals || []).map((r, i) => (
                <div key={i} style={{ marginBottom: '6pt' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontFamily: FONT_SANS, fontSize: '7.5pt',
                                   fontWeight: 600, color: PALETTE.ink }}>{r.name}</span>
                    <span style={{ fontFamily: FONT_MONO, fontSize: '6.5pt',
                                   color: PALETTE.muted }}>{r.capital}</span>
                  </div>
                  <div style={{ height: '5pt', background: PALETTE.rule,
                                borderRadius: '1pt', marginTop: '2pt' }}>
                    <div style={{ width: `${100 * (r.shareTerminal || 0) / maxT}%`,
                                  height: '100%', background: PALETTE.dim,
                                  borderRadius: '1pt' }} />
                  </div>
                  <div style={{ fontFamily: FONT_SANS, fontSize: '6.5pt',
                                color: PALETTE.text, marginTop: '2pt', lineHeight: 1.3 }}>
                    <span style={{ fontFamily: FONT_MONO, color: PALETTE.muted }}>
                      ~{Math.round(100 * (r.shareTerminal || 0))}% terminal share · </span>{r.note}
                  </div>
                </div>
              ))}
              <SectionHeader label="LEAD / LAG · FALSIFIERS" marginTop="10pt" marginBottom="6pt" />
              {(c.leadLag || []).map((l, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between',
                                      alignItems: 'baseline', marginBottom: '4pt', gap: '8pt' }}>
                  <span style={{ fontFamily: FONT_SANS, fontSize: '7pt',
                                 color: PALETTE.text, flex: 1 }}>{l.metric}</span>
                  <span style={{ fontFamily: FONT_MONO, fontSize: '7pt', color: PALETTE.ink }}>
                    {l.company} <span style={{ color: PALETTE.dim }}>vs</span> {l.bestRival}</span>
                  <span style={{ fontFamily: FONT_MONO, fontSize: '6.5pt', fontWeight: 700,
                                 color: VERDICT_COLOR[l.verdict] || PALETTE.muted,
                                 width: '42pt', textAlign: 'right' }}>
                    {(l.verdict || '').toUpperCase()}</span>
                </div>
              ))}
            </>
          ) : (
            <>
              <SectionHeader label="PEER SET" marginTop="0" marginBottom="8pt" />
              {(c.rivals || []).map((r, i) => (
                <div key={i} style={{ marginBottom: '7pt' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between',
                                alignItems: 'baseline' }}>
                    <span style={{ fontFamily: FONT_SANS, fontSize: '7.5pt',
                                   fontWeight: 600, color: PALETTE.ink }}>{r.name}</span>
                    <span style={{ fontFamily: FONT_MONO, fontSize: '6.5pt', color: PALETTE.muted }}>
                      {r.growth != null ? `${Math.round(r.growth * 100)}% gr` : ''}
                      {r.margin != null ? ` · ${Math.round(r.margin * 100)}% mgn` : ''}
                      {r.multiple ? ` · ${r.multiple}` : ''}
                    </span>
                  </div>
                  <div style={{ fontFamily: FONT_SANS, fontSize: '6.5pt',
                                color: PALETTE.text, marginTop: '1pt', lineHeight: 1.3 }}>{r.note}</div>
                </div>
              ))}
              <SectionHeader label="THREAT VECTORS · FALSIFIERS" marginTop="10pt" marginBottom="6pt" />
              {(c.threats || []).map((t, i) => (
                <div key={i} style={{ marginBottom: '6pt' }}>
                  <div style={{ fontFamily: FONT_SANS, fontSize: '7pt',
                                fontWeight: 600, color: PALETTE.ink }}>
                    {POWER_LABEL[_camelVal(t.vector)] || t.vector}
                    <span style={{ color: PALETTE.muted, fontWeight: 400 }}> · {t.who}</span>
                  </div>
                  <div style={{ fontFamily: FONT_SANS, fontSize: '6.5pt',
                                color: PALETTE.text, lineHeight: 1.3 }}>
                    <span style={{ fontFamily: FONT_MONO, color: '#b91c1c' }}>falsifier: </span>{t.falsifier}
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      </div>

      {/* Takeaway — conviction-neutral competitive verdict */}
      <div style={{ marginTop: '12pt', borderLeft: `2pt solid ${PALETTE.accent}`,
                    paddingLeft: '10pt' }}>
        <div style={{ fontFamily: FONT_MONO, fontSize: '6.5pt', fontWeight: 700,
                      color: PALETTE.accent, letterSpacing: '0.05em', marginBottom: '2pt' }}>
          COMPETITIVE READ</div>
        <div style={{ fontFamily: FONT_SANS, fontSize: '8pt',
                      color: PALETTE.ink, lineHeight: 1.4 }}>{c.takeaway}</div>
      </div>

      <PageFooter memo={memo} pageLabel={`page 4 of ${memoTotalPages(memo)}`} />
    </div>
  );
}

// ── Back-matter — POCD underwriting lens (§14). People is the leg scored here
// (the build item); Opportunity / Context / Deal cross-reference §6c/§6d/§13/§12.
// Renders only when memo.print.pocd is present. All inputs observable (§3.5 B). ──
const RISK_COLOR = { low: '#15803d', medium: '#b45309', high: '#b91c1c' };

function ScoreDots({ score, of = 5 }) {
  return (
    <div style={{ display: 'flex', gap: '3pt' }}>
      {Array.from({ length: of }).map((_, i) => (
        <div key={i} style={{
          width: '9pt', height: '9pt', borderRadius: '50%',
          background: i < score ? PALETTE.accent : PALETTE.rule,
        }} />
      ))}
    </div>
  );
}

function PocdRow({ label, body }) {
  if (!body) return null;
  return (
    <div style={{ marginBottom: '6pt' }}>
      <div style={{ fontFamily: FONT_SANS, fontSize: '7pt', fontWeight: 600, color: PALETTE.ink }}>{label}</div>
      <div style={{ fontFamily: FONT_SANS, fontSize: '7pt', color: PALETTE.text, lineHeight: 1.35 }}>{body}</div>
    </div>
  );
}

function PocdLeg({ label, body }) {
  if (!body) return null;
  return (
    <div style={{ marginBottom: '6pt' }}>
      <div style={{ fontFamily: FONT_SANS, fontSize: '7.5pt', fontWeight: 600, color: PALETTE.ink }}>{label}</div>
      <div style={{ fontFamily: FONT_SANS, fontSize: '6.5pt', color: PALETTE.text, lineHeight: 1.3 }}>{body}</div>
    </div>
  );
}

function PagePOCD({ memo }) {
  const pocd = memo.print.pocd || {};
  const p = pocd.people || {};
  const risk = (p.keyPersonRisk || '').toLowerCase();
  return (
    <div className="memo-page">
      <PageHeader memo={memo} suffix="People · Opportunity · Context · Deal"
                  label="the underwriting lens (POCD)" />

      <div style={{ fontFamily: FONT_SANS, fontSize: '8pt', color: PALETTE.text,
                    lineHeight: 1.4, marginTop: '8pt' }}>
        Underwrite the position the way a venture investor underwrites a round — across all four legs,
        public or private. <span style={{ fontWeight: 700, color: PALETTE.ink }}>People</span> is the
        leg scored here (observable only); Opportunity, Context and Deal cross-reference the rest of the memo.
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.25fr 1fr', gap: '20pt', marginTop: '12pt' }}>
        {/* LEFT — People (the build leg) */}
        <div>
          <SectionHeader label="PEOPLE · WHO RUNS / OWNS / FUNDS IT" marginTop="0" marginBottom="8pt" />
          <div style={{ display: 'flex', justifyContent: 'space-between',
                        alignItems: 'baseline', marginBottom: '7pt' }}>
            <span style={{ fontFamily: FONT_SANS, fontSize: '8.5pt', fontWeight: 700, color: PALETTE.ink }}>
              {p.ceo}
              {p.founderLed && <span style={{ fontFamily: FONT_MONO, fontSize: '6.5pt',
                fontWeight: 700, color: PALETTE.accent }}>{'  · founder-led'}</span>}
            </span>
            {p.tenureYears != null && <span style={{ fontFamily: FONT_MONO, fontSize: '7pt',
              color: PALETTE.muted }}>{p.tenureYears} yrs in seat</span>}
          </div>
          <div style={{ display: 'flex', gap: '24pt', marginBottom: '9pt' }}>
            {p.insiderOwnershipPct != null && (
              <div>
                <div style={{ fontFamily: FONT_MONO, fontSize: '13pt', fontWeight: 700, color: PALETTE.ink }}>
                  {p.insiderOwnershipPct}%</div>
                <div style={{ fontFamily: FONT_SANS, fontSize: '6.5pt', color: PALETTE.muted }}>insider ownership</div>
              </div>
            )}
            <div>
              <div style={{ fontFamily: FONT_MONO, fontSize: '10pt', fontWeight: 700,
                            color: RISK_COLOR[risk] || PALETTE.muted, textTransform: 'uppercase' }}>
                {p.keyPersonRisk || '—'}</div>
              <div style={{ fontFamily: FONT_SANS, fontSize: '6.5pt', color: PALETTE.muted }}>key-person risk</div>
            </div>
          </div>
          <PocdRow label="Capital allocation (realized)" body={p.capitalAllocation} />
          <PocdRow label="Incentive alignment" body={p.incentiveAlignment} />
          {(p.governanceFlags || []).length > 0 && (
            <div style={{ marginTop: '6pt' }}>
              <div style={{ fontFamily: FONT_MONO, fontSize: '6.5pt', fontWeight: 700,
                            color: PALETTE.muted, letterSpacing: '0.04em', marginBottom: '3pt' }}>
                GOVERNANCE FLAGS</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4pt' }}>
                {(p.governanceFlags || []).map((g, i) => (
                  <span key={i} style={{ fontFamily: FONT_SANS, fontSize: '6.5pt', color: PALETTE.text,
                    background: PALETTE.rule, borderRadius: '2pt', padding: '1.5pt 5pt' }}>{g}</span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* RIGHT — the four legs at a glance */}
        <div>
          <SectionHeader label="THE FOUR LEGS" marginTop="0" marginBottom="8pt" />
          <div style={{ marginBottom: '9pt' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontFamily: FONT_SANS, fontSize: '7.5pt', fontWeight: 700, color: PALETTE.accent }}>
                People</span>
              <ScoreDots score={p.score || 0} />
            </div>
            <div style={{ fontFamily: FONT_SANS, fontSize: '6.5pt', color: PALETTE.muted, marginTop: '1pt' }}>
              observable composite · 1–5</div>
          </div>
          <PocdLeg label="Opportunity" body={pocd.opportunityRef} />
          <PocdLeg label="Context" body={pocd.contextRef} />
          <PocdLeg label="Deal" body={pocd.deal} />
        </div>
      </div>

      {/* Takeaway — the People read (external, falsifiable; never operator preference) */}
      <div style={{ marginTop: '12pt', borderLeft: `2pt solid ${PALETTE.accent}`, paddingLeft: '10pt' }}>
        <div style={{ fontFamily: FONT_MONO, fontSize: '6.5pt', fontWeight: 700,
                      color: PALETTE.accent, letterSpacing: '0.05em', marginBottom: '2pt' }}>PEOPLE READ</div>
        <div style={{ fontFamily: FONT_SANS, fontSize: '8pt', color: PALETTE.ink, lineHeight: 1.4 }}>{p.takeaway}</div>
      </div>

      <PageFooter memo={memo} pageLabel={`page ${memoTotalPages(memo) - 1} of ${memoTotalPages(memo)}`} />
    </div>
  );
}

function Page4Quantitative({ memo }) {
  return (
    <div className="memo-page">
      <PageHeader memo={memo} suffix="show your work"
                  label="the quantitative" recapWeighted compact />

      {/* Scenario quant grid — fills the page alone. Pushback +
          falsification triggers live on Page 5; we tried Page 4 per the
          spec but the quant content takes the full page. Column count
          tracks scnKeysFor(memo).length (4 for most tickers, 5 with
          ultra_bear). */}
      <div style={{
        marginTop: '8pt',
        display: 'grid',
        gridTemplateColumns: `repeat(${scnKeysFor(memo).length}, 1fr)`,
        columnGap: scnKeysFor(memo).length === 5 ? '10pt' : '16pt',
      }}>
        {scnKeysFor(memo).map(k => (
          <ScenarioQuantColumn key={k} memo={memo} scenarioKey={k} />
        ))}
      </div>

      <PageFooter memo={memo} pageLabel={`page ${hasCompetitive(memo) ? 5 : 4} of ${memoTotalPages(memo)}`} />
    </div>
  );
}

// ── Page 5 — Back matter (pushback, triggers, disclaimers, glossary).
// Spec §6 implies pushback+triggers belong on Page 4 (quant) but the
// 4-column quant grid takes a full page; following memo.py's layout. ──
function Page5BackMatter({ memo }) {
  const { appendix, glossary } = memo.print;
  const disclaimers = window.AR2EB_DATA.PDF_DISCLAIMERS;

  // Substitute ${TICKER} in disclaimer body at render time.
  const renderDisclaimer = d => ({
    ...d,
    p: d.p.replace(/\$\{TICKER\}/g, `$${memo.ticker}`),
  });

  return (
    <div className="memo-page">
      <PageHeader memo={memo} suffix="supporting analysis · disclaimers · glossary"
                  label="the back matter" />

      {/* PUSHBACK */}
      <SectionHeader label="PUSHBACK  ·  WHY THE BASE CASE IS TOO HARSH"
                     marginTop="10pt" marginBottom="8pt" />
      <ThreeColGrid
        items={appendix.pushback}
        rowGap="12pt"
        renderItem={(item, i) => (
          <div style={{ display: 'flex', gap: '6pt' }}>
            <div style={{
              fontFamily: FONT_MONO,
              fontWeight: 700,
              fontSize: '8pt',
              color: PALETTE.muted,
              flexShrink: 0,
              width: '10pt',
            }}>
              {i + 1}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{
                fontFamily: FONT_SANS,
                fontWeight: 600,
                fontSize: '7.5pt',
                color: PALETTE.ink,
                marginBottom: '2pt',
              }}>
                {item.label}
              </div>
              <div style={{
                fontFamily: FONT_SANS,
                fontSize: '7pt',
                color: PALETTE.text,
                lineHeight: 1.35,
              }}>
                {item.body}
              </div>
            </div>
          </div>
        )}
      />

      {/* FALSIFICATION TRIGGERS */}
      <SectionHeader label="FALSIFICATION TRIGGERS" marginTop="10pt" marginBottom="8pt" />
      <ThreeColGrid
        items={appendix.triggers}
        rowGap="10pt"
        renderItem={(item) => (
          <div>
            <div style={{
              fontFamily: FONT_SANS,
              fontWeight: 600,
              fontSize: '8pt',
              color: PALETTE.ink,
              marginBottom: '3pt',
            }}>
              {item.label}
            </div>
            <div style={{
              fontFamily: FONT_SANS,
              fontSize: '7.5pt',
              color: PALETTE.text,
              lineHeight: 1.35,
            }}>
              {item.body}
            </div>
          </div>
        )}
      />

      {/* DISCLAIMERS */}
      <SectionHeader label="DISCLAIMERS  ·  PLEASE READ BEFORE USING THIS DOCUMENT" marginTop="10pt" marginBottom="8pt" />
      <ThreeColGrid
        items={disclaimers.map(renderDisclaimer)}
        rowGap="10pt"
        renderItem={(d) => (
          <div>
            <div style={{
              fontFamily: FONT_SANS,
              fontWeight: 600,
              fontSize: '8.5pt',
              color: PALETTE.ink,
              marginBottom: '3pt',
            }}>
              {d.h}
            </div>
            <div style={{
              fontFamily: FONT_SANS,
              fontSize: '7.5pt',
              color: PALETTE.text,
              lineHeight: 1.35,
            }}>
              {d.p}
            </div>
          </div>
        )}
      />

      {/* GLOSSARY */}
      <SectionHeader label="GLOSSARY  ·  CONCEPTS REFERENCED IN THE NARRATIVE" marginTop="10pt" marginBottom="8pt" />
      <ThreeColGrid
        items={glossary}
        rowGap="8pt"
        renderItem={(g) => (
          <div style={{
            fontFamily: FONT_SANS,
            fontSize: '7.5pt',
            color: PALETTE.text,
            lineHeight: 1.35,
          }}>
            <span style={{ fontWeight: 600, color: PALETTE.ink }}>{g.term}</span>
            <span style={{ color: PALETTE.dim }}>{' — '}</span>
            <span>{g.definition}</span>
          </div>
        )}
      />

      <PageFooter memo={memo} pageLabel={`page ${memoTotalPages(memo)} of ${memoTotalPages(memo)}`} showDisclaimerPointer={false} />
    </div>
  );
}

// ── Root ───────────────────────────────────────────────────────────────
function MemoPDF() {
  const slug = getTickerSlug();
  const memo = findMemo(slug);

  if (!slug) return <div style={{ padding: 40, fontFamily: FONT_SANS }}>
    Missing <code>?ticker=&lt;slug&gt;</code> query parameter.
  </div>;
  if (!memo) return <div style={{ padding: 40, fontFamily: FONT_SANS }}>
    No memo found for ticker <code>{slug}</code>.
  </div>;
  if (!memo.print) return <div style={{ padding: 40, fontFamily: FONT_SANS }}>
    Memo <code>{slug}</code> missing <code>print</code> payload — rerun
    scripts/build_site_data.py.
  </div>;

  return (
    <>
      <Page1Headline memo={memo} />
      <Page2Narratives memo={memo} />
      <Page3Snapshot memo={memo} />
      {hasCompetitive(memo) && <Page4Competitive memo={memo} />}
      <Page4Quantitative memo={memo} />
      {hasPOCD(memo) && <PagePOCD memo={memo} />}
      <Page5BackMatter memo={memo} />
    </>
  );
}

// Export page components so the site (public/pages.jsx → MemoPage) can
// render the same JSX inline. The print harness (print.html) sets
// body[data-harness="print"] and we auto-mount + signal ready; the site
// imports MemoPagesAll and renders it scaled inside MemoPage.
window.AR2EB_MEMO = {
  Page1Headline, Page2Narratives, Page3Snapshot, Page4Competitive, Page4Quantitative, PagePOCD, Page5BackMatter,
  MemoPDF,
  findMemo, getTickerSlug,
};

if (document.body && document.body.dataset.harness === 'print') {
  const root = ReactDOM.createRoot(document.getElementById('root'));
  root.render(<MemoPDF />);

  // Signal to the print renderer that React has mounted and fonts have loaded.
  (async () => {
    if (document.fonts && document.fonts.ready) {
      await document.fonts.ready;
    }
    requestAnimationFrame(() => {
      document.body.dataset.ready = '1';
    });
  })();
}
