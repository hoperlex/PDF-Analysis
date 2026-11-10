# Task MEM-COMMENTS-01 — comments in the decision memory: capture, carry-over, display

## Outcome
`comment` events are captured into `decision_memory_comment`; earlier comments are carried at a case's first ✓/✕; the «Память решений» tab shows them (`ADR-0029` decision 10).

Owner: the memory lane.

## Depends on
- CRIT-SEAL-50

Dispatch the lane only when every task above is merged into the base it works from.

## Frozen inputs
- domain contract: 1.49.0, unchanged until the seal
- API contract: 1.49.0, unchanged until the seal
- analysis/comparison/event contract: 1.49.0, unchanged until the seal
- migration head: `0062_hosts_stage_models`, unchanged until the seal
- the seal: 1.50.0 / `0063`, or the next free numbers if the AR v3 removal wave merges first
- base commit: `47c90e1ec6adf160f788e69279819c0e9c048e8e`
- ADR: `ADR-0029` decision 10; `ADR-0027` addendum 2026-11-10 (Q8)
- the table `decision_memory_comment` comes from the seal
- plan: the «Прецеденты» plan (version 5, with the R-154 correction) is the integrator's working copy `.local/evidence/lane-common-prec/plan-v5.md` and is not in git; the decisions it carries are in `ADR-0029`
- rules: the common rules of the programme (`.local/evidence/lane-common-prec-2026-11-10.md`, git-ignored): minimal checks only, tests under the host lock, no push, merge or tag
- the plan read the code at `5342b7178`, which has the same code as the base; every `path:line` the lane relies on is checked in its own worktree before use

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: none

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/decision_memory/**`
- `tests/unit/decision_memory/**`
- `tests/integration/decisions/**`
- `web/src/_pages/knowledge-base/**`
- `web/src/entities/decision-memory/**`
- `web/tests/unit/decision-memory/**`

## Forbidden hotspots
- `contracts/**` and `db/migrations/**`, unless the lane owns them below
- `src/auditmanager/bootstrap/composition.py` and `src/auditmanager/bootstrap/adapters.py`, unless the lane owns them below
- `pyproject.toml`, `uv.lock`, `web/package-lock.json`, `web/src/app/globals.css`
- `VERSION` and `release-notes/**`, unless the lane owns them below
- the historical records `docs/program/tasks/**` (except the new task files of `CRIT-ADR-29`) and `docs/manual-tests/**`
- any path outside `Allowed paths`; a path a lane needs and lacks is named in its report, not taken
- `src/auditmanager/bootstrap/**`: the wiring is `CRIT-CAPTURE-01`

## Non-goals
- no vote logic: a comment never changes a vote
- no wiring in the composition root

## Deliverables
- the capture of `comment` events as content of the memory (`KEEP`)
- the idempotent carry-over of earlier comments at a case's first ✓/✕
- a read of comments for the case view and the tab «Память решений» (no new concept on the screen: comments appear inside the case)

## Required tests
- command: .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <the test files named above>; from `web/`: `npx vitest run --maxWorkers=1 <files>`, `npx tsc --noEmit -p .` and `npx eslint <files>`
- expected: pass; each check below can fail, and a lane shows the test that proves it can
- a comment on a forgotten case is not inserted
- the carry-over of earlier comments is idempotent

## Integration contract
`PREC-PASS` reads comments through `decision_memory.public` for hint P1.

## Failure/idempotency/security cases
- capture failure cancels the decision, as `ADR-0027` decision 4 requires: no silent fallback

## Rollback / feature flag
The table empties only by forget.

## Handoff
- changed files: `git diff --stat <base>..HEAD` and a proof that the forbidden hotspots are untouched
- commands/results: each check with its exact command, the tree SHA and the counts; «not run» with the reason
- known limits: stated, with `path:line` evidence for any departure from the plan
- integration notes: what the integrator must do next
- visible change: a preview in light and dark at 1280 and 390 px with DOM facts under `.local/reports/<lane>-2026-11-10/`; the lane reports the paths and stops, and the commit of visual changes waits for the owner
