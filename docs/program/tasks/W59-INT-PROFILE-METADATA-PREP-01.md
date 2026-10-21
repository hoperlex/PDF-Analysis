# Task W59-INT-PROFILE-METADATA-PREP-01 — capture legacy section profile vocabulary

## Outcome

A self-contained candidate metadata catalogue records the legacy category
codes and sheet-type codes/labels for all 14 legacy sections, with source-file
digests. It is read-only vocabulary for W59–W62 authors, not a prompt or an
active profile. The separately retained `PB` awaits authored metadata.

## Depends on

- `W59-INT-SECTION-SUGGESTION-PREP-01` — complete at `6336f29e`.

## Frozen inputs

- base commit: `6336f29e008ec8c5c875d984bb708a5a0de186b3` (`origin/dev`);
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- migration head `0022_findings_v2`; `ROADMAP-TO-BETA.md` §10.3;
- legacy registry SHA-256 `0263e34ed60dd025a191230217832580bddefcdf10b7841f326784f8f8b08970`.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `src/auditmanager/analysis/profiles/section_candidates/metadata.json`
- enumerator_owner: `W59-INT-PROFILE-METADATA-PREP-01`
- totality_query: `tests/integration/analysis/test_section_profile_candidates.py::test_fourteen_legacy_candidates_and_no_implicit_pb_profile`

## Captured premise evidence

- premise: 14 legacy directories carry category and drawing-type tables.

### P-01 — source registry and exact base

- captured_at: 2026-10-15
- command: `sha256sum /root/projects/PDF-proverka/prompts/disciplines/_registry.json && git rev-parse HEAD origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/analysis/profiles/section_candidates`
- captured_output:
  ```text
  0263e34ed60dd025a191230217832580bddefcdf10b7841f326784f8f8b08970  /root/projects/PDF-proverka/prompts/disciplines/_registry.json
  6336f29e008ec8c5c875d984bb708a5a0de186b3
  6336f29e008ec8c5c875d984bb708a5a0de186b3
  ```
- interpretation: the new catalogue path is absent; the legacy source is
  available read-only in this workspace for one-time extraction.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/section_candidates/**`
- `tests/integration/analysis/test_section_profile_candidates.py`
- `docs/program/tasks/W59-INT-PROFILE-METADATA-PREP-01.md`
- `docs/program/W59-INT-PROFILE-METADATA-PREP-01.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

`contracts/**`, migrations, existing profiles/stages/runs, provider lock,
root dependencies/locks, composition root, global styles, production
configuration, `VERSION`, recordings, tags and `origin/main`.

## Non-goals

No prompt text, normative conclusion, profile activation, `PB` profile,
contract reseal, provider call, comparison logic, full local gate or
acceptance.

## Deliverables

Candidate metadata JSON, validating loader, focused tests, report and dev
read-back.

## Required tests

- focused loader tests for 14 entries, source digests, duplicate/unknown
  code refusal and absence of normative prose;
- module compilation, direct task governance, `git diff --check` and exact
  changed-path proof; no `make gate`.

## Integration contract

W59–W62 profile authors may use codes and sheet labels as vocabulary only.
Each profile must review legacy prompt instructions separately, verify any
normative claim against an available corpus version and bind an immutable
profile identity before execution. `PB` requires a new authored profile.

## Failure/idempotency/security cases

The bundled resource is digest-checked and refuses tampering or missing
entries. No source file is read from the old repository at runtime. Repeated
loads return the same immutable metadata; no external side effect occurs.

## Rollback / feature flag

Revert the additive package before profile wiring; no DB rollback or flag.

## Handoff

- changed files/checks/limits: report;
- contracts: none;
- next: reviewed prompt material and profile identity per section.
