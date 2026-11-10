# Task CTX-RUNNER — the executor client: one context request before the CLI call

## Outcome
In host mode, when a task has `context_request`, the client requests the context once (8 s, no retry) and appends one block after the JSON (`ADR-0029` decision 3).

Owner: the client lane.

## Depends on
- CTX-STAND

Dispatch the lane only when every task above is merged into the base it works from.

## Frozen inputs
- domain contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- API contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- analysis/comparison/event contract: 1.49.0 at the base; 1.50.0 once the AR v3 removal wave merges (`R-154h`)
- migration head: `0062_hosts_stage_models` at the base; `0063` once the AR v3 removal wave merges (`R-154h`)
- the seals: the first seal of this programme is 1.51.0 / `0064` (`R-154h`: the AR v3 removal wave takes 1.50.0 / `0063` first); the second is 1.52.0 / `0065` (`R-154h`)
- base commit: `47c90e1ec6adf160f788e69279819c0e9c048e8e`
- ADR: `ADR-0029` decision 3; plan section 3.3
- the CLI tools stay closed (`tools/executor-runner/claude_answer.py`, `tools/executor-runner/codex_answer.py`)
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
- `tools/executor-runner/**`
- `tests/unit/executor_runner/**`

## Forbidden hotspots
- `contracts/**` and `db/migrations/**`, unless the lane owns them below
- `src/auditmanager/bootstrap/composition.py` and `src/auditmanager/bootstrap/adapters.py`, unless the lane owns them below
- `pyproject.toml`, `uv.lock`, `web/package-lock.json`, `web/src/app/globals.css`
- `VERSION` and `release-notes/**`, unless the lane owns them below
- the historical records `docs/program/tasks/**` (except the new task files of `CRIT-ADR-29`) and `docs/manual-tests/**`
- any path outside `Allowed paths`; a path a lane needs and lacks is named in its report, not taken

## Non-goals
- no MCP
- no tools for the CLI

## Deliverables
- on 401, 409, 429, 5xx or a timeout the client calls the model without context, with the line «Справочные данные недоступны: причина»; the task never fails because of context; the `Retry-After` rule of the runner API does not apply to context
- the block is a separate section after the JSON of `user_text`, headed `=== СПРАВОЧНО (не основание) ===`; nothing is inserted at the start of the text; the answer carries `context_sha256` of the attached block

## Required tests
- command: .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <the test files named above>
- expected: pass; each check below can fail, and a lane shows the test that proves it can
- no waiting on a 429
- the block stands after the JSON
- the answer echoes `context_sha256`
- a context error does not fail the task
- the CLI tools stay closed

## Integration contract
The old agent keeps working without context; the new one reads an older stand's task.

## Failure/idempotency/security cases
- a refused or slow context never blocks the model call

## Rollback / feature flag
The old agent works without context.

## Handoff
- changed files: `git diff --stat <base>..HEAD` and a proof that the forbidden hotspots are untouched
- commands/results: each check with its exact command, the tree SHA and the counts; «not run» with the reason
- known limits: stated, with `path:line` evidence for any departure from the plan
- integration notes: what the integrator must do next
