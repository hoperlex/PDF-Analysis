# Task W53-QUEUE-TEST-REPAIR-02 — queue regressions tolerate committed sibling tests

## Outcome

The W53 queue regression tests pass in the full combined battery even when prior tests legitimately committed other queued Jobs. Their original A/B anchor-mutation and dispatcher tie-order assertions stay strong and detect the old product defects.

## Depends on

- W53-QA-01
- W53-QUEUE-REPAIR-01
- W53-JOBS-REPAIR-03

## Frozen inputs

- Exact pre-grant integrated code SHA `30448b6ebbed2b78c5a91853ef37b89b64cef1d7`; integrator assigns the post-grant dispatch SHA.
- API `1.0.0-draft.1`, 36/43/91; OpenAPI SHA-256 `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`; domain rev 9/29, state-machine SHA-256 `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`; migration head `0017_execution_queue`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- Independent `W53-QA-RECHECK-01` combined run on a fresh migrated 0017 database: **20 passed, 3 failed**. Full trace `/tmp/w53-qa-recheck-01/required-tests.log`, SHA-256 `2c9613990e02a73627a4789ba38dd864cbf6a282beb655adb20f1a6af073ac1d`. The three failures are `test_queue_cursor_follows_priority_order_after_new_insert`, `test_queue_emitted_cursor_survives_anchor_state_edit_and_refuses_bad_fields`, `test_queued_tie_order_matches_dispatcher`. Each assumes its new Job is globally first; a previous committed test left a queued priority-100 Job. The QA agent reran each node alone on fresh databases, all 1/1; the six original independent QA guards passed 6/6 together and two concurrency guards passed 2/2 on separate fresh databases. The combined-battery failure is a test isolation risk, not evidence of a production SQL regression.
- 2026-10-09 14:06:07 UTC: private ports 56970/60570/60571 unbound; worktree/Docker filesystem each had 10,578,919,424 bytes free. Recheck before use.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `tests/integration/runs/test_w53_execution.py` (only the three queue tests named above and narrow helpers for them)
- `tests/integration/qa_w53/test_queue_and_effect_journal.py` (only the first A/B queue test, if a full-battery reproduction proves it needs the same isolation correction; preserve its unseen-B and no-duplicate assertions)
- `docs/program/W53-QUEUE-TEST-REPAIR-02.md`

## Forbidden hotspots

Production source, all other tests (including the other five independent QA guards), contracts, migration, root dependency/lock, composition root, global styles, release/backup/deployment paths, refs/tags and working stand.

## Non-goals

Weakening expected queue behavior, changing cursor semantics, deleting immutable data or truncating the database, changing test ordering to hide the issue, modifying production code, or asserting a full gate pass.

## Deliverables

- Make each queue test locate its own anchor in an otherwise live global queue, or otherwise isolate the test with a real fresh database. Keep the emitted opaque cursor seam and A/B mutation; old unstable cursor must still fail the unseen-B assertion. For tie order, compare the visible queued order to the dispatcher's true global eligible order while asserting the own equal-priority subsequence; do not merely remove the dispatcher assertion.
- Show the exact combined order from the QA log red before and green after on a fresh migrated 0017 database, including prior committed high-priority Job, all six independent QA tests and the two concurrency nodes. Run focused queue tests, `git diff --check`, frozen hashes and exact path audit.
- Six AGENTS.md §5 handback with branch/HEAD/log hashes.

## Required checks

Private lane `gate-w53qtest`: PG 56970, old S3 API 60570, console 60571; unique DB/bucket/volumes/credentials. Measure free bytes/ports before use and keep logs under `/tmp/w53-queue-test-repair-02/`. Use existing images only; no working stand, shared prune or full image build. Include a mutation or equivalent proof that the original anchor-loss/tie-order defect still makes the corrected tests fail; if that cannot be done safely, state the exact limit and preserve the original assertion text for integrator review.

## Integration contract

Tests only, no frozen contract change. Integrator reviews every assertion change, cherry-picks exact branch SHA, then repeats the formerly red combined test order and independent QA on the merged SHA. A needed path expansion requires a new grant first.

## Failure/idempotency/security cases

Prior priority-100 queued Job, live queue with terminal records, mutated anchor state/priority, no A duplicate, unseen B retained, malformed cursor refused, equal-priority queued order and global dispatcher first.

## Rollback / feature flag

No behavior change or flag. Revert this test-only repair if it weakens regression sensitivity.

## Handoff

Changed files; checks/results; contracts; risks; integrator instructions; forbidden-hotspot proof — all six AGENTS.md §5 items.
