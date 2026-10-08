# Task W52-INT-FRONTEND-BASELINE-01 — remeasure the development frontend

task_id: W52-INT-FRONTEND-BASELINE-01

## Outcome

Record the current complete frontend typecheck, lint and Vitest result on the
post-W51 development tree, so the older red diagnostic is not treated as the
current frontend result. This is diagnostic evidence, not a W52 freeze or a
release verdict.

## Depends on

- `W52-INT-FREEZE-PREFLIGHT-01`, completed on `origin/dev` at `defade8177ed808049425e15f741a8424997d0c3`.

## Frozen inputs

- Clean `integration/w51` and matching local `origin/dev` at
  `defade8177ed808049425e15f741a8424997d0c3`.
- W51 contract set: domain candidate revision 9 / 29 identities, API 27 paths /
  34 operations / 77 schemas, 23 error codes, migration head
  `0015_accounts_roles_registration`. This task does not reseal any contract.
- W52 entry amendment and open validation debts D-137–D-140.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the prior full-gate diagnostic describes frontend failures on an
  earlier development SHA, while the current clean committed base is later.

### P-01 — historical frontend diagnostic and current base

- captured_at: 2026-10-08
- command: `git rev-parse HEAD && rg -n 'Second .make gate. on the same SHA|The two TS2375 errors are' docs/program/W52-INT-VALIDATE-01.md`
- captured_output:
  ```text
  defade8177ed808049425e15f741a8424997d0c3
  14:| Second `make gate` on the same SHA | Foundation **35 passed**; canonical battery **3,245 passed, 6 skipped, 298 subtests passed**; frontend lint **passed**; TypeScript typecheck **failed** with two TS2375 errors. The gate stopped before Vitest and emitted no `GATE OK`. |
  18:The two TS2375 errors are at `web/src/_pages/account/ui/account-page.tsx:40`
  ```
- interpretation: the old diagnostic remains valid for its SHA; the present
  tree needs its own frontend measurement. This says nothing about the full
  gate or browser acceptance on the present tree.

## Historical evidence

- correction_mode: addendum
- source_record: `docs/program/W52-INT-VALIDATE-01.md` at `e2cfea92`
- addendum_path: `docs/program/W52-INT-FRONTEND-BASELINE-01.md`

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W52-INT-FRONTEND-BASELINE-01.md`
- `docs/program/W52-INT-FRONTEND-BASELINE-01.md`
- `docs/program/CURRENT_STATE.md` — current diagnostic status only
- `docs/program/DEBT_REGISTER.md` — D-140 diagnostic addendum only
- local integrator handoff and card under `.local/`
- local `integration/w51` commit; publication to `origin/dev` only after remote
  ref verification and a proven fast-forward

## Forbidden hotspots

Everything else, especially contracts, migrations, dependency/lock files,
composition root, global styles, product code/tests, W52 rulings and freeze,
`origin/main`, tags and deployment.

## Non-goals

No W52 ruling or freeze, no QA or independent review, no built stand, manual
acceptance, full `make gate`, release verdict or deployment.

## Deliverables

- A report naming the exact tree, commands, outcomes and sandbox limitation.
- Bounded current-state and D-140 addenda that preserve the remaining checks.

## Required checks

- `npm --prefix web run typecheck`
- `npm --prefix web run lint -- --quiet`
- `npm --prefix web test -- --run` with child-process execution permitted
- Focused programme governance/prose tests and `git diff --check` on the
  documentation candidate.

## Integration contract

This result narrows the known frontend failures for the measured SHA only.
The later validation stage still owns D-137–D-140, including independent QA,
built-stand/manual checks and a full exact-candidate gate with literal
`GATE OK`. The integrator may publish this docs-only record to `origin/dev`
after checking the remote ref and fast-forward ancestry.

## Failure/idempotency/security cases

- A child-process `EPERM` is classified as an execution-environment failure
  and remeasured with the same command where child processes are permitted.
- Repeating the diagnostic appends no product state and grants no release
  authority.

## Rollback / feature flag

Revert the docs-only commit if the measurement is wrong. No behavior or
feature flag changes.

## Handoff

The report names changed files, checks, contracts, remaining limits,
integration instruction and forbidden-hotspot proof.
