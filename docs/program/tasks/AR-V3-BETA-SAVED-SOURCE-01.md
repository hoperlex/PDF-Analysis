# Task AR-V3-BETA-SAVED-SOURCE-01 — use current Run's saved text in the v3 request

task_id: AR-V3-BETA-SAVED-SOURCE-01
status: completed in development candidate

## Outcome

The read-only AR v3 request boundary loads its text layer from the current Run's saved `source_preparation` artifact and verified Blob; a caller cannot pass arbitrary text to the provider request assembler.

## Depends on

- `AR-V3-BETA-REQUEST-CUSTODY-01` — completed current-Attempt set/request assembly.
- `W57B-INT-SAVED-TEXT-SOURCE-01` — completed saved reference text reader and custody checks.
- `AR-V3-BETA-EXECUTE-PREFLIGHT-01` — completed group/pack binding.

## Frozen inputs

- base published `origin/dev`: `3bea9936c8bc8f1168ad63a08c6db05cb0adf096`.
- contract family/API `1.2.0`; migration head `0032_ar_v3_run_group`; product `0.8.0`.
- `load_saved_reference_text` is the existing Attempt-fenced Run/source-stage/Version/Blob reader; `prepare_v3_execution_request` is unserved.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the v3 assembler accepts a caller supplied TextLayer while a complete saved text reader already exists

### P-01 — seams at the current development base

- captured_at: 2026-10-23
- command: `rg -n '^def (load_saved_reference_text|prepare_v3_execution_request)' src/auditmanager/runs/reference_text_input.py src/auditmanager/runs/v3_execution_request.py`
- captured_output:
  ```text
  src/auditmanager/runs/v3_execution_request.py:60:def prepare_v3_execution_request(
  src/auditmanager/runs/reference_text_input.py:82:def load_saved_reference_text(
  ```
- interpretation: the already verified saved text seam can be composed without changing a contract, Blob reader or migration.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/runs/v3_execution_request.py`
- `tests/integration/runs/test_v3_execution_request.py`
- `docs/program/tasks/AR-V3-BETA-SAVED-SOURCE-01.md`
- `docs/program/AR-V3-BETA-SAVED-SOURCE-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots

Contracts, migration head, root dependencies/lock files, composition root, global styles, norm maps/sets, provider transports, active Run executor, existing saved text reader, CITE publication, `origin/main`, tags and deployment host.

## Non-goals

No group activation, provider call, response journal, StageResult, CITE artifact, finding, source approval, numeric decision or stand import.

## Deliverables

- v3 assembler obtains verified text internally using the current Attempt and explicit byte ceiling.
- Tests cover six scoped bodies and refusal before set read for missing/foreign saved text; existing saved reader custody tests remain green.
- Report and queue note for the full executor.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_execution_request.py tests/integration/runs/test_reference_text_input_offline.py tests/integration/runs/test_v3_corpus_citation_bridge.py tests/integration/analysis/test_ar_v3_request_delivery.py -x --tb=short`.
- `git diff --check` and exact allowed-path inventory. Full `make gate` remains the final beta gate under `R-135`.

## Integration contract

The future executor commits a Job/Attempt and deterministic source stage, then calls this assembler with a positive `max_text_bytes`, provider-selected model identity and generation pins. The assembler reads the saved text and set under that Attempt, returning exact body/candidate SHA values. The executor still rechecks authority before dispatch and after response.

## Failure/idempotency/security cases

Wrong/missing source stage, mismatched Version/page count, changed or oversized saved text, stale Attempt, wrong set/pack and wrong provider mode refuse before provider effect. Repeating the same saved inputs yields the same provider-body SHA.

## Rollback / feature flag

This unserved seam remains behind the active executor's v3 refusal and the empty production pack registry. Revert this task or leave it unused.

## Handoff

- changed files: v3 request assembler, focused tests, task/queue/report
- commands/results: 72 focused source/set/request tests passed; new task governance findings empty; allowed-path inventory and diff check passed
- known limits: v3 dispatch/CITE and reviewed pack still open
- integration notes: caller cannot supply source text; use returned saved text for local grounding
