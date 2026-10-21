# Task W59-INT-SECTION-SUGGESTION-PREP-01 — prepare 15-section suggestions

## Outcome

A pure module suggests project sections from a filename and extracted text
using the local legacy registry's patterns. It covers 14 legacy entries plus
the owner-retained `PB`; `PS` remains «Пояснительная записка». It never
confirms a section or routes an analysis run.

## Depends on

- `W55B-INT-CLOSE` — completed development baseline in `W55B-INT-CLOSE.md`.

## Frozen inputs

- base commit: `206461aa300cc91ec4c5ef14e174857429c4ce4a` (`origin/dev`);
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- migration head `0022_findings_v2`; `ROADMAP-TO-BETA.md` §10.3 S-1–S-6;
- source legacy registry SHA-256 `0263e34ed60dd025a191230217832580bddefcdf10b7841f326784f8f8b08970`.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `src/auditmanager/sections/suggestion_patterns.json`
- enumerator_owner: `W59-INT-SECTION-SUGGESTION-PREP-01`
- totality_query: `tests/integration/sections/test_suggestion.py::test_all_fifteen_sections_have_distinct_codes_and_names`

## Captured premise evidence

- premise: the legacy registry exists locally and no section-suggestion module is committed.

### P-01 — source and absent target

- captured_at: 2026-10-15
- command: `sha256sum /root/projects/PDF-proverka/prompts/disciplines/_registry.json && git rev-parse HEAD origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/sections tests/integration/sections`
- captured_output:
  ```text
  0263e34ed60dd025a191230217832580bddefcdf10b7841f326784f8f8b08970  /root/projects/PDF-proverka/prompts/disciplines/_registry.json
  206461aa300cc91ec4c5ef14e174857429c4ce4a
  206461aa300cc91ec4c5ef14e174857429c4ce4a
  ```
- interpretation: the task can copy only the legacy registry's section names
  and suggestion patterns; the new runtime remains independent of the old repository.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/sections/__init__.py`
- `src/auditmanager/sections/suggestion.py`
- `src/auditmanager/sections/suggestion_patterns.json`
- `tests/integration/sections/test_suggestion.py`
- `docs/program/tasks/W59-INT-SECTION-SUGGESTION-PREP-01.md`
- `docs/program/W59-INT-SECTION-SUGGESTION-PREP-01.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

`contracts/**`, migrations, existing section/API/UI/run code, provider lock,
root dependency/lock files, composition roots, global styles, production
configuration, `VERSION`, recordings, tags and `origin/main`.

## Non-goals

No W59 contract reseal, `PS` in the current API, persisted stage attribute,
automatic assignment, start-run behavior, profiles, provider call, full local
gate or acceptance.

## Deliverables

Self-contained 15-entry suggestion registry with source provenance, pure
ranking function, focused tests and development report.

## Required tests

- focused pytest for all sections, boundary matching, ties, text matches and
  the PB/PS distinction;
- module compilation, direct task governance and `git diff --check`;
- exact changed-path and dev read-back proof; no `make gate`.

## Integration contract

W59 framework may show these suggestions and require explicit expert
confirmation. The result contains possible codes and match evidence only;
it must never become `DocumentVersion.section` or select a profile without
that confirmation. W59's single contract owner adds `PS` and stage to API/DB.

## Failure/idempotency/security cases

No filename is an identity. A neutral or ambiguous input yields no automatic
choice. Pattern matching respects Unicode word boundaries to avoid substring
false positives; repeated inputs return the same ranking. The module makes
no network, DB or external-file access.

## Rollback / feature flag

Revert the additive module before UI/runtime wiring. No flag or DB rollback.

## Handoff

- changed files/checks/limits: report;
- contracts: none;
- next: W59 reseal and expert-confirmation workflow after the prior code blocks.
