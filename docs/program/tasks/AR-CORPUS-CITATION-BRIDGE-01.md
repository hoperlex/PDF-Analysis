# Task AR-CORPUS-CITATION-BRIDGE-01 — bind saved norm set to AR v3 request

task_id: AR-CORPUS-CITATION-BRIDGE-01

## Outcome

A current Attempt can read the exact verified retrieval-set Blob through the
existing custody reader, bind its map/snapshot/set identities to one AR v3
draft request, and ground a supplied response against those same bytes. Only
accepted locally grounded normative proposals become publication candidates;
no provider call or DB finding write occurs in this slice.

## Depends on

- `AR-SET-PROMOTION-01` — completed and published on dev.
- `AR-V3-ORIGINAL-TOPICS-01` — completed at `a955346a`.
- `W57A-INT-V3-LOCAL-EVALUATION-PREP-01` — completed pure replay.
- `W57A-INT-CITATION-PREP-01` — completed pure quote/value grounding.
- `W57A-INT-SET-CUSTODY-READ-PREP-01` — completed Attempt-fenced set reader.
- `W57A-INT-CITE-TXN-PREP-01` — completed unserved citation writer.

## Frozen inputs

- `origin/dev=a955346aa2f30f004de66979acc2262d628ecd02` at start;
- contract `1.0.0`, migration head `0031_executor_pull_channel`;
- 0023 verified retrieval-set custody and immutable Run set pin;
- W57 §A3.3–A3.4: only labelled canonical paragraphs are sent; model proposals
  are checked against PDF and the same pinned set before publication.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: saved-set reader selects `map_sha256` but does not return it; pure
  AR v3 request/evaluation code cannot consume the DB/Blob result directly
  through public bounded-context surfaces.

### P-01 — existing seams

- captured_at: 2026-10-23
- command: `rg -n 'class VerifiedRetrievalSetInput|s.map_sha256|def load_verified_retrieval_set|def prepare_v3_request_candidate|def evaluate_v3_supplied_response' src/auditmanager/findings/retrieval_set_input.py src/auditmanager/analysis/profiles/ar_v3/{request_candidate,local_evaluation}.py`
- captured_output:
  ```text
  src/auditmanager/analysis/profiles/ar_v3/local_evaluation.py:57:def evaluate_v3_supplied_response(
  src/auditmanager/findings/retrieval_set_input.py:26:class VerifiedRetrievalSetInput:
  src/auditmanager/findings/retrieval_set_input.py:39:           s.map_sha256, s.reviewed_content_key
  src/auditmanager/findings/retrieval_set_input.py:110:def load_verified_retrieval_set(
  src/auditmanager/analysis/profiles/ar_v3/request_candidate.py:60:def prepare_v3_request_candidate(
  ```
- interpretation: custody, request and grounding exist separately; the
  adapter must bind their identities without treating supplied bytes as proof.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/findings/retrieval_set_input.py`
- `src/auditmanager/findings/public.py`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/runs/v3_citations.py`
- `tests/integration/findings/test_w57a_retrieval_set_input_offline.py`
- `tests/integration/runs/test_v3_corpus_citation_bridge.py`
- `docs/program/tasks/AR-CORPUS-CITATION-BRIDGE-01.md`
- `docs/program/AR-CORPUS-CITATION-BRIDGE-01.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root,
router/UI/global styles, provider transport, v1/v2 prompt bytes, corpus,
`origin/main`, tags and deployment host.

## Non-goals

No map/legal approval, larger prompt cap, profile registration, served model
dispatch, StageResult or finding write, live cost/sample or beta acceptance.

## Deliverables and checks

One bounded-context bridge, identity/refusal tests, this task/report. Checks:

- `/root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_corpus_citation_bridge.py tests/integration/findings/test_w57a_retrieval_set_input_offline.py tests/integration/analysis/test_ar_v3_prompt_material.py tests/integration/analysis/test_ar_v3_local_evaluation.py tests/contract/program`;
- `python3 -m py_compile` on changed Python paths;
- `git diff --check` and exact allowed-path proof.

R-135 defers the final beta gate.

## Integration contract

The caller supplies a persisted Run and current Attempt and trusted registered
profile/map identity. The reader confirms two-role set custody and exact Blob
bytes; the bridge refuses any Run/reader/profile/map mismatch before prompt.
The same bytes feed response grounding. Successful local evaluation yields
candidate data only; future PROFILE/CITE ownership must recheck Attempt and
model-call provenance, save CITE StageResult, publish in one DB transaction and
commit before exposing a finding. A wrong or absent set never falls back to v1.

## Rollback / feature flag

Revert the additive unserved bridge; no data migration or flag change.
