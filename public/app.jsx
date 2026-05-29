/* AR2EB — app entry + router */

function App() {
  const { useRoute, TopBar, Footer } = window.AR2EB_LIB;
  const { HomePage, CategoryPage, MemoPage, DisclaimersPage, AboutPage, ThesisPage, PortfolioPage, NotFoundPage } = window.AR2EB_PAGES;
  const route = useRoute();

  // Categories are dynamic — any watchlist with ≥1 memo appears in
  // window.AR2EB_DATA.CATEGORIES. Route + title resolve against that, so a
  // new watchlist (private-wishlist, fcf-megacap) works with no router edit.
  const CATS = window.AR2EB_DATA.CATEGORIES;
  const catSlug = route.slice(1);
  const isCategory = CATS && Object.prototype.hasOwnProperty.call(CATS, catSlug);

  // update <title> on route change
  React.useEffect(() => {
    let title = 'AR2EB — Long horizons. Structural shifts. Imagination.';
    if (route === '/about') title = 'About · AR2EB';
    else if (route === '/thesis') title = 'Thesis & Method · AR2EB';
    else if (route === '/disclaimers') title = 'Disclaimers · AR2EB';
    else if (route === '/portfolio') title = 'Portfolio · AR2EB';
    else if (isCategory) title = CATS[catSlug].name + ' · AR2EB';
    else if (route.startsWith('/memo/')) {
      const slug = route.split('/')[2];
      const memo = window.AR2EB_DATA.MEMOS.find(m => m.slug === slug);
      if (memo) title = memo.company + ' (' + memo.ticker + ') · AR2EB Memo';
    }
    document.title = title;
  }, [route, isCategory, catSlug]);

  let page;
  if (route === '/' || route === '') {
    page = <HomePage />;
  } else if (isCategory) {
    page = <CategoryPage slug={catSlug} />;
  } else if (route.startsWith('/memo/')) {
    page = <MemoPage slug={route.split('/')[2]} />;
  } else if (route === '/portfolio') {
    page = <PortfolioPage />;
  } else if (route === '/disclaimers') {
    page = <DisclaimersPage />;
  } else if (route === '/about') {
    page = <AboutPage />;
  } else if (route === '/thesis') {
    page = <ThesisPage />;
  } else {
    page = <NotFoundPage />;
  }

  return (
    <div className="page">
      <TopBar route={route} />
      <main className="shell" key={route}>{page}</main>
      <Footer />
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
