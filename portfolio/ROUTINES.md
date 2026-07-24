# Routines — the three scheduled jobs run from Claude (spec §15, v037/v047)

The §15 cadence runs on **Claude Code Routines** (cloud), not GitHub Actions.
A Routine is a saved prompt + repo + schedule that Claude runs **unattended on
Anthropic's infrastructure** — no machine on, no open session, durable across
restarts. (This replaced `daily-performance.yml` + `monthly-rebuild.yml`, deleted
in v037. The site deploy `pages.yml` stays a plain Action, triggered by the
Routine's commit.)

> **Status: all three Routines created by the owner (1–2 on 2026-06-07; the
> quarterly re-underwrite on 2026-07-22).** This file remains the reference
> config — if you change a routine in the UI, mirror the change here.

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
`pip install pyyaml` first if the import fails). It upserts one row into
`portfolio/performance.csv` — the weighted portfolio vs. the benchmark sleeve,
since the launch epoch — and, once enough return history has accrued, refreshes
`portfolio/risk_stats.csv` (the modified Sortino ratio for the portfolio vs. the
S&P 500 and NASDAQ-100).

Then:
- If `portfolio/performance.csv` and/or `portfolio/risk_stats.csv` changed, stage
  ONLY those two files, commit with the message
  `perf: portfolio vs benchmarks <today's UTC date, YYYY-MM-DD>`, and push to `main`.
- If neither changed (pre-launch epoch, weekend, or market holiday), do nothing and end.

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

1. BUMP = ARCHIVE — for each public data/<ticker>.yml (skip
   private_prevaluation names), run `python scripts/bump_pdf_version.py
   <ticker>`. This IS the archive step: the bump snapshots the OUTGOING stamp
   (version, timestamp, as-of date, spot) into stamp.prior_versions and
   increments the version, so the prior PDF stays in public/memos/ as immutable
   history AND the memo page's "Prior versions (N)" download panel gains one
   entry. Do NOT move PDFs into an archive/ directory — the prior_versions panel
   IS the on-site archive; a move would pull old PDFs out of public/memos/ and
   build_site_data.py would then drop those entries (it 404-guards each prior
   entry against disk).

2. MECHANICAL RE-PRICE (judgment only on edge cases) — for those same tickers,
   refresh `spot` and `market.market_cap_billion` (= current price × shares)
   from current Yahoo prices, and advance the top-level `date:` to today so each
   archived version carries its true as-of date. SURGICALLY edit only those
   numeric lines — do NOT reformat the file or touch the theses/scenarios.
   (Order matters: BUMP before RE-PRICE — the bump files the outgoing spot/date
   under the old version; the new spot/date belong to the new version.) Then
   re-render via the pipeline: validate.py → build_site_data.py →
   `node build.js` → `python scripts/rebuild_all.py --strict-layout`
   (STRICT_LAYOUT=1; every ticker was bumped, so each renders to its new
   versioned filename).

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

## Routine 3 — `ar2eb quarterly re-underwrite` *(v047)*

The holistic pass the monthly deliberately is not: a **full qualitative
re-underwrite** of every public memo — thesis, scenario values and narratives,
probability weights, competitive landscape (§6d Powers + falsifiers), triggers —
driven by fresh evidence, not just fresh prices. **Autonomous by design** (owner
decision, 2026-07-22): it applies its changes and **self-merges**; the PR it
opens is the audit record, not a gate. The owner intercedes only on a true
logical or methodological error.

| Field | Value |
|---|---|
| **Name** | `ar2eb quarterly re-underwrite` |
| **Repository** | `arthurculang/ar2eb` |
| **Model** | Opus (deep agentic research + judgment) |
| **Schedule** | The 15th of Jan/Apr/Jul/Oct (a week ahead of the monthly's 22nd, so the monthly then re-prices the freshly re-underwritten book). **As created (2026-07-22): 1:00 PM PT = `0 20 15 1,4,7,10 *`** — the runbook had proposed 13:00 UTC; the created time stands (date-driven job, hour immaterial). |
| **Env vars** | none |

**Prompt** (paste verbatim):

```
Quarterly ar2eb re-underwrite (spec §15.3) — the full qualitative pressure-test
of every public memo. Unlike the monthly rebuild (mechanical re-price only),
this pass re-underwrites the ANALYSIS: thesis, scenario narratives and values,
probability weights, competitive landscape (§6d Powers and falsifiers), and
triggers. It is AUTONOMOUS: apply the changes and self-merge — do not wait for
human review. Surface only genuine methodology dilemmas, prominently, in the PR
description.

First read CLAUDE.md and spec/memo-spec.md (§3.5, §6b, §6c, §6d, §15.3). Hard
rules: conviction-neutral (§3.5 B) — NEVER touch conviction tiers, category
assignments, or the §12 sizing rule, and no analytical change may rest on
belief or preference: dated, sourced, observable evidence only. Every changed
number must be re-modeled through the engines (scripts/_models/ — model_dcf
for young_company, the mature engine for mature/SOTP) so the validator's
equity-bridge identities tie to the cent. Never fabricate value to make a
model work; if evidence is ambiguous, leave the memo unchanged and say why.
Respect the YAML-safety and page-trim gotchas in CLAUDE.md. The site is
public-facing: no internal spec jargon in any rendered field.

Per public ticker (every data/*.yml except dcf_type private_prevaluation),
in batches of ~6 parallel research subagents:

1. TRIAGE — web-research what changed since the memo's date: news, filings,
   guidance, clinical/regulatory events, competitive moves, capital actions.
   Verdict per ticker: RE-UNDERWRITE (evidence that a thesis element,
   scenario, probability, or Power assessment is stale) or CONFIRM (no
   material qualitative change — record a one-line confirmation with the
   evidence checked).

2. RE-UNDERWRITE (only where triage says so) — draft the specific yml changes
   with the evidence for each; ADVERSARIALLY VERIFY before applying (an
   independent skeptic pass per change: is each cited fact real and datable?
   is the change methodologically sound — monotonic scenarios, §6c.11.2
   spread rule, §6c.18 floors, p_fail/dilution honesty? do the numbers tie
   through the bridge?). Apply only what survives. Re-run
   scripts/validate.py after each ticker's edits.

3. MECHANICAL REFRESH — after all qualitative edits land, run
   `python scripts/reprice.py` (installs: pip install playwright pyyaml;
   npm install; apt-get install -y poppler-utils). It bumps every public
   memo (the quarterly archive), refreshes spot/market-cap/date from Yahoo,
   re-renders everything STRICT, re-weights the book, and regenerates the
   visual baseline — the qualitative edits ride the same bump.

4. SHIP — commit to a feature branch, push, open a PR titled "Quarterly
   re-underwrite <YYYY-Qn>" whose description lists per ticker: verdict,
   changes made with their evidence, and finding old → new — then MERGE it
   (squash). If a ticker's render or validation cannot be fixed after honest
   attempts, revert that ticker, ship the rest, and list the stragglers in
   the PR description.
```

---

## Launch (1 July 2026)

`epoch: 2026-07-01` in `weights.yml` is t₀ for performance — the daily routine
commits nothing before then (the script returns no new row), so both routines
can be created today and simply idle until launch. The "start fresh" archive
move (hide pre-launch memos to a truly-private archive, §15 D3) is a separate
launch-day action, not part of these routines — see the root **`LAUNCH.md`**
(`scripts/launch_archive.py`).
