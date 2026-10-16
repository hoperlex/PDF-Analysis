# Task W57A-INT-SET-PROMPT-INPUT-PREP-01 — pure v3 set-to-grounding input

task_id: W57A-INT-SET-PROMPT-INPUT-PREP-01

## Outcome

One pure function validates supplied canonical retrieval-set bytes and returns the exact prompt part, unique reliable paragraphs and label bindings required by AR v3 grounding. It refuses altered text, forged labels, duplicate canonical identities and an oversized prompt. It does not claim that the supplied bytes passed DB/Blob custody.

## Depends on

- `W57A-INT-SET-ARTIFACT-PREP-01` — completed in the published W57a code-first chain.
- `W57A-INT-CITE-GROUNDING-CORE-01` — completed in `CFB-INT-DEV-PUBLISH-31`.
- `W57A-INT-SET-CUSTODY-READ-PREP-01` — completed in `CFB-INT-DEV-PUBLISH-36`.
- `CFB-INT-DEV-PUBLISH-39` — complete at `45d5772480f62006b430151d464a7f7200be511b`.

## Frozen inputs

- base commit: `45d5772480f62006b430151d464a7f7200be511b`
- API v1 SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- domain IDs SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations` SHA-256: `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- `docs/program/dispatch/W57-PLAN.md` A3.2–A3.4 and R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: published code can build and custody-check set bytes and ground
  supplied paragraphs, but has no v3 parser joining these boundaries.

### P-01 — set builder, custody reader and grounding already exist

- captured_at: 2026-10-16
- command: `git rev-parse HEAD; rg -n '^def (build_retrieval_set|load_verified_retrieval_set|ground_v3_proposals)' src/auditmanager/norms/retrieval/artifact.py src/auditmanager/findings/retrieval_set_input.py src/auditmanager/analysis/profiles/ar_v3/citation_grounding.py; git ls-tree -r --name-only HEAD src/auditmanager/analysis/profiles/ar_v3/set_input.py`
- captured_output:
  ```text
  45d5772480f62006b430151d464a7f7200be511b
  src/auditmanager/analysis/profiles/ar_v3/citation_grounding.py:71:def ground_v3_proposals(
  src/auditmanager/findings/retrieval_set_input.py:110:def load_verified_retrieval_set(
  src/auditmanager/norms/retrieval/artifact.py:210:def build_retrieval_set(
  ```
- interpretation: published code can produce set bytes, verify saved bytes under Attempt authority and ground supplied paragraphs/labels, but no v3 consumer parses saved set bytes into those inputs.

## Historical evidence

- correction_mode: addendum
- source_record: docs/program/tasks/W57A-INT-SET-PROMPT-INPUT-PREP-01.md at 735ef8083dd7b4236e34449c611f72c78922208f
- addendum_path: docs/program/W57A-INT-SET-PROMPT-INPUT-PREP-01.md

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v3/set_input.py`
- `tests/integration/analysis/test_ar_v3_set_input.py`
- `docs/program/tasks/W57A-INT-SET-PROMPT-INPUT-PREP-01.md`
- `docs/program/W57A-INT-SET-PROMPT-INPUT-PREP-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependencies and locks;
- `src/auditmanager/norms/public.py`, builders, existing readers/writers;
- API/routers, `src/auditmanager/bootstrap/**`, composition root;
- `CURRENT_STATE.md`, UI/global styles, remote refs and tags.

## Non-goals

No profile registration, model/prompt bundle identity, output-token cap, provider call, Run activation, set build, custody read, finding publication, route, qualified corpus or beta claim. The untrusted bytes require a prior custody check by the future caller.

## Deliverables

Pure bounded parser/grounding-input DTO, offline refusal tests, task and result report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/analysis/test_ar_v3_set_input.py tests/integration/analysis/test_ar_v3_citation_grounding.py`;
- `python3 -m py_compile src/auditmanager/analysis/profiles/ar_v3/set_input.py tests/integration/analysis/test_ar_v3_set_input.py`;
- `git diff --check`, frozen SHA-256 and `scripts/task_handoff.py` PASS.

## Integration contract

The caller passes bytes read through `load_verified_retrieval_set`, after checking exact Run/Attempt and pinned set identity. This parser checks canonical UTF-8 JSON, fixed artifact/ranking/quote versions, full-text hashes, prompt/full-row equality, sequential labels and unique canonical paragraph IDs; it returns `prompt_part`, `paragraphs` and `label_bindings` for `ground_v3_proposals`. The future prompt owner may use the prompt part only after the same custody proof. A synthetic byte array confers no publication authority.

## Failure/idempotency/security cases

Malformed, noncanonical, oversized, non-NFC, duplicate-key, inconsistent or foreign rows raise `V3SetInputRefused`. The operation is deterministic and read-only; all failure paths produce no model, DB or Blob effect.

## Rollback / feature flag

Unserved additive code; revert the bounded commit before activation. No data rollback or feature flag applies.

## Handoff

- changed files: four exact allowed paths;
- commands/results: result report and ignored technical handoff;
- known limits: offline proof only, no custody or real set;
- integration notes: cherry-pick after dev39; connect only under a later profile/CITE owner after real set and DB/S3 acceptance.
