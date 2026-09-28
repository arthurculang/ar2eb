# Routines — the three scheduled jobs run from Claude (spec §15, v037/v047/v048)

The §15 cadence runs on **Claude Code Routines** (cloud), not GitHub Actions.
A Routine is a saved prompt + repo + schedule that Claude runs **unattended on
Anthropic's infrastructure** — no machine on, no open session, durable across
restarts. (This replaced `daily-performance.yml` + `monthly-rebuild.yml`, deleted
in v037. The site deploy `pages.yml` stays a plain Action, triggered by the
Routine's commit.)

> **Status: all three Routines created by the owner (1–2 on 2026-06-07; the
> quarterly re-underwrite on 2026-07-22).** This file remains the reference
> config — if you change a routine in the UI, mirror the change here.
> **v048 (2026-09-28): re-paste the Routine 2 and Routine 3 prompts below into
> the UI.** The monthly now self-merges, and the quarterly enforces the
> book-wide spec checks.

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
3. Create the routines using the configs below — paste the prompt, set the
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

## Routine 2 — `ar2eb monthly rebuild` *(v048: self-merging)*

Agentic (D2), but mechanical at its core: the re-price is one deterministic
command (`scripts/reprice.py`), and the job's judgment is limited to edge cases
and to **flagging** (never rewriting) memos whose finding moved enough to
deserve the next quarterly re-underwrite. **Self-merges once every gate passes**
(owner decision 2026-09-28). The August PR (#87) sat unmerged for 31 days and
froze the site's findings from Jul 24 to Sep 22, and a human gate on a
mechanical job adds delay, not analysis. The PR stays the audit record.

| Field | Value |
|---|---|
| **Name** | `ar2eb monthly rebuild` |
| **Repository** | `arthurculang/ar2eb` |
| **Model** | Opus |
| **Schedule** | The 22nd, mid-morning ET. Custom cron: `0 13 22 * *` (13:00 UTC; date-driven, not market-time-sensitive). |
| **Env vars** | none |

**Prompt** (paste verbatim — replaces the pre-v048 PR-gated prompt):

```
Monthly ar2eb rebuild (spec §15, v048): a mechanical re-price of every public
memo, shipped autonomously. Open a PR titled "Monthly rebuild <YYYY-MM>" and
squash-merge it yourself once every gate in step 3 passes. Conviction-neutral
(§3.5 B): never touch conviction tiers, categories, the §12 sizing rule, or any
thesis argument, scenario value, or probability.

0. SETUP. Read CLAUDE.md first. Install: `pip install playwright pyyaml`,
   `npm install`, `apt-get update && apt-get install -y poppler-utils`. If an
   earlier "Monthly rebuild" PR is still open, close it with a comment that
   this run supersedes it.

1. RE-PRICE. Run `python scripts/reprice.py`. In one pass it bumps every public
   memo (the archive step), refreshes spot, market cap and date from Yahoo,
   keeps the price-history charts aligned, re-renders everything STRICT,
   re-weights the book, and regenerates the visual baseline. If it aborts:
   - on a failed price fetch: retry once; if it still fails, re-run with
     `--partial-ok` and list the skipped tickers as stragglers;
   - on a stock split since a memo's date: do not guess. Re-run with
     `--partial-ok` (the split name is skipped) and flag it for the quarterly
     re-underwrite to rescale shares and per-share fields.

2. PROSE NUMBER SYNC (mechanical). A re-price leaves hardcoded numbers in
   rendered prose stale (the page-1 companion line and the Deal leg's figure
   render live and need nothing). Run `python scripts/stale_prose.py` for
   candidates, then read each memo's rendered prose yourself: central
   question, thesis, masthead extras, scenario headlines and narratives,
   weighting rationale, pushback and triggers. Update numbers that restate
   the OLD spot price or market cap, a price-based multiple (rescale by the
   price change), a price move (recompute from the memo's own price-history
   points, or delete it), the headline result, or a scenario's value vs spot,
   plus any fair/cheap/rich wording that follows directly from them. Keep
   each field no longer than before. Change nothing else: no argument,
   scenario value or probability. Never write a capitalized word followed by
   colon-space inside an unquoted YAML value. Then, for the edited memos:
   `python scripts/validate.py`, `python scripts/build_site_data.py`,
   `node build.js`, `MEMO_FORCE=1 python scripts/rebuild_all.py --strict-layout <tickers>`,
   `python scripts/visual_hash.py <tickers>`.

3. GATES. All must pass before merging:
   - `python scripts/validate.py` reports no ERROR;
   - every render is STRICT-clean (no page overflow, no clipped chart text);
   - `python scripts/visual_hash.py --check` is clean;
   - `public/data.js` is in sync (re-running build_site_data.py leaves no diff).
   If a page overflows, trim that memo's OWN prose (see "Authoring gotchas" in
   CLAUDE.md), never the shared layout. If a ticker still fails after honest
   fixes, revert it to main (`git checkout origin/main -- data/<t>.yml` and
   delete its new PDF), re-run build_site_data.py,
   `python scripts/visual_hash.py <t>` and the gates, and list it as a
   straggler.

4. JUDGMENT PASS (flag, never rewrite). In the PR description, list every
   ticker whose finding flipped sign or moved 15+ points, with old -> new
   finding and the price move behind it; these are inputs for the next
   quarterly re-underwrite. Also list any stragglers and why.

5. SHIP. Commit to a branch named `monthly/<YYYY-MM>`, push, open the PR with
   that description, then squash-merge it. If a gate cannot be made to pass
   for the book as a whole, do not merge: leave the PR open and make the
   blocking reason the first line of its description.
```

---

## Routine 3 — `ar2eb quarterly re-underwrite` *(v047; spec checks v048)*

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
public-facing: no internal spec jargon in any rendered field. If CLAUDE.md's
"Current state" lists flagged inputs for this quarterly, handle each one
explicitly and report its outcome in the PR description.

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

2b. SPEC CHECKS — on EVERY memo, CONFIRM verdicts included (these are the
   rules a re-underwrite does not reliably enforce on its own):
   - PUSHBACK OPPOSES THE HEADLINE (§3.5 B). Bullish finding: the pushback
     steelmans the bear case and `appendix.pushback_side: bear` is set.
     Bearish finding: it argues the bull case and the field is omitted. A
     sign flip flips the required side.
   - NUMERIC FALSIFIERS (§6d). Every `competitive.threats[].falsifier` states
     a measurable threshold, ideally with a date.
   - STOCK COMP (§4, v048). Where latest-FY stock comp exceeds ~8% of
     revenue, the model values FCF after stock comp on today's diluted share
     count (or models the dilution explicitly — never both). In a loss
     quarter the reported diluted count equals basic: add unvested awards and
     in-the-money options by the treasury method (converts carried as debt
     stay out) — COIN first. Projected operating margins must sit on the same
     after-stock-comp basis as the history chart. Re-model through the engine
     if not; re-check names near the line (ISRG, DASH).
   - COMPANION STATISTIC (§6b). Page 1 now renders "most likely case vs spot
     · chance at or below spot" automatically; confirm it reads correctly, and
     keep any thesis sentence that restates it in sync.
   - STALE PROSE. After your edits, every `python scripts/stale_prose.py`
     hit is either fixed or confirmed a false positive (it is a heuristic).
   - PRICE HISTORY. `reprice.py` keeps charts aligned; if a memo's page-1
     price history is visibly wrong, rebuild it with
     `python scripts/rebuild_history.py <ticker>`.

3. MECHANICAL REFRESH — after all qualitative edits land, run
   `python scripts/reprice.py` (installs: pip install playwright pyyaml;
   npm install; apt-get install -y poppler-utils). It bumps every public
   memo (the quarterly archive), refreshes spot/market-cap/date from Yahoo,
   re-renders everything STRICT, re-weights the book, and regenerates the
   visual baseline — the qualitative edits ride the same bump. The re-price
   moves spot again, so then repeat the monthly's PROSE NUMBER SYNC
   (portfolio/ROUTINES.md, Routine 2, step 2) on every memo and re-render the
   ones you edit.

4. SHIP — commit to a feature branch, push, open a PR titled "Quarterly
   re-underwrite <YYYY-Qn>" whose description lists per ticker: verdict,
   changes made with their evidence, and finding old → new — then MERGE it
   (squash). If a ticker's render or validation cannot be fixed after honest
   attempts, revert that ticker, ship the rest, and list the stragglers in
   the PR description. AUDIT INTEGRITY: if the run was resumed, the
   pressure-test round may have been regenerated with new proposal IDs. Build
   the PR's audit record only from the round that actually applied (the
   applied proposals' own IDs, their skeptic verdicts), never from an earlier
   round.
```

---

## Launch (1 July 2026)

`epoch: 2026-07-01` in `weights.yml` is t₀ for performance — the daily routine
commits nothing before then (the script returns no new row), so both routines
can be created today and simply idle until launch. The "start fresh" archive
move (hide pre-launch memos to a truly-private archive, §15 D3) is a separate
launch-day action, not part of these routines — see the root **`LAUNCH.md`**
(`scripts/launch_archive.py`).
