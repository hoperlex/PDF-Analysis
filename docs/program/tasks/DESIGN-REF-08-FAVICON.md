# Task DESIGN-REF-08-FAVICON — знак вкладки браузера

## Outcome

Фавикон AuditManager повторяет новый знак в боковой панели, остаётся различимым в маленькой вкладке и согласуется с тёмной и светлой темами.

## Depends on

- `DESIGN-REF-07-NORMS` (completed and published at `726a3bc2df5de15582d9ad2ce351b0babd9bd95b`).

## Frozen inputs

- Base: `726a3bc2df5de15582d9ad2ce351b0babd9bd95b` (`origin/dev`).
- API/contract: `1.14.0`; migration head `0043_stage_ai_generations`.
- New brand mark paths in `web/src/_app/app-frame.tsx` at base are read-only; the app-directory icon route stays unchanged.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- Next.js serves `web/src/app/icon.svg`. Its current blue square and white letter A are from the former palette; the sidebar mark introduced by `DESIGN-REF-06-CHROME` uses linked strokes and teal accent.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`
- origin_main_authority: none

## Allowed paths

- `web/src/app/icon.svg`
- `docs/program/tasks/DESIGN-REF-08-FAVICON.md`
- `docs/program/DESIGN-REF-FOLLOWUP-1030.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

- Brand component, global CSS, registry, APIs, contracts, migrations, dependencies, composition roots, other assets and `origin/main`.

## Non-goals

- A logo rework, route or metadata changes, generated raster icon variants.

## Deliverables

- Self-contained SVG icon with the same mark geometry as the sidebar, high contrast on a dark tile.
- XML/production build checks and one fast-forward push to `origin/dev`.

## Required tests

- XML parse, exact path comparison with brand mark, production web build, `git diff --check`.
- Basic checks only, no full gate or review window per owner instruction.

## Integration contract

- Next.js keeps serving the app-directory `/icon.svg`; no import or metadata change is needed. The favicon is an asset and has no application state.

## Failure/idempotency/security cases

- Embedded paths and colors only, no external reference. Browser favicon caching may delay visual update; a hard reload is sufficient after deployment.

## Rollback / feature flag

- Revert the single commit; no flag or migration.

## Handoff

- Changed files are limited to this task's allowed paths. Brand component, global CSS, registry, contracts, migrations, dependencies, composition roots and `origin/main` are untouched.
- SVG XML parsed; all three path strings match the sidebar mark exactly; 16/64 px raster previews were inspected; production web build and diff check passed. The build exposes `/icon.svg`.
- No public contract changed. Publish the exact tested fast-forward commit to `origin/dev` only. Browser favicon caches may require a hard reload.
