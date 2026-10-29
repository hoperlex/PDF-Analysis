# Task CMP-VC-REPORT-01 — the MD summary of a series and the PDF report (client and analytic kinds), the thirteen report operations

## Outcome
On `integration/compare-modules` the thirteen report operations of `CMP-SEAL-C2` section 3 and 9 are served by a real
`ComparisonReportAdapter` over `src/auditmanager/comparison/report/**` (method `report`, work kind `comparison_report`):
(1) `streamComparisonSeriesSummary` -- the deterministic MD summary of a series (the same bytes for the same data, the original's
«Реестр покрытия» and sections, the sheet descriptions with their tiers and the «не подтверждено инженером» mark where there are
any); (2) a PDF report is made as a `draft` with its estimate and no model call, from the summary (`createComparisonReport`) or
from an uploaded MD file (`uploadComparisonReportSource`, raw `text/markdown`, at most 20 MiB, validated), and started with consent
(`startComparisonReport`) through the shared AI-job core; (3) the **client kind** (the default: one model call per transition over
the summary's facts with the discipline's priorities, a program check that drops every point whose number, mark or direction the
facts do not confirm, one chronological table) and the **analytic kind** (analyst, verifier, composer); (4) reuse of finished
parts (`comparison_report_part`), cancel / continue / «Пересобрать PDF» (no model call) / delete (a tombstone) / «Подготовить
отчёт для заказчика» from an analytic report, per-transition progress, history, the PDF and the source MD as downloads; (5) the PDF
is written by a program (reportlab, a free Cyrillic font under `report/fonts/**`) in a child process under the ceilings of
ADR-0025 decision 8, and stored as a blob (`comparison_report_artifact`, append-only). Each safety guard is shown failing under a
quoted mutation; every test runs in recorded mode.

## Depends on
- CMP-SEAL-C2 (migration `0040_comparison_ai_reports`: `comparison_report`, `comparison_report_part`, `comparison_report_artifact`; contract `1.11.0`)
- CMP-AI-JOBS-01 (`ComparisonAiJobService`, `AiMethod`, `RecordedAnswers`, `ai_jobs_support.py`)
- CMP-SPEND-01 (`ComparisonModelCaller`, `Consent`, `CallRoute`), CMP-WORK-01 (`WorkItem`, `HANDLER_FACTORIES`), CMP-SERIES-01 (the series, transitions and sheet pairs the summary reads), CMP-STORAGE-PARTS-01, CMP-ENGINE-01 (read only)

## Frozen inputs
- domain contract: `contracts/domain/v1/**` (prefixes `crt`, `crpt`, `cra`, `cai`)
- API contract: `contracts/api/v1/openapi.json` `1.11.0`, 176 paths / 198 operations / 517 schemas (this lane changes none)
- analysis/comparison/event contract: ADR-0025 decisions 3, 4, 8, 9, 10, 11, 16, 17 to 23, 24 and the addenda; plan `A-6`, `A-8`, `A-12`, sections 1.1, 3.2, 4.0 and the C2 row; `Q-CMP-9` (reportlab and a free Cyrillic font)
- migration head: `0040_comparison_ai_reports` (this lane changes none; a missing column is a STOP to the wave's FIX slot)
- base commit: `0f6a008d91f4fbdf1fd7a3b2561dae57392fa8da`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `tests/integration/composition/test_comparison_ai_stub_operations.py` (`WIRED`), `tests/integration/composition/test_router_answers.py` (`SEALED_STUB_GETS`, `SEALED_STUB_QUERY`), `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py` (`SEALED_STUB_ADDRESSED`, `SEALED_STUB_COLLECTIONS`, `EXPECTED_ADDRESSED`), `scripts/recovery/grant_classification.py` (`SEALED_NOT_YET_WRITTEN`)
- enumerator_owner: this lane, for its thirteen operations and its three tables only (the wave brief's wiring rule; the other C2 lanes edit the same registers for theirs)
- totality_query: the stub-register tests and `tests/integration/recovery/test_grant_classification.py`

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
- `src/auditmanager/comparison/report/**` (new, including `fonts/**`)
- `tests/unit/comparison/report/**`
- `tests/integration/comparison/report/**`
- `docs/program/CMP-VC-REPORT-01.md`
- `docs/program/tasks/CMP-VC-REPORT-01.md`
- wiring hunks for the thirteen operations and the three tables only: `src/auditmanager/bootstrap/adapters.py` (the body of `ComparisonReportAdapter`), `src/auditmanager/bootstrap/composition.py` (its one constructor line and imports), `src/auditmanager/api/routers/ports.py` (rows of the report port, if any), `src/auditmanager/comparison/public.py` (this lane's names and its `HANDLER_FACTORIES` entry), `tests/integration/composition/test_router_answers.py`, `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`, `tests/integration/composition/test_comparison_ai_stub_operations.py`, `scripts/recovery/grant_classification.py` (`SEALED_NOT_YET_WRITTEN`), `tests/unit/comparison/engine/test_handler_unit.py` and `tests/unit/comparison/work/test_composition_unit.py` (the `HANDLER_FACTORIES` pins, for this lane's kind only)

## Lane resources
- foundation_instance: `auditmanager-cmp-vc-report-01`
- postgres_port: `57980`
- s3_api_port: `61980`
- s3_console_port: `61981`
- postgres_db: `auditmanager_cmp_vc_report_01`
- s3_bucket: `auditmanager-cmp-vc-report-01`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**` (no column is missing so far; a missing one is a STOP and the wave's FIX slot)
- `src/auditmanager/comparison/ai_jobs/**`, `work/**`, `spend/**`, `series/**`, `engine/**` (read through `comparison/public.py` names only)
- `src/auditmanager/jobs/**`, `src/auditmanager/executors/**`, `src/auditmanager/analysis/**`
- root dependency / lock files (no new Python or npm dependency: a font file is data), global styles, `web/**`, `infra/**`, `tests/support/**`, any other `conftest.py`

## Non-goals
- no live model call: every test is in recorded mode; the live binding of a comparison work kind (a routed connection's secret and adapter in the worker) is not this lane's (report section on FIX items)
- no web screen (`CMP-VC-UI-02`), no launch queue (`CMP-VC-QUEUE-01`), no sheet description or specification writer (`CMP-VC-AISHEET-01`, `CMP-VC-SPEC-01`: this lane only reads their tables, and renders nothing for them while they are empty)
- no contract or migration change

## Deliverables
1. `src/auditmanager/comparison/report/`: the MD summary builder and its reader, the intake parser and the fact registry, the client and analytic prompts, checks and views (ported from the original with file:line), the PDF renderer, its child and its ceilings, the font and its licence, the repository, the `AiMethod`, the service of the thirteen operations, the work handler.
2. The wiring hunks listed under Allowed paths.
3. Unit and integration tests with a mutation proof for each guard; the report `docs/program/CMP-VC-REPORT-01.md`.

## Required tests
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q --basetemp=/tmp/pytest-cmp-vc-report-01/unit tests/unit/comparison/report`
- expected: all pass, no container needed
- command: `... pytest -q --basetemp=/tmp/pytest-cmp-vc-report-01/integ tests/integration/comparison/report`
- expected: all pass on the lane's own stack (`make up`, `make migrate`)
- command: `... pytest -q tests/integration/comparison` (one process), the whole `tests/integration/composition` directory, `tests/integration/recovery/test_grant_classification.py`
- expected: all pass; after the last code commit also the whole `tests/unit` and `tests/contract` minus the three `D-220` files

## Integration contract
Allowed paths. The wiring hunks are minimal and additive (the other C2 lanes edit the same files); a textual conflict is resolved by keeping both sides.
The shared consented-AI-job core is used as `CMP-AI-JOBS-01` section 2 says: the lane supplies an `AiMethod` and calls `ComparisonAiJobService`; it
writes no row of `comparison_ai_job`. A lane that needs another field STOPs to the wave's FIX slot.

## Failure/idempotency/security cases
- the module flag is the first statement of every adapter method; every write is an expert's act and keyed; a repeat of a key replays
- the upload is refused over 20 MiB, when it is not UTF-8, empty, has no transition heading, or names more transitions than the series has; nothing is written
- an unconfirmed number, mark or direction is dropped from the client report; «Пересобрать PDF» makes no model call; a finished part is reused, not requested again
- the PDF child runs under 768 MiB, 300 s of CPU and 600 s of wall; an end without a result is a typed `pdf_failed` of that report only
- one live job per report (the report row holds the link; a second start is `comparison_report_state`)

## Rollback / feature flag
The operations stay behind the `versions` module flag (`AUDITMANAGER_COMPARISON_MODULES`, default `none`); with it off every operation answers
`503 dependency_unavailable` naming `comparison_modules`, as the sealed stubs did.

## Handoff
- changed files: (written as the last commit)
- commands/results: (written as the last commit)
- known limits: (written as the last commit)
- integration notes: (written as the last commit)
