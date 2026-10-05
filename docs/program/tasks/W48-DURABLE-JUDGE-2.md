# Task W48-DURABLE-JUDGE-2 — independently re-judge durable external effects

## Outcome

An author-independent, report-only verdict establishes which durable-effects findings block
release before any second repair.

## Depends on

- `W48-RULE-01`

## Frozen inputs

- domain contract: W48 revision 8, unchanged
- API contract: 17 / 20 / 61, unchanged
- analysis/comparison/event contract: unchanged
- migration head: subject declares `0014_durable_analysis_effects`
- base commit and subject: `411c6d0a4fcc44a2b522dbb11f7ed726ef87fe12`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the subject descends from Stage A and has no gate at its report-only tip

### P-01 — ancestry and subject

- captured_at: 2026-10-05
- command: `git merge-base --is-ancestor agent/w48-stage-a 411c6d0 && git rev-parse 411c6d0`
- captured_output:
  ```text
  411c6d0a4fcc44a2b522dbb11f7ed726ef87fe12
  ```
- interpretation: the subject identity and ancestry are exact; acceptance is not implied.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/reviews/W48-DURABLE-JUDGE.md`
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/reviews/W48-DURABLE-JUDGE-2.md`

## Forbidden hotspots

- every other tracked path, every ref, tag and deployment action

## Non-goals

- no repair, merge, ruling or debt-register edit

## Deliverables

- report with subject/environment/commands/statuses, findings, mutations, open questions and
  verdict; black-box pass precedes reading author reports

## Required tests

- kill after provider completion and before checkpoint commit
- kill after verified blob publication and before stage commit
- direct INSERT refusals for the composite FK and transition trigger
- occupied-`0014` downgrade refusal; fresh upgrade and full battery
- allowed-path audit using the task files as dispatched at `03c04a1` and `fd9881c`
- final `git diff --name-only 411c6d0..HEAD` names only the report

## Integration contract

Every prior DJ-R item is upheld, narrowed or falsified with a fresh measurement. The integrator
opens only the minimum path grant justified by the verdict.

## Failure/idempotency/security cases

- owned disposable services and unique ports only; no credential, provider body or cookie in
  evidence; all probes restored

## Rollback / feature flag

Report-only; revert the report commit if the judging procedure is invalid.

## Handoff

- changed files: the one report
- commands/results: included verbatim with exit status
- known limits: list untested questions
- integration notes: do not merge the report into the subject before the verdict is consumed
