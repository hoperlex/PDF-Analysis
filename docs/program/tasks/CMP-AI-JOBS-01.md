# Task CMP-AI-JOBS-01 — the shared core of consented AI jobs (estimate, consent, state edges, spend and progress reads, recorded mode)

## Outcome
On `integration/compare-modules` the four AI methods of the version comparison (`pair_check`, `sheet_changes`, `spec`, `report`) share
one core over `comparison_ai_job` (`CMP-SEAL-C2` section 4 and 9) in `src/auditmanager/comparison/ai_jobs/**`:
(1) an estimate protocol -- a method supplies the counts of what it would send, the core prices them from the routed executor connection
of the method's work kind and its pinned model, applies the ceilings (USD 10 per job, USD 50 per day per installation) and makes a stable
`estimate_digest`; (2) a keyed start with consent that, in one transaction, refuses while the `versions` module is off, on a stale digest,
over either ceiling, while a live job holds the scope, or with nothing to do, and otherwise writes the job row and the method's first work
items with `comparison_work.comparison_ai_job_id` set; (3) the state edges pause / resume / cancel / finish / dequeue / retry as core
functions over the job and its items, each refused with `comparison_ai_job_state` when the edge is not allowed, and the x1.2 overrun pause;
(4) the reads -- the job view (state, pause reason, progress, spend so far from the journal, the consented estimate) and the installation's
waiting jobs; (5) a recorded-mode test support that serves recorded answers by prompt digest. Each safety guard is shown failing under a
quoted mutation.

## Depends on
- CMP-SEAL-C2 (migration `0040_comparison_ai_reports`: `comparison_ai_job`, `comparison_work.comparison_ai_job_id`; contract `1.11.0`)
- CMP-SPEND-01 (`ComparisonModelCaller`, `Consent`, `CallRoute`, the ceilings, the journal)
- CMP-WORK-01 (`ComparisonWorkRepository`, `WorkItem`)

## Frozen inputs
- domain contract: `contracts/domain/v1/**` (prefix `cai` exists; `ComparisonAiJobId`)
- API contract: `contracts/api/v1/openapi.json` `1.11.0`, 176 paths / 198 operations / 517 schemas (this lane changes none)
- analysis/comparison/event contract: ADR-0025 decisions 10, 11, 19 and the addenda; plan `A-6`, `A-8`, `A-12`; `Q-CMP-7`; `R-133`
- migration head: `0040_comparison_ai_reports` (this lane changes none; a missing column is a STOP)
- base commit: `901914a5520a2d90b22b0c5c3fcdae1fa3f6e438`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

(The one set this lane touches is `SEALED_NOT_YET_WRITTEN` in `scripts/recovery/grant_classification.py`: it removes its own table,
`comparison_ai_job`, by the wave brief's wiring rule 4.)

## Captured premise evidence
- premise: contract `1.11.0`, 176 paths / 198 operations / 517 schemas, head `0040_comparison_ai_reports`, base `901914a5` (wave C2 brief); the
  lane re-read them before any edit and STOPs if they differ

### P-01 — the base facts the lane re-read before any edit
- captured_at: 2026-10-29
- command: `git rev-parse HEAD; python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas')"; cat VERSION; grep -n "^revision: str" db/migrations/versions/20261029_0040_comparison_ai_reports.py`
- captured_output:
  ```text
  901914a5520a2d90b22b0c5c3fcdae1fa3f6e438
  contract 1.11.0 176 paths 198 operations 517 schemas
  0.9.0
  69:revision: str = "0040_comparison_ai_reports"
  ```
- interpretation: equal to the premise (contract `1.11.0`, 176 / 198 / 517, head `0040_comparison_ai_reports`), so the lane did not STOP

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/ai_jobs/**`
- `src/auditmanager/comparison/public.py`
- `scripts/recovery/grant_classification.py`
- `tests/unit/comparison/ai_jobs/**`
- `tests/integration/comparison/ai_jobs/**`
- `docs/program/CMP-AI-JOBS-01.md`
- `docs/program/tasks/CMP-AI-JOBS-01.md`

## Lane resources
- foundation_instance: `auditmanager-cmp-ai-jobs-01`
- postgres_port: `57940`
- s3_api_port: `61940`
- s3_console_port: `61941`
- postgres_db: `auditmanager_cmp_ai_jobs_01`
- s3_bucket: `auditmanager-cmp-ai-jobs-01`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**` (no column is missing; a missing one is a STOP and the wave's FIX slot)
- `src/auditmanager/bootstrap/**` (`adapters.py`, `composition.py`), `src/auditmanager/api/**` (no operation is wired here)
- `src/auditmanager/jobs/**`, `src/auditmanager/executors/**`, `src/auditmanager/analysis/**`
- `src/auditmanager/comparison/work/**`, `src/auditmanager/comparison/spend/**` (read through `comparison/public.py` names only)
- root dependency / lock files, global styles, `web/**`, `infra/**`, `tests/support/**`, any other `conftest.py`

## Non-goals
- no operation is wired and no adapter replaced: the four method lanes (`CMP-VC-AIPAIR-01`, `CMP-VC-AISHEET-01`, `CMP-VC-SPEC-01` part B,
  `CMP-VC-REPORT-01`) wire theirs through this core
- no method-specific logic: no prompt, no question, no sheet, no specification, no report; a method supplies its counts and its work items
- no handler for any work kind and no live model call (recorded mode only)
- no queue (launch queue) logic: this lane reads the installation's waiting jobs; `CMP-VC-QUEUE-01` wires `getComparisonAiQueue`

## Deliverables
1. `src/auditmanager/comparison/ai_jobs/`: the vocabulary, the estimate protocol and its digest, the repository (the only writer of
   `comparison_ai_job`), the service (keyed start with consent, the six state edges, the system pauses, the reads), the recorded-mode support.
2. `comparison/public.py`: this lane's names; `grant_classification.py`: `comparison_ai_job` leaves the sealed set.
3. Unit and integration tests with a mutation proof for each guard; the report `docs/program/CMP-AI-JOBS-01.md` with the API section.

## Required tests
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q --basetemp=/tmp/pytest-cmp-ai-jobs-01/unit tests/unit/comparison/ai_jobs`
- expected: all pass, no container needed
- command: `... pytest -q --basetemp=/tmp/pytest-cmp-ai-jobs-01/integ tests/integration/comparison/ai_jobs`
- expected: all pass on the lane's own stack (`make up`, `make migrate`)
- command: `... pytest -q tests/integration/comparison` (one process) and `tests/integration/recovery/test_grant_classification.py`
- expected: all pass

## Integration contract
Allowed paths. `comparison/public.py` and `grant_classification.py` are the wave brief's wiring rule 4 (appends for this lane's names only;
the removal of `comparison_ai_job` from `SEALED_NOT_YET_WRITTEN`). The four method lanes build on `ComparisonAiJobService`, `AiMethod` and
`EstimateBuilder`; the report's API section is binding for them. A lane that needs another field STOPs to the wave's FIX slot.

## Failure/idempotency/security cases
- the module flag is checked first, before any read or write; a start with the same key and payload replays the recorded job
- a stale digest, a ceiling, a held scope, an empty job and an edge the trigger does not allow are typed conflicts and write nothing
- a model call, a live one included, never happens here; the spend of a job is read from the journal, never stored on the job

## Rollback / feature flag
Not applicable: the package is unreachable until a lane wires an operation, and the operations stay behind the `versions` module flag
(`AUDITMANAGER_COMPARISON_MODULES`, default `none`).

## Handoff
- changed files: `src/auditmanager/comparison/ai_jobs/{__init__,model,estimate,repository,service,recorded}.py` (new); `src/auditmanager/comparison/public.py` (an import block and 27 names); `scripts/recovery/grant_classification.py` (`comparison_ai_job` out of `SEALED_NOT_YET_WRITTEN`); `tests/unit/comparison/ai_jobs/**` (2 files, 82 tests); `tests/integration/comparison/ai_jobs/**` (`conftest.py`, `ai_jobs_support.py`, 3 files, 99 tests); `docs/program/CMP-AI-JOBS-01.md`; this file
- commands/results: `tests/unit/comparison/ai_jobs` 82 passed; `tests/integration/comparison/ai_jobs` 99 passed; `tests/integration/comparison` in one process 653 passed; `tests/integration/recovery/test_grant_classification.py` 35 passed; `tests/unit` 5044 passed, 76 skipped; `tests/contract` minus the three `D-220` files 1310 passed, 19283 subtests; `git diff --check` clean; 28 mutations, all red but one that survives by design (M4a), each restored green (report section 4)
- known limits: nothing is wired (no adapter, composition or handler); the lock order is documented and not concurrency-tested; the token constants are `[own design]`; no pause reason of its own for a ceiling (contract); the route's probe result and the standby are not read (report section 6)
- integration notes: merge first among the C2 wiring files; the report's section 2 is the API the four method lanes follow; FIX items 1 to 3 of report section 6 (`ComparisonWorkRepository.enqueue` cannot set the frozen job column and `counts` has no job filter; the contract has no pause reason for a ceiling; route usability is not checked by the estimate); the commits carry `Claude Sonnet 5.5` (the harness-given attribution), the integrator may rewrite the trailer
