# W51-ADMIN-REQUESTS — implementation handoff

Base: docs-only `origin/dev` SHA `7d307e0fe4a7b28a73116ef686eaa45f68878e89`.
Branch: `agent/w51-admin-requests` in `.local/worktrees/W51-ADMIN-REQUESTS`.

## Implemented

- `/admin/registrations` reads `listRegistrations`, shows the global pending total, status filter, oldest-first pages from the API's opaque cursor, and explicit loading/empty/error states. Pending requests alone offer actions; decided requests show their state, decision time and the administrator-only rejection reason where present.
- Approval requires at least one selected role, and its idempotency key stays stable for an unchanged request/role intent. Rejection trims the reason and refuses empty or more than 256 characters before any API command. Both actions use the generated client and keep API refusals as typed Russian states.
- A successful decision invalidates `registrations.all()`, including the home pending-total query. Approval also invalidates `users.all()` because it creates an account. The queue is addressed by `request_id`; no applicant password reaches its response or UI.
- The journey manifest now declares the registration queue's `listRegistrations` read. Queue and picker states were added to the rendering census and language matrix.

## Changed files

`web/src/_pages/admin-registrations/ui/admin-registrations-page.tsx`; `web/src/entities/registration-request/**`; `web/src/features/decide-registration/**`; `web/src/widgets/registration-queue/**`; `web/tests/unit/widgets/registration-queue.test.ts`; the request hook entry in `web/tests/guards/dashboard-invalidation.guard.test.ts`; request states in `web/tests/guards/rendered-language.guard.test.ts` and `web/tests/unit/styles/screens.ts`; the admin-registration entry in `tests/e2e/pc01/journey/manifest.json`; this report.

## Basic checks and validation debt

- `npm --prefix web test -- --run tests/unit/widgets/registration-queue.test.ts tests/guards/dashboard-invalidation.guard.test.ts` — 2 files, 20 tests passed.
- `npm --prefix web run lint -- --quiet` — passed.
- `git diff --check` — passed.
- Additional `rendered-language.guard.test.ts` run: 23 passed, 1 failed. Its branch-coverage assertion lists 17 unseeded branch headings across AUTH, ADMIN-USERS and ADMIN-REQUESTS. Its actual `finds none at all` language assertion passed. The owner deferred correction/gate work to separate later stages; this guard is not reported green.
- Full Vitest/typecheck, static PC-01 conformance, production build, live/manual journey, temporary stand, mutation probes, R-70 acceptance and end-of-wave/full gate were not run under the 2026-10-08 owner direction.

## Contracts, risks and integration

No contract, migration, shared API/config or dependency changed. Status values are validated on generated list reads; an unknown status becomes a typed fault. The only client-side validation is for two known-invalid decision forms; the API still decides authorization and legal transitions. A live browser decision and idempotency replay remain unverified until the later validation wave.

All changed files are in this task's allowed paths. Forbidden hotspots, including `contracts/**`, migration head, backend, infra, lockfiles, composition root, global styles, shared API/config, BFF session/forwarder, AUTH/admin-user screens and `tests/e2e/pc01/journey/journey.mjs`, are untouched.

Integrator: review the exact branch and the red guard debt, then merge only under the owner's basic-tests-and-lint implementation direction. Publish only `origin/dev` if accepted. `origin/main` requires separate direct authority and its full deployment policy.
