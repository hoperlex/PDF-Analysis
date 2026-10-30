# Task DESIGN-M06-KNOWLEDGE — knowledge, blocks and norms

## Outcome

The knowledge base, block viewer, norms search/catalogue and norm document routes share readable two-theme panels and responsive search, tab and document surfaces.

## Depends on

- `DESIGN-M05-COMPARISON` (completed and published at `d13da2d98665540a32709bc454997ef4a0b1e788`).

## Frozen inputs

- Domain/API/analysis/events contract: `1.13.0`.
- API surface: 230 paths / 256 operations / 619 schemas.
- Migration head: `0043_stage_ai_generations`.
- Base commit: `d13da2d98665540a32709bc454997ef4a0b1e788`.
- Design contract: `docs/program/DESIGN-31-SCREEN-PLAN.md`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: These four routes already own search, tabs, snapshot designation and PDF/paragraph reading. The task changes local presentation only.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/DESIGN-M06-KNOWLEDGE.md`
- `docs/program/DESIGN-31-SCREEN-PLAN.md`
- `docs/program/CURRENT_STATE.md`
- `web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx`
- `web/src/_pages/knowledge-base/ui/knowledge-base-page.module.css`
- `web/src/_pages/blocks/ui/blocks-page.tsx`
- `web/src/_pages/blocks/ui/blocks-page.module.css`
- `web/src/_pages/norms/ui/norms-page.tsx`
- `web/src/_pages/norms/ui/norm-document-page.tsx`
- `web/src/_pages/norms/ui/norms-page.module.css`
- `web/src/widgets/norm-search/ui/norm-search.module.css`
- `web/src/widgets/norm-catalogue/ui/norm-catalogue.module.css`
- `web/src/widgets/norm-document/ui/norm-document.module.css`

## Forbidden hotspots

- Contracts, migrations, dependencies, backend, route registry, composition root, global styles and unrelated screens.
- `origin/main` and preserved AR v3 branch.

## Non-goals

- Changing search, extraction, snapshots, designation, PDF loading, read permissions or data.

## Deliverables

- Responsive filters, panels, tabs, readable results and norm paragraphs with scroll containment.
- Updated plan/current-state record and basic focused checks.

## Required tests

- Frontend typecheck, lint, focused knowledge/blocks/norms tests, CSS parse and diff/changed-path checks.

## Integration contract

Existing query keys, role gates, actions and wording stay intact. New wrappers and CSS consume shared semantic tokens for both themes.

## Failure/idempotency/security cases

- Loading/refusal/error states and snapshot designation confirmation remain in their original branches.

## Rollback / feature flag

- Revert the single visual commit; no flag, contract or migration is involved.

## Handoff

- Typecheck, lint, CSS parse, diff check and 85 focused knowledge, blocks,
  norms and styling tests passed.
- No forbidden hotspot changed. Start M07 from this commit only after remote
  `origin/dev` confirms its exact SHA.
