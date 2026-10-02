# Task W48-AUDIT — audit the whole frozen tree before W48 repairs bias the search

## Outcome

An independent report covers every bounded context and operational boundary in the frozen tree,
with reproducible findings or explicit measured-clean conclusions before Stage-A/Stage-B changes
can steer the search toward their own diffs.

## Depends on

- `W48-FREEZE-01` — completed by the docs-only dispatch commit containing this task file
- `MAIN-REF-POLICY-01` — completed at `6118e66`

## Frozen inputs

- frozen code base: `6118e66033380661bb747244e0f7a222fb9a87b4`
- dispatch base: exact `origin/dev` tip carrying `docs/program/W48-FREEZE-01.md`; record it before
  the first audit command
- domain/API/error/migration set: revision 8 / 17 paths / 20 operations / 61 schemas / 22 codes /
  `0013_norm_embeddings`
- architecture bans: `AGENTS.md` §4
- audit lenses and required report shape: `docs/program/dispatch/W48-PLAN.md` §7 and
  `docs/program/dispatch/W48-JUDGES.md`

## Allowed paths

- `docs/program/reviews/W48-AUDIT.md`

## Forbidden hotspots

- every path outside the single report file, including contracts, migrations, locks, composition,
  runtime/UI, tests, global styles, workflow/deploy files and all programme state/register files
- Git refs, tags, deployment/alpha state and credentials

## Non-goals

- no repair, refactor, formatting cleanup or debt-register edit
- no severity without a concrete observable consequence
- no assertion that a bounded context is clean without a captured scope query
- no product/contract/owner decision

## Deliverables

- `docs/program/reviews/W48-AUDIT.md` with exact subject SHA, environment, scope inventory,
  commands/exits, findings, untested questions and final verdict
- every finding names path/line, consequence, reproduction and scope query
- every clean conclusion names what was searched and what remains outside the instrument

## Required tests

- enumerate tracked source/test/config/documentation families before selecting findings
- run focused existing tests for every reproduced defect where safe and read-only
- architecture-boundary, identity/idempotency, side-effect ordering, auth/session/secret,
  closed-vocabulary/fallback, migration/storage, frontend truth, false-green, dependency/licence
  and deployment-ref lenses are each present in the report
- `git diff --name-only <dispatch-base>..HEAD` names only
  `docs/program/reviews/W48-AUDIT.md`
- `git diff --check` — empty output

## Integration contract

The integrator may triage a finding only from its reproduction and consequence, not its label.
The audit report is read alongside the Stage-A merge; it is never merged as an implementation
repair. Critical security, data-integrity and false-green findings may open one explicit
`W48-FIX` grant; contract/owner decisions stop the affected repair.

## Failure/idempotency/security cases

- a missing bounded-context scope is a report defect even when no code defect is found
- destructive probes, real customer data, credentials and mutable alpha actions are forbidden
- temporary probes run only in disposable copies and are removed before final diff evidence
- repeating the audit appends no hidden state; the report records exact commands and exits

## Rollback / feature flag

Report-only. Revert the report if its evidence is invalid; no runtime flag or data rollback
applies.

## Handoff

- changed files: the single report path
- commands/results: included verbatim enough to reproduce without secrets
- known limits: explicit in the report
- integration notes: no finding is repaired by this task
