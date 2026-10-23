# Task AR-V3-BETA-REQUEST-CUSTODY-01 — bind a v3 request to current Run and set custody

task_id: AR-V3-BETA-REQUEST-CUSTODY-01
status: completed in development candidate

## Outcome

One current AR v3 group member can produce an exact transport request only from its persisted pack pins and custody-verified retrieval-set bytes. A stale Attempt, changed pack/set, mismatched Run, text version or provider mode refuses before dispatch.

## Depends on

- `AR-V3-BETA-SIX-RUN-02` — completed group and registry.
- `AR-V3-BETA-EXECUTE-GUARD-01` — completed early refusal in the active executor.
- `AR-V3-BETA-REQUEST-DELIVERY-01` — completed sealed request to ModelRequest bridge.
- `AR-V3-BETA-EXECUTE-PREFLIGHT-01` — completed current-Attempt group binding.
- `AR-CORPUS-CITATION-BRIDGE-01` — completed verified-set and scoped request bridge.

## Frozen inputs

- base published `origin/dev`: `8bd816d6e2876b3394df34279ebee86da2f62ba8`
- contract family/API: `1.2.0`; migration head: `0032_ar_v3_run_group`; product `0.8.0`.
- existing `TrustedPackRegistry`, `resolve_v3_execution_binding`, `prepare_v3_corpus_request`, `prepare_beta_v3_request`, `build_v3_model_request` semantics.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: current pack preflight, verified-set reader, sealed profile and transport builder are separate operations

### P-01 — current seams are separate

- captured_at: 2026-10-23
- command: `rg -n '^def (resolve_v3_execution_binding|prepare_v3_corpus_request|prepare_beta_v3_request|build_v3_model_request)' src/auditmanager/runs/v3_execution_binding.py src/auditmanager/runs/v3_citations.py src/auditmanager/analysis/profiles/ar_v3/{v3_profile,request_delivery}.py`
- captured_output:
  ```text
  src/auditmanager/runs/v3_execution_binding.py:74:def resolve_v3_execution_binding(
  src/auditmanager/runs/v3_citations.py:106:def prepare_v3_corpus_request(
  src/auditmanager/analysis/profiles/ar_v3/v3_profile.py:196:def prepare_beta_v3_request(
  src/auditmanager/analysis/profiles/ar_v3/request_delivery.py:109:def build_v3_model_request(
  ```
- interpretation: no one operation rechecks the persisted pack after the Blob read and binds the verified bytes to transport material.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/runs/v3_execution_request.py`
- `src/auditmanager/runs/public.py`
- `tests/integration/runs/test_v3_execution_request.py`
- `docs/program/tasks/AR-V3-BETA-REQUEST-CUSTODY-01.md`
- `docs/program/AR-V3-BETA-REQUEST-CUSTODY-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots

Contracts, migration head, root dependencies/lock files, composition root, global styles, original topics/norm maps/sets, provider transports, active Run executor, CITE publication, `origin/main`, tags and deployment host.

## Non-goals

No provider call, response/cost journal, StageResult, CITE artifact, finding, normative approval, set promotion, stand import or beta acceptance. The caller must supply a text layer from the saved deterministic source stage and a model identity selected by its provider binding.

## Deliverables

- Current-Attempt request assembly and exact return pins/body SHA.
- Positive and refusal tests for set custody, Run/pack drift, provider mode and stale Attempt.
- Report and queue note for the full executor.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_execution_request.py tests/integration/runs/test_v3_corpus_citation_bridge.py tests/integration/analysis/test_ar_v3_request_delivery.py`
- `git diff --check` and exact allowed-path inventory. Full `make gate` is deferred by `R-135` to beta acceptance.

## Integration contract

After committing Job/Attempt, the future executor supplies the saved source-stage text layer and provider-selected model identity, calls this read-only preparation, journals both candidate and provider-body SHA, rechecks Attempt/set authority before dispatch and again after response. Its returned data alone is not dispatch authority across a commit or another Attempt.

## Failure/idempotency/security cases

Missing pack, foreign Run, set Blob custody failure, changed set/pack during read, stale Attempt, wrong provider mode or changed text version refuses. Repeated calls under the same current Attempt and bytes produce equal body SHA and no write/provider effect.

## Rollback / feature flag

Unserved read-only seam. Revert this task or leave it unused; the active executor's v3 guard and empty production registry continue to refuse starts/execution.

## Handoff

- changed files: request assembler, Run public seam, focused tests, task/queue/report
- commands/results: 48 bridge tests and 26 guard/profile tests passed; new task governance findings empty; exact inventory and diff check passed. Full `tests/contract/program` remains blocked by three pre-existing task documents outside this slot (see report).
- known limits: no active v3 executor or approved pack
- integration notes: consume within current Attempt and recheck before/after provider effect
