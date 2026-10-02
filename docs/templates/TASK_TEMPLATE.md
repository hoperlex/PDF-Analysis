# Task <TASK_ID> — <result>

## Outcome
One measurable user/technical result.

## Depends on
- completed task IDs only

## Frozen inputs
- domain contract:
- API contract:
- analysis/comparison/event contract:
- migration head:
- base commit:

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

Use `yes` when the task adds/removes a route, screen, error code, migration or another member of
a maintained set. Then replace every `not_applicable`: name the one file that enumerates the set,
the task that alone owns it in this wave, and the query whose complete output proves totality.

## Captured premise evidence
- premise: none

For every exact path, line or count used to dispatch work, replace `none` with one or more blocks:

### P-01 — <premise>
- captured_at: YYYY-MM-DD
- command: `<complete command, without truncating pipes>`
- captured_output:
  ```text
  <complete output that supports the premise>
  ```
- interpretation: <what the output proves and what it does not>

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

Historical task/review evidence is immutable. For a correction use `correction_mode: addendum`,
name the source and a new owned addendum path; never instruct a lane to rewrite the source.

## Publication authority
- development_target: none
- origin_main_authority: none

For a development publication use `development_target: origin/dev`. `origin/main` may appear as
a target only with `origin_main_authority: separate direct owner instruction <reference>` for the
exact candidate; an integration or closeout task is not authority by implication.

## Allowed paths
- ...

## Forbidden hotspots
- contracts not owned by this task
- root dependency/lock files
- migration head unless explicitly owned
- composition root/global styles unless explicitly owned

## Non-goals
- ...

## Deliverables
- code/schema/test/report/runbook

## Required tests
- command:
- expected:

## Integration contract
What exact provider/consumer behavior integrator can rely on.

## Failure/idempotency/security cases
- ...

## Rollback / feature flag
State whether not applicable and why.

## Handoff
- changed files:
- commands/results:
- known limits:
- integration notes:
