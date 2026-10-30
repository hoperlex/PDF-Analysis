# Task DESIGN-M01-FOUNDATION — shared visual primitives and comparison CSS tokens

## Outcome

Every screen's main content consumes the two-theme presentation surface from the completed dashboard/shell pilots. Common page, control and table geometry is consistent, and the existing comparison CSS has no raw colour literals or undefined `--am-*` references. No page data or routes change.

## Depends on

- `HOTFIX-SHELL-NAVIGATION-INT-20261030` (completed and published at `62002e7139b0c6400a1119e2950e2b9dd17f6d0a`).

## Frozen inputs

- Domain/API/analysis/events contract: `1.13.0`.
- API surface: 230 paths / 256 operations / 619 schemas.
- Migration head: `0043_stage_ai_generations`.
- Base commit: `62002e7139b0c6400a1119e2950e2b9dd17f6d0a`.
- Design inputs: `docs/program/DESIGN-31-SCREEN-PLAN.md`, completed dashboard/shell palette.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: `web/tests/unit/styles/styling-layer.test.ts` fails on two literal fallbacks in the stage upload module; `tokens-defined.test.ts` finds 16 undefined reads in comparison modules. Source scan also finds literal colours in the stage pair viewer. The main content currently retains the older palette while its shell and dashboard consume showcase tokens.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`.
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/DESIGN-M01-FOUNDATION.md`
- `docs/program/DESIGN-31-SCREEN-PLAN.md`
- `docs/program/CURRENT_STATE.md`
- `web/src/app/globals.css`
- `web/src/_pages/stage-compare/ui/stage-upload-panel.module.css`
- `web/src/widgets/stage-sheet-map/ui/stage-pair-viewer.module.css`
- `web/src/widgets/stage-sheet-map/ui/stage-sheet-map.module.css`
- `web/src/widgets/stage-pair-catalog/ui/stage-pair-catalog.module.css`
- `web/src/widgets/stage-changes/ui/stage-changes.module.css`
- `web/src/widgets/stage-changes/ui/stage-journal.module.css`
- `web/src/widgets/stage-text-evidence/ui/stage-text-evidence.module.css`
- `web/src/widgets/stage-run-controls/ui/stage-run-controls.module.css`
- `web/tests/unit/styles/**`

## Forbidden hotspots

- `contracts/**`, migrations, locks/dependencies, composition roots, route registry, backend and all business/analysis behavior.
- Page/widget TypeScript outside the explicitly owned CSS paths, `origin/main`, preserved AR v3 branch.

## Non-goals

- Redesigning each of the 30 remaining screens, adding metrics, changing statuses, or broadening comparison features.
- Adding runtime tokens whose meaning is unclear when an existing semantic token fits.

## Deliverables

- Common presentation surface, page/card/control geometry and base table appearance for two themes. Individual wide-table wrappers belong to their screen mini-tasks.
- Comparison CSS reads existing named tokens; mask/search/focus overlays keep their semantic distinction.
- Focused style checks, current-state and roadmap update.

## Required tests

- `npm --prefix web run typecheck`
- `npm --prefix web run lint`
- `npm --prefix web test -- tests/unit/styles/theme.test.ts tests/unit/styles/dashboard-showcase.test.ts tests/unit/styles/styling-layer.test.ts tests/unit/styles/tokens-defined.test.ts`
- CSS parse, `git diff --check`, changed-path review.

## Integration contract

Only CSS rendering changes. `--am-*` reads resolve to values already defined in the common stylesheet; both dark sources remain equal. The evidence overlays retain three visibly distinct semantic colours. Every future mini-task starts from the resulting `origin/dev` SHA and owns its own local screen styles.

## Failure/idempotency/security cases

- Unknown statuses and missing data still use the existing error/empty states.
- Page roots retain `min-width: 0`; later screen mini-tasks own their wide-table scroll containers.
- Focus and reduced-motion behavior remain visible in both themes.

## Rollback / feature flag

- Revert this single visual commit; no feature flag or data migration is involved.

## Handoff

- Changed files: this task, `docs/program/DESIGN-31-SCREEN-PLAN.md`, `docs/program/CURRENT_STATE.md`, `web/src/app/globals.css` and the eight owned comparison CSS modules listed in `Allowed paths`.
- Checks: frontend typecheck and lint passed; 46 focused styling/theme/token/avatar tests passed, including both guards that were red on the preceding dev base. Edited CSS parsed with PostCSS; `git diff --check` passed. Full gate and browser walkthrough were not run under the owner's development-only testing boundary; `/tmp` has only 1.7 GB free.
- Contracts: unchanged at `1.13.0`; migration head remains `0043_stage_ai_generations`; no runtime data/analysis contract changed.
- Risk: the common colour remap reaches every main page. Semantic status hues remain on their existing tokens, but browser review of all 31 routes is deferred to `DESIGN-M10-ACCEPTANCE`; local screen layout work remains in M02–M09.
- Integrator: fast-forward this exact clean candidate to `origin/dev`; start M02 from its published SHA. Revert this commit to restore the prior visual layer without migration.
- Forbidden-hotspot proof: the diff is contained in `Allowed paths`. This integration task explicitly owns `web/src/app/globals.css`; no contract, migration, dependency, composition root, route registry, backend or page TypeScript is touched.
