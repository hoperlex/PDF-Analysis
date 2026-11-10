# Task QUAL-01 — the quality table for the administrator

## Outcome
A table for the administrator: the share of accepted findings by `stage_plan` cell and section; an ensemble as its own row; the model is read from the cell (`ADR-0029` decision 11).

Owner: the quality lane.

## Depends on
- CRIT-SEAL-51

Dispatch the lane only when every task above is merged into the base it works from.

## Frozen inputs
- domain contract: 1.49.0, unchanged until the seal
- API contract: 1.49.0, unchanged until the seal
- analysis/comparison/event contract: 1.49.0, unchanged until the seal
- migration head: `0062_hosts_stage_models`, unchanged until the seal
- the seal: 1.50.0 / `0063`, or the next free numbers if the AR v3 removal wave merges first
- base commit: `47c90e1ec6adf160f788e69279819c0e9c048e8e`
- ADR: `ADR-0029` decision 11; `R-153ak`
- `model_identity` is not copied into the memory (`D-392`), so the model comes from the cell
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
- `src/auditmanager/precedents/**`
- `src/auditmanager/api/routers/**`
- `web/src/_pages/workers/**`
- `web/tests/unit/workers/**`

## Forbidden hotspots
- `contracts/**` and `db/migrations/**`, unless the lane owns them below
- `src/auditmanager/bootstrap/composition.py` and `src/auditmanager/bootstrap/adapters.py`, unless the lane owns them below
- `pyproject.toml`, `uv.lock`, `web/package-lock.json`, `web/src/app/globals.css`
- `VERSION` and `release-notes/**`, unless the lane owns them below
- the historical records `docs/program/tasks/**` (except the new task files of `CRIT-ADR-29`) and `docs/manual-tests/**`
- any path outside `Allowed paths`; a path a lane needs and lacks is named in its report, not taken

## Non-goals
- no ranking that changes any routing

## Deliverables
- the read model and the admin table; the ensemble as one row; counts, not a score

## Required tests
- command: .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <the test files named above>; from `web/`: `npx vitest run --maxWorkers=1 <files>`, `npx tsc --noEmit -p .` and `npx eslint <files>`
- expected: pass; each check below can fail, and a lane shows the test that proves it can
- a cell with no decisions shows no share
- the table is administrator-only

## Integration contract
Reads decisions through `decision_memory.public`.

## Failure/idempotency/security cases
- no decisions give an empty table, not zeros that look like data

## Rollback / feature flag
Hide the table.

## Handoff
- changed files: `git diff --stat <base>..HEAD` and a proof that the forbidden hotspots are untouched
- commands/results: each check with its exact command, the tree SHA and the counts; «not run» with the reason
- known limits: stated, with `path:line` evidence for any departure from the plan
- integration notes: what the integrator must do next
- visible change: a preview in light and dark at 1280 and 390 px with DOM facts under `.local/reports/<lane>-2026-11-10/`; the lane reports the paths and stops, and the commit of visual changes waits for the owner
