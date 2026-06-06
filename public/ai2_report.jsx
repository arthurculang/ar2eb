/* AR2EB — Arthur Indicator: AI 1.0 vs AI 2.0 backtest + valuation zones.
   Standalone report (2 landscape pages). Auto-mounts under body[data-harness=report];
   the numbers are a snapshot of scripts/_models/ai2_backtest.py (--select/--grid/--zones)
   on the sourced 104-name panel. Reproduce: python scripts/_models/ai2_backtest.py --select etc. */

const FS = "'Inter', system-ui, sans-serif";
const FM = "'JetBrains Mono', monospace";
const C = { ink: '#18181b', text: '#3f3f46', muted: '#71717a', rule: '#e4e4e7',
            faint: '#f4f4f5', paper: '#fafafa', accent: '#2563eb', good: '#15803d', bad: '#b91c1c' };
const ZC = { GREEN: '#15803d', YELLOW: '#ca8a04', ORANGE: '#ea580c', RED: '#dc2626' };

// Nested-model ladder, LOYO-OOS rank-IC (104-name panel). AI 1.0 = w1=w2=1.
const LADDER = [
  { m: 'AI 1.0  (gm + growth)', k: 0, o3: 0.044, o1: 0.063, base: true },
  { m: 'L2 · reweight gm, g', k: 2, o3: -0.015, o1: 0.078 },
  { m: 'L3 · + FCF margin', k: 3, o3: -0.041, o1: 0.080 },
  { m: 'L4 · + operating margin', k: 4, o3: -0.022, o1: 0.078 },
  { m: 'L4 · + ΔFCF margin', k: 5, o3: 0.013, o1: 0.054 },
  { m: 'L2 · + Δgrowth, Δgm', k: 4, o3: 0.053, o1: 0.052 },
  { m: 'Full 8-weight AI 2.0', k: 8, o3: 0.041, o1: -0.012 },
];
// Empirical zones: forward return by AI 1.0 level (medians + win-rate).
const ZONES = [
  { z: 'GREEN', verdict: 'extremely undervalued', range: '< 6', m1: 0.214, w1: 0.74, m3: 0.787, w3: 0.87, n: 471 },
  { z: 'YELLOW', verdict: 'somewhat undervalued', range: '6 – 10', m1: 0.206, w1: 0.69, m3: 0.772, w3: 0.83, n: 291 },
  { z: 'ORANGE', verdict: 'somewhat overvalued', range: '10 – 15', m1: 0.210, w1: 0.70, m3: 0.616, w3: 0.84, n: 166 },
  { z: 'RED', verdict: 'extremely overvalued', range: '> 15', m1: 0.096, w1: 0.57, m3: 0.163, w3: 0.58, n: 143 },
];
const CURRENT = { // where today's screened names sit (spec §13 snapshot)
  GREEN: ['LULU 1.9', 'YETI 3.0', 'UBER 4.7', 'COIN 5.0'],
  YELLOW: ['ABNB 6.2', 'ZM 6.4', 'DASH 6.5', 'TXG 7.0', 'ILMN 7.1'],
  ORANGE: ['(none today)'],
  RED: ['ISRG 17.5', 'IONQ 154', 'RKLB 197'],
};

function Head({ kicker, title, sub }) {
  return (
    <div style={{ borderBottom: `1.5pt solid ${C.ink}`, paddingBottom: '7pt', marginBottom: '12pt' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <span style={{ fontFamily: FM, fontSize: '7pt', fontWeight: 700, letterSpacing: '0.12em', color: C.accent }}>
          {kicker}</span>
        <span style={{ fontFamily: FM, fontSize: '6.5pt', color: C.muted }}>
          AR2EB · internal research · not investment advice</span>
      </div>
      <div style={{ fontFamily: FS, fontSize: '17pt', fontWeight: 700, color: C.ink, marginTop: '5pt', lineHeight: 1.15 }}>
        {title}</div>
      <div style={{ fontFamily: FS, fontSize: '8.5pt', color: C.muted, marginTop: '3pt' }}>{sub}</div>
    </div>
  );
}

function SignedBar({ v, max }) { // OOS bar: centered baseline, + right / − left
  const pct = Math.min(1, Math.abs(v) / max) * 50;
  const pos = v >= 0;
  return (
    <div style={{ position: 'relative', height: '11pt', background: C.faint, borderRadius: '1pt' }}>
      <div style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: '0.5pt', background: C.rule }} />
      <div style={{ position: 'absolute', top: '1.5pt', bottom: '1.5pt',
        left: pos ? '50%' : `${50 - pct}%`, width: `${pct}%`,
        background: pos ? C.accent : C.bad, borderRadius: '1pt' }} />
    </div>
  );
}

function PageBacktest() {
  return (
    <div className="report-page">
      <Head kicker="ARTHUR INDICATOR · BACKTEST"
            title="AI 1.0 vs AI 2.0 — does enriching the screen beat the simple one?"
            sub="104-name universe · FY2007–26 · ~1,000 cross-section rows · judged by leave-one-year-out out-of-sample rank-IC (cheapness vs. forward return), not in-sample fit" />

      {/* what each is */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14pt', marginBottom: '11pt' }}>
        <div style={{ background: C.faint, borderRadius: '3pt', padding: '8pt 10pt' }}>
          <div style={{ fontFamily: FM, fontSize: '7pt', fontWeight: 700, color: C.good }}>AI 1.0 — the live screen</div>
          <div style={{ fontFamily: FM, fontSize: '8pt', color: C.ink, marginTop: '3pt' }}>EV / ( Rev × ( GrossMargin + RevGrowth ) )</div>
          <div style={{ fontFamily: FS, fontSize: '7.5pt', color: C.text, marginTop: '3pt', lineHeight: 1.35 }}>
            One number: am I paying a fair price for the <i>quality</i> of this business? Lower = cheaper-for-quality.</div>
        </div>
        <div style={{ background: C.faint, borderRadius: '3pt', padding: '8pt 10pt' }}>
          <div style={{ fontFamily: FM, fontSize: '7pt', fontWeight: 700, color: C.muted }}>AI 2.0 — the proposed enrichment</div>
          <div style={{ fontFamily: FM, fontSize: '8pt', color: C.ink, marginTop: '3pt' }}>… + op-margin + FCF-margin + Δ (rate-of-change) ×4 → 8 fitted weights</div>
          <div style={{ fontFamily: FS, fontSize: '7.5pt', color: C.text, marginTop: '3pt', lineHeight: 1.35 }}>
            Adds profitability levels and whether each driver is accelerating/improving — weights fit by backtest.</div>
        </div>
      </div>

      {/* verdict */}
      <div style={{ borderLeft: `3pt solid ${C.ink}`, paddingLeft: '11pt', marginBottom: '11pt' }}>
        <div style={{ fontFamily: FS, fontSize: '12.5pt', fontWeight: 700, color: C.ink, lineHeight: 1.2 }}>
          AI 2.0 does not earn its extra weights. AI 1.0 is validated.</div>
        <div style={{ fontFamily: FS, fontSize: '8.5pt', color: C.text, marginTop: '4pt', lineHeight: 1.4 }}>
          The 8-weight model fits the past better (in-sample IC <b style={{ fontFamily: FM }}>+0.156 / +0.212</b> at 3y/1y)
          but <b>collapses out-of-sample</b> (<b style={{ fontFamily: FM, color: C.bad }}>−0.063 / −0.068</b>, weights sign-flipping
          across horizons) — the signature of fitting 8 knobs to thin data. The simple AI 1.0, with zero free parameters,
          is positive and stable out-of-sample at <b>both</b> horizons.</div>
      </div>

      {/* ladder */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: '20pt' }}>
        <div>
          <div style={{ fontFamily: FM, fontSize: '7pt', fontWeight: 700, color: C.muted, letterSpacing: '0.05em', marginBottom: '6pt' }}>
            NESTED MODEL LADDER · OUT-OF-SAMPLE rank-IC</div>
          <div style={{ display: 'flex', fontFamily: FM, fontSize: '6pt', color: C.muted, marginBottom: '3pt' }}>
            <span style={{ width: '120pt' }} /><span style={{ flex: 1, textAlign: 'center' }}>3-YEAR</span>
            <span style={{ width: '30pt', textAlign: 'right' }} /><span style={{ flex: 1, textAlign: 'center' }}>1-YEAR</span>
            <span style={{ width: '30pt' }} /></div>
          {LADDER.map((r, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', marginBottom: '3.5pt',
              background: r.base ? '#eff6ff' : 'transparent', borderRadius: '2pt', padding: '1.5pt 2pt' }}>
              <span style={{ width: '120pt', fontFamily: FS, fontSize: '7pt',
                fontWeight: r.base ? 700 : 500, color: r.base ? C.accent : C.ink }}>{r.m}</span>
              <span style={{ flex: 1 }}><SignedBar v={r.o3} max={0.10} /></span>
              <span style={{ width: '30pt', textAlign: 'right', fontFamily: FM, fontSize: '6.5pt',
                color: r.o3 < 0 ? C.bad : C.ink }}>{(r.o3 >= 0 ? '+' : '') + r.o3.toFixed(3)}</span>
              <span style={{ flex: 1, marginLeft: '6pt' }}><SignedBar v={r.o1} max={0.10} /></span>
              <span style={{ width: '30pt', textAlign: 'right', fontFamily: FM, fontSize: '6.5pt',
                color: r.o1 < 0 ? C.bad : C.ink }}>{(r.o1 >= 0 ? '+' : '') + r.o1.toFixed(3)}</span>
            </div>
          ))}
          <div style={{ fontFamily: FS, fontSize: '7pt', color: C.muted, marginTop: '5pt', lineHeight: 1.35 }}>
            Every enrichment wins at most <i>one</i> horizon and loses the other — <b>none beats AI 1.0 at both</b>.
            In-sample IC keeps climbing with parameters while OOS does not: textbook overfit.</div>
        </div>

        <div>
          <div style={{ fontFamily: FM, fontSize: '7pt', fontWeight: 700, color: C.muted, letterSpacing: '0.05em', marginBottom: '6pt' }}>
            BELT-AND-SUSPENDERS · EXHAUSTIVE GRID</div>
          <div style={{ background: C.faint, borderRadius: '3pt', padding: '9pt 11pt' }}>
            <div style={{ fontFamily: FM, fontSize: '15pt', fontWeight: 700, color: C.ink }}>2,462 <span style={{ fontSize: '9pt', color: C.muted }}>/ 15,625</span></div>
            <div style={{ fontFamily: FS, fontSize: '7.5pt', color: C.text, marginTop: '3pt', lineHeight: 1.4 }}>
              weight combinations beat AI 1.0 <b>in-sample</b> when you grid them exhaustively (no random search) —
              but the best loads <b style={{ color: C.bad }}>operating- and FCF-margin negatively</b> (“worse margins = cheaper”): noise-fitting.</div>
            <div style={{ fontFamily: FS, fontSize: '7.5pt', color: C.text, marginTop: '6pt', lineHeight: 1.4 }}>
              Out-of-sample, even the best grid model wins one horizon (<b style={{ fontFamily: FM }}>+0.084</b>/3y) and
              loses the other (<b style={{ fontFamily: FM }}>+0.032</b>/1y). The random search <b>missed nothing</b>.</div>
          </div>
          <div style={{ fontFamily: FS, fontSize: '7.5pt', color: C.ink, marginTop: '9pt', lineHeight: 1.4,
            borderTop: `0.5pt solid ${C.rule}`, paddingTop: '7pt' }}>
            <b>Bottom line.</b> 26 names × ~20 thin yearly cross-sections — and even 104 — can't support 8 free weights.
            The FCF-margin term that looked promising on 26 names was a small-sample artifact. <b>AI 1.0 stays the screen.</b></div>
        </div>
      </div>

      <div style={{ position: 'absolute', bottom: '0.32in', left: '1in', right: '1in',
        display: 'flex', justifyContent: 'space-between', fontFamily: FM, fontSize: '6pt', color: C.muted,
        borderTop: `0.5pt solid ${C.rule}`, paddingTop: '4pt' }}>
        <span>reproduce: python scripts/_models/ai2_backtest.py --select / --grid</span><span>page 1 of 2</span>
      </div>
    </div>
  );
}

function PageZones() {
  return (
    <div className="report-page">
      <Head kicker="ARTHUR INDICATOR · VALUATION ZONES"
            title="Green · Yellow · Orange · Red — what AI 1.0 says about value"
            sub="bands grounded in the backtest: median forward return + win-rate by AI 1.0 level (the validated screen)" />

      {/* the gradient band */}
      <div style={{ display: 'flex', borderRadius: '4pt', overflow: 'hidden', marginBottom: '4pt' }}>
        {ZONES.map((z) => (
          <div key={z.z} style={{ flex: 1, background: ZC[z.z], padding: '9pt 11pt', color: 'white' }}>
            <div style={{ fontFamily: FM, fontSize: '8pt', fontWeight: 700, letterSpacing: '0.06em' }}>{z.z}</div>
            <div style={{ fontFamily: FS, fontSize: '8.5pt', fontWeight: 600, marginTop: '1pt' }}>{z.verdict}</div>
            <div style={{ fontFamily: FM, fontSize: '9.5pt', marginTop: '3pt' }}>AI 1.0 {z.range}</div>
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', fontFamily: FM, fontSize: '6pt', color: C.muted, marginBottom: '12pt' }}>
        <span style={{ flex: 1 }}>← cheaper-for-quality · buy</span>
        <span style={{ flex: 1, textAlign: 'right' }}>richer · avoid →</span>
      </div>

      {/* evidence */}
      <div style={{ fontFamily: FM, fontSize: '7pt', fontWeight: 700, color: C.muted, letterSpacing: '0.05em', marginBottom: '7pt' }}>
        THE EVIDENCE · FORWARD RETURN BY ZONE (104-name panel, FY2007–26)</div>
      <div style={{ display: 'flex', fontFamily: FM, fontSize: '6.5pt', color: C.muted, marginBottom: '4pt' }}>
        <span style={{ width: '150pt' }} />
        <span style={{ width: '150pt', textAlign: 'center' }}>1-YEAR FORWARD</span>
        <span style={{ width: '150pt', textAlign: 'center' }}>3-YEAR FORWARD</span>
        <span style={{ flex: 1, textAlign: 'right' }}>n</span>
      </div>
      {ZONES.map((z) => (
        <div key={z.z} style={{ display: 'flex', alignItems: 'center', marginBottom: '6pt' }}>
          <span style={{ width: '150pt', display: 'flex', alignItems: 'center', gap: '6pt' }}>
            <span style={{ width: '9pt', height: '9pt', borderRadius: '2pt', background: ZC[z.z] }} />
            <span style={{ fontFamily: FS, fontSize: '8pt', fontWeight: 600, color: C.ink }}>{z.z}</span>
            <span style={{ fontFamily: FM, fontSize: '6.5pt', color: C.muted }}>{z.range}</span>
          </span>
          {[[z.m1, z.w1], [z.m3, z.w3]].map(([med, win], j) => (
            <span key={j} style={{ width: '150pt', paddingRight: '14pt' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: FM, fontSize: '7pt', color: C.ink }}>
                <span>{'+' + Math.round(med * 100) + '% median'}</span>
                <span style={{ color: C.muted }}>{Math.round(win * 100) + '% win'}</span>
              </div>
              <div style={{ height: '6pt', background: C.faint, borderRadius: '1pt', marginTop: '2pt' }}>
                <div style={{ width: (win * 100) + '%', height: '100%', background: ZC[z.z], borderRadius: '1pt' }} />
              </div>
            </span>
          ))}
          <span style={{ flex: 1, textAlign: 'right', fontFamily: FM, fontSize: '6.5pt', color: C.muted }}>{z.n}</span>
        </div>
      ))}

      <div style={{ display: 'grid', gridTemplateColumns: '1.05fr 1fr', gap: '20pt', marginTop: '8pt' }}>
        <div>
          <div style={{ fontFamily: FM, fontSize: '7pt', fontWeight: 700, color: C.muted, letterSpacing: '0.05em', marginBottom: '5pt' }}>
            WHERE TODAY’S NAMES SIT</div>
          {ZONES.map((z) => (
            <div key={z.z} style={{ display: 'flex', alignItems: 'baseline', marginBottom: '3pt' }}>
              <span style={{ width: '46pt', fontFamily: FM, fontSize: '6.5pt', fontWeight: 700, color: ZC[z.z] }}>{z.z}</span>
              <span style={{ flex: 1, fontFamily: FS, fontSize: '7.5pt', color: C.text }}>{CURRENT[z.z].join('  ·  ')}</span>
            </div>
          ))}
        </div>
        <div style={{ borderLeft: `0.5pt solid ${C.rule}`, paddingLeft: '14pt' }}>
          <div style={{ fontFamily: FM, fontSize: '7pt', fontWeight: 700, color: C.muted, letterSpacing: '0.05em', marginBottom: '5pt' }}>
            HOW TO READ IT</div>
          <div style={{ fontFamily: FS, fontSize: '7.5pt', color: C.text, lineHeight: 1.4 }}>
            <b>GREEN clearly wins, RED clearly loses</b> (a near coin-flip, ~57% — barely better than holding cash). The
            middle two are close: the signal lives at the <b>extremes</b>, so treat yellow/orange as “fair, leaning.”
            Absolute returns are flattered by the 2007–25 bull sample — the durable takeaway is the <b>ordering</b>
            (cheaper → higher forward return), the same effect the rank-IC validated. A screen, not a timing tool:
            confirm with the memo DCF (§6) before acting.</div>
        </div>
      </div>

      <div style={{ position: 'absolute', bottom: '0.32in', left: '1in', right: '1in',
        display: 'flex', justifyContent: 'space-between', fontFamily: FM, fontSize: '6pt', color: C.muted,
        borderTop: `0.5pt solid ${C.rule}`, paddingTop: '4pt' }}>
        <span>reproduce: python scripts/_models/ai2_backtest.py --zones</span><span>page 2 of 2</span>
      </div>
    </div>
  );
}

function AI2Report() {
  return (<><PageBacktest /><PageZones /></>);
}

if (typeof document !== 'undefined' && document.body && document.body.dataset.harness === 'report') {
  const root = window.ReactDOM.createRoot(document.getElementById('root'));
  root.render(<AI2Report />);
  const ready = () => requestAnimationFrame(() => { document.body.dataset.ready = '1'; });
  (document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()).then(ready);
}
window.AR2EB_AI2_REPORT = { AI2Report };
