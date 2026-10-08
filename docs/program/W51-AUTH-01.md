# W51-AUTH-01 — implementation handoff

Base: `origin/dev` dispatch SHA `5830c18317064de13910a2a02bfe97e6fb6c44ee`.
Branch: `agent/w51-auth-01` in `.local/worktrees/W51-AUTH-01`.

## Implemented

- Registration and submitted screens replace placeholders. The six closed BFF refusals have Russian states; an unknown query value is an explicit fault. The form is plain HTML POST to `/bff/v1/registration`, with no password in client JavaScript.
- Login labels e-mail and keeps the legacy login input accepted by the existing BFF. Unknown refusal values render a fault. A validated `next` survives sign-in refusal and the forced password route.
- The account screen reads `getMe`, shows names, generated avatar and read-only roles, and edits the profile with `updateMyProfile`. An incomplete profile sends names and e-mail together. A complete profile disables e-mail editing. Successful edits update and invalidate `queryKeys.account.me()`.
- Password refusal and success preserve a validated `next`. After a successful forced change, an incomplete profile receives the destination on `/account`; completion navigates there. External or unregistered destinations are discarded. No-next password behavior remains the existing outcome screen.
- The five AUTH journey entries now describe the implemented screens; `/account` declares its `getMe` read.

## Changed files

`tests/e2e/pc01/journey/manifest.json`; `web/src/app/{login,register,account,account/password}/page.tsx`; `web/src/app/bff/v1/[...path]/route.ts`; `web/src/_pages/{sign-in,register,register-submitted,account,change-password}/**`; `web/src/features/{sign-in,change-password,register,edit-profile}/**`; `web/tests/unit/screens/{account-auth,register-auth}.test.ts`; `web/tests/unit/screens/route-screens.ts`; `web/tests/unit/session/{bff-session,change-password}.test.ts`; `web/tests/guards/dashboard-invalidation.guard.test.ts`; this report.

## Basic checks

- `npm --prefix web test -- --run tests/unit/screens/register-auth.test.ts tests/unit/screens/account-auth.test.ts tests/unit/session/bff-session.test.ts tests/unit/session/registration-door.test.ts tests/unit/session/change-password.test.ts tests/unit/session/sign-in-screen.test.ts tests/guards/dashboard-invalidation.guard.test.ts` — 7 files, 129 tests passed.
- `npm --prefix web run lint -- --quiet` — passed.
- `git diff --check` — passed.

The temporary stand, full frontend suite/typecheck, static PC-01 conformance, production build, live journey, R-70 acceptance, mutation probes and end-of-wave/full gate were not run. The owner deferred these checks to a separately designed wave on 2026-10-08. The stand started before that instruction was stopped and cleaned up; it supplied no acceptance result.

## Contracts, limits and integration

No contract, migration or root dependency changed. The browser profile completion transition relies on the existing BFF's successful `PATCH /me` subject refresh before its response and on the account page's validated server prop for `next`. The focused tests do not exercise a live API or browser navigation; those are explicit validation debt.

All changed files are in this task's `allowed_paths`. Forbidden hotspots, including `contracts/**`, migration head, `web/src/shared/**`, `web/src/app/bff/session/**`, admin pages, composition root, lockfiles, global styles and `tests/e2e/pc01/journey/journey.mjs`, are untouched.

Integrator: verify this exact branch's allowed-path diff and basic checks, then merge it onto `integration/w51` as the accepted AUTH lane. Publish only `origin/dev` under the owner's basic-check direction. Do not publish `origin/main`; its policy requires separate explicit authorization and full gate.
