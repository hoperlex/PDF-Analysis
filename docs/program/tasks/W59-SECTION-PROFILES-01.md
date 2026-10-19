# Task W59-SECTION-PROFILES-01 — draft text profiles for 14 non-AR sections

task_id: W59-SECTION-PROFILES-01

## Outcome

Each non-AR section with legacy source material (АИ, ПЗ, ПОС, ТХ, КЖ, КМ, ОВ, ВК,
ПТ, ЭОМ, СС, ИТП, ГП) has a `text-profile/1` data package that the section-keyed
registry of `W59-SECTION-SEAL-01` loads, so a confirmed version of that section
runs with its own section-specific system prompt instead of being refused. ПБ
(`PB`, no legacy source) gets no package and stays refused.

## Depends on

- `W59-SECTION-IDENTITY-DECISION-01` — completed design input.

## Frozen inputs

- base commit: `9cf21cc0c111c819570927510ef40dec495df5e9` (`origin/dev`; the lane branches from the `integration/night-1020` commit that adds this file on top of it);
- legacy source: `/root/projects/PDF-proverka` at `16ba8e5d`, `prompts/disciplines/<CODE>/**`
  and `prompts/disciplines/_registry.json`;
- v1 prompt contract: `src/auditmanager/analysis/text/prompt.py` (two categories,
  response schema, preamble);
- rulings: `R-135`, `R-139`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/text/profiles/ai/**`
- `src/auditmanager/analysis/text/profiles/ps/**`
- `src/auditmanager/analysis/text/profiles/pos/**`
- `src/auditmanager/analysis/text/profiles/tx/**`
- `src/auditmanager/analysis/text/profiles/kj/**`
- `src/auditmanager/analysis/text/profiles/km/**`
- `src/auditmanager/analysis/text/profiles/ov/**`
- `src/auditmanager/analysis/text/profiles/vk/**`
- `src/auditmanager/analysis/text/profiles/pt/**`
- `src/auditmanager/analysis/text/profiles/eom/**`
- `src/auditmanager/analysis/text/profiles/ss/**`
- `src/auditmanager/analysis/text/profiles/itp/**`
- `src/auditmanager/analysis/text/profiles/gp/**`
- `tests/unit/analysis/text_profiles/**`
- `docs/program/W59-SECTION-PROFILES-01.md`
- `docs/program/tasks/W59-SECTION-PROFILES-01.md`

## Forbidden hotspots

`contracts/**`, migrations, `src/auditmanager/analysis/text/profile.py`,
`profile_registry.py` and `profiles/ar/**` (owned by `W59-SECTION-SEAL-01`),
composition root, dependency files, `CURRENT_STATE.md`, refs, tags, the stand.

## Non-goals

No registry or run-start code, no new categories or response schema (v1's two
categories stay: internal contradiction and explicit placeholder — no
norm-compliance judgement, which is W57), no live provider call, no PB profile.

## Deliverables

Per section: `profile.json` (`format` `text-profile/1`, `section_code` as the
Latin code of `src/auditmanager/sections/suggestion_patterns.json`, fresh
`ap_`/`pb_` ULIDs, `profile_version` `1.0.0`, `status` `draft`, `title_ru` from
S-3, `source` with every legacy file path and SHA-256 used) and
`system_prompt.md` adapted from the legacy role/checklist to v1's
internal-consistency task; a pure unit test that validates every package;
report `docs/program/W59-SECTION-PROFILES-01.md` with the source hashes and what
was excluded (norm-compliance items).

## Required tests

`pytest tests/unit/analysis/text_profiles` (container-free), `git diff --check`,
`tests/contract/program`. No full gate.

## Integration contract

The packages are inert until `W59-SECTION-SEAL-01`'s registry loads them; the
integrator merges the seal first and then this lane, and runs the seal's
registry test over the merged tree. All profiles stay `draft` until an expert
review (debt row at integration).

## Failure/idempotency/security cases

Legacy text is data only; no instruction in it may change the v1 output
contract. Duplicate or unknown section codes must fail the unit test.

## Rollback / feature flag

Delete a section's package directory; its section returns to `section_profile_unavailable`.
