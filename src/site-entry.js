// Site bundle entry — wraps the public/*.jsx files + React.
//
// Output: public/assets/bundle/site.js (loaded by public/index.html).
//
// The JSX files reference React, ReactDOM, and window.AR2EB_* globals.
// We assign React + ReactDOM to window BEFORE loading the JSX files —
// using CommonJS require() not ES import, because ESM imports are
// hoisted and would run the JSX before our window assignments.

const React = require('react');
const ReactDOMClient = require('react-dom/client');

window.React = React;
window.ReactDOM = ReactDOMClient;

require('../public/components.jsx');
require('../public/pages.jsx');
require('../public/memo_pdf.jsx');
require('../public/app.jsx');
