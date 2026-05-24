/* AR2EB — page components */

// Resolve shared lib + data lazily inside components so script load order doesn't bite us.
const L = () => window.AR2EB_LIB;
const D = () => window.AR2EB_DATA;

// ---------- HOME ----------
function HomePage() {
  const { Link } = L();
  const { MEMOS, CATEGORIES } = D();
  const recent = [...MEMOS].sort((a, b) => b.publishedISO.localeCompare(a.publishedISO)).slice(0, 4);
  const countsByCat = MEMOS.reduce((m, x) => { m[x.category] = (m[x.category] || 0) + 1; return m; }, {});

  return (
    <>
      <section className="hero" data-screen-label="Home hero">
        <div className="wrap">
          <img src="assets/logo-full.svg" alt="Alameda Research 2: Electric Boogaloo — Long horizons. Structural shifts. Imagination." className="hero-logo" />
          <h1 className="hero-tagline">Long horizons. Structural shifts. Imagination.</h1>
          <p className="hero-sub">Probability-weighted DCF research on individual equities. Asymmetric bets and free-cash-flow compounders.</p>
        </div>
      </section>

      <section className="cat-section">
        <div className="wrap">
          <div className="cat-grid">
            {Object.values(CATEGORIES).map(cat => (
              <Link to={'/' + cat.slug} className="cat-card" key={cat.slug}>
                <div className="cat-eyebrow">
                  <span className="eyebrow">Category</span>
                  <span className="badge-count">{countsByCat[cat.slug] || 0} {countsByCat[cat.slug] === 1 ? 'memo' : 'memos'}</span>
                </div>
                <h2>{cat.name}</h2>
                <div className="cat-sub">{cat.sub}</div>
                <p className="cat-desc">{cat.long}</p>
                <span className="cat-go">
                  Browse memos
                  <span className="arrow" aria-hidden="true">→</span>
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="recent">
        <div className="wrap">
          <h3>Recent memos</h3>
          <div className="recent-list" role="list">
            {recent.map(m => (
              <Link to={'/memo/' + m.slug} className="recent-row" key={m.slug} role="listitem">
                <span className="ticker">{m.exchange}: {m.ticker}</span>
                <span className="title">{m.company}</span>
                <span className="head">{m.scenarios.find(s => s.key === 'base').headline}</span>
                <span className="date">{m.publishedLabel}</span>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}

// ---------- CATEGORY INDEX ----------
function CategoryPage({ slug }) {
  const { Link, TickerBadge, PricingBlock } = L();
  const { MEMOS, CATEGORIES } = D();
  const cat = CATEGORIES[slug];
  const [sort, setSort] = React.useState('newest');
  const memos = React.useMemo(() => {
    const list = MEMOS.filter(m => m.category === slug);
    return [...list].sort((a, b) => {
      const cmp = a.publishedISO.localeCompare(b.publishedISO);
      return sort === 'newest' ? -cmp : cmp;
    });
  }, [slug, sort]);

  if (!cat) return <NotFoundPage />;

  return (
    <>
      <section className="cat-header" data-screen-label={'Category — ' + cat.name}>
        <div className="wrap">
          <div className="eyebrow" style={{ marginBottom: 18 }}>Category</div>
          <h1>{cat.name}</h1>
          <p>{cat.long}</p>
        </div>
      </section>

      <section className="wrap">
        <div className="cat-controls">
          <span>{memos.length} {memos.length === 1 ? 'memo' : 'memos'}</span>
          <label className="sort">
            <span style={{ color: 'var(--muted-2)' }}>Sort</span>
            <select
              value={sort}
              onChange={e => setSort(e.target.value)}
              style={{
                background: 'transparent',
                border: 'none',
                font: 'inherit',
                color: 'var(--ink-2)',
                cursor: 'pointer',
              }}
            >
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
            </select>
          </label>
        </div>

        <div className="memo-list">
          {memos.map(m => (
            <Link to={'/memo/' + m.slug} className="memo-card" key={m.slug}>
              <TickerBadge ticker={m.ticker} />
              <div>
                <div className="name">{m.company} <span className="ex">{m.exchange}: {m.ticker}</span></div>
                <div className="dcf">{m.dcfType}</div>
                <div className="q">{m.question}</div>
              </div>
              <PricingBlock memo={m} />
            </Link>
          ))}
        </div>
      </section>
    </>
  );
}

// ---------- MEMO DETAIL ----------
// EmbeddedMemo — renders the full 5-page JSX memo (same components the
// Playwright print harness uses) at native 14"×8.5" size, scaled down to
// fit whatever container it lives in. ResizeObserver keeps it responsive.
function EmbeddedMemo({ memo }) {
  const { Page1Headline, Page2Narratives, Page3Snapshot,
          Page4Quantitative, Page5BackMatter } = window.AR2EB_MEMO || {};
  const containerRef = React.useRef(null);
  const [scale, setScale] = React.useState(1);
  const NATIVE_W = 14 * 96; // 14 inches at 96 dpi = 1344px

  React.useEffect(() => {
    const update = () => {
      if (!containerRef.current) return;
      const w = containerRef.current.clientWidth;
      setScale(Math.min(1, w / NATIVE_W));
    };
    update();
    const ro = new ResizeObserver(update);
    if (containerRef.current) ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  if (!Page1Headline) return <p>Memo viewer not loaded — refresh required.</p>;

  return (
    <div className="memo-embed-wrap" ref={containerRef}>
      <div className="memo-embed-inner" style={{
        transform: `scale(${scale})`,
        transformOrigin: 'top left',
        width: NATIVE_W + 'px',
      }}>
        <Page1Headline memo={memo} />
        <Page2Narratives memo={memo} />
        <Page3Snapshot memo={memo} />
        <Page4Quantitative memo={memo} />
        <Page5BackMatter memo={memo} />
      </div>
    </div>
  );
}

function MemoPage({ slug }) {
  const { fmtUSD } = L();
  const { MEMOS, DISCLAIMER_BLOCKS } = D();
  const memo = MEMOS.find(m => m.slug === slug);
  if (!memo) return <NotFoundPage />;

  return (
    <>
      <section className="memo-head" data-screen-label={'Memo — ' + memo.ticker}>
        <div className="wrap">
          <div className="eyebrow">
            Internal Research · Memo · Not Investment Advice · AI-Assisted
          </div>
          <div className="row1">
            <div>
              <h1>{memo.company}</h1>
              <div className="meta">
                <span className="mono"><b>{memo.exchange}: {memo.ticker}</b></span>
                <span className="dot">·</span>
                <span>{memo.dcfType}</span>
                <span className="dot">·</span>
                <span>Mkt cap <b>{memo.metrics.mktCap}</b></span>
                <span className="dot">·</span>
                <span>{memo.metrics.shares} sh</span>
                <span className="dot">·</span>
                <span>{memo.metrics.cash}</span>
              </div>
            </div>
            <div className="spot">
              <div className="label">Spot</div>
              <div className="price">{fmtUSD(memo.spot.price)}</div>
              <div className="as-of">{memo.spot.asOf}</div>
            </div>
          </div>
        </div>
      </section>

      <section className="pdf-cta-wrap">
        <div className="wrap">
          <a href={'memos/' + memo.pdf.file} className="pdf-cta" target="_blank" rel="noopener noreferrer">
            <div className="left">
              <div className="ttl">Download as PDF</div>
              <div className="meta">{memo.pdf.file} · {memo.pdf.size}</div>
            </div>
            <div className="right">
              <span>Download</span>
              <span aria-hidden="true">↓</span>
            </div>
          </a>
        </div>
      </section>

      <section className="memo-embed-section">
        <div className="wrap">
          <EmbeddedMemo memo={memo} />
        </div>
      </section>

      <section className="disclaim">
        <div className="wrap">
          {DISCLAIMER_BLOCKS.map((b, i) => (
            <div key={i}>
              <h6>{b.h}</h6>
              <p>{b.p}</p>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

// ---------- DISCLAIMERS ----------
function DisclaimersPage() {
  const { DISCLAIMER_BLOCKS } = D();
  return (
    <section className="disclaimers-page" data-screen-label="Disclaimers">
      <div className="wrap">
        <div className="eyebrow" style={{ marginBottom: 18 }}>Legal</div>
        <h1>Disclaimers</h1>
        <p className="lead">
          AR2EB publishes individual-equity research for educational purposes. The site is not affiliated with any registered advisor, fund, or broker-dealer. Please read carefully before relying on anything you see here.
        </p>
        {DISCLAIMER_BLOCKS.map((b, i) => (
          <section key={i}>
            <h3>{b.h}</h3>
            <p>{b.p}</p>
          </section>
        ))}
      </div>
    </section>
  );
}

// ---------- ABOUT ----------
function AboutPage() {
  return (
    <section className="about-page" data-screen-label="About">
      <div className="wrap-narrow">
        <div className="eyebrow" style={{ marginBottom: 18 }}>About the operation</div>
        <h1>One operator. Concentrated conviction. The work, in public.</h1>

        <p>
          AR2EB — Alameda Research 2: Electric Boogaloo — is the public-facing publication of a single-operator family-office portfolio. The thesis is concentration: a small number of single-name positions, each backed by a probability-weighted DCF that gets pressure-tested in the open rather than sitting in a private folder.
        </p>

        <h3>Who</h3>
        <p>An individual investor running a family-office portfolio with a concentrated, single-name conviction approach. No external capital, no fund vehicle, no benchmark to chase.</p>

        <h3>What</h3>
        <p>Publishing the same probability-weighted DCF research used internally — so the work gets read, critiqued, and improved by a smarter readership than the four walls of a private doc.</p>

        <h3>Method</h3>
        <p>Probability-weighted DCFs with explicit scenarios — Bear, Base, Bull, and an Ultra Bull conditional tail. Damodaran young-company framework where the company is pre-revenue or pre-profitability; mature-company 5-year explicit DCFs with SOTP framing where significant non-operating value is present.</p>

        <h3>Cadence</h3>
        <p>Irregular. Research is published when conviction crystallizes, not on a schedule. Expect long quiet stretches punctuated by a memo or two.</p>

        <div className="kv">
          <div className="k">Contact</div>
          <div className="v"><a href="mailto:arthur@culang.co">arthur@culang.co</a></div>
          <div className="k">Format</div>
          <div className="v">Memo (PDF), summarized on-site</div>
          <div className="k">Coverage</div>
          <div className="v">Single-name US equities, opportunistic</div>
          <div className="k">Affiliation</div>
          <div className="v">None — individual, not a registered investment advisor</div>
        </div>
      </div>
    </section>
  );
}

// ---------- NOT FOUND ----------
function NotFoundPage() {
  const { Link } = L();
  return (
    <section style={{ padding: '160px 0 200px' }}>
      <div className="wrap">
        <div className="eyebrow" style={{ marginBottom: 12 }}>404</div>
        <h1>Page not found.</h1>
        <p style={{ color: 'var(--muted)', marginTop: 16, fontSize: 17 }}>
          The URL <span className="mono" style={{ color: 'var(--ink-2)' }}>{location.hash}</span> doesn't match a known page.
        </p>
        <p style={{ marginTop: 24 }}>
          <Link to="/" style={{ color: 'var(--accent-ink)', borderBottom: '1px solid var(--accent-ink)' }}>← Back to home</Link>
        </p>
      </div>
    </section>
  );
}

// ────────────────────────────────────────────────────────────────────
// PORTFOLIO — cross-asset weighting per spec §12.
//
// computePortfolio implements the methodology straight from the spec:
//   1. Hurdle: weighted_expected > spot × (1 + hurdle)
//   2. Conviction: P_pos = Σ {scn.prob : scn.price > spot}
//   3. Score:    upside_pct × √P_pos
//   4. Raw w:    score / Σ score
//   5. Cap:      iterate — if any w > MAX_POSITION, clamp it and
//                redistribute the excess proportionally to uncapped
//                names. Repeat until stable. Residual = cash.
//
// Pure function; deterministic given memos + opts. Sliders re-call it.
// ────────────────────────────────────────────────────────────────────
function computePortfolio(memos, opts = {}) {
  const { maxPosition = 0.40, hurdleFrac = 0 } = opts;

  const rows = memos.map(m => {
    const spot = m.spot.price;
    const expected = m.expected.fair;
    const upsidePct = m.expected.deltaPct;
    const passesHurdle = upsidePct > hurdleFrac * 100;
    // P_pos: scenario probabilities where expected price > spot.
    const pPos = m.scenarios
      .filter(s => s.price > spot)
      .reduce((acc, s) => acc + s.prob / 100, 0);
    const score = passesHurdle ? upsidePct * Math.sqrt(pPos) : 0;
    return {
      ticker: m.ticker, slug: m.slug, company: m.company,
      spot, expected, upsidePct, pPos, score,
      passesHurdle, rawWeight: 0, weight: 0,
    };
  });

  // Raw normalize.
  const totalScore = rows.reduce((a, r) => a + r.score, 0);
  if (totalScore > 0) {
    rows.forEach(r => { r.rawWeight = r.score / totalScore; });
  }

  // Iterative cap with proportional redistribution.
  let weights = rows.map(r => r.rawWeight);
  const capped = rows.map(() => false);
  for (let iter = 0; iter < 20; iter++) {
    let excess = 0;
    weights.forEach((w, i) => {
      if (!capped[i] && w > maxPosition) {
        excess += w - maxPosition;
        weights[i] = maxPosition;
        capped[i] = true;
      }
    });
    if (excess < 1e-9) break;
    const uncappedTotal = weights.reduce(
      (a, w, i) => a + (capped[i] ? 0 : w), 0
    );
    if (uncappedTotal < 1e-9) break;  // all capped; excess → cash
    weights = weights.map(
      (w, i) => capped[i] ? w : w * (1 + excess / uncappedTotal)
    );
  }
  rows.forEach((r, i) => { r.weight = weights[i]; });

  const totalDeployed = rows.reduce((a, r) => a + r.weight, 0);
  const cashWeight = Math.max(0, 1 - totalDeployed);

  // Weighted-avg portfolio upside (longs only, by capped weight)
  const portfolioUpside = totalDeployed > 0
    ? rows.reduce((a, r) => a + r.weight * r.upsidePct, 0) / totalDeployed
    : 0;

  return { rows, cashWeight, portfolioUpside, totalScore };
}

// Renders three buttons that copy the current portfolio state to the
// clipboard in different formats: JSON (machine-readable, full math),
// CSV (spreadsheet-pasteable), and a deep-link URL (shareable).
function PortfolioExport({ portfolio, maxPosition, hurdleFrac }) {
  const [flash, setFlash] = React.useState(null);
  const showFlash = (msg) => {
    setFlash(msg);
    setTimeout(() => setFlash(null), 1600);
  };

  const buildJson = () => JSON.stringify({
    computed_at: new Date().toISOString(),
    settings: { max_position: maxPosition, hurdle: hurdleFrac },
    summary: {
      portfolio_weighted_upside_pct: portfolio.portfolioUpside,
      names_allocated: portfolio.rows.filter(r => r.weight > 0).length,
      names_passed_hurdle: portfolio.rows.filter(r => r.passesHurdle).length,
      cash_weight: portfolio.cashWeight,
    },
    rows: portfolio.rows.map(r => ({
      ticker: r.ticker, spot: r.spot, expected: r.expected,
      upside_pct: r.upsidePct, p_pos: r.pPos, score: r.score,
      raw_weight: r.rawWeight, weight: r.weight,
      passes_hurdle: r.passesHurdle,
    })),
  }, null, 2);

  const buildCsv = () => {
    const header = 'ticker,spot,expected,upside_pct,p_pos,score,raw_weight,weight';
    const lines = portfolio.rows.map(r => [
      r.ticker,
      r.spot.toFixed(2),
      r.expected.toFixed(2),
      r.upsidePct.toFixed(2),
      r.pPos.toFixed(4),
      r.score.toFixed(2),
      r.rawWeight.toFixed(4),
      r.weight.toFixed(4),
    ].join(','));
    if (portfolio.cashWeight > 0.001) {
      lines.push(`cash,,,,,,,${portfolio.cashWeight.toFixed(4)}`);
    }
    return header + '\n' + lines.join('\n') + '\n';
  };

  const buildUrl = () => {
    const params = new URLSearchParams();
    if (Math.abs(maxPosition - 0.40) > 1e-6) params.set('cap', maxPosition.toFixed(2));
    if (hurdleFrac > 1e-6) params.set('hurdle', hurdleFrac.toFixed(2));
    const qs = params.toString();
    return location.origin + '/#/portfolio' + (qs ? '?' + qs : '');
  };

  const copy = (text, label) => {
    if (!navigator.clipboard) {
      // Older-browser fallback. Cloudflare Pages is HTTPS so clipboard
      // should work, but include the fallback for paranoia.
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); } catch (e) { /* swallow */ }
      document.body.removeChild(ta);
      showFlash(label + ' copied');
      return;
    }
    navigator.clipboard.writeText(text).then(
      () => showFlash(label + ' copied'),
      () => showFlash('Copy failed — your browser may block clipboard access')
    );
  };

  return (
    <section className="portfolio-export">
      <div className="wrap">
        <div className="export-row">
          <span className="export-label">Export this view</span>
          <button onClick={() => copy(buildJson(), 'JSON')}>Copy JSON</button>
          <button onClick={() => copy(buildCsv(), 'CSV')}>Copy CSV</button>
          <button onClick={() => copy(buildUrl(), 'URL')}>Copy URL</button>
          {flash && <span className="export-flash">{flash}</span>}
        </div>
      </div>
    </section>
  );
}

function PortfolioPage() {
  const { fmtUSD, fmtPct } = L();
  const { MEMOS } = D();

  // URL state — read initial values from the hash query (`#/portfolio?cap=0.6&hurdle=0.05`).
  // Lets a particular allocation be bookmarked or shared.
  const initial = React.useMemo(() => {
    const hash = location.hash || '#/portfolio';
    const q = hash.indexOf('?');
    if (q < 0) return { maxPosition: 0.40, hurdleFrac: 0 };
    const params = new URLSearchParams(hash.slice(q + 1));
    const cap = parseFloat(params.get('cap'));
    const hurdle = parseFloat(params.get('hurdle'));
    return {
      maxPosition: isFinite(cap) ? Math.max(0.10, Math.min(1.0, cap)) : 0.40,
      hurdleFrac:  isFinite(hurdle) ? Math.max(0, Math.min(0.20, hurdle)) : 0,
    };
  }, []);

  const [maxPosition, setMaxPosition] = React.useState(initial.maxPosition);
  const [hurdleFrac, setHurdleFrac] = React.useState(initial.hurdleFrac);

  // Persist slider state to URL without triggering navigation. Only encode
  // non-default values so a clean #/portfolio remains a clean shareable.
  React.useEffect(() => {
    const params = new URLSearchParams();
    if (Math.abs(maxPosition - 0.40) > 1e-6) params.set('cap', maxPosition.toFixed(2));
    if (hurdleFrac > 1e-6) params.set('hurdle', hurdleFrac.toFixed(2));
    const qs = params.toString();
    const newHash = '#/portfolio' + (qs ? '?' + qs : '');
    if (location.hash !== newHash) {
      history.replaceState(null, '', newHash);
    }
  }, [maxPosition, hurdleFrac]);

  const portfolio = React.useMemo(
    () => computePortfolio(MEMOS, { maxPosition, hurdleFrac }),
    [MEMOS, maxPosition, hurdleFrac]
  );

  // Sort the table by raw score desc so the strongest names lead.
  const sortedRows = [...portfolio.rows].sort((a, b) => b.score - a.score);
  const maxBarWeight = Math.max(
    maxPosition, ...portfolio.rows.map(r => r.weight)
  );

  // Bar chart helpers — simple horizontal bars, scaled to maxBarWeight.
  const barRows = sortedRows
    .filter(r => r.weight > 0)
    .map(r => ({ key: r.slug, label: r.ticker, weight: r.weight, color: 'var(--accent)' }));
  if (portfolio.cashWeight > 0.001) {
    barRows.push({ key: 'cash', label: 'Cash', weight: portfolio.cashWeight, color: 'var(--ink-2)' });
  }

  const longCount = portfolio.rows.filter(r => r.weight > 0).length;
  const passedHurdleCount = portfolio.rows.filter(r => r.passesHurdle).length;

  return (
    <>
      <section className="portfolio-head" data-screen-label="Portfolio">
        <div className="wrap">
          <div className="eyebrow">Cross-asset · Portfolio construction</div>
          <h1>Weighted portfolio</h1>
          <p className="lead">
            Five memos. One portfolio. The methodology is{' '}
            <a href="https://github.com/arthurculang/ar2eb/blob/main/spec/memo-spec__v023__2026-05-23_21-30.md#12-portfolio-construction-draft"
               target="_blank" rel="noopener noreferrer">spec §12</a> —
            conviction-weighted long with hurdle and cap. Drag the
            sliders to see what changes.
          </p>
        </div>
      </section>

      <section className="portfolio-controls">
        <div className="wrap">
          <div className="control-grid">
            <div className="control">
              <label htmlFor="cap">
                Position cap{' '}
                <span className="mono">{(maxPosition * 100).toFixed(0)}%</span>
              </label>
              <input id="cap" type="range" min="0.10" max="1.0" step="0.05"
                     value={maxPosition}
                     onChange={(e) => setMaxPosition(parseFloat(e.target.value))} />
              <div className="hint">
                No single name above this fraction. If raw weight exceeds
                the cap, excess redistributes proportionally to remaining
                names. Iterates until stable.
              </div>
            </div>
            <div className="control">
              <label htmlFor="hurdle">
                Hurdle{' '}
                <span className="mono">+{(hurdleFrac * 100).toFixed(0)}%</span>
              </label>
              <input id="hurdle" type="range" min="0" max="0.20" step="0.01"
                     value={hurdleFrac}
                     onChange={(e) => setHurdleFrac(parseFloat(e.target.value))} />
              <div className="hint">
                Minimum upside vs spot to earn an allocation. 0% =
                "expected &gt; spot." Slide up to use a Treasury or
                S&amp;P-like hurdle.
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="portfolio-summary">
        <div className="wrap">
          <div className="summary-grid">
            <div>
              <div className="lbl">Names that pass</div>
              <div className="big mono">{passedHurdleCount} / {portfolio.rows.length}</div>
            </div>
            <div>
              <div className="lbl">Names allocated</div>
              <div className="big mono">{longCount}</div>
            </div>
            <div>
              <div className="lbl">Portfolio-weighted upside</div>
              <div className={'big mono ' + (portfolio.portfolioUpside >= 0 ? 'delta-pos' : 'delta-neg')}>
                {fmtPct(portfolio.portfolioUpside)}
              </div>
            </div>
            <div>
              <div className="lbl">Cash sleeve</div>
              <div className="big mono">{(portfolio.cashWeight * 100).toFixed(1)}%</div>
            </div>
          </div>
        </div>
      </section>

      <section className="portfolio-bars">
        <div className="wrap">
          <div className="eyebrow">Allocation</div>
          <div className="bars">
            {barRows.length === 0 ? (
              <div className="empty">
                No names pass the hurdle. Cash sleeve = 100%.
              </div>
            ) : (
              barRows.map(r => (
                <div className="bar-row" key={r.key}>
                  <div className="bar-label mono">{r.label}</div>
                  <div className="bar-track">
                    <div className="bar-fill"
                         style={{
                           width: ((r.weight / maxBarWeight) * 100) + '%',
                           background: r.color,
                         }} />
                  </div>
                  <div className="bar-value mono">{(r.weight * 100).toFixed(1)}%</div>
                </div>
              ))
            )}
          </div>
        </div>
      </section>

      <PortfolioExport memo={null} portfolio={portfolio}
                       maxPosition={maxPosition} hurdleFrac={hurdleFrac} />

      <section className="portfolio-table">
        <div className="wrap">
          <div className="eyebrow">Math (show your work)</div>
          <table className="ptable">
            <thead>
              <tr>
                <th>Ticker</th>
                <th className="num">Spot</th>
                <th className="num">Expected</th>
                <th className="num">Upside</th>
                <th className="num">P(pos)</th>
                <th className="num">Score</th>
                <th className="num">Raw w</th>
                <th className="num">Capped w</th>
              </tr>
            </thead>
            <tbody>
              {sortedRows.map(r => (
                <tr key={r.slug} className={r.passesHurdle ? '' : 'row-out'}>
                  <td>
                    <a href={'#/memo/' + r.slug}>{r.ticker}</a>
                  </td>
                  <td className="num mono">{fmtUSD(r.spot)}</td>
                  <td className="num mono">{fmtUSD(r.expected)}</td>
                  <td className={'num mono ' + (r.upsidePct >= 0 ? 'delta-pos' : 'delta-neg')}>
                    {fmtPct(r.upsidePct)}
                  </td>
                  <td className="num mono">{(r.pPos * 100).toFixed(0)}%</td>
                  <td className="num mono">{r.score > 0 ? r.score.toFixed(1) : '—'}</td>
                  <td className="num mono">{r.rawWeight > 0 ? (r.rawWeight * 100).toFixed(1) + '%' : '—'}</td>
                  <td className="num mono"><b>{r.weight > 0 ? (r.weight * 100).toFixed(1) + '%' : '—'}</b></td>
                </tr>
              ))}
              {portfolio.cashWeight > 0.001 && (
                <tr className="row-cash">
                  <td>Cash</td>
                  <td colSpan="6" className="num">unallocated (hurdle fail / cap residual)</td>
                  <td className="num mono"><b>{(portfolio.cashWeight * 100).toFixed(1)}%</b></td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="portfolio-method">
        <div className="wrap">
          <div className="eyebrow">How the score works</div>
          <p>
            <span className="mono">score = upside_pct × √P_pos</span>, where{' '}
            P_pos sums scenario probabilities for cases that beat spot.
            The square root softens the conviction component so neither
            upside nor conviction dominates. Names below the hurdle score
            zero. Raw weights are <span className="mono">score / Σ score</span>;
            the cap is applied iteratively with proportional redistribution;
            any unallocated weight becomes cash.
          </p>
          <p className="lead">
            This is intentionally minimal. It's a framework to debate, not
            a black box. Operator overrides on any name with a structural
            view.
          </p>
        </div>
      </section>
    </>
  );
}



window.AR2EB_PAGES = { HomePage, CategoryPage, MemoPage, DisclaimersPage, AboutPage, PortfolioPage, NotFoundPage };
