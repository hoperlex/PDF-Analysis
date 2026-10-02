# Task W48-GUARDS — close migration, dashboard-swap and invalidation false greens

## Outcome

D-87, D-114 and D-116 are executable failures: schema invariants are tested against a freshly
migrated database, swapping pairwise-distinct dashboard rows fails, and comments cannot satisfy
the invalidation guard.

## Depends on

- `W48-FREEZE-01` — completed by the docs-only dispatch commit containing this task file
- `MAIN-REF-POLICY-01` — completed at `6118e66`

## Frozen inputs

- frozen code base: `6118e66033380661bb747244e0f7a222fb9a87b4`
- dispatch base: exact `origin/dev` tip carrying `docs/program/W48-FREEZE-01.md`
- API: 17 paths / 20 operations / 61 schemas; error catalog 22
- migration head: `0013_norm_embeddings`
- debts: `DEBT_REGISTER.md` D-87, D-114 and D-116

## Allowed paths

- `tests/integration/db/**`
- `tests/integration/composition/test_dashboard_summary_over_a_fresh_deployment.py`
- `web/tests/guards/dashboard-invalidation.guard.test.ts`
- `web/tests/unit/widgets/dashboard.test.ts`
- `docs/program/W48-GUARDS.md`

## Forbidden hotspots

- `contracts/**`, generated clients, error catalog and `db/migrations/**`
- production backend/frontend code, root dependencies/locks, `Makefile`, composition and workflow
- global styles, programme state/register/history, refs, tags, host and secrets

## Non-goals

- no schema/migration repair; this task tests the accepted head
- no dashboard API/UI behaviour change
- no broad AST framework or new dependency for one guard
- no mutation of a shared/lane database as evidence for edited migration source

## Deliverables

- schema-invariant inventory with fresh-migration coverage or explicit non-schema classification
- pairwise-distinct backend/browser dashboard fixtures and row-swap mutations
- behavioural or comment-stripped invalidation proof with both-direction mutation
- completion report `docs/program/W48-GUARDS.md`

## Required tests

- focused `tests/integration/db/**` against a newly created disposable database
- `.venv/bin/python -m pytest
  tests/integration/composition/test_dashboard_summary_over_a_fresh_deployment.py -q`
- `npm --prefix web test -- dashboard-invalidation.guard.test.ts dashboard.test.ts`
- weaken each migration invariant in a full-tree scratch copy and freshly migrate before testing
- swap distinct section/verdict/run-state rows; comment out invalidation; add decoy comment text
- `git diff --check` and an allowed-path-only diff

## Integration contract

Every schema invariant is either observed from a fresh database built from the edited migration
bytes or explicitly classified as application-only. Dashboard assertions bind keys to distinct
values, not merely totals. Invalidation evidence ignores comments and proves the real call site.

## Failure/idempotency/security cases

- already-migrated service state is never accepted as migration-source mutation evidence
- scratch mutations use unique disposable lanes and are removed after each case
- a decoy comment cannot make a missing invalidation pass
- tests perform no external network/provider call and use no alpha credential

## Rollback / feature flag

Tests only. Revert the task commit if an instrument is unsound; no runtime flag or data rollback
applies.

## Handoff

- changed files/checks: recorded in `docs/program/W48-GUARDS.md`
- contracts/migrations/runtime: unchanged
- known limits: every justified non-schema invariant remains named for the judge
- integration notes: do not merge Stage B before `W48-JUDGE-A`
