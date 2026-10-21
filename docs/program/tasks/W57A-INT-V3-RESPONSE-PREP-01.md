# Task W57A-INT-V3-RESPONSE-PREP-01 — pure AR v3 citation proposal input

task_id: W57A-INT-V3-RESPONSE-PREP-01

## Outcome

A pure, unserved AR v3 response schema and parser distinguish five normative
categories, which require 1–5 labelled citation proposals and both values,
from seven nonnormative categories, which forbid those properties. Malformed
and truncated proposals cannot acquire publication authority.

## Depends on

- `W57A-SEAL-01B` — complete at `c08182cab78bed70afbc777019d43de6c0bd2e18`;
- `CFB-INT-DEV-PUBLISH-28` — complete at `f468d20eaf46dba82908615b04f20090541b21df`.

## Frozen inputs

- base commit: `f468d20eaf46dba82908615b04f20090541b21df`;
- domain identifiers: SHA-256 `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- domain error catalogue: SHA-256 `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- API v1: SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- analysis registry: SHA-256 `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- migration head: `0023_norm_citations`, SHA-256 `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- functional rules: `docs/program/dispatch/W57-PLAN.md` §A3.3–A3.5.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `src/auditmanager/analysis/profiles/ar_v3/response_schema.py`
- enumerator_owner: `W57A-INT-V3-RESPONSE-PREP-01`
- totality_query: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/analysis/test_ar_v3_response_schema.py`

## Captured premise evidence

- premise: v3 has no registered runtime profile or response parser; the pure
  W57a quotation gate already exists, and the sealed category set is twelve.

### P-01 — missing response shape and existing pure gate

- captured_at: 2026-10-16
- command: `rg --files src/auditmanager/analysis/profiles src/auditmanager/norms | rg '(ar_v3|citation_prep)'`
- captured_output:
  ```text
  src/auditmanager/norms/citation_prep.py
  ```
- interpretation: no AR v3 profile files exist on the exact base. The existing
  citation gate is a separate pure function; this task supplies only its strict
  proposed-input shape, with no corpus or database authority.

### P-02 — frozen category vocabulary

- captured_at: 2026-10-16
- command: `sed -n '43,49p' db/migrations/versions/20261016_0023_norm_citations.py`
- captured_output:
  ```text
  OLD_CATEGORIES = (
      "internal_contradiction", "explicit_placeholder", "dimensions", "layout",
      "facade", "roof", "documentation",
  )
  NORM_CATEGORIES = (
      "evacuation", "fire_safety", "accessibility", "insulation", "sound",
  )
  ```
- interpretation: parser accepts exactly these twelve categories, with the
  normative five explicitly separated from legacy v2 categories.

### P-03 — stale v2 test pin after the additive API seal

- captured_at: 2026-10-16
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/analysis/test_ar_v2_response_schema.py tests/integration/analysis/test_ar_v2_response_parser.py`
- captured_output:
  ```text
  FAILED tests/integration/analysis/test_ar_v2_response_schema.py::test_v2_response_enums_match_the_sealed_api
  1 failed, 17 passed in 1.15s
  ```
- interpretation: the v2 test compared its seven unchanged categories to all
  twelve sealed API categories. Only this test's assertion is added to the
  grant; v2 production behavior and response bytes remain untouched.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W57A-INT-V3-RESPONSE-PREP-01.md`
- `docs/program/W57A-INT-V3-RESPONSE-PREP-01.md`
- `src/auditmanager/analysis/profiles/ar_v3/__init__.py`
- `src/auditmanager/analysis/profiles/ar_v3/response_schema.py`
- `src/auditmanager/analysis/profiles/ar_v3/response.py`
- `tests/integration/analysis/test_ar_v3_response_schema.py`
- `tests/integration/analysis/test_ar_v3_response_parser.py`
- `tests/integration/analysis/test_ar_v2_response_schema.py`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependencies and locks;
- `src/auditmanager/bootstrap/**`, existing v1/v2 profile and executor paths;
- API routes/schemas, `CURRENT_STATE.md`, UI, deployment inputs and global styles;
- remote refs, tags, stand services and corpus files.

## Non-goals

No AR v3 profile identity, owner-reviewed map, prompt bundle, CAP sample,
qualified retrieval set, grounding decision, citation write, report read,
provider call, served activation or corpus publication.

## Deliverables

Independent closed v3 proposal schema/parser, focused tests, and measured
report. Every parser field is untrusted model output until document grounding,
norm grounding, merged publication and persisted custody checks succeed.
The one v2 test pin checks its own seven legacy categories against the
additively extended API enum; v2 implementation is byte-identical.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/analysis/test_ar_v3_response_schema.py tests/integration/analysis/test_ar_v3_response_parser.py`;
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/analysis/test_ar_v2_response_schema.py tests/integration/analysis/test_ar_v2_response_parser.py`;
- `python3 -m py_compile src/auditmanager/analysis/profiles/ar_v3/*.py`;
- `git diff --check`; direct task governance findings `[]`;
- no PostgreSQL, S3, Docker, paid call or full suite during W55b host gate.

## Integration contract

Consumers receive structurally valid model proposals only. Normative proposals
carry exactly 1–5 `{label, quote}` pairs and two values; nonnormative proposals
carry none of those keys. No proposed citation is called verified, rebound,
persisted or published. The future profile/CITE owner must bind this schema to
reviewed prompt material and run the independent grounding gate.

## Failure/idempotency/security cases

Malformed complete elements are counted and dropped; an incomplete final
element is salvageable only with an explicit provider truncation signal.
Unknown fields, `null`, booleans as page numbers, empty values and out-of-range
citations refuse. Pure parsing is deterministic, has no state or external
effect, and never turns LLM output into an expert decision.

## Rollback / feature flag

The module is unserved and has no runtime side effect. Roll back the bounded
source commit if the later profile rejects this proposal shape.

## Handoff

- changed files: exact allowlist above;
- commands/results: completion report;
- known limits: no corpus-backed or service acceptance;
- integration notes: cherry-pick after dev28; do not activate a v3 Run from this slice.
