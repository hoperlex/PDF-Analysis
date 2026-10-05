# Task W49-JUDGE-Y — judge of the identity wave, architecture entry point

## Outcome

A report-only, author-independent verdict on the merged W49 candidate.

## Depends on

- `W49-QA-01`

## Frozen inputs

- domain contract: revision 8, 27 opaque identities (moves only in `W49-SEAL-01`)
- API contract: 17 / 20 / 61 (moves only in `W49-SEAL-01`)
- error catalog: 22 codes (moves only in `W49-SEAL-01`: `rate_limited`)
- migration head: `0014_durable_analysis_effects` (moves only in `W49-ACCESS-01`)
- code base: `23e0579`, the W48 closure published to `origin/dev`
- controlling plan: `docs/program/dispatch/W49-PLAN.md` at the freeze commit

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: judges read only this task file and the subject SHA before their own pass

### P-01 — base measurement

- captured_at: 2026-10-05
- command: `git log --oneline -1`
- captured_output:
  ```text
  (the merged W49 candidate)
  ```
- interpretation: measured on the code base before dispatch; the lane re-measures it first.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/dispatch/W49-PLAN.md`
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/reviews/W49-JUDGE-Y.md`

## Forbidden hotspots

- every other tracked path, every ref, tag and deployment action

## Non-goals

- no repair, merge, ruling or register edit

## Deliverables

- architecture entry point: routers free of SQL/logic; invariants in `access`; ALR-05 guard green; migration fresh and both upgrade paths; partial unique; reference register equals the schema's foreign keys; reseal documents and routers in one slot; registers equal sweeps; `AGENTS.md` §4; `KNOWN_OUTSTANDING_CLAIMS` empty and every pin's needle live; findings classed release-blocking / must-fix-before-merge / register; cross-examination with the other judge

## Required tests

- every probe restored; final `git diff --name-only <subject>..HEAD` names only the report

## Integration contract

The integrator opens `W49-FIX` only for release-blocking findings.

## Failure/idempotency/security cases

- unique lane ports taken with `ss -ltn` and recorded; owned disposable services only; never kill a process by pattern; no credential in evidence

## Rollback / feature flag

Report-only; revert the report commit.

## Handoff

- changed files: listed in `docs/program/W49-JUDGE-Y.md` with `git diff --name-only <base>..<sha>`
- commands/results: verbatim with exit status; every mutation with its red output
- known limits: listed, never decided silently
- integration notes: hand back branch `agent/w49-judge-y` at a recorded SHA
