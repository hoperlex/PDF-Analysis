# Task CMP-VC-QUEUE-01 — durable launch queue for version comparison

## Outcome
The seven sealed queue operations serve a per-project launch queue that starts one selected step at a time across document sets, holds AI consent by estimate digest, and exposes the installation AI-job queue. Pause, resume, clear and remove have durable, keyed results. The UI can read «готово N из M · пропущено K · ошибок E».

## Depends on
- CMP-SEAL-C2
- CMP-AI-JOBS-01
- CMP-VC-SPEC-01
- CMP-VC-AIPAIR-01
- CMP-VC-AISHEET-01
- CMP-VC-REPORT-01

## Frozen inputs
- domain contract: ADR-0025 and its addenda; `COMPARE-MODULES-PLAN.md` §1.1 and §4 C2
- API contract: `contracts/api/v1/openapi.json` version `1.11.0`, 176 paths / 198 operations / 517 schemas
- analysis/comparison/event contract: the sealed C2 comparison operation and work schemas; no new event type
- migration head: `0040_comparison_ai_reports`
- base commit: `4c8b3e89` on `integration/compare-modules`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `src/auditmanager/comparison/public.py`
- enumerator_owner: `CMP-VC-QUEUE-01`
- totality_query: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/unit/comparison/engine/test_handler_unit.py tests/integration/composition/test_comparison_ai_stub_operations.py --basetemp=/tmp/pytest-cmp-vc-queue-01/enumerators`

## Captured premise evidence
- premise: P-01

### P-01 — frozen API, migration and base
- captured_at: 2026-10-29
- command: `python3 -c 'import json;d=json.load(open("contracts/api/v1/openapi.json"));print("version",d["info"]["version"]);print("paths",len(d["paths"]));print("operations",sum(k in {"get","post","put","patch","delete","head","options","trace"} for p in d["paths"].values() for k in p));print("schemas",len(d["components"]["schemas"]))' && git rev-parse --short HEAD && ls db/migrations/versions/*0040*`
- captured_output:
  ```text
  version 1.11.0
  paths 176
  operations 198
  schemas 517
  4c8b3e89
  db/migrations/versions/20261029_0040_comparison_ai_reports.py
  ```
- interpretation: the seal is present and the queue can use its two tables; this does not claim the seven stub operations are implemented.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/queue/**`
- `src/auditmanager/comparison/public.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `scripts/recovery/grant_classification.py`
- `tests/unit/comparison/queue/**`
- `tests/integration/comparison/queue/**`
- `tests/unit/comparison/engine/test_handler_unit.py`
- `tests/integration/composition/test_router_answers.py`
- `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`
- `tests/integration/composition/test_comparison_ai_stub_operations.py`
- `docs/program/CMP-VC-QUEUE-01.md`
- `docs/program/tasks/CMP-VC-QUEUE-01.md`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, root dependency and lock files, global styles, `web/**`, `infra/**`
- other comparison modules and their tables except through public services
- other bootstrap adapters and routes outside the queue adapter and constructor
- `src/auditmanager/jobs/**`, `src/auditmanager/executors/**`, `src/auditmanager/analysis/**`

## Non-goals
- no new API field for renewing consent of a `needs_consent` entry; that contract gap belongs to SEAL-C3
- no live model call; queued AI steps use the existing consented AI-job services
- no contract or migration change, no deployment or external ref update

## Deliverables
- queue repository, service, work handler and API adapter over the sealed tables
- unit and integration tests of serial execution, consent, state edges, role, key replay and module gate
- `docs/program/CMP-VC-QUEUE-01.md` with results, risks and integration notes

## Required tests
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q --basetemp=/tmp/pytest-cmp-vc-queue-01/unit tests/unit/comparison/queue`
- expected: all pass without services
- command: `set -a; . ./.env; set +a; AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q --basetemp=/tmp/pytest-cmp-vc-queue-01/integration tests/integration/comparison/queue tests/integration/composition/test_comparison_ai_stub_operations.py`
- expected: all pass on the isolated CMP integration stack at migration 0040

## Integration contract
`ComparisonLaunchQueueAdapter` serves the seven sealed operations. A project queue has at most one running entry; each selected step delegates to the existing comparison service. A queued AI step stores the expert's digest and starts only when that digest still matches the current estimate. A moved estimate yields `needs_consent`, and the queue continues to the next entry. The installation read projects `ComparisonAiJobService.waiting()` without starting work. `comparison_launch_queue` and `comparison_launch_entry` are the only new tables this task writes.

## Failure/idempotency/security cases
- an unknown project, document outside that project or unknown entry: 404
- upload or consent on a deterministic step: 422; duplicate active document/step: 409
- only an expert may write; every write is keyed and the module flag is checked first
- pause lets the current step finish; clear and remove leave running work alone
- unknown AI outcome is handled by the AI-job core; no duplicate model request is sent by this queue

## Rollback / feature flag
`AUDITMANAGER_COMPARISON_MODULES=none` refuses all seven operations before a read or write. The durable queue rows remain for a later resume; no destructive rollback of in-flight work.

## Handoff
- changed files: `src/auditmanager/comparison/queue/**`, the queue adapter and constructor in bootstrap, `comparison/public.py`, grant classification, the three composition registers, the handler register test, `tests/{unit,integration}/comparison/queue/**`, this task and `docs/program/CMP-VC-QUEUE-01.md`.
- commands/results: queue and composition 111 passed / 2 skipped / 1 warning; queue integration after final change 4 passed; grant classification 35 passed; `compileall` and `git diff --check` passed.
- contracts: no new or changed API/domain/event contract; no migration change.
- known limits: a `needs_consent` entry has no in-place consent renewal operation in contract 1.11.0; child services do not accept an external attempt fence; live model binding is pending C2 FIX. See the report.
- integration notes: `comparison_launch_handler` is appended to the one public handler tuple; `comparison_launch_queue` and `comparison_launch_entry` leave `SEALED_NOT_YET_WRITTEN`. Run the whole C2 and gate batteries after FIX. No publication from this task.
