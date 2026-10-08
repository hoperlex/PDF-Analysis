# Task W52-INT-HOTFIX-BACKPORT-01 — bring the deployed W51 web correction to dev

task_id: W52-INT-HOTFIX-BACKPORT-01

## Outcome

The development line contains the already deployed W51 web hotfix without losing its
later D-128 language-guard repair. The two TS2375 errors and the seven frontend test
failures measured by `W52-INT-VALIDATE-01` no longer reproduce in focused checks.

## Depends on

- `W51-INT-HOTFIX-01` — completed on `origin/main` at
  `1e9bb1308b7b97cd75eef28e206b23c569871b68`.
- `W52-INT-VALIDATE-01` — completed on `origin/dev` at
  `60968f5cfbc4cb31660c077504290fba99e39398`.

## Frozen inputs

- Exact development base: `60968f5cfbc4cb31660c077504290fba99e39398`.
- Hotfix source: the six tracked web-file changes of
  `0df3649526ade130a8dcb715ec8190f3cce0e051..1e9bb1308b7b97cd75eef28e206b23c569871b68`.
- Domain candidate revision 9 / 29 opaque identities; API 27 paths / 34 operations /
  77 schemas; error catalog 23; migration head `0015_accounts_roles_registration`.
- D-128 F-1's later development-line change to the rendered-language guard must survive.
- Owner's code-first direction: basic/focused checks and lint; QA, live and full gate stay
  D-137–D-140.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the already accepted main hotfix fixes the validation failures, but the
  development line has a separate later change to the same guard.

### P-01 — divergence and exact paths

- captured_at: 2026-10-08
- command: `git diff --name-only 0df3649526ade130a8dcb715ec8190f3cce0e051 60968f5cfbc4cb31660c077504290fba99e39398 -- web/src/_pages/account/ui/account-page.tsx web/src/_pages/register/ui/register-page.tsx web/src/entities/account/model/account.ts web/src/features/manage-user/model/use-manage-user.ts web/tests/guards/rendered-language.guard.test.ts web/tests/unit/session/login-route.test.ts`
- captured_output:
  ```text
  web/tests/guards/rendered-language.guard.test.ts
  ```
- interpretation: five hotfix web files have the same base bytes on dev and the
  failed-main parent; the language guard alone needs a three-way reconciliation.

## Historical evidence

- correction_mode: addendum
- source_record: `docs/program/tasks/W51-INT-HOTFIX-01.md` on `origin/main` and
  `docs/program/W52-INT-VALIDATE-01.md` on `origin/dev`
- addendum_path: `docs/program/W52-INT-HOTFIX-BACKPORT-01.md`

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `web/src/_pages/account/ui/account-page.tsx`
- `web/src/_pages/register/ui/register-page.tsx`
- `web/src/entities/account/model/account.ts`
- `web/src/features/manage-user/model/use-manage-user.ts`
- `web/tests/guards/rendered-language.guard.test.ts`
- `web/tests/unit/session/login-route.test.ts`
- `docs/program/tasks/W52-INT-HOTFIX-BACKPORT-01.md`
- `docs/program/W52-INT-HOTFIX-BACKPORT-01.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/DEBT_REGISTER.md`

## Forbidden hotspots

Every other path, including contracts, migration head, root dependencies and locks,
composition root, global styles, deployment inputs, refs and tags. The historical
`W51-INT-HOTFIX-01` task on `main` is not rewritten.

## Non-goals

No new identity flow or contract, no temporary stand, QA judgement, full gate, release,
tag or `origin/main` update. This is a backport of an existing accepted correction.

## Deliverables

- The five unmodified hotfix web files and a reconciled language guard preserving the
  D-128 F-1 shared-renderer change.
- Focused frontend checks and a handoff with exact changed-path proof.
- Development-line debt/state notes that do not claim `GATE OK` or live acceptance.

## Required tests

- Focused Vitest files: `query-key-shape.guard.test.ts`,
  `rendered-language.guard.test.ts`, `login-route.test.ts`, and relevant account,
  registration and user-management tests.
- `npm --prefix web run typecheck`; `npm --prefix web run lint`;
  governance/prose tests and `git diff --check`.
- Full gate and live/browser/manual acceptance remain deferred; no green claim for them.

## Integration contract

The validated `next` and typed refusal preserve their values, using `null` when absent.
The own-account cache read no longer overrides its tagged key type. The shared
render-language harness retains D-128 F-1's screen cases while covering the W51 branches
as the hotfix did. Integrator publishes only a fast-forward `origin/dev` commit after
checks and a remote-ref re-read.

## Failure/idempotency/security cases

- Reject a merge that replaces the later shared-renderer repair with the older main
  guard. Mutation/branch coverage remains measured by the focused guard test.
- No credential, session, deploy or private data is changed.

## Rollback / feature flag

Revert the development backport commit if needed. The original main hotfix remains
untouched. No feature flag applies to these corrections.

## Handoff

- Changed files, checks/results, contracts, risks, integration instructions and
  forbidden-hotspot proof are in `docs/program/W52-INT-HOTFIX-BACKPORT-01.md`.
