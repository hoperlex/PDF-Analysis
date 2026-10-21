# Task BETA-LIVE-JOURNEY-01 — the live PC-01 journey over the night-window screens (D-186)

task_id: BETA-LIVE-JOURNEY-01

## Outcome

The browser journey (`tests/e2e/pc01/journey`) walks every screen the night window of
2026-10-20 added, on a real stack with a real browser, and the run proves each screen
renders, performs its named action once and refuses what it must refuse. Every defect the
walk finds is fixed in this lane when it is inside the allowed paths, or recorded with the
exact reproduction when it is not. This is the live evidence `B12` asks for ("every menu
destination has an actual role-appropriate action, result and live acceptance") for the
code that exists today; it does not replace expert acceptance.

Screens and actions to cover, each with its route in `manifest.json`:

- confirm a version's stage and section (`classifyDocumentVersion`) and the section review;
- upload the next version of a set, open the version comparison and, for a П set with a Р
  successor, the П→Р comparison; carry a decision over an `unchanged` finding;
- «Нормы»: the catalogue and its Excel; «Настройки анализа» (profile list);
- «Диспетчер» and «Мои задачи»: assign, accept, change status as the right roles;
- «Оптимизация»: upload a price list (CSV), set a global and a project vendor list,
  «Спецификация и цены», start an optimisation pass, decide a proposal, download its CSV;
- «Оптимизация разделов» (section Form-7);
- the dashboard's section panel.

## Depends on

- `NIGHT-1020-INT-01` (dev `cc7b0994`); nothing else. It does not wait for
  `CLASSIFICATION-CORRECTION-01` or `NORM-REFS-RUN-01`; the integrator re-runs the walk on the
  merged tree afterwards.

## Frozen inputs

- base commit: `cc7b0994` on `integration/night-1020` (surface 71/81/235, head `0027`);
- `tests/e2e/pc01/journey/README.md` (the origin must be one you may write to; the write half
  creates state) and `manifest.json` as the journey's single declaration;
- rulings `R-135`, `R-139`, `R-140`; the rendered-language rule (Russian copy, one wording each);
- no contract change, no migration, no new dependency.

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

- `tests/e2e/pc01/**`
- `tests/contract/**` (only the journey-conformance pins that follow the manifest)
- `web/src/widgets/**`, `web/src/entities/**`, `web/src/features/**`, `web/src/_pages/**`,
  `web/src/app/**` (only to repair a defect the walk proves; each repair carries a vitest
  case that fails without it)
- `web/tests/**`
- `src/auditmanager/api/**`, `src/auditmanager/<context>/**` (only to repair a proven defect,
  with a test that fails without the repair; no behaviour change beyond the defect)
- `docs/manual-tests/**`
- `docs/program/BETA-LIVE-JOURNEY-01.md`
- `docs/program/tasks/BETA-LIVE-JOURNEY-01.md`

## Lane resources

- foundation_instance: `auditmanager-beta-live-journey`
- postgres_port: `57700`
- s3_api_port: `61300`
- s3_console_port: `61301`
- postgres_db: `auditmanager_beta_live_journey`
- s3_bucket: `auditmanager-beta-live-journey`
- the web tier and API on ports of the lane's choosing above 61310, chosen free by `ss -ltn`.

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, dependency and lock files, `web/FRONTEND_LOCK.json`,
`web/openapi/**`, `web/src/_app/providers.tsx`, global styles, `CURRENT_STATE.md`,
`tests/support/expected_facts.json`, refs, tags, the stand, anything under `.local/worktrees`
other than the lane's own. A defect that needs a contract or migration change is recorded,
not repaired.

## Non-goals

No new screen, no new operation, no live provider call (recorded adapter only, the lane's
stack is `FOUNDATION` recorded mode), no expert acceptance claim, no full gate. Do not
widen a screen's copy beyond fixing a proven wording defect.

## Deliverables

1. The manifest and journey steps for the screens above, each with a negative case (a
   role that must be refused, an input that must be refused).
2. The walk's envelope from a green run on the lane's stack, kept under the lane's
   `.local` evidence directory, and quoted in the report with the exact command.
3. Every defect found: reproduction, repair (with its failing-first test) or the record.
4. Report `docs/program/BETA-LIVE-JOURNEY-01.md` with the AGENTS section 5 list.

## Required tests

`npm --prefix web run e2e:pc01 -- --phase all` on the lane's own stack to a green exit;
journey static conformance (`pytest tests/e2e/test_pc01_journey_conformance.py`);
`tests/contract`; changed vitest files; lint and typecheck of touched web code; the
guard-can-fail proofs the journey README names. Each new assertion is shown failing under
a quoted mutation.

## Integration contract

Merges as one slice into `integration/night-1020` by a real merge
(`git merge-base --is-ancestor <tip> HEAD`); no generated artifact is touched, so there is
nothing to re-derive. Run the stack staggered: `free -m` available >= 2500 MiB and load
below 6 before `make up`; `make down` and remove the lane volumes at the end. Stop on
"GATE WINDOW" messages from the integrator.

## Failure/idempotency/security cases

A role refused where the screen says refused; a second identical submit changes nothing;
a read-only role sees no write control; a price-list or CSV cell starting with `=`, `+`,
`-` or `@` is escaped on export.

## Rollback / feature flag

Revert the merge; the repaired defects return with it.
