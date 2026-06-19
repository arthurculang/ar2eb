# portfolio/ — weights, performance, automation (spec §15)

The single-investor book and its daily performance track, plus the two scheduled
workflows that keep it current. **Live launch epoch: 1 July 2026** (`epoch` in
`weights.yml`) — the daily tracker is a no-op until then.

## Files

- **`build_weights.py`** → **`weights.yml`** — the deterministic three-factor sizing rule (§12 / §15 **D1**, v039):
  `weight ∝ max(0, weighted_DCF/spot − 1) × conviction_mult × arthur_indicator_mult`, capped 15%/name
  (water-filled), cash residual, long-only, **publicly-tradeable names only** (private excluded — no daily price).
  Conviction tier (High 2.0…Low 0.35) is the human input; the §13 Indicator zone (green 1.25…red 0.70, neutral
  where undefined) is the validated-OOS overlay. `weights.yml` carries the full per-name breakdown. Run anytime:
  `python portfolio/build_weights.py`. *(The site `<PortfolioPage>` computes the identical rule, interactively.)*
- **`track_performance.py`** → **`performance.csv`** + **`risk_stats.csv`** — daily weighted-portfolio
  cumulative return vs. a wide multi-asset benchmark sleeve (**D4**: VT · SPY/QQQ/IWM · EFA/EEM · AGG ·
  SHY/IEF/TLT · TIP · BIL · GLD · DBC · VNQ; BTC-USD optional), from Yahoo split/div-adjusted
  closes. **Also computes a modified Sortino ratio** for the portfolio vs. the **S&P 500 (SPY)** and
  **NASDAQ-100 (QQQ)** — `(annualized return − MAR) / annualized downside deviation`, where the downside
  deviation is the full-sample target semideviation below the MAR (denominator = all N periods, the
  statistically-correct form), MAR = realized risk-free (BIL) by default, annualized √252; Sharpe +
  downside-dev + max-drawdown reported alongside, snapshot persisted to `risk_stats.csv`. Deterministic —
  **no Claude**. `AI_EPOCH=YYYY-MM-DD` overrides the epoch (e.g. a trailing-window Sortino backtest before
  launch); `AI_MAR=<annual %>` overrides the target; `--sortino` runs only the Sortino comparison.

## Automation — Claude Routines (cloud), **`ROUTINES.md`** *(v037)*

| Routine | Cadence (UTC cron) | Engine | Model |
|---|---|---|---|
| `ar2eb daily performance` | weekdays `0 22 * * 1-5` (after US close) | **thin** Routine — just runs `track_performance.py` + commits | Haiku |
| `ar2eb monthly rebuild` | the **22nd** `0 13 22 * *` | **agentic** Routine (judgment refresh, **D2**) — opens a PR | Opus |

**Mechanism (§15, v037):** **Claude Code Routines** (`claude.ai/code/routines`), not GitHub Actions
and not `/loop`. Routines run unattended on Anthropic's cloud (no machine, no live session). This
replaced the two `.github/workflows/*.yml` jobs (deleted); `pages.yml` still deploys the site. The
monthly job is agentic because the refresh benefits from judgment (re-price + flag stale theses);
the daily job is deterministic arithmetic, so its Routine prompt just runs the script.

## One-time setup (repo owner — ~2 min, **in Claude, not GitHub**)

Create the two Routines once from **`ROUTINES.md`** (copy-paste configs). Because Routines run on
your Claude **subscription** and commit via their own GitHub connection:

- **No `ANTHROPIC_API_KEY` secret** and **no "Actions → Read and write" toggle** — both former
  chores are gone.
- The daily routine **no-ops until** `epoch: 2026-07-01`, so it's safe to create now.
- At setup, confirm direct push to `main` isn't blocked by branch protection (else switch the daily
  prompt to "open a PR"). Full steps in **`ROUTINES.md`**.

## Launch (1 July 2026)

`epoch: 2026-07-01` sets t₀ for performance. The "start fresh" step (hide pre-launch memos to a
**private** archive — **D3** — and publish the official set) is push-button:
`scripts/launch_archive.py` (`--export` then `--flip --yes`) with the day-of runbook in the root
**`LAUNCH.md`**.
