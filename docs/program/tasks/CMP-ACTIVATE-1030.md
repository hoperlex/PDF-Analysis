# Task CMP-ACTIVATE-1030 — expose and configure comparison modules

## Outcome
The deployed API and worker default to both comparison modules on; the module setting remains aligned and reversible, and navigation offers the stage screen beside the version screen.

## Depends on
- CMP-INT-CODE-1030
- HOTFIX-PRESENTATION-INT-1030

## Frozen inputs
- domain contract: current dev candidate, unchanged
- API contract: `1.14.0`, unchanged
- comparison contract: ADR-0025 module set `none | versions | versions,stages`, unchanged
- migration head: `0043_stage_ai_generations`, unchanged
- base commit: `3037749df82191a1d265c05229d5e5788707cbc3`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
### P-01 — the development Compose candidate forwards the flag but defaults it off
- captured_at: 2026-10-30
- command: `rg -n 'AUDITMANAGER_COMPARISON_MODULES' infra/deploy/compose.server.yml infra/deploy/env/alpha.env.example`
- captured_output: `compose.server.yml` has one environment row on each of `api` and `worker`; `alpha.env.example` has one blank assignment; exit 0
- interpretation: this hotfix changes the deployment default and example to `versions,stages`; an explicit `none` remains the rollback.

### P-02 — stage screen is registered but hidden from the menu
- captured_at: 2026-10-30
- command: `rg -n -A 6 "address: '/stage-comparison'" web/src/shared/config/screen-registry.ts`
- captured_output: `inMenu: false`
- interpretation: the route exists but the global navigation cannot offer it.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev (owner's 2026-10-30 hotfix instruction: no gates, minimal checks and deploy build)
- origin_main_authority: none

## Allowed paths
- `docs/program/tasks/CMP-ACTIVATE-1030.md`
- `docs/program/CMP-ACTIVATE-1030.md`
- `infra/deploy/README.md`
- `infra/deploy/compose.server.yml`
- `infra/deploy/env/alpha.env.example`
- `web/src/shared/config/screen-registry.ts`
- `web/src/widgets/version-series/ui/specification-panel.tsx`
- `web/tests/unit/shell/navigation.test.ts`
- `web/tests/guards/screen-registry.guard.test.ts`
- `tests/integration/composition/test_comparison_module_env_wiring.py`

## Forbidden hotspots
- `contracts/**`, `db/**`, root dependency and lock files, composition roots, global styles, `origin/main`

## Non-goals
- no contract or database migration or live model call
- no new administration control: the module set is a deployment-wide operator choice

## Deliverables
- module activation default, menu entry, focused deployment-regression check, operator notes and handoff report

## Required tests
- `.venv/bin/python -m pytest -q tests/integration/composition/test_comparison_module_env_wiring.py`
- `npm --prefix web run test -- --run tests/unit/shell/navigation.test.ts tests/unit/screens/stage-compare.test.ts tests/guards/screen-registry.guard.test.ts`
- `npm --prefix web run build`
- `docker compose --env-file infra/deploy/env/alpha.env.example -f infra/deploy/compose.server.yml config --format json` (inspect only the comparison variable of api/worker/web)
- `git diff --check`

## Integration contract
The Compose deployment defaults `AUDITMANAGER_COMPARISON_MODULES` to `versions,stages` for both API and worker. An explicit `none` pauses new comparison work. The pages read `ProductVersion.comparison_modules`; both addresses are discoverable in the menu.
The user's hotfix instruction supersedes the former full-gate plan for dev publication only; it does not authorise main.

## Failure/idempotency/security cases
- An unknown module value remains a startup error. The off value keeps operations unavailable and no comparison work is claimed.
- No browser environment variable or client-side guess substitutes for the API's module value. Opening a menu address while its module is off shows the explicit module-off state.

## Rollback / feature flag
Set `AUDITMANAGER_COMPARISON_MODULES=none` on both deployed services and recreate them. Persisted comparison evidence remains.

## Handoff
- changed files, checks, limitations and integration notes: `docs/program/CMP-ACTIVATE-1030.md`
