# Task CRIT-SEAL-51 — the second seal: patterns, cross-document evidence, parameter facts

## Outcome
One contract version and one migration for the wave 5 tables: `decision_memory_pattern` and its status journal, `finding_cross_evidence`, `project_parameter_fact`, `FindingCategory += parameter_mismatch`. Numbers: the numbers after the first seal (planned 1.51.0 / `0064`, or the next free numbers).

Owner: the slot holder, appointed by the integrator.

## Depends on
- PREC-PASS
- PREC-WEB

Dispatch the lane only when every task above is merged into the base it works from.

## Frozen inputs
- domain contract: 1.49.0, unchanged until the seal
- API contract: 1.49.0, unchanged until the seal
- analysis/comparison/event contract: 1.49.0, unchanged until the seal
- migration head: `0062_hosts_stage_models`, unchanged until the seal
- the seal: 1.50.0 / `0063`, or the next free numbers if the AR v3 removal wave merges first
- base commit: `47c90e1ec6adf160f788e69279819c0e9c048e8e`
- ADR: `ADR-0029` decisions 11 and 12
- paths and pins: as `CRIT-SEAL-50`, with the next numbers
- plan: the «Прецеденты» plan (version 5, with the R-154 correction) is the integrator's working copy `.local/evidence/lane-common-prec/plan-v5.md` and is not in git; the decisions it carries are in `ADR-0029`
- rules: the common rules of the programme (`.local/evidence/lane-common-prec-2026-11-10.md`, git-ignored): minimal checks only, tests under the host lock, no push, merge or tag
- the plan read the code at `5342b7178`, which has the same code as the base; every `path:line` the lane relies on is checked in its own worktree before use

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json`, `db/migrations/versions/` and the recovery sets in `scripts/recovery/product_purge.py`
- enumerator_owner: CRIT-SEAL-51
- totality_query: `git grep -n "0064" -- db/migrations/versions` and the operation ids added to `contracts/api/v1/openapi.json`

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
- `db/migrations/versions/**`
- `contracts/api/v1/**`
- `contracts/domain/v1/**`
- `contracts/analysis/v1/**`
- `contracts/events/v1/**`
- `src/auditmanager/api/schemas/**`
- `src/auditmanager/api/routers/**`
- `src/auditmanager/api/security.py`
- `src/auditmanager/shared/identity/**`
- `web/openapi/openapi.json`
- `web/src/shared/api/**`
- `web/FRONTEND_LOCK.json`
- `scripts/recovery/product_purge.py`
- `scripts/recovery/grant_classification.py`
- `scripts/recovery/schema_coverage.py`
- `scripts/recovery/memory_forget.py`
- `infra/deploy/apply-grants.sh`
- `infra/deploy/proxy/**`
- `tools/executor-runner/RUNNER_API.md`
- `tests/contract/**`
- `tests/integration/db/**`
- `tests/integration/recovery/**`
- `tests/integration/runs/test_stage_plan_db.py`
- `tests/support/expected_facts.json`
- `tests/unit/api/**`
- `tests/unit/runs/**`
- `tests/unit/executor_runner/**`
- `web/tests/unit/**`
- `web/tests/guards/**`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots
- `contracts/**` and `db/migrations/**`, unless the lane owns them below
- `src/auditmanager/bootstrap/composition.py` and `src/auditmanager/bootstrap/adapters.py`, unless the lane owns them below
- `pyproject.toml`, `uv.lock`, `web/package-lock.json`, `web/src/app/globals.css`
- `VERSION` and `release-notes/**`, unless the lane owns them below
- the historical records `docs/program/tasks/**` (except the new task files of `CRIT-ADR-29`) and `docs/manual-tests/**`
- any path outside `Allowed paths`; a path a lane needs and lacks is named in its report, not taken
- in `db/migrations/versions/**` only the new file is added

## Non-goals
- no behaviour: stubs only until `PAT-01`, `QUAL-01`, `XDOC-01` land

## Deliverables
- `decision_memory_pattern` with a status journal; `finding_cross_evidence` (the second document's evidence with its `version_uid`); `project_parameter_fact`; `FindingCategory += parameter_mismatch`
- the command type `review_decision_pattern` and every new table and event classified in the recovery tools
- the pins moved as `CRIT-SEAL-50` did, with the captured sweeps repeated on the new base

## Required tests
- command: .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <the test files named above>
- expected: pass; each check below can fail, and a lane shows the test that proves it can
- as `CRIT-SEAL-50`: migration up/down/up, the classification guard, the inventories, `tests/contract/api_v1`

## Integration contract
Takes the numbers after the first seal, or the next free ones if another wave merged in between.

## Failure/idempotency/security cases
- an unclassified table, command or event makes the recovery guard refuse

## Rollback / feature flag
The migration with rows is not rolled back.

## Handoff
- changed files: `git diff --stat <base>..HEAD` and a proof that the forbidden hotspots are untouched
- commands/results: each check with its exact command, the tree SHA and the counts; «not run» with the reason
- known limits: stated, with `path:line` evidence for any departure from the plan
- integration notes: what the integrator must do next
