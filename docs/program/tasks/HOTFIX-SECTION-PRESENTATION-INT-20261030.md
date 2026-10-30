# Task HOTFIX-SECTION-PRESENTATION-INT-20261030 — original-style analysis presentation for all sections

## Outcome

The home and dashboard show the fifteen section rows in an original-style overview; a project's section groups look like compact cards, and a Run displays a horizontal stage rail. Every count and state comes from existing API data. The existing analysis route and results remain authoritative.

## Depends on

- `HOTFIX-AR-ORIGINAL-PROFILE-INT-20261030` (completed on `origin/dev` at `3821261a7241d83625dbea5eb86755224229c5be`).

## Frozen inputs

- Domain/API/analysis/events contract: `1.13.0`.
- API surface: 131 paths / 148 operations / 432 schemas.
- Migration head: `0039_comparison_core`.
- Base commit: `3821261a7241d83625dbea5eb86755224229c5be`.
- Visual reference: `SU10KAZ/PDF-proverka` commit `3c99481719218b9cfa7560886529916646c61939`, `frontend/index.html` section overview, project cards, pipeline and `frontend/static/css/styles.css`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the original UI has compact section rows and project cards plus horizontal stage cards; this tree has a plain section list and a stage table. The current dashboard contract gives document counts per section, not per-section finding or expert-decision counts, so those columns cannot be populated honestly.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`, continuing the owner's development-only publication preference.
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/HOTFIX-SECTION-PRESENTATION-INT-20261030.md`
- `docs/program/CURRENT_STATE.md`
- `web/src/_pages/home/ui/home-page.tsx`
- `web/src/_pages/home/ui/home-page.module.css`
- `web/src/_pages/dashboard/ui/dashboard-page.tsx`
- `web/src/widgets/dashboard/**`
- `web/src/widgets/project-sections/**`
- `web/src/widgets/run-progress/ui/run-progress.tsx`
- `web/src/widgets/run-progress/ui/run-progress.module.css`
- `web/tests/unit/screens/home.test.ts`
- `web/tests/unit/widgets/dashboard.test.ts`
- `web/tests/unit/sections/project-structure.test.ts`
- `web/tests/unit/screens/run-progress.test.ts`
- `web/tests/unit/styles/**`

## Forbidden hotspots

- `contracts/**`, migrations, root or web dependency locks, composition root, global styles and all backend analysis/Run behavior.
- The historical AR v3 branch and `origin/main`.

## Non-goals

- Implementing the original application's unported analysis stages or inventing per-section findings, expert decisions, model cost, or completion states.
- Changing API routes, stored evidence, prompt semantics, or adding a presentation-only backend response.

## Deliverables

- Original-inspired section overview on home/dashboard, section cards for all fifteen codes, and a horizontal rail of actual Run stages.
- Focused rendered tests and a short current-state record.

## Required tests

- `npm --prefix web run typecheck`
- `npm --prefix web run lint`
- Focused Vitest for home, dashboard, project structure and Run progress.
- `git diff --check` and a forbidden-hotspot diff review.

## Integration contract

The visual layer consumes the existing dashboard, document-list and Run-status reads. A section count is the server's `document_count`; selecting a row does not imply a per-section project list the API cannot supply. The rail derives only from `stageRows(status)`, and the detailed stage table remains visible. Missing data stays missing and error states remain errors.

## Failure/idempotency/security cases

- An incomplete section breakdown still shows the existing error state, not invented zeroes.
- An unknown Run stage/status still shows the existing closed-vocabulary fault, not a visual card.
- Static links follow existing project/Run routes and the server still enforces every action.

## Rollback / feature flag

- A revert restores the previous presentation. No runtime flag is needed because data and actions are unchanged.

## Handoff

- Changed files: home and dashboard section overview, project section cards, Run
  stage rail and their collocated CSS modules, focused rendering tests, current
  state and this record. The integration commit contains the exact path list.
- Checks: frontend typecheck and lint passed; 156 focused home/dashboard/project/
  Run rendering tests passed; `npm --prefix web run api:verify` reported 256
  operations; `git diff --check` passed. The 11 styling-layer tests passed on
  the original base, but after the concurrent comparison integration one of
  those tests fails on literal colours in its unowned
  `web/src/_pages/stage-compare/ui/stage-upload-panel.module.css` (166 of 167
  tests in the combined run passed). The broader rendered-language and
  contrast suites each exceeded a 45-second focused-check window without
  reporting a result. No full gate or provider call was requested.
- Contracts: unchanged at `1.13.0`; no migration or shared schema moved.
- Limitation: the current summary only has documents per section. The original
  app's project, expert-decision and finding columns cannot be populated from
  that response. The rail shows only stages in the current Run's recorded or
  scheduled set; it does not claim the original pipeline is implemented.
- Integrator: publish the tested commit by fast-forward to `origin/dev`; keep
  the original source snapshot and `origin/main` unchanged. Revert restores
  the previous layout without a data migration.
- Concurrent integration: before publication, `origin/dev` advanced to
  `3dbf4837` with the comparison beta. The visual commit was rebased over it;
  the Run's new `PdfPrecheckProgress` remains beside the stage table and the
  current-state record names the integrated `0043_stage_ai_generations` head.
- Forbidden-hotspot proof: the diff contains only the `Allowed paths`; no
  contract, migration, backend analysis, composition root, dependency lock or
  global stylesheet is touched.
