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
// Cloudflare Pages auto-runs `npm run build` when its Build command is
// set to that. See PR description for the one-time settings change.

const esbuild = require('esbuild');
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
  { entry: 'src/site-entry.js',  out: 'public/assets/bundle/site.js'  },
  { entry: 'src/print-entry.js', out: 'public/assets/bundle/print.js' },
];

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
      console.log(`built:    ${b.entry} → ${b.out}`);
    }
  }
}

run().catch(err => { console.error(err); process.exit(1); });
