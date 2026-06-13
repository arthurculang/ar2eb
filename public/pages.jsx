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
          Page4Competitive, Page4Quantitative, PagePOCD, Page5BackMatter } = window.AR2EB_MEMO || {};
  const containerRef = React.useRef(null);
  const innerRef = React.useRef(null);
  const [scale, setScale] = React.useState(1);
  const NATIVE_W = 14 * 96; // 14 inches at 96 dpi = 1344px
  // Mirror the PDF gate (memo_pdf.jsx → hasCompetitive): the §6d page renders
  // only when the ticker carries a `competitive` block, so 5- and 6-page memos
  // both come out right.
  const hasCompetitive = !!(memo.print && memo.print.competitive);
  const hasPOCD = !!(memo.print && memo.print.pocd);   // §14 back-matter scorecard

  React.useEffect(() => {
    const update = () => {
      if (!containerRef.current) return;
      const w = containerRef.current.clientWidth;
      const s = Math.min(1, w / NATIVE_W);
      setScale(s);
      // transform: scale() is visual only and doesn't reserve flow space, so
      // size the wrap explicitly to the scaled content height. scrollHeight is
      // the untransformed layout height (any page count), so this stays correct
      // whether the memo has the §6d page (6) or not (5).
      if (innerRef.current) {
        containerRef.current.style.height = (innerRef.current.scrollHeight * s) + 'px';
      }
    };
    update();
    const ro = new ResizeObserver(update);
    if (containerRef.current) ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, [memo]);

  if (!Page1Headline) return <p>Memo viewer not loaded — refresh required.</p>;

  return (
    <div className="memo-embed-wrap" ref={containerRef}>
      <div className="memo-embed-inner" ref={innerRef} style={{
        transform: `scale(${scale})`,
        transformOrigin: 'top left',
        width: NATIVE_W + 'px',
      }}>
        <Page1Headline memo={memo} />
        <Page2Narratives memo={memo} />
        <Page3Snapshot memo={memo} />
        {hasCompetitive && Page4Competitive && <Page4Competitive memo={memo} />}
        <Page4Quantitative memo={memo} />
        {hasPOCD && PagePOCD && <PagePOCD memo={memo} />}
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
          {memo.pdf.priorVersions && memo.pdf.priorVersions.length > 0 && (
            <details className="prior-versions">
              <summary>
                Prior versions <span className="mono">({memo.pdf.priorVersions.length})</span>
              </summary>
              <ul className="prior-versions-list">
                {memo.pdf.priorVersions.map(pv => (
                  <li key={pv.version}>
                    <a href={'memos/' + pv.file} target="_blank" rel="noopener noreferrer">
                      <span className="pv-version mono">v{pv.version}</span>
                      <span className="pv-asof">as of {pv.asOfDate}</span>
                      <span className="pv-spot mono">spot {fmtUSD(pv.spotPrice)}</span>
                      <span className="pv-size mono">{pv.size}</span>
                      <span className="pv-arrow" aria-hidden="true">↓</span>
                    </a>
                  </li>
                ))}
              </ul>
              <p className="prior-versions-note">
                PDFs accumulate as immutable history — each version captures the spot price
                and analysis as of the date shown. The current version is at top of the page.
              </p>
            </details>
          )}
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

// ---------- THESIS & METHOD ----------
function ThesisPage() {
  const { Link } = L();
  return (
    <section className="about-page thesis-page" data-screen-label="Thesis & Method">
      <div className="wrap-narrow">
        <div className="eyebrow" style={{ marginBottom: 18 }}>Thesis &amp; method</div>
        <h1>Long horizons. Structural shifts. Imagination.</h1>

        <p className="thesis-lead">
          Three words seed everything published here. They are not a slogan — they are the filter every position passes through. We underwrite individual equities on a multi-year, probability-weighted basis: a concentrated book of asymmetric bets and free-cash-flow compounders, each one valued in the open with the work shown.
        </p>

        <h3>Long horizons</h3>
        <p>
          Markets price the next quarter with great precision and the next decade with almost none. That gap is the opportunity. Every memo is built on a multi-year discounted-cash-flow model — five to ten years of explicit projection, then a terminal value — and a forward-value chart that runs from today out to twenty years. The discipline is patience: the goal is to be approximately right about 2035, not precisely right about next earnings. Time-horizon arbitrage is the most durable edge available to an investor with no redemption pressure and no benchmark to chase.
        </p>

        <h3>Structural shifts</h3>
        <p>
          We don't diversify across sectors; we concentrate on structural change. The universe is organized by theme — autonomous mobility, energy transition, single-molecule biology, surgical robotics, AI compute, and a dozen others — because the question that matters is not "which industry" but "what is becoming structurally true that the market hasn't yet underwritten." A theme earns a position only when a specific company is the cleanest expression of it at a defensible price. The map of themes is where we look; the DCF is how we decide.
        </p>

        <h3>Imagination</h3>
        <p>
          A single point-estimate price target is a failure of imagination. Every memo carries explicit scenarios — Bear, Base, Bull, and, where the asymmetry warrants, an Ultra Bear or Ultra Bull tail — each with its own probability, its own cash-flow path, and its own honest math. The probability-weighted expected value is the output, but the distribution is the point. The work is to imagine the futures consensus won't: the wipeout and the multi-bagger, priced side by side, so the shape of the bet is visible before any capital is committed.
        </p>

        <h3>How we keep it honest</h3>
        <p>
          Imagination without discipline is just storytelling. Every scenario is a full DCF that has to balance — an equity bridge that reconciles, a terminal value that's defensible, arithmetic a validator checks on every build. When a company doesn't fit the standard framework, we don't force it: a high-multiple compounder earns an exit-multiple terminal rather than a perpetuity that flatters it; a business with significant non-operating value is valued on its parts; a pre-revenue platform gets a Damodaran young-company treatment with an explicit failure probability. The memo is an auditable artifact, not a pitch — published as a PDF, summarized on-site, and kept as version-stamped history when the facts change.
        </p>

        <p className="thesis-close">
          None of this is investment advice. All of it shows its work. Browse the{' '}
          <Link to="/asymmetrical-moonshots">asymmetric bets</Link>, the{' '}
          <Link to="/fcf-plus-plus-growth">free-cash-flow compounders</Link>, or see how
          they combine into a <Link to="/portfolio">conviction-weighted portfolio</Link>.
        </p>
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
          AR2EB — Alameda Research 2: Electric Boogaloo — is the public-facing publication of a single-operator portfolio. The thesis is concentration: a small number of single-name positions, each backed by a probability-weighted DCF that gets pressure-tested in the open rather than sitting in a private folder.
        </p>

        <h3>Who</h3>
        <p>An individual investor running a single-operator portfolio with a concentrated, single-name conviction approach. No external capital, no fund vehicle, no benchmark to chase.</p>

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
// PORTFOLIO — human conviction × quantitative forecast (spec §12).
//
//   weight ∝ max(0, upside) × conviction_mult × indicator_mult
//
//   · upside           — the AI memo's probability-weighted fair value vs spot
//                        (the quantitative forecast).
//   · conviction_mult  — the HUMAN input: Arthur's conviction tier per name
//                        (High 2.0 … Low 0.35). Conviction-neutral: it enters
//                        only here at sizing, never the analysis (spec §3.5 B).
//   · indicator_mult   — the Arthur Indicator valuation zone (§13), a gentle
//                        validated tilt (green 1.25 … red 0.70); neutral 1.0
//                        where the Indicator is undefined (pre-revenue names).
//
// Then: hurdle gate, raw = score/Σscore, iterative cap with proportional
// redistribution, residual = cash. Mirrors portfolio/build_weights.py (the
// tracked book); the cap/hurdle sliders make this the interactive explorer.
// ────────────────────────────────────────────────────────────────────
const CONVICTION_MULT = { 'High': 2.0, 'Med-High': 1.5, 'Med': 1.0, 'Med-Low': 0.6, 'Low': 0.35 };
const AI_ZONE_MULT = { green: 1.25, yellow: 1.10, orange: 0.90, red: 0.70 };

function computePortfolio(memos, opts = {}) {
  const { maxPosition = 0.15, hurdleFrac = 0 } = opts;

  const rows = memos.map(m => {
    const spot = m.spot.price;
    const expected = m.expected.fair;
    const upsidePct = m.expected.deltaPct;
    const passesHurdle = upsidePct > hurdleFrac * 100;
    const tier = (m.taxonomy && m.taxonomy.tier) || null;
    const convMult = CONVICTION_MULT[tier] != null ? CONVICTION_MULT[tier] : 1.0;
    const ai = m.ai || null;                                   // {value, zone} | null
    const aiMult = ai ? (AI_ZONE_MULT[ai.zone] != null ? AI_ZONE_MULT[ai.zone] : 1.0) : 1.0;
    const score = (passesHurdle && upsidePct > 0) ? upsidePct * convMult * aiMult : 0;
    return {
      ticker: m.ticker, slug: m.slug, company: m.company,
      spot, expected, upsidePct, tier, convMult, ai, aiMult, score,
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
      upside_pct: r.upsidePct,
      tier: r.tier, conviction_mult: r.convMult,
      indicator: r.ai ? r.ai.value : null, indicator_zone: r.ai ? r.ai.zone : 'n/a',
      indicator_mult: r.aiMult, score: r.score,
      raw_weight: r.rawWeight, weight: r.weight,
      passes_hurdle: r.passesHurdle,
    })),
  }, null, 2);

  const buildCsv = () => {
    const header = 'ticker,spot,expected,upside_pct,tier,conviction_mult,indicator,indicator_zone,indicator_mult,score,raw_weight,weight';
    const lines = portfolio.rows.map(r => [
      r.ticker,
      r.spot.toFixed(2),
      r.expected.toFixed(2),
      r.upsidePct.toFixed(2),
      r.tier || '',
      r.convMult.toFixed(2),
      r.ai ? r.ai.value.toFixed(2) : '',
      r.ai ? r.ai.zone : 'n/a',
      r.aiMult.toFixed(2),
      r.score.toFixed(2),
      r.rawWeight.toFixed(4),
      r.weight.toFixed(4),
    ].join(','));
    if (portfolio.cashWeight > 0.001) {
      lines.push(`cash,,,,,,,,,,,${portfolio.cashWeight.toFixed(4)}`);
    }
    return header + '\n' + lines.join('\n') + '\n';
  };

  const buildUrl = () => {
    const params = new URLSearchParams();
    if (Math.abs(maxPosition - 0.15) > 1e-6) params.set('cap', maxPosition.toFixed(2));
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
          <button onClick={() => copy(buildJson(), 'JSON')}>JSON</button>
          <span className="export-sep">·</span>
          <button onClick={() => copy(buildCsv(), 'CSV')}>CSV</button>
          <span className="export-sep">·</span>
          <button onClick={() => copy(buildUrl(), 'URL')}>URL</button>
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
    if (q < 0) return { maxPosition: 0.15, hurdleFrac: 0 };
    const params = new URLSearchParams(hash.slice(q + 1));
    const cap = parseFloat(params.get('cap'));
    const hurdle = parseFloat(params.get('hurdle'));
    return {
      maxPosition: isFinite(cap) ? Math.max(0.10, Math.min(1.0, cap)) : 0.15,
      hurdleFrac:  isFinite(hurdle) ? Math.max(0, Math.min(0.20, hurdle)) : 0,
    };
  }, []);

  const [maxPosition, setMaxPosition] = React.useState(initial.maxPosition);
  const [hurdleFrac, setHurdleFrac] = React.useState(initial.hurdleFrac);

  // Persist slider state to URL without triggering navigation. Only encode
  // non-default values so a clean #/portfolio remains a clean shareable.
  React.useEffect(() => {
    const params = new URLSearchParams();
    if (Math.abs(maxPosition - 0.15) > 1e-6) params.set('cap', maxPosition.toFixed(2));
    if (hurdleFrac > 1e-6) params.set('hurdle', hurdleFrac.toFixed(2));
    const qs = params.toString();
    const newHash = '#/portfolio' + (qs ? '?' + qs : '');
    if (location.hash !== newHash) {
      history.replaceState(null, '', newHash);
    }
  }, [maxPosition, hurdleFrac]);

  // Private companies (private-wishlist) aren't publicly buyable, so they're
  // excluded from the conviction-weighted long portfolio — it allocates across
  // positions you can actually take.
  const publicMemos = React.useMemo(
    () => MEMOS.filter(m => !m.taxonomy || m.taxonomy.watchlist !== 'private-wishlist'),
    [MEMOS]
  );
  const portfolio = React.useMemo(
    () => computePortfolio(publicMemos, { maxPosition, hurdleFrac }),
    [publicMemos, maxPosition, hurdleFrac]
  );

  // Sort the table by raw score desc so the strongest names lead.
  const sortedRows = [...portfolio.rows].sort((a, b) => b.score - a.score);

  // Allocation segments for the stacked bar — longs first, cash last.
  // The two-tone indigo palette keeps longs visually grouped while still
  // letting individual segments be distinguishable.
  const longSegments = sortedRows
    .filter(r => r.weight > 0)
    .map((r, i) => ({
      key: r.slug, slug: r.slug, label: r.ticker,
      sublabel: r.company, weight: r.weight,
      shade: i,  // 0 = primary accent, 1 = secondary accent, etc.
    }));
  const cashSegment = portfolio.cashWeight > 0.001
    ? { key: 'cash', label: 'Cash', weight: portfolio.cashWeight, sublabel: 'unallocated' }
    : null;

  const longCount = longSegments.length;
  const passedHurdleCount = portfolio.rows.filter(r => r.passesHurdle).length;
  const deployedPct = (1 - portfolio.cashWeight) * 100;

  return (
    <>
      <section className="portfolio-head" data-screen-label="Portfolio">
        <div className="wrap">
          <div className="eyebrow">Cross-asset · Portfolio construction</div>
          <h1>Weighted portfolio</h1>
          <p className="lead">
            One portfolio. Each position sized by three transparent factors —
            the memo's quantitative upside, the operator's conviction, and the
            Arthur Indicator — with a hurdle and per-name cap. Methodology:{' '}
            <a href="https://github.com/arthurculang/ar2eb/blob/main/spec/memo-spec__v023__2026-05-23_21-30.md#12-portfolio-construction-draft"
               target="_blank" rel="noopener noreferrer">spec §12</a>.
          </p>
        </div>
      </section>

      <section className="portfolio-hero">
        <div className="wrap">
          <div className="hero-card">
            <div className="hero-numbers">
              <div className="hero-primary">
                <div className={'big-number ' + (portfolio.portfolioUpside >= 0 ? 'delta-pos' : 'delta-neg')}>
                  {portfolio.portfolioUpside >= 0 ? '+' : ''}{portfolio.portfolioUpside.toFixed(1)}%
                </div>
                <div className="big-label">weighted upside (longs)</div>
              </div>
              <div className="hero-sep" aria-hidden="true" />
              <div className="hero-secondary">
                <div className="big-number">{deployedPct.toFixed(0)}%</div>
                <div className="big-label">deployed · {(portfolio.cashWeight * 100).toFixed(0)}% cash</div>
              </div>
            </div>
            <div className="hero-meta">
              <span><b>{passedHurdleCount}</b> of <b>{portfolio.rows.length}</b> names pass hurdle</span>
              <span className="meta-sep">·</span>
              <span>cap <b>{(maxPosition * 100).toFixed(0)}%</b></span>
              <span className="meta-sep">·</span>
              <span>hurdle <b>+{(hurdleFrac * 100).toFixed(0)}%</b></span>
            </div>
          </div>
        </div>
      </section>

      <section className="portfolio-allocation">
        <div className="wrap">
          <div className="eyebrow">Allocation</div>
          {longSegments.length === 0 ? (
            <div className="alloc-empty">
              No names pass the hurdle. Cash sleeve = 100%.
            </div>
          ) : (
            <>
              <div className="alloc-bar" role="img"
                   aria-label={`Allocation: ${longSegments.map(s => `${s.label} ${(s.weight*100).toFixed(0)}%`).join(', ')}${cashSegment ? `, cash ${(cashSegment.weight*100).toFixed(0)}%` : ''}`}>
                {longSegments.map(s => (
                  <div key={s.key}
                       className={`alloc-seg alloc-seg-long alloc-shade-${s.shade}`}
                       style={{ width: (s.weight * 100) + '%' }}>
                    <span className="alloc-seg-label">
                      <span className="t">{s.label}</span>
                      <span className="p mono">{(s.weight * 100).toFixed(0)}%</span>
                    </span>
                  </div>
                ))}
                {cashSegment && (
                  <div className="alloc-seg alloc-seg-cash"
                       style={{ width: (cashSegment.weight * 100) + '%' }}>
                    <span className="alloc-seg-label">
                      <span className="t">Cash</span>
                      <span className="p mono">{(cashSegment.weight * 100).toFixed(0)}%</span>
                    </span>
                  </div>
                )}
              </div>
              <ul className="alloc-legend">
                {longSegments.map(s => (
                  <li key={s.key} className={`alloc-legend-row alloc-shade-${s.shade}`}>
                    <span className="swatch" aria-hidden="true" />
                    <a href={'#/memo/' + s.slug} className="t mono">{s.label}</a>
                    <span className="sub">{s.sublabel}</span>
                    <span className="p mono">{(s.weight * 100).toFixed(1)}%</span>
                  </li>
                ))}
                {cashSegment && (
                  <li className="alloc-legend-row alloc-legend-cash">
                    <span className="swatch" aria-hidden="true" />
                    <span className="t mono">Cash</span>
                    <span className="sub">{cashSegment.sublabel}</span>
                    <span className="p mono">{(cashSegment.weight * 100).toFixed(1)}%</span>
                  </li>
                )}
              </ul>
            </>
          )}
        </div>
      </section>

      <section className="portfolio-controls">
        <div className="wrap">
          <div className="eyebrow">Controls</div>
          <div className="control-grid">
            <div className="control">
              <div className="control-row">
                <label htmlFor="cap">Position cap</label>
                <span className="mono control-value">{(maxPosition * 100).toFixed(0)}%</span>
              </div>
              <input id="cap" type="range" min="0.10" max="1.0" step="0.05"
                     value={maxPosition}
                     onChange={(e) => setMaxPosition(parseFloat(e.target.value))} />
              <div className="hint">
                Excess over cap redistributes proportionally to remaining names.
              </div>
            </div>
            <div className="control">
              <div className="control-row">
                <label htmlFor="hurdle">Hurdle</label>
                <span className="mono control-value">+{(hurdleFrac * 100).toFixed(0)}%</span>
              </div>
              <input id="hurdle" type="range" min="0" max="0.20" step="0.01"
                     value={hurdleFrac}
                     onChange={(e) => setHurdleFrac(parseFloat(e.target.value))} />
              <div className="hint">
                Minimum upside vs spot to earn an allocation.
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="portfolio-table">
        <div className="wrap">
          <div className="eyebrow">Math</div>
          <table className="ptable">
            <thead>
              <tr>
                <th>Ticker</th>
                <th className="num">Spot</th>
                <th className="num">Expected</th>
                <th className="num">Upside <span className="muted">(quant)</span></th>
                <th className="num">Conviction <span className="muted">(human)</span></th>
                <th className="num">Indicator <span className="muted">(quant)</span></th>
                <th className="num col-secondary">Raw</th>
                <th className="num">Weight</th>
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
                  <td className="num mono">{r.tier || '—'} <span className="muted">×{r.convMult.toFixed(2)}</span></td>
                  <td className="num mono">{r.ai ? `${r.ai.zone} ${r.ai.value.toFixed(1)}` : 'n/a'} <span className="muted">×{r.aiMult.toFixed(2)}</span></td>
                  <td className="num mono col-secondary">{r.score > 0 ? (r.rawWeight * 100).toFixed(1) + '%' : '—'}</td>
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
          <details>
            <summary>
              <span className="eyebrow">How the score works</span>
            </summary>
            <div className="method-body">
              <p>
                <span className="mono">weight ∝ max(0, upside) × conviction × indicator</span>.
                Three transparent factors: the memo's probability-weighted{' '}
                <b>upside</b> (the machine's forecast), the operator's{' '}
                <b>conviction</b> tier (High&nbsp;2.0 · Med-High&nbsp;1.5 · Med&nbsp;1.0 · Med-Low&nbsp;0.6 · Low&nbsp;0.35),
                and the <b>Arthur Indicator</b> valuation zone (green&nbsp;1.25 · yellow&nbsp;1.10 · orange&nbsp;0.90 · red&nbsp;0.70;
                neutral for pre-revenue names). Conviction is the only human number and it
                enters only here, never the analysis. Names below the hurdle score zero; raw
                weights are <span className="mono">score / Σ score</span>; the cap is applied
                iteratively with proportional redistribution; the rest is cash.
              </p>
              <p>
                Intentionally minimal — a framework to debate, not a black box.
                Operator overrides on any name with a structural view.
              </p>
            </div>
          </details>
        </div>
      </section>

      <PortfolioExport memo={null} portfolio={portfolio}
                       maxPosition={maxPosition} hurdleFrac={hurdleFrac} />
    </>
  );
}



// ---------- ARTHUR INDICATOR ----------
// Dedicated page: the equation, how to read it, the live snapshot, and the
// backtest — with an honest IC primer + significance treatment (spec §13).
function IndicatorPage() {
  const { MEMOS } = D();

  // Backtest results of record (scripts/_models/ai2_results.md + the robustness
  // run). Static research output — not live data. Panel: 111 tickers / 1,483
  // name-years / FY2009–2025; rank-IC judged leave-one-year-out out-of-sample.
  const ZONES = [
    { z: 'green',  label: 'Green — extremely undervalued', band: '< 6',     r1: '+38%', w1: '74%', r3: '+159%', w3: '87%' },
    { z: 'yellow', label: 'Yellow — somewhat undervalued',  band: '6 – 10',  r1: '+28%', w1: '69%', r3: '+106%', w3: '83%' },
    { z: 'orange', label: 'Orange — somewhat overvalued',   band: '10 – 15', r1: '+31%', w1: '70%', r3: '+93%',  w3: '84%' },
    { z: 'red',    label: 'Red — extremely overvalued',     band: '> 15',    r1: '+14%', w1: '57%', r3: '+48%',  w3: '58%' },
  ];
  const IC = [
    { h: '1-year forward', ic: '+0.063', t: '+1.14', pos: '59%', n: '17' },
    { h: '3-year forward', ic: '+0.044', t: '+0.90', pos: '47%', n: '15' },
  ];

  // Live snapshot: where today's covered names sit on the Indicator.
  const scored = MEMOS.filter(m => m.ai).map(m => ({
    ticker: m.ticker, slug: m.slug, value: m.ai.value, zone: m.ai.zone,
  })).sort((a, b) => a.value - b.value);

  return (
    <>
      <section className="portfolio-head" data-screen-label="Arthur Indicator">
        <div className="wrap">
          <div className="eyebrow">Valuation screen · §13</div>
          <h1>The Arthur Indicator</h1>
          <p className="lead">
            One number for a hard question: <em>am I paying a fair price for the
            quality of this business?</em> A fast valuation screen that complements
            the full DCF — and a worked example of how to read a backtest honestly.
          </p>
          <div className="ai-equation">
            <span className="mono">
              Arthur Indicator = EV ÷ ( Revenue × ( Gross Margin + Revenue Growth ) )
            </span>
          </div>
        </div>
      </section>

      <section className="portfolio-method">
        <div className="wrap">
          <div className="eyebrow">How to read it</div>
          <p>
            The numerator is <b>enterprise value</b> — what you pay for the whole
            business (market cap + debt − cash). The denominator scales revenue by
            its <b>quality</b>: a "Rule of 40"-style sum of gross margin and revenue
            growth. A dollar of revenue from an 80%-margin business growing 30% is
            worth far more than a dollar from a 20%-margin business growing 5%, and
            the denominator says so. So the Indicator is, in plain terms,{' '}
            <b>EV/Revenue divided by business quality</b> — lower is cheaper-for-quality.
          </p>
          <p>
            It deliberately ignores the near-term "fixable" costs a free-cash-flow DCF
            penalises (stock comp, R&D, capex), valuing instead from a durable
            product-economics angle. It is therefore a <b>complement</b> to the memo
            DCF, not a replacement — and the disagreements between the two are the
            interesting part. It is undefined for pre-revenue or gross-loss names
            (those are the young-company DCF's domain).
          </p>
          <div className="ai-zones" role="img" aria-label="Valuation zones from green (cheap) to red (rich)">
            {ZONES.map(z => (
              <div key={z.z} className={`ai-zone-chip ai-zone-${z.z}`}>
                <span className="t">{z.label}</span>
                <span className="b mono">{z.band}</span>
              </div>
            ))}
          </div>
          <p className="hint">Zones anchored on META (~8.5 historically). Green = buy range · red = priced richly on revenue.</p>
        </div>
      </section>

      <section className="portfolio-allocation">
        <div className="wrap">
          <div className="eyebrow">Where today's names sit</div>
          <table className="ptable">
            <thead>
              <tr><th>Ticker</th><th className="num">Indicator</th><th>Zone</th></tr>
            </thead>
            <tbody>
              {scored.map(s => (
                <tr key={s.slug}>
                  <td><a href={'#/memo/' + s.slug}>{s.ticker}</a></td>
                  <td className="num mono">{s.value.toFixed(1)}</td>
                  <td><span className={`ai-dot ai-zone-${s.zone}`} aria-hidden="true" /> {s.zone}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="hint">Live, computed from each memo. Pre-revenue names (the moonshots) don't appear — the Indicator is undefined there.</p>
        </div>
      </section>

      <section className="portfolio-method">
        <div className="wrap">
          <div className="eyebrow">Does it actually work? — the backtest</div>
          <p>
            Tested on a panel of <b>111 companies</b> across <b>FY2009–2025</b>{' '}
            (~1,500 company-years). The method: each year, rank every name from
            cheapest to richest on the Indicator, and see whether the cheap ones
            actually went on to outperform. Judged <b>out-of-sample</b> — the test
            never sees the year it's scoring.
          </p>
          <p><b>Forward return by zone</b> (the practical read):</p>
          <table className="ptable">
            <thead>
              <tr>
                <th>Zone</th>
                <th className="num">1-yr return</th><th className="num col-secondary">1-yr win</th>
                <th className="num">3-yr return</th><th className="num col-secondary">3-yr win</th>
              </tr>
            </thead>
            <tbody>
              {ZONES.map(z => (
                <tr key={z.z}>
                  <td><span className={`ai-dot ai-zone-${z.z}`} aria-hidden="true" /> {z.label}</td>
                  <td className="num mono delta-pos">{z.r1}</td>
                  <td className="num mono col-secondary">{z.w1}</td>
                  <td className="num mono delta-pos">{z.r3}</td>
                  <td className="num mono col-secondary">{z.w3}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="hint">
            Green clearly best, red clearly worst — the ordering is the result. Absolute
            returns are inflated by a 2009–25 bull sample; what's durable is that cheaper → higher forward return.
          </p>
        </div>
      </section>

      <section className="portfolio-method">
        <div className="wrap">
          <div className="eyebrow">What is IC — and is this good?</div>
          <p>
            The standard way to score a signal is its <b>Information Coefficient (IC)</b>:
            the correlation between what the signal predicted and what actually
            happened. Here it's a <b>rank</b> correlation — how well the cheapest-to-richest
            ordering lines up with the best-to-worst forward-return ordering. It runs
            from −1 (perfectly backwards) through 0 (noise) to +1 (perfect).
          </p>
          <table className="ptable">
            <thead>
              <tr><th>Horizon</th><th className="num">Out-of-sample IC</th><th className="num">t-stat</th><th className="num col-secondary">years positive</th><th className="num col-secondary">N years</th></tr>
            </thead>
            <tbody>
              {IC.map(r => (
                <tr key={r.h}>
                  <td>{r.h}</td>
                  <td className="num mono delta-pos">{r.ic}</td>
                  <td className="num mono">{r.t}</td>
                  <td className="num mono col-secondary">{r.pos}</td>
                  <td className="num mono col-secondary">{r.n}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p>
            An IC near <b>+0.05</b> means that on any single pair of names you'd call
            the winner ~52% of the time — barely above a coin flip. The edge is small
            per bet but compounds across many names and many years; rough industry
            yardstick: 0.02–0.05 useful, 0.05–0.10 good, above 0.10 excellent (and
            usually overfit if you see it in a backtest). So the <em>direction</em> is
            a legitimately useful, if modest, value signal.
          </p>
          <p>
            <b>But honesty about significance.</b> The <b>t-stat</b> asks whether the
            positive average could just be luck. Above ~2 is the conventional bar for
            "real." This signal is at <b>+1.1 (1-yr) and +0.9 (3-yr)</b> — directionally
            positive every way we slice it (both horizons, both halves of the sample),
            but <b>not yet statistically significant</b>. The reason is structural: the
            value effect genuinely runs hot some years and cold others (the yearly IC
            swings from −0.31 to +0.56), and ~16 years of annual data isn't enough to
            pin a +0.05 average down tightly. That is exactly why the Indicator is used
            as a <b>gentle tilt</b> in position sizing, never a dominant factor.
          </p>
          <p className="hint">
            A note on what didn't work: enriching the formula with operating-margin,
            FCF-margin and momentum terms ("AI 2.0", 8 tunable weights) raised in-sample
            accuracy but <b>overfit</b> — out-of-sample it went negative. An exhaustive
            15,625-combination search confirmed no enrichment beats the simple one-line
            formula. So the live screen stays AI 1.0.
          </p>
        </div>
      </section>

      <section className="portfolio-method">
        <div className="wrap">
          <details>
            <summary><span className="eyebrow">Caveats &amp; method notes</span></summary>
            <div className="method-body">
              <p>
                Fundamentals-only and therefore conviction-neutral (EV, revenue,
                margin, growth — all observable). Gross margin and forward growth are
                research-sourced; the rest reads from each memo. The screen overlaps the
                DCF's own cheapness signal, so its unique value is the divergences (a
                name the DCF likes but the Indicator flags red gets trimmed in sizing).
                Full results and the reproduction commands live in{' '}
                <a href="https://github.com/arthurculang/ar2eb/blob/main/scripts/_models/ai2_results.md"
                   target="_blank" rel="noopener noreferrer">ai2_results.md</a>;
                methodology in spec §13.
              </p>
            </div>
          </details>
        </div>
      </section>
    </>
  );
}

window.AR2EB_PAGES = { HomePage, CategoryPage, MemoPage, DisclaimersPage, AboutPage, ThesisPage, PortfolioPage, IndicatorPage, NotFoundPage };
