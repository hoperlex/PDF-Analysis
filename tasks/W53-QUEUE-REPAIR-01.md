# Task W53-QUEUE-REPAIR-01 — stable continuation and truthful dispatch order

## Outcome

An already emitted queue cursor must not change its boundary when that Job's priority/state changes; an unseen Job that was behind the boundary remains reachable on the next page. For equal-priority queued Jobs, displayed order must match the dispatcher's `created_at ASC, job_id ASC` order.

## Depends on

- W53-SEAL-01
- W53-EXEC-01
- W53-EXEC-WEB
- W53-REHEARSAL-01
- W53-QA-01 (red counterexample integrated; acceptance pending repair)
- W53-JUDGE-Y (independent private-DB confirmation integrated)

## Frozen inputs

- domain revision 9 / 29 identities; state-machine SHA-256 `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`.
- API `1.0.0-draft.1`, 36/43/91; OpenAPI SHA-256 `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`; Cursor is an opaque continuation string to clients.
- analysis/comparison/event: frozen W53 SEAL set; migration head `0017_execution_queue`.
- base code before this dispatch amendment: `1a788a77c42869ae4d17e3decb8733983a04ee50`, including QA and X/Y reports, proxy repair and rehearsal repair. Integrator assigns the exact post-amendment SHA.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

### P-01 — QA private DB counterexample

- captured_at: 2026-10-09
- command: `sha256sum /tmp/w53-qa-01/queue-effect-counterexamples.log`
- captured_output:
  ```text
  73839e55c2ffc1dc092f8c14e1affa02af2b9c34017c286fa3fa201f45be0c00  /tmp/w53-qa-01/queue-effect-counterexamples.log
  ```
- interpretation: the preserved QA log contains the complete `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/pytest -q tests/integration/qa_w53/test_queue_and_effect_journal.py` result, **3 failed in 0.48 s**. `test_priority_edit_does_not_hide_an_unseen_queue_job` showed A(priority 100), B(priority 90) on baseline page two, then A changed to priority 50 and B disappeared from page two. Two other red tests in the same log are assigned to a separate effect-journal repair.

### P-02 — displayed tie order differs from dispatcher

- captured_at: 2026-10-09
- command: `git grep -n -E 'j.created_at DESC|j.created_at, j.job_id' -- src/auditmanager/execution/public.py src/auditmanager/jobs/repository.py`
- captured_output:
  ```text
  src/auditmanager/execution/public.py:62:              j.priority DESC, j.created_at DESC, j.job_id DESC
  src/auditmanager/jobs/repository.py:43:    "ORDER BY j.priority DESC, j.created_at, j.job_id LIMIT 1 "
  ```
- interpretation: for equal priority, the queue shows newest first while the dispatcher selects oldest first. Keep queue grouping and other state behavior unless a direct test requires change.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/execution/public.py`
- `src/auditmanager/bootstrap/adapters.py` (only execution queue cursor encode/decode and mapping)
- `tests/integration/runs/test_w53_execution.py` (only queue pagination tests)
- `tests/integration/qa_w53/test_queue_and_effect_journal.py` (only `test_priority_edit_does_not_hide_an_unseen_queue_job`: adapt it to the emitted opaque API cursor without weakening its unseen-B assertion; the other QA tests are forbidden)
- `docs/program/W53-QUEUE-REPAIR-01.md`

## Forbidden hotspots

- `contracts/**`, migration, `jobs/repository.py` and its dispatch query, API routers/schema/common cursor codec, other QA tests, root dependency/lock, composition root elsewhere, global styles, UI, release/backup/deployment paths, refs/tags/stand.

## Non-goals

- Claiming a snapshot of all future queue mutations; the contract promises an opaque continuation, not a historical snapshot. Fix the anchor-mutation loss and deterministic tie order without inventing a global snapshot protocol.
- Fixing effect journal, pause race or public global pause event.

## Deliverables

- Carry the emitted immutable sort tuple in the opaque cursor rather than resolving current Job coordinates; validate malformed/untrusted token fields and keep `validation_failed` behavior. The cursor must remain an opaque string at the API boundary and must not leak privileged data.
- Regression for changed anchor priority/state and queued equal-priority order, plus six-item handback and path audit.

## Required tests

- On a private migrated 0017 database, demonstrate the QA counterexample red before and green after by equivalent in-grant test; prove first/second page have no duplicate, unseen B remains, and malformed cursor refuses. Check tie order against dispatch query. Run focused existing queue/API tests; `git diff --check`, frozen hashes and exact path audit. Preflight disk under AGENTS.md §8 before a large battery; no image build or working stand. Logs under `/tmp/w53-queue-repair-01/`.
- QA's original first test calls the internal repository with a raw Job ID; a stable emitted API cursor may change that internal method signature. Its narrow test amendment must exercise the **emitted continuation token** at the public execution adapter seam, retain the original A/B mutation sequence and the exact unseen-B assertion. Do not edit or skip the five other independent QA guards. The integrator reviews the test diff and independently repeats it.
- Private lane: `gate-w53queue`, PostgreSQL `56940`, S3 API `60540`, console `60541`. Measure all ports before use, isolate volumes/credentials, and remove only own resources at handback.

## Integration contract

Existing UI continues to treat `next_cursor` as opaque. The integrator repeats the independent QA test after merging QA and this repair. Any need to widen contract/source paths returns an exact stop, not an ungranted edit.

## Failure/idempotency/security cases

- Handle deleted/mutated anchor ID using captured sort tuple; reject malformed tuples and extreme values. Priority changes of other Jobs may still reorder live queue, and UI action refreshes from page one; report this limitation accurately.

## Rollback / feature flag

No flag; rollback the narrow cursor implementation if it fails the frozen shape. No database migration.

## Handoff

- changed files; commands/results; contracts; risks; integration instructions; forbidden-hotspot proof — six AGENTS.md §5 items.
