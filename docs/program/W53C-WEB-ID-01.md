# W53C-WEB-ID-01 — hand-back report

Lane: WEB-ID. Branch `agent/w53c-web-id`, base `04de50c` (`W53-CLOSE-PLAN` on
`integration/w53-close`). Task file: `docs/program/tasks/W53C-WEB-ID-01.md`.

Every finding (C-07 web half, C-20 to C-25) reproduced on the base at the cited locations.
None was skipped as stale.

## 1. Changed files

Product code (`web/src`):

| Finding | Files |
|---|---|
| C-07 (`R-80`) | `shared/config/screen-registry.ts` (new `'any-role'` value, `screenRolesAdmit`, `REGISTER_SCREEN`; all product rows `any-role`), `_pages/home/ui/home-page.tsx` (tiles follow the registry) |
| C-20 | `features/edit-profile/{ui/edit-profile-form.tsx, model/after-save.ts (new), index.ts}`, `features/manage-user/{ui/manage-user-controls.tsx, model/use-manage-user.ts, index.ts}`, `widgets/user-card/{ui/user-card.tsx, index.ts}`, `_pages/admin-user/ui/admin-user-page.tsx`, `app/admin/users/[user_uid]/page.tsx` |
| C-21 | `_pages/sign-in/ui/sign-in-page.tsx` |
| C-22 | `shared/ui/submit-lock.tsx` (new), `features/sign-in/ui/sign-in-form.tsx`, `features/register/ui/register-form.tsx`, `features/change-password/ui/change-password-form.tsx` |
| C-23 | `shared/api/failure-message.ts` (new), `entities/user/model/failure.ts`, `entities/registration-request/model/presentation.ts`, `entities/account/{model/account.ts, index.ts}` (`unreadableAccountDetail`), `_pages/account/ui/account-page.tsx`, `widgets/user-card/ui/user-card.tsx`, `features/edit-profile/ui/edit-profile-form.tsx`, `widgets/home-tiles/model/read-failure.ts` |
| C-24 | `features/manage-user/ui/manage-user-controls.tsx` (archive confirmation), `features/decide-registration/ui/registration-decision-controls.tsx` (reject confirmation), `entities/user/{model/identity.ts (new), index.ts}` (`looksLikeUserUid`), `app/admin/users/[user_uid]/page.tsx` (`notFound()`), `app/global-error.tsx` (new) |
| C-25 | `shared/lib/routes.ts` (`routes.users()`), `features/register/{model/exchange.ts, index.ts}` (`REGISTRATION_SUBMIT_PATH` from `BFF_MOUNT`), `_pages/account/ui/account-page.tsx`, `_pages/register-submitted/ui/register-submitted-page.tsx`, `_pages/forbidden/ui/forbidden-page.tsx`, `features/manage-user/ui/manage-user-controls.tsx`, `widgets/user-card/ui/user-card.tsx`; dead code removed: `_pages/sign-in/ui/sign-in-page.tsx` signed-in branch, `features/sign-in/ui/sign-out-form.tsx` (deleted) and its export in `features/sign-in/index.ts`, `_pages/change-password/ui/change-password-page.tsx` guest branch, stale "no row in W50" comments in `widgets/home-tiles/{model/registrations-screen.ts, ui/pending-registrations-tile.tsx}` |

New tests (`web/tests/unit`):

- `widgets/identity-actions.test.ts` — C-20, C-24 (pressing the controls; see §2).
- `session/submit-lock.test.ts` — C-22.
- `api/failure-message.test.ts` — C-23.
- `screens/global-error.test.ts` — C-24 `global-error.tsx`.

Existing tests and guards changed, each only where this change required it:

- `tests/guards/screen-registry.guard.test.ts` — the shape rule reads a role *list* with
  `Array.isArray` (a string `'any-role'` must not be iterated as roles); new finding "asks for a
  role on a public row" with its can-fail case; the R-60 admin-set filter; the four R-66 stubs
  are now `any-role`.
- `tests/guards/screen-guard.guard.test.ts` — decision 4: an empty role set opens `/`,
  `/account`, `/account/password`; new case: it is sent to `/403` from `/projects`, one role
  opens it.
- `tests/unit/shell/screen-decision.test.ts` — `any-role` decision cases, unknown role counts
  as none, live-registry `any` set pinned to the seven non-product rows.
- `tests/unit/shell/navigation.test.ts`, `tests/unit/qa_w50/r66-navigation.test.ts`,
  `tests/unit/qa_w50/role-gated.test.ts` — a role-less session's menu is Главная alone; stubs and
  `/optimisation` are `any-role`; `/403` for an `any-role` screen names both roles.
- `tests/unit/screens/home.test.ts` — a role-less home page mounts no tile and asks nothing;
  role-less state added to the language sweep.
- `tests/unit/screens/routes.test.ts` — admin-user route props carry `signedInLogin`;
  `routes.users` in the D-94 builder census; new malformed-`user_uid` 404 case.
- `tests/unit/session/change-password.test.ts` — the guest-shape case replaced by the one-shape case.
- `tests/unit/session/sign-in-screen.test.ts` — `sign-out-form.tsx` dropped from the slice list;
  the signed-in-shape case replaced by one-shape, `/register` link and submit-lock cases.

Report: `docs/program/W53C-WEB-ID-01.md` (this file).

## 2. Checks run and results

All in `/root/projects/PDF-Analysis/.local/worktrees/w53c-web-id`, container-free, no Next
server, no browser, no docker.

| Command | Result |
|---|---|
| `git diff --check` (plus `git diff --cached --check` before commit) | clean |
| `npm --prefix web run lint` | exit 0, no findings |
| `npm --prefix web run typecheck` | exit 0 |
| `cd web && npx vitest run tests/guards tests/unit/qa_w50 tests/unit/qa_w51 tests/unit/shell tests/unit/screens tests/unit/session tests/unit/widgets tests/unit/entities tests/unit/api` | 65 files, 1082 tests passed |
| `cd web && npx vitest run` (whole suite) | 120 files, 1789 tests passed, 34 s |
| the same, again, after the last change (registry exports moved from `shared/config/index.ts` to deep imports; no behaviour change) | 120 files, 1789 tests passed, 33 s |

How each new test fails without the fix: the base version of the named files was restored
(`git show 04de50c:<path> > <path>`), the named tests run, and `web/src` restored from a copy
(`diff -r` identical afterwards).

| Mutation | Red cases |
|---|---|
| base `manage-user-controls.tsx` + `registration-decision-controls.tsx` | 5 in `identity-actions.test.ts`: archive trigger sends `POST /users/{uid}/archive`; reject submit sends `POST /registrations/{id}/reject`; no confirmation group; `isSelf` restore makes no `refresh` |
| base `edit-profile-form.tsx` | 1 in `identity-actions.test.ts` (form does not hand the save to `followProfileSave`) |
| base sign-in, register, change-password forms | 3 in `submit-lock.test.ts` (no `data-submit-lock` in any form) |
| `lockOnSubmit` without the second-submit cancel | 1 in `submit-lock.test.ts` |
| base account page, user card, user/registration mappers | 4 in `failure-message.test.ts` (`transport` for a thrown `Error`, raw message rendered) |
| base registry + base home page | 6 across `screen-decision.test.ts`, `home.test.ts`, `screen-guard.guard.test.ts` |
| base home page only | 1 in `home.test.ts` (role-less page mounts tiles) |
| base admin-user route | 2 in `routes.test.ts` (no 404; no `signedInLogin`) |
| base sign-in page (+ sign-out form) | 2 in `sign-in-screen.test.ts` (signed-in shape; no `/register` link) |
| base change-password page | 1 in `change-password.test.ts` (guest shape) |
| no `global-error.tsx` | `global-error.test.ts` cannot import it |

The controls are driven without a DOM: a probe component calls the control as a function inside
a server render and keeps its element tree; the test calls that tree's own `onClick`/`onSubmit`
and reads the result off a recording `fetch` (generated client) and a recording router. Confirm
shapes are reached by seeding initial `useState` values through a `react` mock that wraps the
real hook.

## 3. New or changed contracts

No API, domain, event, error-catalog or migration contract changed. Web-internal surfaces:

- `ScreenRoles` gains `'any-role'`. `requiredRolesFor` answers every contract role for an
  `any-role` screen. New exports `screenRolesAdmit` and `REGISTER_SCREEN` live in
  `@/shared/config/screen-registry`.
- New modules `@/shared/api/failure-message` (`failureMessage`, `FailureWording`,
  `UNEXPECTED_FAILURE_DETAIL`, `TRANSPORT_FAILURE_DETAIL`) and `@/shared/ui/submit-lock`
  (`SubmitLock`, `lockOnSubmit`).
- Consumers import all of these by deep path. `shared/config/index.ts`, `shared/api/index.ts`
  and `shared/ui/index.ts` are outside this lane's allowed paths and were not edited.
- Slice exports added: `routes.users`, `looksLikeUserUid`, `unreadableAccountDetail`,
  `followProfileSave`, `followUserCommand`, `REGISTRATION_SUBMIT_PATH`,
  `ManageUserControlsProps`, `UserCardProps`. Removed: `SignOutForm`, `SignOutFormProps`.
- Props: `ManageUserControls.isSelf?`, `UserCard.signedInLogin?`, `AdminUserPage.signedInLogin?`.
  `SignInPage.login` and `ChangePasswordPage.login` stay accepted and unused because their
  route files are outside this lane.

## 4. Risks and known limitations

- C-20 for manage-user: `router.refresh()` re-renders the frame from the session subject. The
  subject changes after a self-targeted `PATCH /users/{uid}` only with EDGE's C-19. Without it
  the refresh is harmless but shows the old subject.
- The jsdom-free interaction tests mock `react`'s `useState` for the confirmation shapes. This
  stands in for a DOM and is not a substitute for the browser journey; `make gate` was not run
  (`R-84`).
- The confirmation steps are client-side only. The API still decides, so a double-confirmed
  archive is refused as `state_transition_not_allowed`, as before.
- `global-error.tsx` renders without the root layout's stylesheet (Next replaces the layout),
  so the page is plain semantic markup.
- A role-less account's `/403` for a product screen names both roles (`«Эксперт»,
  «Администратор»`). This is accurate under `R-80`.

## 5. Integrator instructions

1. Merge `agent/w53c-web-id` as is. Expected overlaps:
   - **WEB-OPS:** its queue/release work may assert `/queue` registry rows or a role-less menu.
     After this lane, `/queue` is `any-role` and a role-less menu is Главная alone.
   - **EDGE C-19:** `web/tests/unit/entities/account.test.ts` holds `entities/account`'s
     `initialsOf` and `app/bff/session/subject.ts`'s to the same answers. If EDGE changes the
     `ß` rule in `subject.ts`, the `entities/account/model/account.ts` copy must change too.
     This lane did not touch it.
2. Optional follow-ups for whoever owns the hotspots:
   - add re-exports to the three `index.ts` files: `screenRolesAdmit` and `REGISTER_SCREEN` to
     `shared/config/index.ts`, `failure-message` to `shared/api/index.ts`, `submit-lock` to
     `shared/ui/index.ts`;
   - drop the unused `login` prop from `app/login/page.tsx` and `app/account/password/page.tsx`
     and from the two page props.
3. Post-merge checks per §5 of the plan: lint, typecheck, full Vitest. The Python journey
   conformance (`tests/e2e/test_pc01_journey_conformance.py`) reads the registry's address set.
   That set did not change, but the journey's seeded accounts must hold a role to walk product
   screens.

## 6. Containment

- `git diff --name-only 04de50c..HEAD` lists only paths in the task's allowed set: the slices
  above, `shared/config/screen-registry.ts`, `shared/lib/routes.ts`, the three new shared files,
  `app/global-error.tsx`, `app/admin/users/[user_uid]/page.tsx`, `web/tests/**` and this
  report. The commit section below gives the exact list.
- Untouched: `web/src/app/bff/**`, `_app/**` (including `release-notices*`, `account-menu.tsx`,
  `navigation.ts`, `frame-navigation.tsx`), execution/release slices, `globals.css`, lock files,
  `contracts/**`, migrations and Python.
- `git status --porcelain -uall` is clean after the commit. No containers, ports or processes
  were started besides Vitest/ESLint/tsc, which exited.

### Committed paths

`git diff --name-only 04de50c..HEAD` (53 paths). Each was checked against the task's
`allowed_paths` patterns by script, and none falls outside them:

```
docs/program/W53C-WEB-ID-01.md
web/src/app/admin/users/[user_uid]/page.tsx
web/src/app/global-error.tsx
web/src/entities/account/index.ts
web/src/entities/account/model/account.ts
web/src/entities/registration-request/model/presentation.ts
web/src/entities/user/index.ts
web/src/entities/user/model/failure.ts
web/src/entities/user/model/identity.ts
web/src/features/change-password/ui/change-password-form.tsx
web/src/features/decide-registration/ui/registration-decision-controls.tsx
web/src/features/edit-profile/index.ts
web/src/features/edit-profile/model/after-save.ts
web/src/features/edit-profile/ui/edit-profile-form.tsx
web/src/features/manage-user/index.ts
web/src/features/manage-user/model/use-manage-user.ts
web/src/features/manage-user/ui/manage-user-controls.tsx
web/src/features/register/index.ts
web/src/features/register/model/exchange.ts
web/src/features/register/ui/register-form.tsx
web/src/features/sign-in/index.ts
web/src/features/sign-in/ui/sign-in-form.tsx
web/src/features/sign-in/ui/sign-out-form.tsx
web/src/_pages/account/ui/account-page.tsx
web/src/_pages/admin-user/ui/admin-user-page.tsx
web/src/_pages/change-password/ui/change-password-page.tsx
web/src/_pages/forbidden/ui/forbidden-page.tsx
web/src/_pages/home/ui/home-page.tsx
web/src/_pages/register-submitted/ui/register-submitted-page.tsx
web/src/_pages/sign-in/ui/sign-in-page.tsx
web/src/shared/api/failure-message.ts
web/src/shared/config/screen-registry.ts
web/src/shared/lib/routes.ts
web/src/shared/ui/submit-lock.tsx
web/src/widgets/home-tiles/model/read-failure.ts
web/src/widgets/home-tiles/model/registrations-screen.ts
web/src/widgets/home-tiles/ui/pending-registrations-tile.tsx
web/src/widgets/user-card/index.ts
web/src/widgets/user-card/ui/user-card.tsx
web/tests/guards/screen-guard.guard.test.ts
web/tests/guards/screen-registry.guard.test.ts
web/tests/unit/api/failure-message.test.ts
web/tests/unit/qa_w50/r66-navigation.test.ts
web/tests/unit/qa_w50/role-gated.test.ts
web/tests/unit/screens/global-error.test.ts
web/tests/unit/screens/home.test.ts
web/tests/unit/screens/routes.test.ts
web/tests/unit/session/change-password.test.ts
web/tests/unit/session/sign-in-screen.test.ts
web/tests/unit/session/submit-lock.test.ts
web/tests/unit/shell/navigation.test.ts
web/tests/unit/shell/screen-decision.test.ts
web/tests/unit/widgets/identity-actions.test.ts
```
