# Task RELEASE-0-7-0-NOTES-01 — release notes, version slot and technical record for 0.7.0

task_id: RELEASE-0-7-0-NOTES-01

## Outcome

A release candidate commit `R` on top of the gated candidate `9627e58a` that moves `VERSION` from `0.6.0` to `0.7.0` with a truthful, form-checked release-notes entry `release-notes/0.7.0.json` (revision 1, Russian user layer), the English technical record row in `docs/program/RELEASES.md`, and the `CURRENT_STATE.md` statement of the new version — nothing else. Every product claim in the notes is backed by a commit or a test named in the report, and an independent judge (run by the integrator after hand-back) checks each claim against the diff `v0.6.0..9627e58a`.

## Depends on

- the second complete gate of `9627e58a` (in progress; its log `.local/gates/night-9627e58a/gate.log`);
- the owner's statement of 2026-10-20 that the next release is `0.7.0` (the plan's bundled-history question for the 0.7–0.9 interval is thereby answered: one release `0.7.0` describes everything served since `0.6.0`).

## Frozen inputs

- base commit: `9627e58a1a2d5f85e0850dd62fe5e8a84524e0c6` (the gated candidate; descends from `origin/main` `ec3ebf07`);
- API 71 paths / 81 operations / 235 schemas (release tree `v0.6.0`: 47/54/123), 25 error codes, migration head `0027_optimisation_proposals` (release tree head `0021_portal_bundles`);
- the release rules: `docs/program/RELEASE_PROCESS.md`, `docs/program/VERSIONING_AND_FREEZE_POLICY.md`, `docs/program/VERSION_FIXATION.md`, W52 design `docs/program/dispatch/W52-PLAN.md` §3.2–§3.5 and `ROADMAP-TO-BETA.md` §8.3; the form test `tests/contract/release_notes/test_release_notes_form.py`.

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

- `VERSION`
- `release-notes/0.7.0.json`
- `docs/program/RELEASES.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/RELEASE-0-7-0-NOTES-01.md`
- `docs/program/tasks/RELEASE-0-7-0-NOTES-01.md`

## Forbidden hotspots

Everything else: `src/**`, `web/**`, `contracts/**`, migrations, tests, `release-notes/*` other than `0.7.0.json` (history is immutable), dependency files, refs, tags, the stand. If a test or document elsewhere pins the literal `0.6.0` as the product version and turns red, STOP and report the exact path to the integrator (do not edit it).

## Non-goals

No tag, no push, no deployment, no change of product behaviour. Do not claim anything that is not served: the two unmerged slices (classification correction, normative references) and everything marked draft/unserved in `CURRENT_STATE.md` are NOT part of 0.7.0.

## Deliverables

`release-notes/0.7.0.json` (version `0.7.0`, `revision` 1, `date` 2026-10-20, a short title, items grouped Новое / Улучшено / Исправлено, each with `screen` an address from `web/src/shared/config/screen-registry.ts` and a `where` path matching the registry's current group and screen labels, texts in the user's words with on-screen labels in «ёлочки»); the English row in `RELEASES.md` (what changed technically: surface 47/54/123 → 71/81/235, migrations 0022–0027 applied forward at deploy with no backfill, new upload proxy locations, nothing deployed yet, rollback notes); `VERSION` = `0.7.0`; the `CURRENT_STATE.md` sentence that carries `VERSION is \`0.7.0\``; and the report `docs/program/RELEASE-0-7-0-NOTES-01.md` with a CLAIM TABLE: each note item → the commit(s)/test(s) that prove it (derive from `docs/program/NIGHT-1020-INT-01.md`, the task reports under `docs/program/`, `git log v0.6.0..9627e58a`, and the screens/operations that exist in the registry and contract).

## Required tests

Container-free only, light: `tests/contract/release_notes`, `tests/contract/program`, `tests/contract/api_v1/test_doc_prose_facts.py`, the dictionary/prose rules the form test uses, and whatever else `grep -rn "0.6.0" tests web/tests` shows reads the version — run those. No full gate (the integrator runs it on the final R).

## Integration contract

The integrator hands `R` to an independent judge, then runs the complete gate on the exact `R` and asks the owner for the exact-SHA `main` instruction (AGENTS §6). The notes must therefore be final in one pass; later corrections are higher revisions only after `main`.

## Failure/idempotency/security cases

A claim without proof is deleted, not softened. A feature that exists only behind an unserved module is not listed. Opaque identifiers, file names and internal terms stay out of the user text.

## Rollback / feature flag

Revert the commit; `VERSION` returns to `0.6.0`.
