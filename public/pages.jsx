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
function MemoPage({ slug }) {
  const { fmtUSD, fmtPct, fmtMult } = L();
  const { MEMOS, DISCLAIMER_BLOCKS } = D();
  const memo = MEMOS.find(m => m.slug === slug);
  if (!memo) return <NotFoundPage />;
  const positive = memo.expected.deltaPct >= 0;

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

      <section className="central-q">
        <div className="wrap">
          <div className="eyebrow">Central question</div>
          <blockquote>{memo.question}</blockquote>
        </div>
      </section>

      <section className="pwev">
        <div className="wrap">
          <div className="eyebrow">Probability-weighted expected value</div>
          <div className="pwev-grid">
            <div className="pwev-headline">
              <div className="label">Expected fair value today</div>
              <div className="big">{fmtUSD(memo.expected.fair)}</div>
              <div className={'delta ' + (positive ? 'pos' : 'neg')} style={{ color: positive ? 'var(--pos)' : 'var(--neg)' }}>
                {fmtPct(memo.expected.deltaPct)} vs spot
              </div>
              <div className="vs">Spot {fmtUSD(memo.spot.price)} · {memo.spot.asOf}</div>
            </div>
            <table className="compound-table" aria-label="Forward compounded value">
              <thead>
                <tr>
                  <th>Forward year</th>
                  <th>Compounded value</th>
                  <th>× spot</th>
                </tr>
              </thead>
              <tbody>
                {memo.compound.map(r => (
                  <tr key={r.y}>
                    <td>+{r.y}y</td>
                    <td>{fmtUSD(r.value)}</td>
                    <td>{fmtMult(r.mult)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="scenarios">
        <div className="wrap">
          <div className="eyebrow">Four scenarios</div>
          <div className="scenarios-grid">
            {memo.scenarios.map(s => (
              <div className={'scn ' + s.key} key={s.key}>
                <div className="label">{s.label}</div>
                <div className="price">{fmtUSD(s.price)}</div>
                <div className={'delta ' + (s.price >= memo.spot.price ? 'delta-pos' : 'delta-neg')}
                     style={{ color: s.price >= memo.spot.price ? 'var(--pos)' : 'var(--neg)' }}>
                  {fmtPct(((s.price - memo.spot.price) / memo.spot.price) * 100)} vs spot
                </div>
                <div className="prob">Probability <b>{s.prob}%</b></div>
                <div className="head">{s.headline}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="pdf-cta-wrap">
        <div className="wrap">
          <a href={'memos/' + memo.pdf.file} className="pdf-cta" target="_blank" rel="noopener noreferrer"
             onClick={(e) => { /* PDFs not present in prototype; let browser try */ }}>
            <div className="left">
              <div className="ttl">Read full memo (PDF)</div>
              <div className="meta">{memo.pdf.file} · {memo.pdf.size}</div>
            </div>
            <div className="right">
              <span>Download</span>
              <span aria-hidden="true">↓</span>
            </div>
          </a>
        </div>
      </section>

      <section className="narr">
        <div className="wrap">
          <div className="eyebrow">Scenario narratives</div>
          <div className="narr-grid">
            {memo.scenarios.map(s => (
              <div className={'narr-col ' + s.key} key={s.key}>
                <div className="lbl">{s.label}</div>
                <div className="top">
                  <span className="price">{fmtUSD(s.price)}</span>
                  <span className="prob">{s.prob}%</span>
                </div>
                <div className="head">{s.headline}</div>
                <h5>Why</h5>
                <p>{s.why}</p>
                <h5>What happens</h5>
                {s.what.map((line, i) => <p key={i}>{line}</p>)}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="methodology">
        <div className="wrap">
          <div className="eyebrow">Methodology</div>
          <p>{memo.methodology}</p>
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

window.AR2EB_PAGES = { HomePage, CategoryPage, MemoPage, DisclaimersPage, AboutPage, NotFoundPage };
