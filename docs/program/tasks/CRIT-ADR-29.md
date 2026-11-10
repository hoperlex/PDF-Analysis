# Task CRIT-ADR-29 — ADR-0029, the owner's rulings and the task files of the precedents programme

## Outcome
`docs/architecture/adr/ADR-0029-precedents.md` records the decisions, the two temporary decisions with their end conditions and the accepted risks; `ADR-0027` and `DECISION-MEMORY-01` carry short dated amendments; `OWNER_RULINGS_2026-09-17.md` records every owner answer of 2026-11-10 in section 3.55; every lane of the programme has a task file. Documents only.

Owner: the planning lane (the «Прецеденты» programme).

## Depends on
- none (this task has no predecessor)

## Frozen inputs
- domain contract: 1.49.0, unchanged until the seal
- API contract: 1.49.0, unchanged until the seal
- analysis/comparison/event contract: 1.49.0, unchanged until the seal
- migration head: `0062_hosts_stage_models`, unchanged until the seal
- the seal: 1.50.0 / `0063`, or the next free numbers if the AR v3 removal wave merges first
- base commit: `47c90e1ec6adf160f788e69279819c0e9c048e8e`
- plan: wave 0 of the «Прецеденты» plan (the integrator's copy, git-ignored)
- ADR: `ADR-0027`, `ADR-0028`, `ADR-0021`; `docs/program/DECISION-MEMORY-01.md`
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
- `docs/architecture/adr/**`
- `docs/program/OWNER_RULINGS_2026-09-17.md`
- `docs/program/DECISION-MEMORY-01.md`
- `docs/program/tasks/**`

## Forbidden hotspots
- `contracts/**` and `db/migrations/**`, unless the lane owns them below
- `src/auditmanager/bootstrap/composition.py` and `src/auditmanager/bootstrap/adapters.py`, unless the lane owns them below
- `pyproject.toml`, `uv.lock`, `web/package-lock.json`, `web/src/app/globals.css`
- `VERSION` and `release-notes/**`, unless the lane owns them below
- the historical records `docs/program/tasks/**` (except the new task files of `CRIT-ADR-29`) and `docs/manual-tests/**`
- any path outside `Allowed paths`; a path a lane needs and lacks is named in its report, not taken
- `docs/architecture/ADR_INDEX.md`: `scripts/validate_bootstrap.py` requires every ADR file to be indexed, so the integrator adds the row for `ADR-0029` (the lane reports the row, it does not take the path)
- existing task records under `docs/program/tasks/**`: only new files are added

## Non-goals
- no code, contract, migration or UI change
- no record of `R-154a`…`R-154d`: another lane owns section 3.54 of the rulings

## Deliverables
- `ADR-0029-precedents.md`; a dated addendum in `ADR-0027` (decisions 2, 3 and 6, Q8, Q4); dated notes in `DECISION-MEMORY-01` (Q4, Q8, Q9, Q10, section 5.3, phase M4)
- section 3.55 of the rulings: `R-153q`…`R-153ar`, one row per owner answer
- one task file per lane under `docs/program/tasks/`

## Required tests
- command: .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <the test files named above>
- expected: pass; each check below can fail, and a lane shows the test that proves it can
- `tests/contract/program/**` (prose, link and record guards) stay green; the task-file governance guard accepts every new file
- `scripts/task_handoff.py` reads every new task file (`read_task`) without a `HandoffError`

## Integration contract
Every other lane cites `ADR-0029 decision n` and its own task file. The integrator adds the `ADR-0029` row to `docs/architecture/ADR_INDEX.md` when it merges this lane.

## Failure/idempotency/security cases
- a guard that pins a count or a list these files change lies outside the allowed paths: the lane stops and reports it

## Rollback / feature flag
Not applicable: documents. Revert the commits.

## Handoff
- changed files: `git diff --stat <base>..HEAD` and a proof that the forbidden hotspots are untouched
- commands/results: each check with its exact command, the tree SHA and the counts; «not run» with the reason
- known limits: stated, with `path:line` evidence for any departure from the plan
- integration notes: what the integrator must do next
