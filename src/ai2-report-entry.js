// AI 2.0 backtest report bundle entry — loaded by public/ai2_report.html.
// ai2_report.jsx auto-mounts when document.body.dataset.harness === 'report'.
// Assign React + ReactDOM to window via require() (not ESM import) so they
// exist before the JSX runs.

const React = require('react');
const ReactDOMClient = require('react-dom/client');

window.React = React;
window.ReactDOM = ReactDOMClient;

require('../public/ai2_report.jsx');
