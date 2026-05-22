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
    <div style={{
      position: 'absolute',
      left: '1in',
      right: '1in',
      bottom: '0.40in',
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

// ── Page 5 — Back matter (pushback, triggers, disclaimers, glossary) ──
function Page5BackMatter({ memo }) {
  const { appendix, glossary } = memo.print;
  const disclaimers = window.AR2EB_DATA.PDF_DISCLAIMERS;
  const bear = memo.scenarios.find(s => s.key === 'bear');
  const base = memo.scenarios.find(s => s.key === 'base');
  const bull = memo.scenarios.find(s => s.key === 'bull');

  // Substitute ${TICKER} in disclaimer body at render time.
  const renderDisclaimer = d => ({
    ...d,
    p: d.p.replace(/\$\{TICKER\}/g, `$${memo.ticker}`),
  });

  return (
    <div className="memo-page">
      {/* Header strip. Logo is 150pt wide (memo.py LOGO_W_P3). The text
          column starts 28pt to the right of the logo. The logo TOP sits
          22pt below the page-content top so the header has breathing room. */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '28pt',
                    paddingTop: '22pt' }}>
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
              {fmtDayMonthYear(memo.publishedISO)}  ·  the back matter
            </div>
          </div>
          <div style={{
            marginTop: '12pt',
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
              supporting analysis · disclaimers · glossary
            </div>
          </div>
          <div style={{
            marginTop: '8pt',
            textAlign: 'right',
            fontFamily: FONT_MONO,
            fontSize: '9pt',
            color: PALETTE.muted,
          }}>
            Bear  {fmtDollars(bear.price)}     Base  {fmtDollars(base.price)}     Bull  {fmtDollars(bull.price)}
          </div>
        </div>
      </div>

      <div style={{ marginTop: '14pt' }}>
        <Rule strong />
      </div>

      {/* PUSHBACK */}
      <SectionHeader label="PUSHBACK  ·  WHY THE BASE CASE IS TOO HARSH" marginTop="14pt" />
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

  return <Page5BackMatter memo={memo} />;
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
