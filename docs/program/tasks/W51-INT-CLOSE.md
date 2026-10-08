# Task W51-INT-CLOSE — accelerated development closure with validation debt

task_id: W51-INT-CLOSE

## Outcome

W51 implementation is explicitly closed on `origin/dev` so the integrator can
resume the code queue. The record names the exact code candidate and checks,
and preserves W51 QA/live/manual and complete-gate obligations as D-137/D-138.
No release or deployed-state claim is made.

## Depends on

- `W51-E2E-01` — Stage C code accepted on `origin/dev` at `4400e81`.
- `W52-INT-HOTFIX-BACKPORT-01` — W51 frontend correction accepted on `origin/dev`
  at `2c2e7d8a75d360bb9dc6cc0fc9916c55892886c5`.
- `W52-INT-VERSION-READ-PREP-01` — latest completed development preparation
  at `5a25e07956459f510addf1f142ec8a4c26591111`.

## Frozen inputs

- Exact clean development base `5a25e07956459f510addf1f142ec8a4c26591111`.
  W51 Stage C is its ancestor; later W52 preparations are in the same
  development lineage and are not claimed as W51 deliverables.
- Domain `1.0.0-draft.1` candidate revision 9 / 29 opaque identities; API
  27 paths / 34 operations / 77 schemas; error catalog 23; migration head
  `0015_accounts_roles_registration`.
- Owner directions 2026-10-08: basic tests and lint during implementation;
  temporary stand, QA/live/manual and complete wave gate deferred as
  D-137/D-138; direct instruction now to accelerate W51 closure.
- `docs/program/dispatch/W51-PLAN.md` §4–§5 and W51 lane handbacks; D-137/D-138
  are explicit exceptions to their validation sequence, not passed checks.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the clean published development base contains completed Stage C
  but the plan still labels W51 open, and neither contract nor migration
  changed since W50 closure.

### P-01 — exact base and open status

- captured_at: 2026-10-08
- command: `git rev-parse HEAD && git status --porcelain --untracked-files=no && git merge-base --is-ancestor 4400e81 HEAD && rg -n 'QA, correction and release checks remain open; W51 is not closed' docs/program/dispatch/W51-PLAN.md && git diff --name-only 75dd708 HEAD -- contracts db/migrations`
- captured_output:
  ```text
  5a25e07956459f510addf1f142ec8a4c26591111
  9:QA, correction and release checks remain open; W51 is not closed. Deferred QA/live
  ```
- interpretation: the W51 status is stale for an accelerated implementation
  close; blank output from tracked status and protected-path diff means the
  committed base is clean and frozen contract/migration files are unchanged.

## Historical evidence

- correction_mode: addendum
- source_record: `docs/program/W51-ROUTES-01.md`, `W51-AUTH-01.md`,
  `W51-ADMIN-USERS.md`, `W51-ADMIN-REQUESTS.md`, `W51-E2E-01.md` and
  `W52-INT-VALIDATE-01.md`
- addendum_path: `docs/program/W51-INT-CLOSE.md`

Historical lane and failed-gate reports remain unchanged.

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W51-INT-CLOSE.md`
- `docs/program/W51-INT-CLOSE.md`
- `docs/program/CURRENT_STATE.md` — W51 current status only
- `docs/program/DEBT_REGISTER.md` — D-137/D-138 status only
- `docs/program/dispatch/W51-PLAN.md` — status, exit and integration order only
- local integrator card/handoff under `.local/` after publication
- `integration/w51` commit and fast-forward publication to `origin/dev`

## Forbidden hotspots

Everything else, especially contracts, migrations, root dependency/lock files,
composition root, global styles, product code/tests, planning worktrees,
`origin/main`, tags and deployment.

## Non-goals

No claim that W51 passed QA, independent judges, built-stand journey,
manual A13–A20 or `make gate`; no correction of findings inside this close;
no release/tag, temporary stand or `origin/main` publication. W52 release
entry conditions are not silently waived by this W51 development close.

## Deliverables

- Development-only W51 closure report with code lineage, exact test results,
  frozen contract and validation-debt matrix.
- Current state and W51 plan status distinguishing implementation closure
  from release validation; D-137/D-138 remain open with exact flip conditions.
- Exact clean close commit published/read back on `origin/dev` as a
  fast-forward, followed by an integrator handoff.

## Required tests

- On the clean pre-close code candidate: frontend lint, typecheck and Vitest;
  static PC-01 conformance, programme governance/prose and frozen-contract
  tests; `bash -n` and `shellcheck` if installed. Record any sandbox-only
  child-process refusal and the authorized repeat result.
- On the docs-only clean close commit: repeat basic/frontend and static
  checks, `git diff --check`, exact changed-path proof.
- Defer complete `make gate`, QA, judges, built stand, identity journey and
  human A13–A20 to D-137/D-138; no `GATE OK` claim.

## Integration contract

This closes **implementation W51 on the development line** only. Validation
debt stays release-blocking: any future W51 release or `origin/main` candidate
needs the separate validation/correction work, a literal `GATE OK` on its
exact SHA and direct owner publication authority. The integrator alone
publishes this exact docs-only close commit to `origin/dev` after remote-ref
review and ancestor proof. W52 freeze still resolves its own entry conditions.

## Failure/idempotency/security cases

- A red basic check or changed remote `dev` stops publication pending repair.
- No credential, stand or external service is touched by the docs closure.
- Repeating the task must not close D-137/D-138 without the named evidence.

## Rollback / feature flag

Revert the documentation close commit if the recorded status is wrong.
No product behavior or feature flag changes.

## Handoff

- Changed paths, check results, contracts, open risks, integration instruction
  and forbidden-hotspot proof are in `docs/program/W51-INT-CLOSE.md`.
