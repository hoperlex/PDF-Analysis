# Task W57A-INT-V3-PROMPT-MATERIAL-PREP-01 — unserved AR v3 prompt material

task_id: W57A-INT-V3-PROMPT-MATERIAL-PREP-01

## Outcome

A pure AR v3 renderer prepares separate system and user prompt strings from reviewed AR v2 checklist sections, a supplied PDF text layer and a previously parsed W57a prompt part. The user string sends only the selected norm prompt part, not the full rebinding corpus. No model or finding is invoked.

## Depends on

- `W56A-INT-AR-V2-RECORDED-PROFILE-01` — completed reviewed AR v2 material.
- `W57A-INT-V3-RESPONSE-PREP-01` — completed v3 response shape.
- `W57A-INT-SET-PROMPT-INPUT-PREP-01` — completed and integrated in `CFB-INT-DEV-PUBLISH-40`.
- `CFB-INT-DEV-PUBLISH-41` — published development base `6f1307412c94de45e67ffdeba71506dc5a0aa8fb`.

## Frozen inputs

- base commit: `6f1307412c94de45e67ffdeba71506dc5a0aa8fb`
- API v1 SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- domain IDs SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations` SHA-256: `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- reviewed v2 material digest `01bee01f8c7f1c59227ff6c17398f1034f5094c9c3b8e26fc66ab5130a4ca610`;
- `docs/program/dispatch/W57-PLAN.md` A3.3 and R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: dev41 has reviewed v2 prompt sections and a pure v3 set parser, but no v3 prompt renderer or registered v3 profile.

### P-01 — exact base and candidate inputs

- captured_at: 2026-10-16
- command: `git rev-parse HEAD; rg -n '^def (system_prompt|render_user_prompt|parse_v3_set_input)' src/auditmanager/analysis/profiles/ar_v2/prompt_material.py src/auditmanager/analysis/profiles/ar_v3/set_input.py; git ls-tree -r --name-only HEAD src/auditmanager/analysis/profiles/ar_v3/prompt_material.py`
- captured_output:
  ```text
  6f1307412c94de45e67ffdeba71506dc5a0aa8fb
  src/auditmanager/analysis/profiles/ar_v3/set_input.py:128:def parse_v3_set_input(
  src/auditmanager/analysis/profiles/ar_v2/prompt_material.py:52:def system_prompt() -> str:
  src/auditmanager/analysis/profiles/ar_v2/prompt_material.py:60:def render_user_prompt(
  ```
- interpretation: reviewed v2 material and the set-input boundary exist; the exact base has no v3 renderer. The capture proves code presence, not any qualified set, CAP-01 or profile activation.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v3/prompt_material.py`
- `tests/integration/analysis/test_ar_v3_prompt_material.py`
- `docs/program/tasks/W57A-INT-V3-PROMPT-MATERIAL-PREP-01.md`
- `docs/program/W57A-INT-V3-PROMPT-MATERIAL-PREP-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependencies/locks;
- existing v1/v2 production files, `src/auditmanager/norms/**`;
- API/routers, `src/auditmanager/bootstrap/**`, composition root;
- `CURRENT_STATE.md`, UI/global styles, remote refs and tags.

## Non-goals

No reviewed W57a map, qualified set/snapshot, registered v3 identity, prompt bundle seal, CAP-01 output cap, provider call, Run activation, CITE publication, expert verdict or beta claim. The renderer is only draft material until the later profile owner binds and reviews its bytes.

## Deliverables

Pure unserved renderer, focused tests and task/result report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/analysis/test_ar_v3_prompt_material.py tests/integration/analysis/test_ar_v3_set_input.py`;
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract/program/test_wave_governance.py`;
- `python3 -m py_compile src/auditmanager/analysis/profiles/ar_v3/prompt_material.py tests/integration/analysis/test_ar_v3_prompt_material.py`;
- `git diff --check`, frozen SHA-256 and `scripts/task_handoff.py` PASS.

## Integration contract

The later profile owner supplies a `V3SetInput` produced from the Run-pinned custody-checked set, plus the exact TextLayer and optional selected OCR context. This renderer adds plan-frozen v3 instructions to the reviewed AR sections, JSON-quotes PDF pages and appends exactly the selected prompt part. It never sends `rebinding_paragraphs`, never decides applicability or publishes a finding. The caller must separately enforce input budget, registered map identity and CAP-01 output cap.

## Failure/idempotency/security cases

Missing/invalid text layer, foreign OCR page, malformed set-input DTO or prompt cap violation refuse without side effects. PDF, OCR and norm paragraphs are data in the user prompt, never system instructions. Identical inputs yield identical prompt bytes.

## Rollback / feature flag

Unserved additive source; revert before activation. No data rollback or feature flag.

## Handoff

- changed files: four exact allowed paths;
- commands/results: accompanying report and ignored technical handoff;
- known limits: draft-only, no qualified W54 set or CAP-01;
- integration notes: cherry-pick after dev41, then a later PROFILE owner must review/seal material, prove custody and measured cap before any model call.
