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
  const m = scn.dcfMetrics;
  const p = scn.dcfPath;
  const probPct = (scn.probability * 100).toFixed(0);
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
    return [
      ['5y revenue CAGR (%)',     `${sign}${m.cagr_5y.toFixed(1)}`],
      ['Year-5 op margin (%)',    (p.op_margin[p.op_margin.length - 1] * 100).toFixed(1)],
      ['WACC (%)',                (m.wacc * 100).toFixed(1)],
      ['Terminal growth (%)',     (p.term_g * 100).toFixed(1)],
      ['5y SLB total ($B)',       m.slb_total_5y.toFixed(2)],
      ['Starting revenue ($B)',   p.rev_b.toFixed(2)],
      ['Scenario probability (%)', probPct],
    ];
  }
  // mature_company_sotp
  const signS = m.cagr_5y >= 0 ? '+' : '';
  return [
    ['5y revenue CAGR (%)',     `${signS}${m.cagr_5y.toFixed(1)}`],
    ['Year-5 op margin (%)',    (p.op_margin[p.op_margin.length - 1] * 100).toFixed(1)],
    ['WACC (%)',                (m.wacc * 100).toFixed(1)],
    ['Terminal growth (%)',     (p.term_g * 100).toFixed(1)],
    ['Anthropic stake ($B)',    (m.anthropic_stake ?? 0).toFixed(1)],
    ['Starting revenue ($B)',   p.rev_b.toFixed(2)],
    ['Scenario probability (%)', probPct],
  ];
}

function equityBuildRows(scn, dcfType) {
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
      rows.push(['− Net debt',   `$${p.net_debt.toFixed(2)}B`,     'normal']);
    }
    rows.push(
      ['= Equity value',         `$${p.total_equity.toFixed(2)}B`, 'subtotal'],
      ['FY30 shares (M)',        p.final_shares.toLocaleString(),  'normal'],
      ['= Expected per share',   `$${scn.expectedPerShare.toFixed(2)}`, 'total'],
    );
    return rows;
  }
  // mature_company_sotp
  const saLabel = scn.dcfMetrics.anthropic_stake != null ? '+ Anthropic stake' : '+ Special assets';
  const rowsS = [
    ['Operating EV',             `$${p.op_ev.toFixed(2)}B`,        'normal'],
    ['+ Cash & investments',     `$${p.cash.toFixed(2)}B`,         'normal'],
    [saLabel,                    `$${(p.special_assets || 0).toFixed(2)}B`, 'normal'],
  ];
  if ((p.net_debt || 0) > 0) {
    rowsS.push(['− Net debt',    `$${p.net_debt.toFixed(2)}B`,     'normal']);
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
    ? "NOT INVESTMENT ADVICE  ·  Not from a registered investment advisor  ·  AI-assisted analysis  ·  Author may hold positions  ·  See full disclaimers, page 5"
    : "NOT INVESTMENT ADVICE  ·  Not from a registered investment advisor  ·  AI-assisted analysis  ·  Author may hold positions";
  const footerStamp = `v${stamp.footerVersion} · ${stamp.footerTimestamp} · derived from ${stamp.canonicalJsx} (canonical)`;
  return (
    // Page bottom margin matches memo.py's MARGIN_B = 0.55in.
    // Background masks any column text that reaches into the footer band
    // (NAUT v002 has unusually long probability_rationale paragraphs).
    <div style={{
      position: 'absolute',
      left: '1in',
      right: '1in',
      bottom: '0.15in',
      background: PALETTE.paper,
      paddingTop: '4pt',
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
            Alameda Research 2: Electric Boogaloo (AR2EB)  ·  arthur@culang.co  ·  {pageLabel}
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
  const probStrip = (
    `Bear ${memo.scenarios.find(s => s.key === 'bear').prob}%     `
    + `Base ${memo.scenarios.find(s => s.key === 'base').prob}%     `
    + `Bull ${memo.scenarios.find(s => s.key === 'bull').prob}%     `
    + `Ultra Bull ${memo.scenarios.find(s => s.key === 'ultra').prob}%     ·     `
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

      {/* 4-column narrative grid */}
      <div style={{
        marginTop: '12pt',
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        columnGap: '16pt',
      }}>
        {memo.scenarios.map(scn => {
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
                  fontFamily: FONT_SANS, fontWeight: 600, fontSize: '11pt',
                  color: PALETTE.ink, letterSpacing: '0.02em',
                }}>
                  {scn.label}
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{
                    fontFamily: FONT_MONO, fontWeight: 700, fontSize: '18pt',
                    color: PALETTE.ink, lineHeight: 1.0,
                  }}>
                    ${scn.price.toFixed(2)}
                  </div>
                  <div style={{
                    marginTop: '4pt',
                    fontFamily: FONT_MONO, fontSize: '8.5pt', color: upColor,
                  }}>
                    {upSign}{upside.toFixed(1)}%  vs spot
                  </div>
                </div>
              </div>

              {/* Probability emphasized */}
              <div style={{
                marginTop: '10pt',
                fontFamily: FONT_MONO, fontSize: '8pt', color: PALETTE.accent,
              }}>
                Probability  {scn.prob}%
              </div>

              <div style={{ marginTop: '4pt' }}><Rule /></div>

              {/* Headline */}
              <div style={{
                marginTop: '8pt',
                fontFamily: FONT_SANS, fontWeight: 500, fontSize: '11pt',
                color: PALETTE.ink, lineHeight: 1.15,
              }}>
                {scn.headline}
              </div>

              {/* WHY x% */}
              <div style={{
                marginTop: '10pt',
                fontFamily: FONT_SANS, fontWeight: 600, fontSize: '7pt',
                color: PALETTE.muted, letterSpacing: '0.04em',
                textTransform: 'uppercase',
              }}>
                WHY {scn.prob}%
              </div>
              <div style={{
                marginTop: '3pt',
                fontFamily: FONT_SANS, fontSize: '6.75pt', color: PALETTE.text,
                lineHeight: 1.28,
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
                fontFamily: FONT_SANS, fontWeight: 600, fontSize: '7pt',
                color: PALETTE.muted, letterSpacing: '0.04em',
                textTransform: 'uppercase',
              }}>
                WHAT HAPPENS
              </div>
              {scn.what.map((para, pi) => (
                <div key={pi} style={{
                  marginTop: pi === 0 ? '3pt' : '4pt',
                  fontFamily: FONT_SANS, fontSize: '6.75pt', color: PALETTE.text,
                  lineHeight: 1.28,
                }}>
                  {para}
                </div>
              ))}
            </div>
          );
        })}
      </div>

      <PageFooter memo={memo} pageLabel="page 2 of 5" />
    </div>
  );
}

// ── Page 4 — Quantitative (show your work) ─────────────────────────────
function ScenarioQuantColumn({ memo, scenarioKey }) {
  const print = memo.print;
  const scn = print.scenarios[scenarioKey];
  const dcfType = print.dcfType;
  const n = print.dcfPeriodYears;
  const fyLabels = dcfYearLabels(dcfType, n);
  const rev = dcfRevenueDisplay(scn, dcfType, n);
  const margins = scn.dcfPath.op_margin;
  const fcf = scn.dcfPath.fcf;
  const pvFcf = scn.dcfPath.pv_fcf;
  const sumPv = scn.dcfPath.sum_pv_fcf;
  const pvTerm = scn.dcfPath.pv_terminal;
  const termG = scn.dcfPath.term_g;
  const waccTerm = scn.dcfPath.wacc_path[scn.dcfPath.wacc_path.length - 1];
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
  const SectionEyebrow = ({ children }) => (
    <div style={{ marginTop: '4pt', marginBottom: '4pt' }}>
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

      {/* DCF table */}
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
                            color: PALETTE.text, lineHeight: '9pt' }}>{fy}</div>
              <div style={{ ...cell, lineHeight: '9pt' }}>{rev[i].toFixed(2)}</div>
              <div style={{ ...cell, lineHeight: '9pt' }}>
                {marginSign}{(margins[i] * 100).toFixed(0)}%
              </div>
              <div style={{ ...cell, color: fcfColor, lineHeight: '9pt' }}>
                {fcfSign}{fcf[i].toFixed(2)}
              </div>
              <div style={{ ...cell, lineHeight: '9pt' }}>
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

      {/* Equity build */}
      <SectionEyebrow>EQUITY BUILD  ·  $B & per share</SectionEyebrow>
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

      {/* Future fair value */}
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
    </div>
  );
}

function Page4Quantitative({ memo }) {
  return (
    <div className="memo-page">
      <PageHeader memo={memo} suffix="show your work"
                  label="the quantitative" recapWeighted compact />

      {/* 4-column scenario quant grid — fills the page alone. Pushback +
          falsification triggers live on Page 5; we tried Page 4 per the
          spec but the quant content takes the full page. */}
      <div style={{
        marginTop: '8pt',
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        columnGap: '16pt',
      }}>
        {['bear', 'base', 'bull', 'ultra_bull'].map(k => (
          <ScenarioQuantColumn key={k} memo={memo} scenarioKey={k} />
        ))}
      </div>

      <PageFooter memo={memo} pageLabel="page 4 of 5" />
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
                     marginTop="14pt" />
      <ThreeColGrid
        items={appendix.pushback}
        rowGap="18pt"
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
      <SectionHeader label="FALSIFICATION TRIGGERS" />
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
      <SectionHeader label="DISCLAIMERS  ·  PLEASE READ BEFORE USING THIS DOCUMENT" />
      <ThreeColGrid
        items={disclaimers.map(renderDisclaimer)}
        rowGap="22pt"
        renderItem={(d) => (
          <div>
            <div style={{
              fontFamily: FONT_SANS,
              fontWeight: 600,
              fontSize: '9pt',
              color: PALETTE.ink,
              marginBottom: '4pt',
            }}>
              {d.h}
            </div>
            <div style={{
              fontFamily: FONT_SANS,
              fontSize: '8pt',
              color: PALETTE.text,
              lineHeight: 1.4,
            }}>
              {d.p}
            </div>
          </div>
        )}
      />

      {/* GLOSSARY */}
      <SectionHeader label="GLOSSARY  ·  CONCEPTS REFERENCED IN THE NARRATIVE" />
      <ThreeColGrid
        items={glossary}
        rowGap="10pt"
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

      <PageFooter memo={memo} pageLabel="page 5 of 5" showDisclaimerPointer={false} />
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
      <Page2Narratives memo={memo} />
      <Page4Quantitative memo={memo} />
      <Page5BackMatter memo={memo} />
    </>
  );
}

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
