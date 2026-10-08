# W51-ADMIN-USERS — implementation handoff

Base: docs-only `origin/dev` SHA `6e5d59232d9573927e5f59c0079fa70a957ef2bd`.
Branch: `agent/w51-admin-users` in `.local/worktrees/W51-ADMIN-USERS`.

## Implemented

- `/admin/users` reads `listUsers`, offers the archived toggle, a role filter explicitly scoped to the current page, opaque-cursor pagination and links built from `user_uid`. The table has fixed layout and wraps long names.
- `/admin/users/[user_uid]` reads `getUser`, shows login, names, role set, state and generated avatar. It offers separate name and role edits, archive, restore and temporary-password reset. Purge is offered only for an archived account after an irreversible confirmation naming its login.
- All writes use generated operations. A password mismatch produces no mutation. Typed Russian states cover self-action permission refusal, last administrator, referenced account, login conflict, state transition and other catalog errors. Successful writes refresh `users.all()`, the detail view and the signed-in account key when affected.
- The two administrator journey rows now declare `listUsers`/`getUser`, and the list captures a real `user_uid` from its rendered link instead of using a sample identity.

## Changed files

`web/src/_pages/{admin-users,admin-user}/ui/**`; `web/src/entities/user/**`; `web/src/widgets/{user-list,user-card}/**`; `web/src/features/manage-user/**`; `web/tests/unit/widgets/user-management.test.ts`; the ADMIN-USERS hook entry in `web/tests/guards/dashboard-invalidation.guard.test.ts`; the ADMIN-USERS states in `web/tests/guards/rendered-language.guard.test.ts` and `web/tests/unit/styles/screens.ts`; the two admin-user entries in `tests/e2e/pc01/journey/manifest.json`; this report.

## Basic checks and validation debt

- `npm --prefix web test -- --run tests/unit/widgets/user-management.test.ts tests/guards/dashboard-invalidation.guard.test.ts` — 2 files, 24 tests passed.
- `npm --prefix web run lint -- --quiet` — passed.
- `git diff --check` — passed.
- Additional `rendered-language.guard.test.ts` run: 23 passed, 1 failed. Its branch-coverage assertion lists 12 unseeded branch headings: six introduced in AUTH and six in ADMIN-USERS. These are language-matrix coverage debt, not evidence of English text on a rendered screen; the guard's actual `finds none at all` language assertion passed. The owner assigned gate and correction work to later stages. This result is not described as green.
- Full Vitest/typecheck, static PC-01 conformance, build, live/manual journey, temporary stand, mutation probes, R-70 acceptance and end-of-wave/full gate were not run under the 2026-10-08 owner direction.

## Contracts, risks and integration

No contract, migration, shared API/config or dependency changed. The API has no server-side role filter; the UI labels its filter as applying to the current page. The 780 px layout has a fixed table and wrap rules but no browser measurement under the temporary stand deferral. Role-change and reset effects rely on the existing API revocation semantics. The current language matrix needs later branch-state coverage before it can be green.

All changed files are in this task's allowed paths. Forbidden hotspots, including `contracts/**`, migration head, backend, infra, lockfiles, composition root, global styles, shared API/config, BFF session/forwarder, AUTH screens, registration queue and `tests/e2e/pc01/journey/journey.mjs`, are untouched.

Integrator: review the exact branch and this red guard debt, then merge only under the owner's basic-tests-and-lint implementation direction. Publish only `origin/dev` if accepted. `origin/main` requires separate direct authority and its full deployment policy.
