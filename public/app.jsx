/* AR2EB — app entry + router */

function App() {
  const { useRoute, TopBar, Footer } = window.AR2EB_LIB;
  const { HomePage, CategoryPage, MemoPage, DisclaimersPage, AboutPage, NotFoundPage } = window.AR2EB_PAGES;
  const route = useRoute();

  // update <title> on route change
  React.useEffect(() => {
    let title = 'AR2EB — Long horizons. Structural shifts. Imagination.';
    if (route === '/about') title = 'About · AR2EB';
    else if (route === '/disclaimers') title = 'Disclaimers · AR2EB';
    else if (route === '/asymmetrical-moonshots') title = 'Asymmetrical Moonshots · AR2EB';
    else if (route === '/fcf-plus-plus-growth') title = 'FCF++Growth · AR2EB';
    else if (route.startsWith('/memo/')) {
      const slug = route.split('/')[2];
      const memo = window.AR2EB_DATA.MEMOS.find(m => m.slug === slug);
      if (memo) title = memo.company + ' (' + memo.ticker + ') · AR2EB Memo';
    }
    document.title = title;
  }, [route]);

  let page;
  if (route === '/' || route === '') {
    page = <HomePage />;
  } else if (route === '/asymmetrical-moonshots' || route === '/fcf-plus-plus-growth') {
    page = <CategoryPage slug={route.slice(1)} />;
  } else if (route.startsWith('/memo/')) {
    page = <MemoPage slug={route.split('/')[2]} />;
  } else if (route === '/disclaimers') {
    page = <DisclaimersPage />;
  } else if (route === '/about') {
    page = <AboutPage />;
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
