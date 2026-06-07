# portfolio/ — weights, performance, automation (spec §15)

The single-investor book and its daily performance track, plus the two scheduled
workflows that keep it current. **Live launch epoch: 1 July 2026** (`epoch` in
`weights.yml`) — the daily tracker is a no-op until then.

## Files

- **`build_weights.py`** → **`weights.yml`** — the deterministic sizing rule (§12 / §15 **D1**):
  `weight ∝ max(0, weighted_DCF/spot − 1)`, capped 15%/name (water-filled), cash residual,
  long-only, **publicly-tradeable names only** (private_prevaluation excluded — no daily price).
  Run by hand anytime: `python portfolio/build_weights.py`.
- **`track_performance.py`** → **`performance.csv`** — daily weighted-portfolio cumulative
  return vs. a wide multi-asset benchmark sleeve (**D4**: VT · SPY/QQQ/IWM · EFA/EEM · AGG ·
  SHY/IEF/TLT · TIP · BIL · GLD · DBC · VNQ; BTC-USD optional), from Yahoo split/div-adjusted
  closes. Deterministic — **no Claude**. `AI_EPOCH=YYYY-MM-DD` overrides the epoch for testing.

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

`epoch: 2026-07-01` sets t₀ for performance. Separately, the "start fresh" step (hide pre-launch
memos to a **private** archive — **D3** — and publish the official set) is a launch-day action,
not automated here yet.
