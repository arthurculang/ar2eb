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

## Automation (`.github/workflows/`)

| Workflow | Cadence | Engine | Needs |
|---|---|---|---|
| `daily-performance.yml` | weekdays ~22:00 UTC (after US close) | **plain script** | only repo **write permission** (no secret) |
| `monthly-rebuild.yml` | the **22nd**, ~13:00 UTC | **agentic Claude Code Action** (judgment refresh, **D2**) | Claude GitHub App + `ANTHROPIC_API_KEY` secret + write permission |

**Mechanism (§15):** scheduled **GitHub Actions cron**, not the `/loop` skill (which needs a live
session). The monthly job is agentic because the refresh benefits from judgment (re-price + flag
theses that look stale enough to warrant human re-research); the daily job is pure arithmetic, so
it stays a plain script. (A Claude **Routine** on the web is an equivalent alternative for the
monthly job — zero-config but off-repo.)

## One-time setup (repo owner)

1. **Settings → Actions → General → Workflow permissions → "Read and write"** — lets both jobs commit results back. *(Required for either workflow.)*
2. For the **monthly** (agentic) job only: install the **[Claude GitHub App](https://github.com/apps/claude)** and add the **`ANTHROPIC_API_KEY`** repo secret. *(The monthly job guards itself off until the secret exists.)*
3. Scheduled workflows activate once merged to `main` (GitHub runs `schedule:` from the default branch).

## Launch (1 July 2026)

`epoch: 2026-07-01` sets t₀ for performance. Separately, the "start fresh" step (hide pre-launch
memos to a **private** archive — **D3** — and publish the official set) is a launch-day action,
not automated here yet.
