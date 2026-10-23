# Task AR-SIX-RUN-SCOPE-BRIDGE-01 — bind each draft v3 request to one of six Run scopes

task_id: AR-SIX-RUN-SCOPE-BRIDGE-01

## Outcome

The unserved AR v3 Run/corpus bridge accepts exactly one of six owner-selected scopes F1/F2/A1/A2/S1/S2, confirms that the saved set's ordered C items equal that scope, and binds scope/composition to its request digest. A cross-scope or unscoped bridge call refuses before provider material. The six groups cover C01–C22 exactly once.

## Depends on

- `AR-CORPUS-CITATION-BRIDGE-01` — completed Run/Attempt/set bridge.
- `AR-NORM-MAP-APPROVAL-PREP-01` — completed C01–C22 decision sheet.

## Frozen inputs

- base commit: `0205e2f63c4b41bab5b99aa4868170858c290772`
- owner decision in this conversation, 2026-10-23: six separate Runs F1/F2/A1/A2/S1/S2 for C01–C22, preserving shared project context and each Run's provenance;
- contract `1.0.0`; migration head `0031_executor_pull_channel`; W57 22,000-character set prompt-part cap;
- request/set versions `ar-v3-request-prep-v1` and `norm-retrieval-set-prep-v1` and existing bridge bytes;
- prior pure scope work `c4ba51e7`/`c7860132` on the separate `integration/ar-evidence-01` line is candidate code for adaptation, not served authority.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `src/auditmanager/analysis/profiles/ar_v3/scope_partition.py`
- enumerator_owner: `AR-SIX-RUN-SCOPE-BRIDGE-01`
- totality_query: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/analysis/test_ar_v3_scope_partition.py`

## Captured premise evidence

- premise: current dev has no six-scope enumerator or scoped request, and the current bridge calls the unscoped draft.

### P-01 — current entry points

- captured_at: 2026-10-23
- command: `rg -n '^class V3SetInput|^def parse_v3_set_input|^def prepare_v3_request_candidate|^def prepare_v3_corpus_request|^def plan_v3_corpus_citations|^def scope_membership' src/auditmanager/analysis/profiles/ar_v3/{set_input,request_candidate,scope_partition}.py src/auditmanager/runs/v3_citations.py 2>&1`
- captured_output:
  ```text
  rg: src/auditmanager/analysis/profiles/ar_v3/scope_partition.py: No such file or directory (os error 2)
  src/auditmanager/runs/v3_citations.py:77:def prepare_v3_corpus_request(
  src/auditmanager/runs/v3_citations.py:114:def plan_v3_corpus_citations(
  src/auditmanager/analysis/profiles/ar_v3/set_input.py:33:class V3SetInputRefused(ValueError):
  src/auditmanager/analysis/profiles/ar_v3/set_input.py:38:class V3SetInput:
  src/auditmanager/analysis/profiles/ar_v3/set_input.py:128:def parse_v3_set_input(
  src/auditmanager/analysis/profiles/ar_v3/request_candidate.py:60:def prepare_v3_request_candidate(
  ```
- interpretation: scope/Run selection is not currently bound; this slice can add a pure and bridge-level refusal without claiming map or provider authority.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v3/scope_partition.py`
- `src/auditmanager/analysis/profiles/ar_v3/set_input.py`
- `src/auditmanager/analysis/profiles/ar_v3/request_candidate.py`
- `src/auditmanager/analysis/profiles/ar_v3/local_evaluation.py`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/runs/v3_citations.py`
- `tests/integration/analysis/test_ar_v3_scope_partition.py`
- `tests/integration/analysis/test_ar_v3_scope_request.py`
- `tests/integration/runs/test_v3_corpus_citation_bridge.py`
- `docs/program/tasks/AR-SIX-RUN-SCOPE-BRIDGE-01.md`
- `docs/program/AR-SIX-RUN-SCOPE-BRIDGE-01.md`

## Forbidden hotspots

`contracts/**`, migration head, root dependencies/locks, composition root, global styles, routers/UI, provider transport, v1/v2 prompt bytes, corpus/Blob/DB state, `origin/main`, tags and stand.

## Non-goals

No map/legal approval, query vectors, six verified sets, six persisted Run linkage/aggregation, profile registration, provider call, saved citations or live acceptance.

## Deliverables

Six-scope enumerator, scoped set/request and bridge binding, refusal/totality tests, this task/report.

## Required tests

- Focused scope, request, bridge, existing v3 prompt/grounding and programme-governance tests — pass.
- Python compilation of changed modules, `git diff --check` and exact allowed-path proof — pass.
- No full `make gate` under R-135 for an intermediate development slice.

## Integration contract

A future served caller supplies the scope and composition identity from a trusted reviewed six-map pack, along with the registered v3 profile/bundle/map and Run/Attempt/set authority. This bridge checks the selected item sequence and binds the scope to its draft digest; it does not prove caller trust or that six Runs were started. The runtime owner must persist one scope/map/set per Run and preserve a relation for the six results. No missing scope or set may fall back to v1.

## Failure/idempotency/security cases

Unknown scope, stale composition, wrong/duplicate/missing C item, wrong map/set binding or changed source text refuses. Exact bytes are deterministic. No external effect occurs in this task.

## Rollback / feature flag

Forward revert the additive unserved scope path. No migration or flag change.
