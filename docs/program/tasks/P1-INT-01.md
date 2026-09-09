# Task P1-INT-01 — accept the early foundation and hand it to P02

> **Status: specified; dispatch after accepted `P1-QA-00`.**

## Outcome

A concise `PF-01` acceptance record identifies the exact foundation commits, locks,
container images, migration head, commands and known limits. No self-referential digest
or multi-round ratification mechanism is introduced.

## Depends on

- `P1-INT-00` — completed and integrated
- `P1-INF-01` — completed and integrated
- `P1-DB-01` — completed and integrated
- `P1-STO-01` — completed and integrated
- `P1-QA-00` — independently accepted and integrated

## Frozen inputs

- FF-01, foundation lock and accepted provider/QA commits
- migration head from `P1-DB-01`
- base commit: accepted `P1-QA-00` integration commit

## Allowed paths

- `artifacts/checkpoints/PF-01/**`
- the `PF-01` status row only in `docs/program/CHECKPOINT_REGISTRY.md`
- P01 status rows in `docs/program/ROADMAP.md`
- prototype banner in `docs/program/CURRENT_STATE.md`
- status/handoff banners of `docs/program/tasks/P1-*.md`

## Forbidden hotspots

- root locks/commands, providers, migrations, contracts, tests and product runtime
- CP-00 evidence, architecture documents, Git tags and remote refs

## Non-goals

- No provider repair, product implementation, tag or publication.
- No approval of P02–P05.

## Deliverables

- one short PF-01 report and machine-readable build information
- exact lock hashes, image digests, migration head and certified commits
- commands/results, known limits and non-destructive restart/rollback note
- P02 handoff matching FF-01 section 8
- `PF-01` registry row changed from `planned` to `accepted` only after every required
  check and manual review passes

## Required tests

- Command: `make foundation`
  Expected: exit `0` on the exact convergence commit.
- Command: `git diff --check`
  Expected: exit `0`.
- Manual review: report claims resolve to existing files/commits and no product scope
  is declared accepted.
  Expected: pass.

## Integration contract

After PF-01 acceptance and completion of `P0-PLN-01`, P02 may consume the database and
BlobStore foundation. P01 remains valid while later planning changes.

## Failure/idempotency/security cases

- A failed command blocks PF-01; documentation-only wording does not open review loops.
- The task writes no credential, product data, tag or remote ref.

## Rollback / feature flag

Revert the report/state commit. Provider rollback follows each provider's policy.

## Handoff

- changed files and exact accepted commit
- commands/results
- migration head, lock/image hashes and known limits
- P02 may start only when its separate plan is accepted
