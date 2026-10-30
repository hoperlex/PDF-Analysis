# Task HOTFIX-NAV-20261030 — убрать дубль домашней навигации

## Outcome

Верхнее и мобильное меню не показывают пункт «Главная». Логотип AuditManager открывает `/`, а права доступа к домашнему экрану остаются прежними.

## Depends on

- Нет.

## Frozen inputs

- Base commit: `e8567a1981cbe35cf66bae4ce79b2877224df1be` (`origin/dev` при выделении worktree).
- API contract: `1.10.0`, 131 paths / 148 operations / 432 schemas; unchanged.
- Migration head: `0039_comparison_core`; unchanged.
- Screen registry and `screenDecision` on the base commit; no access-rule change.

## Allowed paths

- `web/src/_app/navigation.ts`
- `web/src/_app/frame-navigation.tsx`
- `web/src/_app/app-frame.module.css`
- `web/src/shared/config/screen-registry.ts`
- `web/tests/unit/shell/navigation.test.ts`
- `web/tests/unit/shell/screen-decision.test.ts`
- `web/tests/unit/qa_w50/r66-navigation.test.ts`
- `web/tests/unit/qa_w50/role-gated.test.ts`
- `web/tests/guards/screen-registry.guard.test.ts`
- `docs/program/tasks/HOTFIX-NAV-20261030.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root manifests and lockfiles, composition root, `web/src/app/globals.css`.
- Other screen rows, access roles, route handlers and the logo destination.

## Non-goals

- Change the home page, authorization, route redirects or other navigation groups.

## Deliverables

- Registry row for `/` retained with `inMenu: false`.
- Navigation model and both rendered menu layouts without the duplicate link.
- Focused navigation checks aligned with the new menu.

## Required tests

- `npm --prefix web run typecheck` — success.
- `npm --prefix web test -- --run tests/unit/shell/navigation.test.ts tests/unit/shell/screen-decision.test.ts tests/unit/qa_w50/r66-navigation.test.ts tests/unit/qa_w50/role-gated.test.ts tests/guards/screen-registry.guard.test.ts` — success.
- `git diff --check` — success.

The owner explicitly waived a complete gate and verification window for these hotfixes.

## Integration contract

`buildNavigation` returns only grouped menu entries. The home screen remains in `SCREEN_REGISTRY` for route matching and access checks; `AppFrame` continues to link its brand to `HOME_SCREEN`. A role-less account gets no product navigation landmark but can still open `/` through the brand.

## Failure/idempotency/security cases

- A guest, default credential, or incomplete profile still gets no product menu.
- Role-gated groups remain filtered by `screenDecision`.

## Rollback / feature flag

No feature flag. Revert this task's code and test changes to restore the previous menu entry.

## Handoff

- Integrator combines this task with the independent favicon and AI-limit tasks on `dev`.
- No contract, migration, lockfile or global-style changes in this task.
- `npm test -- --run tests/unit/shell/navigation.test.ts tests/unit/shell/screen-decision.test.ts tests/unit/qa_w50/r66-navigation.test.ts tests/unit/qa_w50/role-gated.test.ts tests/guards/screen-registry.guard.test.ts` from `web/`: 71 passed.
- `npm run typecheck` from `web/`: passed.
- Targeted `eslint --quiet`: passed.
- `git diff --check`: passed.
