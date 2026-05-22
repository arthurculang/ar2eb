/* AR2EB — PDF-only memo component (Phase 1 shell).
 *
 * This is intentionally minimal: a masthead-only page that proves the
 * Playwright + JSX + local-font pipeline produces a deterministic PDF.
 * Page 2-5 components will be ported here in Phase 2 (one page at a time,
 * each replacing its memo.py equivalent).
 *
 * Render harness: public/print.html?ticker=<slug>
 * Renderer:       scripts/render_memo_pdf.py
 */

function getTickerSlug() {
  const params = new URLSearchParams(location.search);
  return (params.get('ticker') || '').toLowerCase();
}

function findMemo(slug) {
  if (!window.AR2EB_DATA || !window.AR2EB_DATA.MEMOS) return null;
  return window.AR2EB_DATA.MEMOS.find(m => m.slug === slug) || null;
}

function Masthead({ memo }) {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'flex-start',
      borderBottom: '1px solid #18181b',
      paddingBottom: 12,
    }}>
      <div>
        <div style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 8,
          fontWeight: 400,
          letterSpacing: '0.16em',
          color: '#71717a',
          textTransform: 'uppercase',
          marginBottom: 6,
        }}>
          INTERNAL RESEARCH · MEMO · NOT INVESTMENT ADVICE · AI-ASSISTED
        </div>
        <div style={{
          fontFamily: 'Inter, sans-serif',
          fontSize: 28,
          fontWeight: 700,
          letterSpacing: '-0.01em',
          color: '#18181b',
          lineHeight: 1.0,
        }}>
          {memo.company} <span style={{ color: '#71717a', fontWeight: 500 }}>· ${memo.ticker}</span>
        </div>
        <div style={{
          fontFamily: 'Inter, sans-serif',
          fontSize: 10,
          fontWeight: 500,
          color: '#52525b',
          marginTop: 6,
        }}>
          {memo.exchange} : {memo.ticker} · {memo.dcfType}
        </div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <div style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 32,
          fontWeight: 700,
          color: '#18181b',
          lineHeight: 1.0,
        }}>
          ${memo.spot.price.toFixed(2)}
        </div>
        <div style={{
          fontFamily: 'Inter, sans-serif',
          fontSize: 9,
          color: '#71717a',
          marginTop: 4,
        }}>
          {memo.spot.asOf}
        </div>
        <div style={{
          fontFamily: 'Inter, sans-serif',
          fontSize: 9,
          color: '#52525b',
          marginTop: 6,
        }}>
          {memo.metrics.mktCap} mkt cap · {memo.metrics.shares} sh · {memo.metrics.cash}
        </div>
      </div>
    </div>
  );
}

function Page1Shell({ memo }) {
  return (
    <div className="memo-page">
      <Masthead memo={memo} />
      <div style={{
        marginTop: 36,
        fontFamily: 'Inter, sans-serif',
        fontSize: 14,
        color: '#52525b',
        fontStyle: 'italic',
      }}>
        Phase 1 shell · Playwright + JSX pipeline verified.
        Page bodies will be ported here in Phase 2 (Page 5 → 4 → 1 → 2 → 3).
      </div>
      <div style={{
        position: 'absolute',
        bottom: '0.55in',
        left: '1in',
        right: '1in',
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 7,
        color: '#a1a1aa',
        display: 'flex',
        justifyContent: 'space-between',
        borderTop: '0.5px solid #d4d4d8',
        paddingTop: 6,
      }}>
        <span>{memo.ticker} · {memo.publishedLabel}</span>
        <span>Page 1 of 5 (shell)</span>
      </div>
    </div>
  );
}

function MemoPDF() {
  const slug = getTickerSlug();
  const memo = findMemo(slug);

  if (!slug) return <div style={{ padding: 40, fontFamily: 'Inter' }}>
    Missing <code>?ticker=&lt;slug&gt;</code> query parameter.
  </div>;
  if (!memo) return <div style={{ padding: 40, fontFamily: 'Inter' }}>
    No memo found for ticker <code>{slug}</code>.
  </div>;

  return (
    <>
      <Page1Shell memo={memo} />
    </>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<MemoPDF />);

// Signal to the print renderer that React has mounted and fonts have loaded.
// scripts/render_memo_pdf.py waits for document.body.dataset.ready === '1'.
(async () => {
  if (document.fonts && document.fonts.ready) {
    await document.fonts.ready;
  }
  // Defer one frame so React commits before we flip the ready flag.
  requestAnimationFrame(() => {
    document.body.dataset.ready = '1';
  });
})();
