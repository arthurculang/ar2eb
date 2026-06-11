# LAUNCH — 1 July 2026 "start fresh" (spec §15, decision D3)

The launch: **hide every pre-launch memo from public view** (they move to a
truly-private archive), **publish the first official set** (the same tickers,
freshly stamped — optionally re-priced), and **begin performance tracking**
from t₀ = 2026-07-01 (automatic — `epoch` in `portfolio/weights.yml`; the
daily Routine starts committing rows after the first post-epoch close).

Tooling: **`scripts/launch_archive.py`** (built + self-tested 2026-06-11; the
flip's stamp transform passes on all 20 live YMLs). Everything below is
push-button; the only judgment steps are marked.

**What "hide" actually does:** the site links each memo's current PDF *and*
a "Prior versions (N)" history panel (from `stamp.prior_versions`); 41 PDF
versions have accumulated in `public/memos/`. The flip clears every
`prior_versions` block, removes all 41 pre-launch PDFs, and re-renders the
official set at one shared launch stamp — so the deployed site carries *only*
launch-day artifacts. **Caveat (decided, documented):** this repo is public,
so pre-launch memos remain reachable in git *history*; truly-private = the
separate archive repo. No history rewrite.

---

## T-minus (any time before 1 July) — owner, ~1 minute

- [ ] **Create the private archive repo:** github.com/new → name
  **`ar2eb-archive`** → **Private** → initialize with a README. That's all.
  (Claude's GitHub scope in remote sessions is `ar2eb`-only by default; a
  launch session can request it via `list_repos`/`add_repo`, or you push the
  export yourself — step 3 has both paths.)

## Launch day (1 July 2026) — in order

Run in a Claude Code session on this repo (or locally — prereqs:
`npm install`, `pip install playwright pyyaml`, poppler/`pdftoppm` for the
baseline, Chromium present). Work on a branch, e.g. `launch-2026-07`.

### 1. (Recommended, judgment) Re-price the official set

So the launch memos price off the June 30 close rather than the June 22
monthly PR: refresh `spot` + `market.market_cap_billion` per public ticker
from Yahoo — surgical numeric edits only, theses/scenarios untouched, skip
`private_prevaluation` (same mechanics as the monthly Routine's step 2).
Then `python portfolio/build_weights.py` so weights match launch prices.
Commit this separately *before* the flip. (Skipping is fine — then the
official set carries the June 22 prices.)

### 2. Export the pre-launch archive  *(safe, idempotent)*

```
python scripts/launch_archive.py --export
```

→ `archive-export/prelaunch-<date>/` (gitignored): all `data/` YAMLs, all 41
`public/memos/` PDFs, weights/performance, baseline, spec, and a `MANIFEST.md`
(git sha, per-ticker stamp/spot table, sha256 of every file). Eyeball the
MANIFEST.

### 3. Push the export to the PRIVATE repo

**Path A — from the Claude session:** ask it to add `ar2eb-archive` via
`add_repo`, then copy `archive-export/prelaunch-<date>/` in, commit, push.

**Path B — owner, locally:**
```
git clone git@github.com:arthurculang/ar2eb-archive.git
cp -r <ar2eb>/archive-export/prelaunch-<date> ar2eb-archive/
cd ar2eb-archive && git add -A && git commit -m "pre-launch archive (2026-07-01 launch)" && git push
```

Verify the MANIFEST renders on the private repo before proceeding — the flip
guard requires a same-day export to exist locally (`--skip-export-check`
overrides if you exported/pushed earlier).

### 4. The flip  *(destructive to the tree; reviewed, not auto-committed)*

```
python scripts/launch_archive.py --flip          # prints the plan (dry run)
python scripts/launch_archive.py --flip --yes    # executes
```

Does, in order: every stamp → version+1 at one shared launch timestamp with
`prior_versions` cleared → `git rm` all 41 pre-launch PDFs → full pipeline
(validate → site data → bundle → `MEMO_FORCE`+`STRICT_LAYOUT` rebuild of all
20 → regenerate `tests/visual_baseline.json`) → `git add -A`. Refuses on a
dirty tree. Verifies every official PDF landed before staging.

### 5. Review, PR, merge

- `git diff --cached --stat` — expect: 20 YMLs (stamp-only), 41 PDFs deleted,
  20 added, `data.js`/bundles/baseline regenerated.
- `python scripts/validate.py` green · `python scripts/visual_hash.py --check`
  green · spot-check one memo page in `out/`.
- Commit (e.g. `Launch 2026-07-01: official set v+1, pre-launch memos
  archived`), PR, merge → Pages deploys ar2eb.com.

### 6. Post-launch checks

- [ ] Site memo pages show **no "Prior versions" panel**.
- [ ] An old PDF URL (grab one from the MANIFEST) → **404**.
- [ ] July 1 after close (~22:00 UTC): first `portfolio/performance.csv` row
  appears via the daily Routine; benchmarks populated.
- [ ] `portfolio/weights.yml` reflects launch prices (if step 1 ran).

## Rollback

Revert the launch PR — stamps, PDFs, history panels and baseline all return
(git keeps everything). The archive repo is additive and unaffected.
