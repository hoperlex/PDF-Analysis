# W52-INT-HOTFIX-BACKPORT-01 — W51 web correction returned to dev

Base: clean `origin/dev` `60968f5cfbc4cb31660c077504290fba99e39398`.
Source: accepted `origin/main` hotfix `1e9bb1308b7b97cd75eef28e206b23c569871b68`
over its parent `0df3649526ade130a8dcb715ec8190f3cce0e051`.

The five non-conflicting web files have the hotfix's exact bytes. The
`rendered-language.guard.test.ts` file was reconciled in three-way form: dev's
D-128 F-1 `ScreenCase.seedClient` and shared `renderScreen` path remain, while the
hotfix's account/user/registration fixtures, extra identity states and six
documented one-pass exceptions are present. The registration queue cases still
seed their own client through `ScreenCase`, using the same registration query key
as the added hotfix fixtures.

## Changed files

- `web/src/_pages/account/ui/account-page.tsx`
- `web/src/_pages/register/ui/register-page.tsx`
- `web/src/entities/account/model/account.ts`
- `web/src/features/manage-user/model/use-manage-user.ts`
- `web/tests/guards/rendered-language.guard.test.ts`
- `web/tests/unit/session/login-route.test.ts`
- `docs/program/tasks/W52-INT-HOTFIX-BACKPORT-01.md`, this report,
  `docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`

## Checks

- `npm --prefix web run typecheck`: passed; the two TS2375 errors reported by
  `W52-INT-VALIDATE-01` no longer reproduce.
- Focused Vitest across query-key shape, rendered language, login route,
  user management, account and registration: **72 passed in seven files**. This
  includes the 17-branch language-coverage assertion and the guard against an
  explicit cache type argument.
- `npm --prefix web run lint`: passed.
- `git diff --exit-code 1e9bb13 --` the five non-conflicting web paths: passed;
  their bytes equal the accepted main hotfix.
- Governance/prose tests: **60 passed**; `git diff --check`: passed.
- Full gate, independent QA, temporary product stand, live/browser journey and
  human manual acceptance: not run here; D-137–D-140 remain open.

## Contracts, risks and integration

No API/domain/event contract, migration, dependency/lock, composition root,
global style or deployment input changed. The account and registration props
normalize an absent optional value to `null`; the own-account cache read uses
the key's tagged type. No new redirect or refusal is introduced. The remaining
risk is unmeasured behavior outside these focused tests and the deferred QA/live
pack. Publish only a fast-forward `origin/dev` commit after exact ref review;
`origin/main` is already at the accepted hotfix and receives no push here.

Every changed tracked path is in `W52-INT-HOTFIX-BACKPORT-01`'s allowed list;
forbidden hotspots are untouched. Revert this development commit to roll back
the backport without changing the deployed main hotfix.
