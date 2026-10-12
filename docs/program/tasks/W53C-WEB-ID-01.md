# Task W53C-WEB-ID-01 — Identity screens are coherent and honest: the frame follows profile edits

## Outcome
Identity screens are coherent and honest: the frame follows profile edits, registration is reachable, forms cannot double-submit, failures read in Russian, destructive actions confirm, and role-less accounts see no product screens (C-07 web half, C-20…C-25).

## Depends on
- `W53-CLOSE-PLAN` (this wave's plan commit on `integration/w53-close`)

## Frozen inputs
- domain contract: `contracts/domain/v1` at base, unchanged
- API contract: `contracts/api/v1/openapi.json` at base (SHA-256 `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`), unchanged
- analysis/comparison/event contract: unchanged
- migration head: `0017_execution_queue`
- base commit: the `W53-CLOSE-PLAN` commit on `integration/w53-close`, itself on `origin/dev` `872266038a83568b56f6302f01b97771b9aaf281`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: none

The findings come from the 2026-10-12 static review of `872266038a83568b56f6302f01b97771b9aaf281`; `docs/program/dispatch/W53-CLOSE-PLAN.md` §2 lists them. Re-read each cited location before changing it and report any finding that no longer reproduces instead of changing code for it.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

The lane commits only on `agent/w53c-web-id`; the integrator merges and publishes.

## Allowed paths
- `web/src/_pages/{sign-in,register,register-submitted,account,change-password,admin-users,admin-user,admin-registrations,home,forbidden}/**`
- `web/src/features/{sign-in,register,change-password,edit-profile,manage-user,decide-registration}/**`
- `web/src/entities/{account,user,registration-request}/**`
- `web/src/widgets/{user-card,user-list,registration-queue,home-tiles}/**`
- `web/src/shared/config/screen-registry.ts`, `web/src/shared/lib/routes.ts`, `web/src/_app/navigation.ts`, `web/src/_app/frame-navigation.tsx`
- new `web/src/shared/ui/submit-lock.tsx`, new `web/src/shared/api/failure-message.ts`, new `web/src/app/global-error.tsx`
- `web/src/app/admin/users/[user_uid]/page.tsx`
- `web/tests/unit/**` test files covering the files above (existing or new); any guard that enumerates `web/src/app` files, only to admit `global-error.tsx`
- `docs/program/W53C-WEB-ID-01.md` (hand-back report)

## Forbidden hotspots
- `contracts/**` (no API, domain, event or error-catalog change in this wave)
- `db/migrations/**` (head stays `0017_execution_queue`)
- root dependency and lock files (`pyproject.toml`, `uv.lock`, `requirements/**`, `web/package.json`, `web/package-lock.json`)
- `Makefile`, `tests/support/**`, every `conftest.py`, global styles (`web/src/app/globals.css`)
- `VERSION`, `release-notes/**`, `docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`
- any path owned by another `W53C-*` lane (see `docs/program/dispatch/W53-CLOSE-PLAN.md` §4)

## Non-goals
- BFF code (EDGE); release notices and execution screens (WEB-OPS); a jsdom/Testing Library dependency

## Deliverables
- C-07 (`R-80`): the screen registry distinguishes "any complete account" from "any role"; product screens (projects, dashboard, documents, runs, review, comparison, blocks, norms, queue, logs, workers, …) require at least one role; a role-less account sees only home (with the existing «Роли не назначены.» message and no product tiles), account, password and release history. Update registry tests.
- C-20: after `useEditProfile` succeeds call `router.refresh()` before/with `router.push(next)`; likewise after a manage-user mutation whose target is the signed-in account.
- C-21: the sign-in page links «Подать заявку на доступ» to `/register` (address from the registry/`routes`).
- C-22: `shared/ui/submit-lock.tsx`, a tiny client island that disables the form's submit button on `submit` without reading any field; used by sign-in, register and change-password forms.
- C-23: one `failureMessage(error)` mapper in `shared/api/failure-message.ts` returning Russian text by `error_code`; `account-page`, `user-card` and the entity mappers use it; no screen renders `error.message`; a non-`ApiError` is reported as an unexpected error, not as a transport failure.
- C-24: «Архивировать» and «Отклонить» require a confirmation step; `/admin/users/[user_uid]` calls `notFound()` for a malformed id like the project routes; add `app/global-error.tsx` rendering a Russian message.
- C-25: replace W51 literal addresses with registry/`routes` constants and `BFF_MOUNT`; remove the unreachable signed-in branch of the sign-in page, the guest branch of the change-password page and the stale "no row in W50" comments.

## Required tests
- command: `git diff --check`; `.venv/bin/ruff check` on changed Python; `.venv/bin/python -m compileall -q` on changed modules; for web, `npm --prefix web run lint`, `npm --prefix web run typecheck` and `npx --prefix web vitest run <touched test files>`; for backend, the touched test modules (DB-backed ones on the private ports below, one run at a time)
- expected: all exit 0; every new behaviour has a test that fails without the change (state how you showed it)
- private ports: none — container-free

## Integration contract
The integrator merges `agent/w53c-web-id` as is after reading the diff and the report. Everything outside the allowed paths is unchanged; no contract, migration, dependency or published ref moves.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; kill only PIDs you started. Never touch the working stand, another lane's ports or containers, the main checkout or any published ref.
- Remove your private containers and volumes before handing back; prove containment with `git status --porcelain -uall` and `git diff --name-only <base>..HEAD`.
