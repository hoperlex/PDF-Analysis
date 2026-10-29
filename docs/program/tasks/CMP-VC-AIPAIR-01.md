# Task CMP-VC-AIPAIR-01 — the AI check of the doubtful sheet pairs (method `pair_check`): questions with images, content-keyed answers, accepted AI links by rule, hints

## Outcome
On `integration/compare-modules` the seven operations `estimateComparisonAiPairCheck`, `getComparisonAiPairCheck`,
`startComparisonAiPairCheck`, `pauseComparisonAiPairCheck`, `resumeComparisonAiPairCheck`, `cancelComparisonAiPairCheck` and
`listComparisonAiPairHints` are served by `ComparisonAiPairAdapter` (it replaces the stub) over the shared AI-job core
(`CMP-AI-JOBS-01`): (1) the doubtful pairs of a document set's matrix -- cells of medium confidence and unmatched cells with candidates, read
from the matrix's effective read model -- become questions (`comparison_ai_pair_question`) with images (the sheet and its candidates, the
stored page previews through the C0 image channel, at most 8 per request); (2) the answer (`comparison_ai_pair_answer`, content-keyed by
project, prompt version, model and the input digests) is stored once and **never sent again**; (3) an answer is **accepted** only with high
confidence **and** an agreeing reverse question, never for a sheet inside a multi-sheet specification, never over a B that is already
linked, never when two sheets chose the same B -- it then becomes an accepted-AI-link row (`comparison_ai_link`, which the effective matrix
already reads; a manual edit still wins); a rejected or low answer is a hint («вероятно стр. N», «ИИ ?»); (4) the counts
«вопросов · пар · подсказок · против». The work kind `comparison_pair_check` has a handler in `HANDLER_FACTORIES`. The model's answer never
rewrites the deterministic result. Every guard is shown failing under a quoted mutation. Every test runs in recorded mode.

## Depends on
- CMP-SEAL-C2 (contract `1.11.0`, migration `0040_comparison_ai_reports`: `comparison_ai_pair_question`, `comparison_ai_pair_answer`; `comparison_ai_link` of `0039`)
- CMP-AI-JOBS-01 (`ComparisonAiJobService`, `AiMethod`, `RecordedAnswers`, `ai_jobs_support.py`)
- CMP-SPEND-01 (`ComparisonModelCaller`, `CallRoute`, `Consent`), CMP-WORK-01 (the handler registry, `WorkItem`)
- CMP-EXEC-IMAGES-01 (`attach_images`, `CropImage`, `image_load`), CMP-PROFILE-01 (stored page previews, `PageProfileReader`)
- CMP-MATRIX-01 (the effective matrix, `effective_matrix`, `comparison_ai_link` read)

## Frozen inputs
- domain contract: `contracts/domain/v1/**` (prefixes `cpq`, `cpa`, `cak`, `cai` exist)
- API contract: `contracts/api/v1/openapi.json` `1.11.0`, 176 paths / 198 operations / 517 schemas (this lane changes none)
- ADR-0025 decisions 3, 4, 10, 11, 12, 14, 16, 17-23 and the addenda; plan `A-3`, `A-6`, `A-8`, `A-12`, `R3-02`, `R3-10`; `Q-CMP-7`; `R-133`
- migration head: `0040_comparison_ai_reports` (this lane changes none; a missing column is a STOP to the wave's FIX slot)
- the original at commit `23f379fd` (`backend/app/services/version_comparison_ai/sheet_match.py`, `settings.py`, `tests/test_version_comparison_sheet_match.py`), read as data from `raw.githubusercontent.com` into a scratch directory outside git
- base commit: `0f6a008d91f4fbdf1fd7a3b2561dae57392fa8da`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `tests/integration/composition/test_comparison_ai_stub_operations.py` (`WIRED`), `tests/integration/composition/test_router_answers.py` (`SEALED_STUB_GETS`), `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py` (`SEALED_STUB_ADDRESSED`, `SEALED_STUB_COLLECTIONS`, `EXPECTED_ADDRESSED`), `scripts/recovery/grant_classification.py` (`SEALED_NOT_YET_WRITTEN`), `src/auditmanager/comparison/public.py` (`HANDLER_FACTORIES`)
- enumerator_owner: this lane, for its seven operations, its three tables and its one work kind only (the wave brief's wiring rule 4)
- totality_query: `tests/integration/composition/test_comparison_ai_stub_operations.py` (every operation is either wired or a stub), `tests/integration/recovery/test_grant_classification.py` (a table is either written or sealed), `tests/unit/comparison/work/test_composition_unit.py` (every work kind has one handler)

## Captured premise evidence
- premise: contract `1.11.0`, 176 paths / 198 operations / 517 schemas, head `0040_comparison_ai_reports`, base `0f6a008d` (wave C2 brief); the lane re-read them before any edit and STOPs if they differ

### P-01 — the base facts the lane re-read before any edit
- captured_at: 2026-10-29
- command: `git rev-parse HEAD; python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas')"; cat VERSION; grep -n "^revision: str" db/migrations/versions/20261029_0040_comparison_ai_reports.py`
- captured_output:
  ```text
  0f6a008d91f4fbdf1fd7a3b2561dae57392fa8da
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
- `src/auditmanager/comparison/ai_pairs/**`
- `tests/unit/comparison/ai_pairs/**`
- `tests/integration/comparison/ai_pairs/**`
- `docs/program/CMP-VC-AIPAIR-01.md`
- `docs/program/tasks/CMP-VC-AIPAIR-01.md`
- the wiring hunks of the wave brief (rule 4), for this lane's seven operations, three tables and one work kind only: the body of `ComparisonAiPairAdapter` in `src/auditmanager/bootstrap/adapters.py`; the one constructor line of that adapter in `src/auditmanager/bootstrap/composition.py`; `src/auditmanager/api/routers/ports.py` (a row, if any); `src/auditmanager/comparison/public.py` (this lane's names and its line of `HANDLER_FACTORIES`); `tests/integration/composition/test_router_answers.py`, `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`, `tests/integration/composition/test_comparison_ai_stub_operations.py`; `scripts/recovery/grant_classification.py`; the `HANDLER_FACTORIES` pins of `tests/unit/comparison/engine/test_handler_unit.py` and `tests/unit/comparison/work/test_composition_unit.py` (this lane's kind only)

## Lane resources
- foundation_instance: `auditmanager-cmp-vc-aipair-01`
- postgres_port: `57960`
- s3_api_port: `61960`
- s3_console_port: `61961`
- postgres_db: `auditmanager_cmp_vc_aipair_01`
- s3_bucket: `auditmanager-cmp-vc-aipair-01`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**` (a missing field or column is a STOP and the wave's FIX slot)
- `src/auditmanager/comparison/ai_jobs/**`, `src/auditmanager/comparison/matrix/**`, `src/auditmanager/comparison/work/**`, `src/auditmanager/comparison/spend/**`, `src/auditmanager/comparison/profile/**` (used through their names only)
- `src/auditmanager/api/routers/comparison_ai_pairs.py` (the router; the port is what this lane implements), `src/auditmanager/jobs/**`, `src/auditmanager/executors/**`, `src/auditmanager/analysis/**`, `src/auditmanager/workers/**`
- root dependency / lock files, global styles, `web/**`, `infra/**`, `tests/support/**`, any other `conftest.py` outside `tests/integration/comparison/ai_pairs/`

## Non-goals
- no live model call and no provider credential; every test runs in recorded mode (`RecordedAnswers`)
- no binding of a routed connection to an adapter in the worker (the composition root's `build_comparison_work` hands a handler only `WorkDependencies`): the handler takes a `ModelBinder`, and the report names the one line the integrator wires
- no matrix change: the effective matrix already reads accepted AI links; no migration, no contract change, no other lane's file
- no launch-queue step (`CMP-VC-QUEUE-01`) and no screen (`CMP-VC-UI-02`)

## Deliverables
1. `src/auditmanager/comparison/ai_pairs/`: the questions (a pure derivation over the effective matrix), the prompt and the answer validator, the acceptance rule, the content key, the repository (the only writer of `comparison_ai_pair_question`, `comparison_ai_pair_answer` and `comparison_ai_link`), the `AiMethod`, the work handler (kind `comparison_pair_check`) and the service the adapter calls.
2. The wiring hunks listed under allowed paths.
3. Unit and integration tests with a mutation proof for each safety guard; the report `docs/program/CMP-VC-AIPAIR-01.md` (what was built, the original's rules and prompt ported with file:line, proofs, commands, limits, notes for the queue and the UI lanes, FIX items).

## Required tests
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q --basetemp=/tmp/pytest-cmp-vc-aipair-01/unit tests/unit/comparison/ai_pairs`
- expected: all pass, no container needed
- command: `... pytest -q --basetemp=/tmp/pytest-cmp-vc-aipair-01/integ tests/integration/comparison/ai_pairs`
- expected: all pass on the lane's own stack (`make up`, `make migrate`)
- command: `... pytest -q tests/integration/comparison` (one process), the whole `tests/integration/composition` directory, then the whole `tests/unit` and `tests/contract` minus the three `D-220` files
- expected: all pass

## Integration contract
Allowed paths. The wiring files are edited in the wave's merge order (AI-JOBS, SPEC, AIPAIR, AISHEET, REPORT, QUEUE, UI-02); the hunks are minimal (one adapter body, one constructor line, this lane's rows and names). The adapter takes the module set, the provider mode (`live` or `recorded`) and the blob store; the handler takes a `ModelBinder` for a live route.

## Failure/idempotency/security cases
- the module flag is the first statement of every wired adapter method; a start with the same key and payload replays the recorded job; a start is an expert's act
- nothing is sent to a model before the consent and the estimate agree; a stored answer is never sent again; at most 8 images in a request
- an answer is accepted only with high confidence, an agreeing candidate number and page, a sheet outside a multi-sheet specification, a B that no other A claims, and a reverse question that returns A with high confidence; any other answer is a hint; a manual edit wins
- the AI layer writes only its own rows; the raw matrix and the deterministic results are never rewritten

## Rollback / feature flag
The operations stay behind the `versions` module flag (`AUDITMANAGER_COMPARISON_MODULES`, default `none`); with it off every operation answers `503 dependency_unavailable` (`comparison_modules`) as the stub did.

## Handoff
- changed files: to be completed by the last commit
- commands/results: to be completed by the last commit
- known limits: to be completed by the last commit
- integration notes: to be completed by the last commit
