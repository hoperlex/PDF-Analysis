# Task W57A-INT-V3-LOCAL-EVALUATION-PREP-01 — pure AR v3 response replay

task_id: W57A-INT-V3-LOCAL-EVALUATION-PREP-01

## Outcome

A supplied, untrusted AR v3 response can be replayed offline only against the exact draft request candidate and its original set bytes, PDF text layer and OCR selection. The replay returns local PDF-first/norm-second accepted/rejected diagnostics with malformed/salvaged counts, never a canonical finding or expert decision.

## Depends on

- `W57A-INT-V3-REQUEST-CANDIDATE-PREP-01` — completed locally at `9978ded43b3ac42aa5327dcf552f11097e15ddd2`.
- `W57A-INT-SET-PROMPT-INPUT-PREP-01` — completed pure set parser.
- `W57A-INT-V3-RESPONSE-PREP-01` — completed strict v3 response parser.
- `W57A-INT-CITE-GROUNDING-CORE-01` — completed PDF-first and norm-second pure gate.

## Frozen inputs

- base commit: `9978ded43b3ac42aa5327dcf552f11097e15ddd2`
- API v1 SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- domain IDs SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations` SHA-256: `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- request-candidate source SHA-256: `7155467e274e7b9f79ac15dd403252343625ea941ddc3b56b8217e487e3a2e40`;
- v3 parser source SHA-256: `1afac650f56877c04e5102e144cdb47adf247c1e4d96bd3f66a916c7e16c73f6`;
- v3 grounding source SHA-256: `9f7d49c1d9ac320ebbc55f0405a76b17636061bc15e39e0e96ed5099f8425aa1`;
- `docs/program/dispatch/W57-PLAN.md` A3.3–A3.5 and R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: base 9978 has a pure draft request builder, response parser and grounding gate, but no request-bound offline response replay.

### P-01 — exact base and source functions

- captured_at: 2026-10-16
- command: `git rev-parse HEAD; rg -n '^def (prepare_v3_request_candidate|parse_response|ground_v3_proposals)' src/auditmanager/analysis/profiles/ar_v3/request_candidate.py src/auditmanager/analysis/profiles/ar_v3/response.py src/auditmanager/analysis/profiles/ar_v3/citation_grounding.py; git ls-tree -r --name-only HEAD src/auditmanager/analysis/profiles/ar_v3/local_evaluation.py`
- captured_output:
  ```text
  9978ded43b3ac42aa5327dcf552f11097e15ddd2
  src/auditmanager/analysis/profiles/ar_v3/citation_grounding.py:71:def ground_v3_proposals(
  src/auditmanager/analysis/profiles/ar_v3/response.py:169:def parse_response(output_text: str, *, truncated: bool) -> ParsedResponse:
  src/auditmanager/analysis/profiles/ar_v3/request_candidate.py:60:def prepare_v3_request_candidate(
  ```
- interpretation: the three pure parts exist and the local replay module does not. This proves no provider provenance, corpus custody, CAP-01 or runtime activation.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v3/local_evaluation.py`
- `tests/integration/analysis/test_ar_v3_local_evaluation.py`
- `docs/program/tasks/W57A-INT-V3-LOCAL-EVALUATION-PREP-01.md`
- `docs/program/W57A-INT-V3-LOCAL-EVALUATION-PREP-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependencies and lockfiles;
- W54/W56b modules, existing v1/v2 production source, `src/auditmanager/norms/**`;
- API/routers, `src/auditmanager/bootstrap/**`, composition root;
- `CURRENT_STATE.md`, UI/global styles, remote refs and tags.

## Non-goals

No provider call, provider provenance, response recording, Run/Attempt or DB/Blob custody, qualified corpus, reviewed map, profile seal, G-11/CAP-01 enforcement, merge/publication, expert verdict, canonical finding or beta claim. Matching a supplied response digest claim to a draft request does not authenticate the response.

## Deliverables

Pure local evaluator with request/set/PDF identity recheck, offline withholding tests, task and result report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/analysis/test_ar_v3_local_evaluation.py tests/integration/analysis/test_ar_v3_request_candidate.py tests/integration/analysis/test_ar_v3_response_parser.py tests/integration/analysis/test_ar_v3_citation_grounding.py`;
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract/program/test_wave_governance.py`;
- `python3 -m py_compile src/auditmanager/analysis/profiles/ar_v3/local_evaluation.py tests/integration/analysis/test_ar_v3_local_evaluation.py`;
- `git diff --check`, frozen SHA-256 and `scripts/task_handoff.py` PASS.

## Integration contract

The later caller provides a `V3RequestCandidate`, the exact supplied set bytes and text layer/OCR used to build it, plus raw response text, explicit truncation signal and the response's claimed request digest. The evaluator rebuilds and compares the full draft request, checks its digest pairing, reparses the same set bytes, then invokes strict v3 response parsing and PDF-first/norm-second grounding. It returns only typed local diagnostics and a digest of raw response UTF-8 bytes. A later authorized adapter must separately prove provider/custody/effect provenance, enforce input/output caps and decide whether anything is publishable.

## Failure/idempotency/security cases

Changed hidden set text, PDF text, schema, request digest or OCR selection refuses before parsing. Malformed untruncated JSON refuses; truncated JSON salvages only complete initial proposals. PDF failure withholds before norm failure; OCR-only quotes cannot ground PDF evidence. Replaying identical inputs is deterministic and has no side effects.

## Rollback / feature flag

Unserved additive source; revert the bounded commit before activation. No data rollback or feature flag.

## Handoff

- changed files: four exact allowed paths;
- commands/results: accompanying report and ignored technical handoff;
- known limits: synthetic replay only, no custody/provider proof or canonical decision;
- integration notes: cherry-pick after request candidate commit 9978; later PROFILE/CITE owners must integrate with authority gates.
