# Task W48-DURABLE-JUDGE — attack the durable-effect candidate

## Outcome

An adversarial report determines whether candidate `00100e8` actually removes every reachable
unrecorded provider/artifact interval behind `A-01` and `A-02`, or names a reproducible blocker
without repairing it.

## Depends on

- `W48-DURABLE-01` — completed at `00100e8129ab0d144d66f7bac4899c069879b3cb`
- `W48-AUDIT` — completed at `c11f1b6`
- `W48-JUDGE-X` — completed and cross-examined at `349e824`
- `W48-JUDGE-Y` — completed and cross-examined at `9a31264`

## Frozen inputs

- subject: `00100e8129ab0d144d66f7bac4899c069879b3cb`
- implementation base: `e3fedd0fdf2f2eda18e55c22867201f5663717a6`
- domain contract: `1.0.0-draft.1` revision 8
- API: 17 paths / 20 operations / 61 schemas; error catalog: 22
- migration head: `0014_durable_analysis_effects`
- audit findings under judgment: `A-01` and `A-02`; `A-03` remains outside this repair

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: exact clean subject and migration head

### P-01 — exact subject

- captured_at: 2026-10-02
- command: `git rev-parse HEAD`
- captured_output:
  ```text
  00100e8129ab0d144d66f7bac4899c069879b3cb
  ```
- interpretation: the review subject includes the implementation and completion report; this
  proves no remote ref or deployed host names it.

### P-02 — declared migration head

- captured_at: 2026-10-02
- command: `env PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -c 'from auditmanager.shared.db.migrations import head_revision; print(head_revision())'`
- captured_output:
  ```text
  0014_durable_analysis_effects
  ```
- interpretation: the tree resolves one outgoing head; it does not prove the migration's
  constraints, upgrade or downgrade behaviour.

### P-03 — review delta size

- captured_at: 2026-10-02
- command: `git diff --name-only e3fedd0fdf2f2eda18e55c22867201f5663717a6..HEAD | wc -l`
- captured_output:
  ```text
  42
  ```
- interpretation: the judge must inspect a bounded 42-path task delta and independently search
  callers outside it for bypasses; the count alone is no allowed-path or correctness proof.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/reviews/W48-AUDIT.md`
- addendum_path: not_applicable

The audit and prior judge reports remain immutable. This task judges their blockers against the
new subject and records a new report rather than rewriting earlier verdicts.

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W48-DURABLE-JUDGE.md`
- `docs/program/reviews/W48-DURABLE-JUDGE.md`

## Forbidden hotspots

- every other tracked path, including the implementation under judgment and its tests
- `contracts/**`, every migration, dependency/lock file, composition root, API router, workflow,
  global style and deployment file
- database/object-store evidence outside disposable test namespaces
- tags, `origin/dev`, `origin/main`, deployment state, credentials and public-host writes

## Non-goals

- no repair, refactor, formatting cleanup or test-instrument commit
- no assertion of provider exactly-once execution where the provider offers no idempotency key
- no `A-03` architecture repair or debt-register reconciliation
- no replacement of an organisationally independent reviewer by an undisclosed self-review
- no alpha tag, remote publication, deployment or public acceptance

## Deliverables

- `docs/program/reviews/W48-DURABLE-JUDGE.md` with exact subject, method, command/exits,
  findings, untested questions and verdict
- a transaction-order trace from run acceptance through Job/Attempt creation to each external
  effect and from each effect checkpoint to consumer-visible publication
- disposable fault attacks at provider and object boundaries, including a separate transaction's
  view of every crash state
- migration, fencing, cross-wiring, idempotency, token non-disclosure and reconciliation attacks
- restored worktree whose final tracked diff contains only the task and report

## Required tests

- run the durable DB/fault/reconciliation suites against PostgreSQL and MinIO owned by the local
  gate instance; expected: green baseline before inventing attacks
- search every production `adapter.complete()` and analysis `put_blob()` caller for a path that
  bypasses the durable journal/decorator; expected: no live production bypass
- attempt run/job/attempt cross-wiring, wrong/current-old token publication and populated
  downgrade; expected: database or repository refusal with no token in exception text
- inject failure before dispatch, after remote acceptance, after response checkpoint, after
  object verification, after intent commit and after canonical publication; expected: every
  possibly external effect has a stable enumerable breadcrumb and no automatic live retry
- hide a bound object and leave an unbound publication; expected: exact run/stage/role reports
  without bucket listing or deletion
- run `git diff --check` and the governance suite; expected: exit 0

## Integration contract

The report may accept closure only if a process loss cannot leave a possibly paid provider call
or canonical analysis object without a stable database identity enumerable from a new
transaction. Acceptance means auditable at-least-once boundaries with explicit ambiguity, not a
claim of provider exactly-once. Any reproducible escape is release-blocking and requires a new
bounded repair task; the judge grants no repair path.

## Failure/idempotency/security cases

- the execution token never appears in logs, error detail, SQL bind diagnostics or API output
- only the current running Attempt may checkpoint or publish; superseded authority fails closed
- duplicate execution cannot mint a second first Attempt or dispatch the same live call silently
- a provider exception after dispatch is ambiguous and suppresses automatic live retry
- canonical objects are never deleted as implicit cleanup, and reconciliation performs no bucket
  listing or silent adoption
- downgrade refuses populated durable-effect relations instead of discarding audit evidence

## Rollback / feature flag

Report/task documentation only. Revert these two files if the evidence is invalid. No runtime
feature flag or data rollback applies.

## Handoff

- changed files: task and report only
- commands/results: recorded in the report with exact exit status
- known limits: public-provider idempotency and organisational independence stated explicitly
- integration notes: `W48-INT-CLOSE` remains blocked by any red verdict and still has no implied
  `origin/main` authority
