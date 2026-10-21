# Task W57A-INT-V3-REQUEST-CANDIDATE-PREP-01 — unserved AR v3 request candidate

task_id: W57A-INT-V3-REQUEST-CANDIDATE-PREP-01

## Outcome

A pure builder verifies supplied retrieval-set bytes against expected W57a identities, binds them to the exact PDF version, and emits deterministic draft system/user/schema material with a local request digest. The returned object excludes full rebinding paragraphs and cannot activate a model call.

## Depends on

- `W57A-INT-SET-PROMPT-INPUT-PREP-01` — completed pure set parser.
- `W57A-INT-V3-RESPONSE-PREP-01` — completed v3 response schema.
- `W57A-INT-V3-PROMPT-MATERIAL-PREP-01` — completed pure draft renderer, integrated in `CFB-INT-DEV-PUBLISH-42`.
- `CFB-INT-DEV-PUBLISH-43` — completed development base `4c16ccd7ae975d5a32829e9bcdf975f8b12f66e1`.

## Frozen inputs

- base commit: `4c16ccd7ae975d5a32829e9bcdf975f8b12f66e1`
- API v1 SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- domain IDs SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations` SHA-256: `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- AR v3 set parser SHA-256: `401c718fdd9632c1b1373734f5775b4980912a26711d6e7f2b8115effcac3c31`;
- AR v3 draft renderer SHA-256: `f698bb02640fcc68d98aabeabd9f16fe3b11c58f9ece4735349f09bff3703c26`;
- AR v3 schema SHA-256: `2f0ef00356e9ba274d6261cf45dd871f463deba167cd3a68c0378266c1ffe6a7`;
- `docs/program/dispatch/W57-PLAN.md` A3.3–A3.4 and R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: dev43 has a pure set parser, draft prompt renderer and v3 schema, but no function binds them into one request candidate or digest.

### P-01 — exact base and available inputs

- captured_at: 2026-10-16
- command: `git rev-parse HEAD; rg -n '^def (parse_v3_set_input|prepare_v3_prompt|response_schema)' src/auditmanager/analysis/profiles/ar_v3/set_input.py src/auditmanager/analysis/profiles/ar_v3/prompt_material.py src/auditmanager/analysis/profiles/ar_v3/response_schema.py; git ls-tree -r --name-only HEAD src/auditmanager/analysis/profiles/ar_v3/request_candidate.py`
- captured_output:
  ```text
  4c16ccd7ae975d5a32829e9bcdf975f8b12f66e1
  src/auditmanager/analysis/profiles/ar_v3/response_schema.py:90:def response_schema() -> dict[str, Any]:
  src/auditmanager/analysis/profiles/ar_v3/set_input.py:128:def parse_v3_set_input(
  src/auditmanager/analysis/profiles/ar_v3/prompt_material.py:79:def prepare_v3_prompt(
  ```
- interpretation: the three pure inputs exist at the published base and the request-candidate module does not. This does not prove qualified corpus custody, CAP-01 or profile activation.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v3/request_candidate.py`
- `tests/integration/analysis/test_ar_v3_request_candidate.py`
- `docs/program/tasks/W57A-INT-V3-REQUEST-CANDIDATE-PREP-01.md`
- `docs/program/W57A-INT-V3-REQUEST-CANDIDATE-PREP-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependencies and lockfiles;
- existing v1/v2 production source, `src/auditmanager/norms/**`;
- API/routers, `src/auditmanager/bootstrap/**`, composition root;
- `CURRENT_STATE.md`, UI/global styles, remote refs and tags.

## Non-goals

No model/provider choice, `max_output_tokens`, G-11 start/reaudit budget enforcement, reviewed W57a map, qualified W54 snapshot/set, DB/Blob custody, profile or prompt-bundle seal, CAP-01 measurement, Run activation, model output, canonical finding or beta claim.

## Deliverables

Pure unserved request candidate and deterministic digest, focused tests, task and result report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/analysis/test_ar_v3_request_candidate.py tests/integration/analysis/test_ar_v3_prompt_material.py tests/integration/analysis/test_ar_v3_set_input.py`;
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract/program/test_wave_governance.py`;
- `python3 -m py_compile src/auditmanager/analysis/profiles/ar_v3/request_candidate.py tests/integration/analysis/test_ar_v3_request_candidate.py`;
- `git diff --check`, frozen SHA-256 and `scripts/task_handoff.py` PASS.

## Integration contract

The later PROFILE owner must first prove exact Run/Attempt authority and custody-check the pinned retrieval-set Blob, then pass its bytes and expected set/map/snapshot IDs plus a validated TextLayer and pinned version UID. The builder repeats deterministic byte/schema/prompt checks and returns only selected prompt text, schema JSON, identity fields and a local digest. Its digest is for draft reproducibility, not a Run fingerprint or authority proof. The later caller must separately parse the same custody-checked set for local citation grounding and enforce G-11 and CAP-01 before any provider effect.

## Failure/idempotency/security cases

Foreign version, map, snapshot, SHA, altered set bytes, malformed set or foreign OCR context refuse without side effects. Full rebinding paragraphs cannot leak through the returned DTO. Identical inputs yield identical candidate bytes/digest; a changed PDF or hidden set paragraph changes the digest.

## Rollback / feature flag

Unserved additive source; revert the bounded commit before activation. No data rollback or feature flag.

## Handoff

- changed files: four exact allowed paths;
- commands/results: accompanying report and ignored technical handoff;
- known limits: no real corpus, custody proof, prompt seal or CAP-01;
- integration notes: cherry-pick after dev43, review and seal draft material only under later PROFILE ownership.
