# Task HOSTS-WEB-01 — «Исполнители» as servers, models by stage and a quiet advanced page

## Outcome
«Исполнители» has two tabs, «Серверы» and «Модели по этапам», and for an administrator a quiet link «Расширенные ▸» to a separate page that keeps the former connections, groups, rules, routes, processes and analysis presets. A server is a row with a «Использовать» switch, its models and its load; it is connected by one window with two ways (a terminal command, SSH). The stage layout is a read-only table for an expert and an editable one for an administrator. Unavailable things are not listed; the reason shows only where an action is blocked.

## Depends on
- HOSTS-SEAL-1

## Frozen inputs
- domain contract: 1.45.0, owned by `HOSTS-SEAL-1`; frozen here
- API contract: 1.45.0, with the host, layout and catalogue operations and the regenerated client in `web/src/shared/api/generated/**`; frozen here
- analysis/comparison/event contract: 1.45.0
- migration head: `0062_hosts_stage_models`
- base commit: `8f76b4ed6daadad95f9c001e2c2c0dca717aad2d`
- the dispatcher replaces the base by the tip carrying `HOSTS-SEAL-1` at dispatch
- architecture: `docs/architecture/adr/ADR-0028-hosts-and-stage-models.md` decisions 1, 3, 12, 14, 16, 17; rulings `R-153a`, `R-153d`, `R-153f` and `R-149n` (the reason of a wait stays visible)
- the web rules: the application's own `--am-*` styles with no UI library; module CSS follows the census rules; no direct fetch outside the generated client; the viewer role sees none of the new reads (`R-150w`)
- `HOSTS-SEAL-1` already added one neutral entry to the four enum mirrors under `web/src/entities/**`; this task owns the final words of the two in `entities/executor-group/`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `web/src/shared/config/screen-registry.ts`
- enumerator_owner: HOSTS-WEB-01
- totality_query: `grep -n "address:" web/src/shared/config/screen-registry.ts`

## Captured premise evidence
- premise: «Исполнители» has six tabs today

### P-01 — the tabs now
- captured_at: 2026-11-09
- command: `grep -n "export const WORKERS_TABS" web/src/_pages/workers/model/tabs.ts`
- captured_output:
  ```text
  22:export const WORKERS_TABS = ['overview', 'connections', 'processes', 'groups', 'rules', 'routes'] as const;
  ```
- interpretation: six tabs become two plus the advanced page; the former tabs move, they are not rewritten. The count of concepts per screen is in `HOSTS-PLAN.md` §9.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `web/src/_pages/workers/**`
- `web/src/app/workers/**`
- `web/src/widgets/executor-connections/**`
- `web/src/widgets/executor-groups/**`
- `web/src/widgets/executor-routes/**`
- `web/src/widgets/executor-rules/**`
- `web/src/widgets/worker-list/**`
- `web/src/widgets/analysis-presets/**`
- `web/src/widgets/executor-hosts/**`
- `web/src/features/connect-remote-agent/**`
- `web/src/features/manage-executor-connection/**`
- `web/src/features/manage-executor-group/**`
- `web/src/features/manage-executor-host/**`
- `web/src/features/manage-stage-layout/**`
- `web/src/features/set-worker-intake/**`
- `web/src/features/manage-analysis-preset/**`
- `web/src/entities/executor-connection/**`
- `web/src/entities/executor-group/**`
- `web/src/entities/executor-host/**`
- `web/src/entities/stage-layout/**`
- `web/src/shared/config/screen-registry.ts`
- `web/tests/unit/workers/**`
- `web/tests/unit/executor-groups/**`
- `web/tests/unit/stage-layout/**`
- `web/tests/guards/screen-registry.guard.test.ts`
- `web/tests/guards/screen-set.guard.test.ts`
- `web/tests/guards/rendered-language.guard.test.ts`

## Created by this task
Not yet in the tree at the base: `web/src/widgets/executor-hosts/`, `web/src/features/manage-executor-host/`, `web/src/features/manage-stage-layout/`, `web/src/entities/executor-host/`, `web/src/entities/stage-layout/`, `web/src/app/workers/advanced/page.tsx` (inside the allowed `web/src/app/workers/**`) and `web/tests/unit/stage-layout/`.

## Forbidden hotspots
- `web/src/shared/api/generated/**`, `web/openapi/**`, `web/FRONTEND_LOCK.json`: regenerated only by the contract task
- `web/src/widgets/run-progress/**`, `web/src/widgets/extended-review/**`, `web/src/_pages/run/**`, `web/src/features/start-run/**`, `web/src/features/reaudit-run/**`, `web/src/features/start-run-from-stage/**`: wave 2 (`RUN-SCREEN-01`, `RUN-START-ONE-01`)
- `web/src/entities/audit-run/**` and `web/src/entities/version-series/**`: wave 2
- global styles (`web/src/app/globals.css`), root `package.json` and `package-lock.json`
- every other guard under `web/tests/guards/`: a guard that fails for another reason is reported to the integrator
- `src/**`, `contracts/**`, `db/migrations/**`

## Non-goals
- no run screen, no start button, no stages window (wave 2)
- no new control the plan does not name (`R-153f`): the server row has the switch, the models, the load and a «⋮» of two items
- no reserve-set control (`R-153e`)
- no stand-side logic in a component: the web calls the generated client only
- no browser journey run

## Deliverables
- **«Серверы».** A summary («На связи 2 из 3 · свободно 3 из 5»); a row per server: online mark, name, «Использовать» (administrator only), model chips without prefixes, a label «API» only on metered models, the load, a «⋮» with «Подробнее» (slots, «Проверить сейчас», reasons of unavailability, current tasks) and «Удалить». A server without contact is a grey row with «нет связи с …»; without an available model, «нет доступных моделей». Unavailable models are not drawn as chips. Polling every 10 s while the screen is open. The `D-291` warning in one line, here and in the connect window, while the debt is open.
- **«Подключить сервер».** One window, two tabs: «Командой в терминале» (the line, «Копировать», a live status «найдено: …») and «По SSH» (host and user, a generated key, the fingerprint and three steps; port and own key under «Дополнительно»). The model is never asked.
- **«Модели по этапам».** A table of six rows «строка — модель · усилие», read-only for an expert, with «⚠ нет на серверах» on a row whose model no server has. An administrator gets «Изменить»: the segments «Только Claude · Только Codex · Свой набор», models from the available ones, and under «Дополнительно» the answer limit and the timeout. The viewer sees neither the tab nor the table.
- **«Расширенные ▸».** A separate page for an administrator: the former «Подключения», «Группы», «Правила», «Назначения», «Процессы», the analysis presets moved from their place, the layout journal and the switch «Модели по этапам: включены». The former tabs are reused, not rewritten.
- **Enum words.** The final words of `MEMBER_ISSUE_SENTENCES` and `WAIT_CAUSE_SENTENCES` for `host_disabled`, `model_not_verified` and `model_cooling_down`.
- **Screen registry and guards.** One row for the advanced page; the registry, screen-set and rendered-language guards follow, nothing else.

## Required tests
- command: `npm --prefix web run typecheck`, `npm --prefix web run lint`, `npm --prefix web test -- tests/unit/workers tests/unit/executor-groups tests/unit/stage-layout tests/guards/screen-registry.guard.test.ts tests/guards/screen-set.guard.test.ts tests/guards/rendered-language.guard.test.ts`; then the style census guards of the touched widgets with the same runner
- expected: pass. Cases: two tabs and the advanced link for an administrator only; an unavailable model is not a chip; the expert's layout table has no control; the viewer sees none of the new reads; a server row has exactly the controls the plan names; the «Использовать» switch is absent for an expert; the connect window never asks for a model

## Integration contract
- `RUN-START-ONE-01` and `RUN-SCREEN-01` (wave 2) read the layout only through the generated client and the entity `stage-layout` exported here.
- The overlap with the UI-parity programme (the «Обзор» of «Исполнители» becomes the summary line) is agreed with its integrator before dispatch.

## Failure/idempotency/security cases
- a command the administrator repeats carries one idempotency key, as every write of the client does
- a refusal shows the catalogue message and never an internal identifier
- the connect window shows the enrollment secret once and never stores it

## Rollback / feature flag
Revert the lane. The layout tab shows nothing editable while the layout switch is off, and the advanced page keeps every former control.

## Handoff
- changed files: the lane lists them; it does not run git
- commands/results: the web checks above; no browser journey
- known limits: no live check against a real server (owner act)
- integration notes: the entities exported; the concept count of each screen before and after
