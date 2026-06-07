# Routines — the two scheduled jobs run from Claude (spec §15, v037)

The §15 cadence runs on **Claude Code Routines** (cloud), not GitHub Actions.
A Routine is a saved prompt + repo + schedule that Claude runs **unattended on
Anthropic's infrastructure** — no machine on, no open session, durable across
restarts. (This replaced `daily-performance.yml` + `monthly-rebuild.yml`, deleted
in v037. The site deploy `pages.yml` stays a plain Action, triggered by the
Routine's commit.)

## Why Routines (and why this clears your old setup chores)

Routines execute on your **Claude subscription**, so:

- **No `ANTHROPIC_API_KEY` repo secret** — Claude *is* the runtime; the jobs only
  call keyless feeds (Yahoo `query1.finance.yahoo.com`, SEC `data.sec.gov`).
- **No "Actions → Read and write" toggle** — a Routine commits through its own
  GitHub connection, not Actions' `GITHUB_TOKEN`.
- **No live session / no machine** — unlike `/loop`, which only runs in a live
  session and expires after 7 days.

Tradeoff: Routines draw on subscription usage (incl. the daily run) vs. Actions'
free CI minutes — negligible at a weekday + monthly cadence. Minimum interval is
**1 hour** (irrelevant here).

---

## One-time setup (~2 min, owner only)

Routines can't be created from inside a remote-exec Claude session, so create
them once yourself:

1. Go to **https://claude.ai/code/routines** → **New routine** (or, in an
   interactive Claude Code session, run `/schedule`).
2. **Connect the repo** `arthurculang/ar2eb` as the routine's source (same
   GitHub connection Claude Code on the web already uses).
3. Create **two** routines using the configs below — paste the prompt, set the
   schedule, pick the model, leave env vars empty (feeds are keyless).
4. Save. They activate immediately; the daily one **no-ops until the launch
   epoch** (`epoch: 2026-07-01` in `weights.yml`), so it's safe to create now.

**Confirm two things at setup (I can't see them from here):**

- **Direct push to `main` isn't blocked** by branch protection. If it is, change
  the daily prompt's "push to `main`" to "open a PR" (noisier, but works).
- The repo shows up as a **connected source** in your Routines workspace.

To test without waiting for the schedule: open the routine and use **Run now**
(or just run `python portfolio/track_performance.py` locally — it's the same
script).

---

## Routine 1 — `ar2eb daily performance`

Deterministic. The prompt only runs the tracking script and commits the appended
row; no judgment, so use a cheap/fast model.

| Field | Value |
|---|---|
| **Name** | `ar2eb daily performance` |
| **Repository** | `arthurculang/ar2eb` |
| **Model** | Haiku (it doesn't reason — just runs a script) |
| **Schedule** | Weekdays, after the US close. Custom cron: `0 22 * * 1-5` (22:00 UTC = comfortably after the 16:00 ET close in both EST and EDT). If the UI offers a timezone/preset, "weekdays ~17:00 ET" is equivalent. |
| **Env vars** | none |

**Prompt** (paste verbatim):

```
Run `python portfolio/track_performance.py` from the repo root (run
`pip install pyyaml` first if the import fails). It appends one row to
`portfolio/performance.csv` — the weighted portfolio vs. the benchmark sleeve,
since the launch epoch.

Then:
- If `portfolio/performance.csv` changed, stage ONLY that file, commit with the
  message `perf: portfolio vs benchmarks <today's UTC date, YYYY-MM-DD>`, and
  push to `main`.
- If it did NOT change (pre-launch epoch, weekend, or market holiday), do
  nothing and end.

Do not edit any other file, do not reformat anything, and do not make any
analytical judgment — this is a deterministic data append.
```

---

## Routine 2 — `ar2eb monthly rebuild`

Agentic (D2) — the refresh carries judgment (re-price + flag theses that look
stale enough to warrant human re-research). Opens a PR; does **not** self-merge.

| Field | Value |
|---|---|
| **Name** | `ar2eb monthly rebuild` |
| **Repository** | `arthurculang/ar2eb` |
| **Model** | Opus |
| **Schedule** | The 22nd, mid-morning ET. Custom cron: `0 13 22 * *` (13:00 UTC; date-driven, not market-time-sensitive). |
| **Env vars** | none |

**Prompt** (paste verbatim):

```
Monthly ar2eb rebuild (spec §15, conviction-neutral §3.5 B). Open a PR titled
"Monthly rebuild <YYYY-MM>" containing, in order:

1. ARCHIVE the prior month — move the currently published memos into
   archive/<YYYY-MM>/ (an immutable record; do not delete history).

2. MECHANICAL RE-PRICE (judgment only on edge cases) — for each public
   data/<ticker>.yml, refresh `spot` and `market.market_cap_billion`
   (= current price × shares) from current Yahoo prices. SURGICALLY edit only
   those numeric lines — do NOT reformat the file or touch the theses/scenarios.
   Skip private_prevaluation names. Then re-render via the pipeline:
   validate.py → build_site_data.py → `node build.js` →
   `python scripts/rebuild_all.py --strict-layout` (STRICT_LAYOUT=1).

3. RE-WEIGHT — run `python portfolio/build_weights.py` to refresh
   portfolio/weights.yml from the new findings.

4. JUDGMENT PASS (why this job is agentic, not a cron script): list, in the PR
   description, any ticker whose entry-price-vs-distribution finding has moved
   enough that a full human RE-RESEARCH looks warranted. DO NOT rewrite theses —
   only flag them.

Keep everything observable/fundamentals-only. Leave the PR for review; do not
self-merge.
```

---

## Launch (1 July 2026)

`epoch: 2026-07-01` in `weights.yml` is t₀ for performance — the daily routine
commits nothing before then (the script returns no new row), so both routines
can be created today and simply idle until launch. The "start fresh" archive
move (hide pre-launch memos to a truly-private archive, §15 D3) is a separate
launch-day action, not part of these routines.
