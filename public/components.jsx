/* AR2EB — shared layout components */

const { useState, useEffect, useMemo, useRef } = React;

// ---------- routing ----------
function parseHash() {
  const raw = (location.hash || '#/').replace(/^#/, '');
  // Strip query string so /portfolio?cap=0.6 still routes to /portfolio.
  // Components read location.hash directly when they need their own params.
  const path = raw.split('?')[0];
  return path || '/';
}
function useRoute() {
  const [route, setRoute] = useState(parseHash());
  useEffect(() => {
    const h = () => {
      setRoute(parseHash());
      // scroll to top on nav
      window.scrollTo({ top: 0, behavior: 'instant' });
    };
    window.addEventListener('hashchange', h);
    return () => window.removeEventListener('hashchange', h);
  }, []);
  return route;
}
function Link({ to, className, children, ...rest }) {
  const onClick = (e) => {
    // Only hijack a plain left-click — modifier clicks (cmd/ctrl/shift/alt) and
    // middle-click keep their native open-in-new-tab/window behavior.
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
    e.preventDefault();
    if (location.hash === '#' + to) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      location.hash = '#' + to;
    }
  };
  return (
    <a href={'#' + to} className={className} onClick={onClick} {...rest}>
      {children}
    </a>
  );
}

// ---------- formatting ----------
// Negatives use a true minus (U+2212), not a hyphen-minus — the finance-site
// glyph standard. Build from the magnitude so the sign is always the real glyph.
function fmtUSD(n, opts = {}) {
  const { decimals = 2 } = opts;
  if (n == null) return '—';
  const abs = Math.abs(n);
  return (n < 0 ? '−' : '') + '$' + abs.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}
function fmtPct(n, opts = {}) {
  const { sign = true, decimals = 1 } = opts;
  if (n == null) return '—';
  const abs = Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  const prefix = n < 0 ? '−' : (sign && n > 0 ? '+' : '');
  return prefix + abs + '%';
}
function fmtMult(n) {
  return n.toFixed(2) + '\u00d7';
}

// ---------- header ----------
function TopBar({ route }) {
  const showLogo = route !== '/'; // home shows plain-text brand (the hero IS the full logo); sub-pages show the box mark only — the wordmark text reads poorly at topbar size
  return (
    <header className="topbar">
      <div className="wrap topbar-inner">
        <Link to="/" className="topbar-logo" aria-label="AR2EB — home">
          {showLogo ? (
            <img src="assets/logo-box.svg" alt="AR2EB" />
          ) : (
            <span style={{ fontFamily: 'var(--type-mono)', fontSize: 12, letterSpacing: '0.12em', color: 'var(--ink-2)' }}>AR2EB</span>
          )}
        </Link>
        <nav className="topbar-nav" aria-label="Primary">
          <Link to="/portfolio" className={route === '/portfolio' ? 'active' : ''}>Portfolio</Link>
          <Link to="/thesis"    className={route === '/thesis'    ? 'active' : ''}>Thesis</Link>
          <Link to="/indicator" className={route === '/indicator' ? 'active' : ''}>Indicator</Link>
          <Link to="/about"     className={route === '/about'     ? 'active' : ''}>About</Link>
        </nav>
      </div>
    </header>
  );
}

// ---------- footer ----------
function Footer() {
  return (
    <footer className="footer">
      <div className="wrap">
        <div className="footer-strip" aria-label="Disclaimer">
          <span>Not investment advice</span>
          <span className="dot">·</span>
          <span>Not from a registered investment advisor</span>
          <span className="dot">·</span>
          <span>AI-assisted analysis</span>
          <span className="dot">·</span>
          <span>Author may hold positions</span>
          <span className="dot">·</span>
          <Link to="/disclaimers">See full disclaimers</Link>
        </div>
        <div className="footer-bottom">
          <span>© 2026 AR2EB · Alameda Research 2: Electric Boogaloo</span>
          <span style={{ display: 'inline-flex', gap: 18 }}>
            <Link to="/about">About</Link>
            <Link to="/disclaimers">Disclaimers</Link>
            <a href="mailto:arthur@culang.co">arthur@culang.co</a>
          </span>
        </div>
      </div>
    </footer>
  );
}

// ---------- ticker badge ----------
function TickerBadge({ ticker }) {
  return <div className="ticker-badge mono">{ticker}</div>;
}

// ---------- compact pricing block (used in memo list) ----------
function PricingBlock({ memo }) {
  const delta = memo.expected.deltaPct;
  const positive = delta >= 0;
  return (
    <div className="pricing">
      <div className="lbl" style={{ marginTop: 0 }}>Spot</div>
      <div className="row"><span className="v">{fmtUSD(memo.spot.price)}</span></div>
      <div className="lbl">Expected fair value</div>
      <div className="row">
        <span className="v">{fmtUSD(memo.expected.fair)}</span>
      </div>
      <div className="row" style={{ marginTop: 2 }}>
        <span className={positive ? 'delta-pos' : 'delta-neg'}>{fmtPct(delta)} vs spot</span>
      </div>
    </div>
  );
}

window.AR2EB_LIB = {
  useRoute, Link, parseHash,
  fmtUSD, fmtPct, fmtMult,
  TopBar, Footer, TickerBadge, PricingBlock,
};
