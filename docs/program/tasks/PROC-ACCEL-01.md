# Task PROC-ACCEL-01 — shorten the required state read and automate lane evidence

## Outcome

A coding agent can read a compact authoritative current state, prepare an isolated lane from an exact task base, and produce a machine-checked technical handoff without changing product behavior.

## Depends on

- none; this is a process-only task based on a completed development integration.

## Frozen inputs

- base commit: `ccfb97352b2755c4ec8214adc3e46485089b51a6`
- domain contract: candidate revision 13, 32 opaque identities
- API contract: 47 paths / 54 operations / 124 schemas; error catalog 25
- analysis/comparison/event contract: unchanged by this task
- migration head: `0022_findings_v2`
- product version: `0.6.0`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: required state length and fetched development base

### P-01 — required state document is long

- captured_at: 2026-10-15
- command: `git show origin/dev:docs/program/CURRENT_STATE.md | wc -lc`
- captured_output:
  ```text
     1214   82947
  ```
- interpretation: the local `origin/dev` snapshot contains 1153 lines; this does not measure the tokens actually read by a particular agent.

### P-02 — development base and product boundary

- captured_at: 2026-10-15
- command: `git rev-parse origin/dev`
- captured_output:
  ```text
  ccfb97352b2755c4ec8214adc3e46485089b51a6
  ```
- interpretation: this SHA was fetched from the remote before preparation; it must be rechecked immediately before publication.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/PROC-ACCEL-01.md`
- `docs/program/PROC-ACCEL-01.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/history/CURRENT_STATE_2026-10-15_ccfb9735.md`
- `docs/templates/TASK_TEMPLATE.md`
- `scripts/README.md`
- `scripts/task_handoff.py`
- `scripts/lane_prepare.py`
- `tests/contract/program/test_process_acceleration.py`

## Forbidden hotspots

- `contracts/**`, migration head and root dependency/lock files
- composition roots, global styles, runtime source and product tests
- `AGENTS.md`, owner rulings, debt register and historical task/review evidence
- tags, `origin/main`, deployment host and real credentials

## Non-goals

- changing product behavior, acceptance criteria or the code-first gate cadence
- publishing `origin/main`, approving another task or changing runtime behavior
- running a full gate on this development-only process branch

## Deliverables

- one compact live `CURRENT_STATE.md` and an exact archive of its base version
- technical handoff CLI with fail-closed path and SHA checks
- isolated lane preparation CLI consuming task-assigned resources
- focused tests, operating instructions and process handoff report

## Required tests

- command: `python3 -m unittest tests.contract.program.test_process_acceleration -q`
- expected: all focused tests pass, including negative path and ownership cases
- command: `.venv/bin/python -m pytest -q tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`
- expected: live prose and history-boundary guards pass
- command: `git diff --check`
- expected: no whitespace errors

## Integration contract

The owner directly requested publication to `origin/dev` and `origin/main` on 2026-10-15, while waiving a version change and the full gate for this process-only change. This task owns only the `origin/dev` fast-forward from its exact fetched base after focused checks, path review, a clean candidate and a remote-ref reread. A separate main integration task owns the independent `origin/main` candidate. The archive preserves the dev-base state bytes. The CLIs do not merge, push, deploy or claim release acceptance.

## Failure/idempotency/security cases

- reject dirty trees, an invalid or non-ancestor base, unowned changed paths, and unparseable task allowlists
- reject lane resource collisions, unsafe task IDs, mismatched existing `.env` files and non-exact branch bases
- write only disposable local `.env` values; never copy real provider or deployment credentials
- a repeat with the same inputs is idempotent; a conflicting repeat fails

## Rollback / feature flag

Revert this task's commits. There is no product feature flag because runtime behavior is unchanged.

## Handoff

- changed files: fill at hand-back
- commands/results: fill at hand-back
- known limits: fill at hand-back
- integration notes: fill at hand-back
