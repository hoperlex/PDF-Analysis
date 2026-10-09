# Task W53-GATE-QA-REPAIR-01 — isolate pause/claim race guard from other queued Runs

task_id: W53-GATE-QA-REPAIR-01

## Outcome

The pause-between-hint-and-claim guard passes inside the complete gate while still proving that a pause prevents authority for its own Job after a real earlier dispatcher hint.

## Depends on

- `W53-FREEZE-01` (completed). The integrated EXEC, Jobs and queue-test repair code is a frozen input below, with EXEC owner stops still open.

## Frozen inputs

- Diagnostic product base: `9a121cf28de619d6ff8f5fcb765aa1c62d522307`; dispatch worktree base is the exact grant commit supplied by the integrator.
- OpenAPI SHA-256 `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`, `1.0.0-draft.1`; state-machine SHA-256 `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`; migration head `0017_execution_queue`.
- Full gate log `/tmp/w53-int-gate/gate.log`, SHA-256 `0178e881a6f7571abd8909ceb95d67a9b24da386f9fee3733c119fc791c6434e`.

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the pause race test assumes its own Job is globally first

### P-01 — direct failure after prior tests queued a competing Job
- captured_at: 2026-10-09
- command: `grep -n -A1 '^FAILED tests/integration/qa_w53/test_queue_and_effect_journal.py' /tmp/w53-int-gate/gate.log`
- captured_output:
  ```text
  740:FAILED tests/integration/qa_w53/test_queue_and_effect_journal.py::test_pause_between_hint_and_claim_refuses_new_authority
  741-13 failed, 3343 passed, 6 skipped, 6 warnings, 298 subtests passed in 721.66s (0:12:01)
  ```
- interpretation: traceback at log line 682 shows `next_queued_run` returned a different earlier queued Run despite the test setting its own priority 100. This is test pollution, not evidence that pause acquired authority.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `tests/integration/qa_w53/test_queue_and_effect_journal.py`
- `docs/program/W53-GATE-QA-REPAIR-01.md` (handback only)

## Forbidden hotspots

All other paths, especially the Job implementation, contracts, migration head, root locks, composition roots, global styles, working stand, refs and tags.

## Non-goals

No change to dispatcher ordering or pause semantics, no product behavior change, no empty-global-queue assumption.

## Deliverables

Robust real race guard, focused regression evidence with a competing high-priority Job, and six-item §5 handback including branch/SHA and changed-path audit.

## Required tests

- On private `gate-w53qa` DB/S3 lane (ports 56922, 60524/60525), run the owned test file and a combined order containing the W53 queue tests after older tests or a seeded competing Job. Check ports/disk first.
- Prove a process-only mutation removing pause protection reds the assertion; `git diff --check`.

## Integration contract

Work in isolated worktree at exact dispatch SHA. Obtain a genuine prior hint for the test's own `run_id` without assuming it is globally first, then pause on a separate committed connection and assert no authority/attempt for the same Job. Preserve teardown unpause even on assertion failure. Return branch, SHA and all six §5 items; no publication, tags or working stand.

## Failure/idempotency/security cases

A foreign queued Job must not cause a false failure or let the test skip its own hint. Removing the pause check from `start_execution` must still make the test red.

## Rollback / feature flag

Test-only repair; revert if the race assertion weakens. No feature flag applies.
