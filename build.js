// ar2eb.com build — bundles JSX into single files via esbuild.
//
// Two entry points (src/site-entry.js + src/print-entry.js) wrap the
// public/*.jsx files plus React. esbuild bundles each into a single IIFE
// that the HTML can load with a normal <script> tag — no in-browser
// Babel transpile, no 3MB runtime cost.
//
// Run: node build.js          (one-shot build)
//      node build.js --watch  (re-build on file change)
//
// Output: public/assets/bundle/site.js
//         public/assets/bundle/print.js
//
// The GitHub Pages workflow (.github/workflows/pages.yml) runs
// `npm run build` before uploading public/ as the Pages artifact.

const esbuild = require('esbuild');
const fs = require('fs');
const crypto = require('crypto');
const path = require('path');

const watch = process.argv.includes('--watch');

const common = {
  bundle: true,
  format: 'iife',
  loader: { '.jsx': 'jsx' },
  // Keep React's "development" / "production" check honest:
  define: { 'process.env.NODE_ENV': '"production"' },
  minify: true,
  sourcemap: true,
  // The JSX files reference React / ReactDOM as globals — entry files
  // assign window.React and window.ReactDOM before importing the JSX,
  // so subsequent code resolves them via window.
  target: ['chrome90', 'firefox90', 'safari14', 'edge90'],
  logLevel: 'info',
};

const builds = [
  { entry: 'src/site-entry.js',  out: 'public/assets/bundle/site.js',  html: 'public/index.html' },
  { entry: 'src/print-entry.js', out: 'public/assets/bundle/print.js', html: 'public/print.html' },
];

// Cache-bust the bundle URL in HTML by appending ?v=<content-hash>. Without
// this, Cloudflare's CDN and end-user browsers can serve a stale bundle for
// minutes-to-hours after a deploy. Content hash means the URL only changes
// when bundle content changes — identical builds keep caches warm.
function stampHtml(htmlPath, bundleRelPath, hash) {
  const html = fs.readFileSync(htmlPath, 'utf8');
  // Match the bundle reference with or without an existing ?v= query.
  const escaped = bundleRelPath.replace(/[.]/g, '\\.');
  const re = new RegExp(`(src="${escaped})(\\?v=[a-f0-9]+)?(")`, 'g');
  let replaced = false;
  const next = html.replace(re, (_m, a, _q, c) => { replaced = true; return `${a}?v=${hash}${c}`; });
  if (!replaced) {
    throw new Error(`stampHtml: no <script src="${bundleRelPath}"> found in ${htmlPath}`);
  }
  if (next !== html) fs.writeFileSync(htmlPath, next);
}

function hashFile(p) {
  return crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex').slice(0, 12);
}

async function run() {
  if (watch) {
    for (const b of builds) {
      const ctx = await esbuild.context({
        ...common,
        entryPoints: [b.entry],
        outfile: b.out,
      });
      await ctx.watch();
      console.log(`watching: ${b.entry} → ${b.out}`);
    }
  } else {
    for (const b of builds) {
      await esbuild.build({
        ...common,
        entryPoints: [b.entry],
        outfile: b.out,
      });
      const hash = hashFile(b.out);
      const bundleRel = path.relative('public', b.out);
      stampHtml(b.html, bundleRel, hash);
      console.log(`built:    ${b.entry} → ${b.out}  [${hash}]`);
    }
  }
}

run().catch(err => { console.error(err); process.exit(1); });
