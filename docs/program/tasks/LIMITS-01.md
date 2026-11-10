# Task LIMITS-01 — no answer cap reaches a model, a row's timeout is a code constant, the agent waits 600 s

Extended record: the task changes a shared contract (1.49.0) and a decision of `ADR-0028`, and it ships to a host agent that is installed
separately from the stand. Owner decisions of 2026-11-10 (poll): `R-153n`, `R-153o`, `R-153p` in `docs/program/OWNER_RULINGS_2026-09-17.md`
section 3.53. Analysis with file and line evidence: `.local/reports/limits-timeouts-2026-11-10.md` (git-ignored).

## Outcome
- No answer cap reaches any model: not in the layout, the frozen plan, the host task (`payload.host`) or the agent's call of a model.
- The call window of a stage cell is a code constant of its row (the original's values); «Модели по этапам» → «Изменить» has no
  «Дополнительно», no «Ответ, токенов» and no «Таймаут, с».
- The host agent extends a claim while its call produced output in the last 600 s (it was 120 s), equal to the stand's stall window.

## Depends on
- `HOSTS-L1` (contract 1.48.0, VERSION 0.23.0): completed, base `3ab7338fe`.

## Frozen inputs
- domain contract: 1.48.0 (domain catalogs at candidate revision 65; they move to 1.49.0 / revision 66 with this task)
- API contract: 1.48.0, 296 paths / 324 operations / 798 schemas
- analysis/comparison/event contract: 1.48.0 (versions move with the API contract)
- migration head: `0062_hosts_stage_models` (unchanged: migration 0062 checks only the key and the model of a cell)
- base commit: `3ab7338fe` (`origin/dev`, VERSION 0.23.0)

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No route, screen, error code, migration or schema is added or removed: three schemas lose members and one loses a member.

## Captured premise evidence
- premise: none

The analysis report above holds the file and line evidence; the lane re-read each place against the tree before editing, and the one premise
that changed shape is recorded under Handoff (the migration does not need the two numbers, so no stored value is written for them).

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `contracts/**`
- `web/openapi/**`
- `web/FRONTEND_LOCK.json`
- `web/src/shared/api/generated/**`
- `web/src/shared/api/credentialed-forward.ts`
- `web/src/entities/stage-layout/**`
- `web/src/features/manage-stage-layout/**`
- `web/src/widgets/run-stages-dialog/**`
- `web/tests/**`
- `src/auditmanager/runs/stage_layout.py`
- `src/auditmanager/runs/stage_layout_store.py`
- `src/auditmanager/runs/stage_facts.py`
- `src/auditmanager/runs/preflight.py`
- `src/auditmanager/analysis/text/cell_settings.py`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/analysis/engine/result.py`
- `src/auditmanager/executors/pull.py`
- `src/auditmanager/executors/runner.py`
- `src/auditmanager/bootstrap/stage_plan_service.py`
- `src/auditmanager/bootstrap/providers.py`
- `src/auditmanager/bootstrap/runner.py`
- `src/auditmanager/comparison/ai_jobs/**`
- `src/auditmanager/comparison/spend/**`
- `src/auditmanager/api/schemas/models.py`
- `src/auditmanager/api/routers/stage_models.py`
- `src/auditmanager/api/routers/run_stages.py`
- `src/auditmanager/api/routers/__init__.py`
- `tools/executor-runner/**`
- `tests/**`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/proxy/tls-server.conf`
- `docs/program/OWNER_RULINGS_2026-09-17.md`
- `docs/program/ALPHA_ROADMAP.md`
- `docs/program/CURRENT_STATE.md`
- `docs/architecture/adr/ADR-0028-hosts-and-stage-models.md`
- `docs/program/tasks/LIMITS-01.md`
- `release-notes/0.23.1.json`
- `VERSION`

Beyond the brief's list the lane touched six paths that the contract change makes unavoidable, each for one reason: `executors/runner.py`
and `bootstrap/runner.py` (the closed list of host members a claim hands over), `runs/stage_layout_store.py` and `runs/stage_facts.py` (the
two readers of a stored cell), `runs/preflight.py` (two reads of the renamed estimate figure) and `analysis/public.py` (the exported names).

## Forbidden hotspots
- `db/migrations/**`, root dependency or lock files, `docs/program/P02_LOCK.json`, global styles, other worktrees
- the composition root

## Non-goals
- No change to `analysis/extended/**`: its builders keep calling `limit_of(settings, default)`, which now returns the default (see Handoff).
- The legacy proxy route (a run with no stage plan) keeps the `max_tokens` its request bodies carry; the owner's ruling is about the layout's cells.
- No new model pin and no per-model maximum for Anthropic: the repository records none.
- The availability probe's own 4096-token ceiling on an API call stays.

## Deliverables
- `CellSettings` is a model and an effort (and an access in a plan); `timeout_seconds` and `estimate_output_tokens` are derived from the row.
- `HostCall` and `payload.host` without `max_output_tokens`; D-677's request-limit channel and the `min(cell, module)` capping removed.
- The agent: no `CLAUDE_CODE_MAX_OUTPUT_TOKENS`; no output-token parameter for OpenAI and OpenRouter; 64000 for Anthropic; `ACTIVITY_WINDOW_SECONDS` 600.
- Contract 1.49.0, the generated web client and the frontend lock.
- The editor without «Дополнительно»; the stage dialog without «ответ до N токенов».
- `R-153n`..`R-153p`, the `ADR-0028` addendum, VERSION 0.23.1 and its note.

## Required tests
- command: `.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <the touched modules' files>`, the contract seal tests and the
  release-note form test, then in `web/`: `npx tsc --noEmit -p .`, `npx eslint <changed files>`, `npx vitest run --maxWorkers=1 <changed test files>`
- expected: green, except two reds that are not this task's (listed under Handoff)

## Integration contract
- Consumer: the web client of contract 1.49.0 and the host agent of this version.
- Provider: the stand serves a task with six host members; an agent of this version reads a task of an older stand and ignores its cap.
- **Order of deployment.** Install the agent first (it reads both shapes), then publish the stand. An older agent refuses a task without
  `max_output_tokens` as `host_task_incomplete`.
- A frozen plan, a stored layout revision and a stored comparison estimate written before this task still read; their two numbers are not read.

## Failure/idempotency/security cases
- A layout write that names `max_output_tokens` or `timeout_seconds` is refused `422 validation_failed` (the objects are closed; nothing is ignored).
- A plan frozen before is read only if every cell carries both old members; a half-old plan is refused.
- The Claude Code child never inherits `CLAUDE_CODE_MAX_OUTPUT_TOKENS`.

## Rollback / feature flag
No flag. Rollback is a forward revert of the branch; the stand and the agent are then reverted together (the older agent needs the older task).

## Handoff
See the lane report. Debt-row candidates: the Anthropic maximum is 64000 by default, not a recorded per-model figure; `analysis/extended` still
calls `limit_of(settings, default)`; `test_layout_route.py::test_a_revision_that_follows_its_sets_table_gives_the_kind_the_sets_cell` was red at
the base (the fixture serves `gpt-6-astra`, the table gives `gpt-6-luna`).
