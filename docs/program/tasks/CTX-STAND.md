# Task CTX-STAND — context on the stand: descriptor, operation, 404 rules, idempotency, budget, journal, policy

## Outcome
The stand side of `ADR-0029` decision 3: `context_request` in the claim, `getExecutorTaskContext`, the 404 refusals, idempotency by (task, kind), the budget, the `KEEP` delivery journal and the policy in the consent. While temporary decision 2 stands the answer is `status: unavailable, reason: until_move`.

Owner: the stand lane; `src/auditmanager/runs/extended_review.py` after `F8-PUBLISH`.

## Depends on
- CRIT-SEAL-50
- F8-PUBLISH

Dispatch the lane only when every task above is merged into the base it works from.

## Frozen inputs
- domain contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- API contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- analysis/comparison/event contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- migration head: `0062_hosts_stage_models` at the base; `0063` once the AR v3 removal wave merges (`R-154h`)
- the seals: the first seal of this programme is 1.51.0 / `0064` (`R-154h`: the AR v3 removal wave takes 1.50.0 / `0063` first); the second is 1.52.0 / `0065` (`R-154h`)
- base commit: `47c90e1ec6adf160f788e69279819c0e9c048e8e`
- ADR: `ADR-0029` decision 3 and temporary decision 2; plan sections 3.2 and 3.5
- the policy is built like `norm_paragraph_context_policy`
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
- `src/auditmanager/executors/**`
- `src/auditmanager/api/routers/runner.py`
- `src/auditmanager/runs/preflight.py`
- `src/auditmanager/runs/extended_review.py`
- `tests/integration/executors/**`
- `tests/unit/executors/**`
- `tests/unit/runs/**`

## Forbidden hotspots
- `contracts/**` and `db/migrations/**`, unless the lane owns them below
- `src/auditmanager/bootstrap/composition.py` and `src/auditmanager/bootstrap/adapters.py`, unless the lane owns them below
- `pyproject.toml`, `uv.lock`, `web/package-lock.json`, `web/src/app/globals.css`
- `VERSION` and `release-notes/**`, unless the lane owns them below
- the historical records `docs/program/tasks/**` (except the new task files of `CRIT-ADR-29`) and `docs/manual-tests/**`
- any path outside `Allowed paths`; a path a lane needs and lacks is named in its report, not taken

## Non-goals
- no MCP, no CLI tools
- no precedents content until the encoder moves: `until_move`
- no reference block for plan v2: its critic is deterministic and reads none (`ADR-0029` decision 14)

## Deliverables
- the descriptor `context_request: [{input_id, text_sha256, section}]` only on `review:main` tasks of runs with a `stage_plan`
- the operation answers 404 for a legacy run, a cell other than `review:main`, a task that is not `run_call`, and a consent without the same `executor_context_policy`; a repeat for the same (task, kind) returns the same answer and spends no budget
- the budget: 2 requests and 12 000 characters per task; selection by window order, at most 3 cases per candidate, then «не уместилось: N»; `input_tokens_reserved_per_call` 5 000
- the journal `executor_task_context_delivery` (`KEEP`, no foreign keys, no text)
- the policy placed in the consent only while the switch «контекст критику» is on

## Required tests
- command: .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <the test files named above>
- expected: pass; each check below can fail, and a lane shows the test that proves it can
- a legacy run, a cell other than `review:main` and a comparison task get 404
- a repeat does not spend the budget
- a consent without the policy gets 404
- the journal survives the erase of a project and holds no text

## Integration contract
`CTX-RUNNER` calls the operation; `CTX-CRITIC` changes the critic's prompt; the three share `runs/extended_review.py` in order.

## Failure/idempotency/security cases
- a foreign token or a task without a claim never reads the context

## Rollback / feature flag
The switch «контекст критику».

## Handoff
- changed files: `git diff --stat <base>..HEAD` and a proof that the forbidden hotspots are untouched
- commands/results: each check with its exact command, the tree SHA and the counts; «not run» with the reason
- known limits: stated, with `path:line` evidence for any departure from the plan
- integration notes: what the integrator must do next
