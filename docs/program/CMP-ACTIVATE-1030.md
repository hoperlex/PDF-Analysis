# CMP-ACTIVATE-1030 — comparison hotfix

## Result

The server Compose candidate defaults `AUDITMANAGER_COMPARISON_MODULES` to `versions,stages` in both `api` and `worker`. The example `alpha.env` selects the same value. An operator can set `none` to pause new comparison work. «Сравнение стадий» is now in the Work menu next to «Сравнение версий». The existing pages still read the API's `ProductVersion.comparison_modules` and show an explicit off state when applicable.

The flag forwarding itself arrived on `origin/dev` in `HOTFIX-PRESENTATION-INT-1030` while this task was being prepared. This task sets its deployment default and example to on. The upstream branch was rebased before the hotfix. `origin/main` at `f0156895` has the stage route but not this flag forwarding or the menu change.

## Changed files

- `infra/deploy/compose.server.yml`, `infra/deploy/env/alpha.env.example`, `infra/deploy/README.md`: default-on deployment setting, example and rollback notes;
- `web/src/shared/config/screen-registry.ts`: stage screen in the Work menu;
- `web/src/widgets/version-series/ui/specification-panel.tsx`: two strict null/undefined checks for pagination, closing incoming lint failures;
- `web/tests/unit/shell/navigation.test.ts`, `web/tests/guards/screen-registry.guard.test.ts`, `tests/integration/composition/test_comparison_module_env_wiring.py`: focused menu and deployment assertions;
- `docs/program/tasks/CMP-ACTIVATE-1030.md` and this report: task and handoff.

## Verification

- Focused module and deployment tests: **24 Python passed**; focused menu/stage tests: **35 frontend passed**.
- The previous revision also passed 74 composition checks, 36 module tests, 92 related frontend tests, frontend lint and typecheck. The current code change since those runs is only the Compose value, example and docs.
- `npm --prefix web run build`: **passed**. Production output includes `/version-comparison` and `/stage-comparison`.
- `docker compose ... config --format json` using the example environment: **passed**; `api` and `worker` each resolve to `versions,stages`, `web` has no comparison flag.
- `git diff --check`: passed. No `make gate` was run for this hotfix, per the owner's direct instruction.

## Contracts, limitations and integration

No contract, migration, generated client, root dependency/lock, composition root or global style changed. API remains `1.14.0`; migration head remains `0043_stage_ai_generations`.

The menu is static and shows both comparison addresses even when the module is explicitly off; the opened page then says it is off. The older plan's statement that an off module has no menu item remains an interface difference. The broader C2–C4 browser and live-provider acceptance is still tracked by `D-290`; this hotfix claims build and wiring, not that acceptance. Drawings may reach a model only after an expert consents to a specific comparison job; enabling the module makes those commands available.

Publish this exact candidate to `origin/dev` by fast-forward after a remote-ref check. Deployment needs the full comparison code from `dev`; updating `origin/main` remains a separate action requiring the owner's direct instruction naming the exact candidate. On the host, inspect any explicit `AUDITMANAGER_COMPARISON_MODULES` override in the private `alpha.env`; `none` keeps the module off. Recreate `api` and `worker` through `infra/deploy/deploy.sh`, then read `ProductVersion.comparison_modules` and run `infra/deploy/verify-deployed.sh`. Rollback is `AUDITMANAGER_COMPARISON_MODULES=none` with both services recreated; stored evidence remains.

Forbidden-hotspot proof: the task diff is confined to its allowed paths and changes no `contracts/**`, `db/**`, root lock, composition root or global style file.
