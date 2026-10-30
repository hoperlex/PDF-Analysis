# Task DESIGN-M03-PROJECT — project, document and version presentation

## Outcome

The project detail, document detail and version detail routes group their existing controls and evidence into responsive panels consistent with the two-theme shell.

## Depends on

- `DESIGN-M02-ENTRY` (completed and published at `611448ccaf1b80ea1b9212ea3103ce37b40e2a1d`).

## Frozen inputs

- Domain/API/analysis/events contract: `1.13.0`.
- API surface: 230 paths / 256 operations / 619 schemas.
- Migration head: `0043_stage_ai_generations`.
- Base commit: `611448ccaf1b80ea1b9212ea3103ce37b40e2a1d`.
- Design contract: `docs/program/DESIGN-31-SCREEN-PLAN.md`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: The three routes already compose the data and action widgets; this task adds local grouping only. Project tab reads remain lazy, and version back links still follow the fetched body's project identity.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/DESIGN-M03-PROJECT.md`
- `docs/program/DESIGN-31-SCREEN-PLAN.md`
- `docs/program/CURRENT_STATE.md`
- `web/src/_pages/project-detail/ui/project-detail-page.tsx`
- `web/src/_pages/project-detail/ui/project-detail-page.module.css`
- `web/src/_pages/document-detail/ui/document-detail-page.tsx`
- `web/src/_pages/document-detail/ui/document-detail-page.module.css`
- `web/src/_pages/version-detail/ui/version-detail-page.tsx`
- `web/src/_pages/version-detail/ui/version-detail-page.module.css`
- `web/src/widgets/project-sections/ui/project-sections.module.css`

## Forbidden hotspots

- Contracts, migrations, dependencies, backend, route registry, composition root, global styles and other screens.
- `origin/main` and preserved AR v3 branch.

## Non-goals

- Changing document and version reads, upload, classification, run launch, permissions or route identity.
- Restyling Run and comparison details owned by M04/M05.

## Deliverables

- Local panel hierarchy, contained long identifiers and section cards at narrow widths.
- Updated plan/current state and basic focused checks.

## Required tests

- Frontend typecheck, lint, focused project/document/version render tests, CSS parse and diff/changed-path checks.

## Integration contract

All existing widgets, links and conditional mount rules remain in their current order. The new classes provide presentation only and consume existing semantic tokens in both themes.

## Failure/idempotency/security cases

- Malformed address branches remain intact; pending/error/empty data still use existing state components.
- No new network reads or write controls.

## Rollback / feature flag

- Revert the single visual commit; no flag, contract or migration is involved.

## Handoff

- Typecheck, lint, CSS parse, diff check and 116 focused tests across cold load,
  upload, section structure, classification, optimisation and styling passed.
  An additional legacy comparison-only version test file has eight pre-existing
  assertions about the old immediate start button; the current cost preflight
  adds an estimate control and disabled start until consent. This task did not
  edit that component or its behavior.
- No forbidden hotspot changed. Start M04 from this commit only after remote
  `origin/dev` confirms its exact SHA.
