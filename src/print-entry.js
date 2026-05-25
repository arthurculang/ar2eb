// Print harness bundle entry — loaded by public/print.html.
//
// memo_pdf.jsx auto-mounts when document.body.dataset.harness === 'print'.
// We assign React + ReactDOM to window via CommonJS require() (not ESM
// import — which would hoist and run the JSX before our assignments).

const React = require('react');
const ReactDOMClient = require('react-dom/client');

window.React = React;
window.ReactDOM = ReactDOMClient;

require('../public/memo_pdf.jsx');
