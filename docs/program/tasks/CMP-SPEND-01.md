# Task CMP-SPEND-01 — the comparison spend journal, its call wrapper, the USD ceilings and the one-connection check

## Outcome
On `integration/compare-modules` every model call of the comparison modules goes through one wrapper that
(1) commits a `prepared` row of `comparison_model_call` in its own transaction before the adapter is called,
(2) refuses before the call when a USD ceiling (`Q-CMP-7`: USD 10 per job, USD 50 per day per installation), the
consent binding {estimate digest, ceiling, connection revision, pinned model}, the connection's single user or the
reply-model identity (`R-133`) says no, (3) marks `sent`, then `completed`, `failed` or `unknown`, (4) pauses the job
at an actual spend above 1.2 x the estimate, and (5) never lets a reclaim re-send a call that was `prepared` or `sent`
(`spend_unknown`); a connection's one-active-run check also counts an active comparison call on it; the deployment
spend of the dashboard is the union of the two journals. Each guard is shown failing under a quoted mutation.

## Depends on
- CMP-SEAL-C0 (migration `0038_comparison_foundation`: `comparison_model_call`, the `comparison_call` origin of `executor_task`)
- CMP-WORK-01 (`SPEND_SETTLERS`, `WorkItem`, `WorkDependencies`, `Failed` / `Yielded`)
- CMP-EXEC-IMAGES-01 (`attach_images`, `image_load`; the named refusal `executor_image_input_unsupported`)

## Frozen inputs
- domain contract: `contracts/domain/v1/**` (prefix `cmc` exists; `ComparisonModelCallId`)
- API contract: `contracts/api/v1/openapi.json` `1.9.0`, 115 paths / 130 operations / 351 schemas (this lane changes none)
- analysis/comparison/event contract: ADR-0025 decisions 5, 6, 19 and the 2026-10-27 addendum; `Q-CMP-7`; `R-29`; `R-133`
- migration head: `0038_comparison_foundation` (this lane changes none; a missing column is a STOP)
- base commit: `34dcf9a1` on `integration/compare-modules`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

(The one set this lane touches is `SEALED_NOT_YET_WRITTEN` in `scripts/recovery/grant_classification.py`: it removes its own
table, `comparison_model_call`, by the wave brief's wiring rule 4.)

## Captured premise evidence
- premise: contract `1.9.0`, 115 / 130 / 351, head `0038_comparison_foundation`, base `34dcf9a1` (wave brief section 1.1); the lane
  re-read them before any edit and STOPs if they differ

### P-01 — the base facts the lane re-read before any edit
- captured_at: 2026-10-28
- command: `git rev-parse HEAD; python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas',len(d['components']['schemas']['ErrorCode']['enum']),'error codes')"; cat VERSION; grep -n "^revision: str" db/migrations/versions/20261028_0038_comparison_foundation.py`
- captured_output:
  ```text
  34dcf9a1dad7c4f9e3ac131eb990ab673502dc12
  contract 1.9.0 115 paths 130 operations 351 schemas 27 error codes
  0.9.0
  81:revision: str = "0038_comparison_foundation"
  ```
- interpretation: equal to the premise (contract `1.9.0`, 115 / 130 / 351, head `0038_comparison_foundation`), so the lane did not STOP

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/spend/**`
- `src/auditmanager/dashboard/repository.py`
- `src/auditmanager/executors/runner_repository.py`
- `src/auditmanager/jobs/repository.py`
- `src/auditmanager/comparison/public.py`
- `scripts/recovery/grant_classification.py`
- `tests/unit/comparison/spend/**`
- `tests/integration/comparison/spend/**`
- `docs/program/CMP-SPEND-01.md`
- `docs/program/tasks/CMP-SPEND-01.md`

The first three and the two test directories are the wave brief's row. `src/auditmanager/jobs/repository.py` is open **only** by the
grant of the `PROD-20` owner, asked by the integrator (the PW5 integrator's grant, conditions binding): exactly one query, the
one-active-run-per-connection check; no schema change; no other edit anywhere in `src/auditmanager/jobs/**`; a mutation proof; a test
that a plain run still serialises per connection as before; the `EXEC-PAR-QUEUE-01` tests stay green unmodified; the function name and
the before/after SQL are quoted in the report. `comparison/public.py` and `grant_classification.py` are the wave brief's wiring rule 4
(appends for this lane's names only; the removal of `comparison_model_call` from `SEALED_NOT_YET_WRITTEN`).

## Lane resources
- foundation_instance: `auditmanager-cmp-spend-01`
- postgres_port: `57780`
- s3_api_port: `61780`
- s3_console_port: `61781`
- postgres_db: `auditmanager_cmp_spend_01`
- s3_bucket: `auditmanager-cmp-spend-01`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**` (no column is missing; a missing one is a STOP and the wave's FIX slot)
- `src/auditmanager/jobs/**` apart from the one granted query of `src/auditmanager/jobs/repository.py`
- `src/auditmanager/comparison/work/**` (the queue lane's; read through `comparison/public.py` names only)
- `src/auditmanager/executors/pull.py` and the other executor files (the image lane's), `src/auditmanager/analysis/**`
- `src/auditmanager/bootstrap/**`, `src/auditmanager/api/routers/ports.py` (this lane implements no sealed operation)
- root dependency / lock files, global styles, `web/**`, `infra/**`

## Non-goals
- no handler for any kind and no AI job object (the estimate, the consent screen and the job's typed pause state are `CMP-SEAL-C2`'s;
  this lane takes a consent as a value and answers a typed refusal the job layer turns into a pause)
- no change to how the Run path records its calls (`provider_call_effect`, `model_call`) and no change to `_COST_SUMMARY`
- no change to the dispatch hint `_NEXT_JOB` of `jobs/repository.py` (the grant is for the check only)
- `pull.py` is not edited: the one hunk that makes a `PullAdapter` write the `comparison_call` origin is the integrator's (pinned by a strict xfail)
- no screen, no API operation and no change of the product contract

## Deliverables
1. `src/auditmanager/comparison/spend/`: the journal repository (the only writer of `comparison_model_call`), the ceiling policy, the
   consent binding, the call wrapper `ComparisonModelCaller`, the settler for `SPEND_SETTLERS`, the typed refusals.
2. `executors/runner_repository.py`: the `comparison_call` origin path (insert with `comparison_attempt_id`, the live comparison attempt
   as an alternative to the live Run attempt in `sweep`, `claim_next` and `live_claim_and_attempt`).
3. `dashboard/repository.py`: `_SPEND` as the union of `model_call` and the settled rows of `comparison_model_call`.
4. `jobs/repository.py`: the one query of the connection check (grant).
5. `comparison/public.py`: this lane's names and the settler in `SPEND_SETTLERS`; `grant_classification.py`: the table leaves the sealed set.
6. Unit and integration tests, with a mutation proof for each guard; the report `docs/program/CMP-SPEND-01.md`.

## Required tests
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/unit/comparison/spend`
- expected: all pass, no container needed
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/integration/comparison/spend`
- expected: all pass on the lane's own stack (`make up`, `make migrate`)
- command: `... pytest -q tests/integration/jobs/test_connection_limit_claim.py tests/integration/workers/test_worker_slots.py tests/integration/workers/test_worker_composition.py` and `tests/integration/executors/test_http_run_path.py`
- expected: all pass **unmodified** (the `EXEC-PAR-QUEUE-01` tests and the dashboard spend test of the HTTP run path)

## Integration contract
The integrator can rely on: `ComparisonSpendRepository` is the only writer of `comparison_model_call`; a provider call of the comparison
modules is made only by `ComparisonModelCaller.call`, which commits a `prepared` row before the adapter is called and never retries; a
reclaimed attempt's `prepared` / `sent` rows become `unknown` in the reclaim transaction (the entry of `SPEND_SETTLERS`) and the item ends
`spend_unknown`; a Run's claim is refused while a live attempt has a `prepared` / `sent` call on the same connection, and a comparison call is
refused while a Run is active on its connection (one advisory lock, the Run path's own key); the dashboard's deployment spend adds the
comparison journal.

## Failure/idempotency/security cases
- the process dies between `prepared` and the reply: the row is `unknown` after the reclaim and the call is never repeated
- a worker that lost its lease cannot send (`require_current` before `sent`) and cannot overwrite a settled row
- the execution token, the key and the request body never enter the journal, a refusal message or a log line
- a refusal reason and an error code are typed codes, never free text

## Rollback / feature flag
`AUDITMANAGER_COMPARISON_MODULES=none` (the default) means no comparison item is claimed, so no call is made; the settler is inert
(it only touches rows of attempts the queue lost). The grant's query change is behaviour-neutral while the table is empty.

## Handoff
- changed files: filled in by the last commit
- commands/results: filled in by the last commit
- known limits: filled in by the last commit
- integration notes: filled in by the last commit
