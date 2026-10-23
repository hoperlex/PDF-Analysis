# Task AR-V3-BETA-GROUP-REVIEW-01 — collect six scoped review outcomes

## Outcome
A read-only Runs service returns all six AR v3 scope outcomes for one durable group, including pending and failed Runs, while projecting a verified review to user-safe topics and provisional citations for available members. A corrupted review is an explicit per-member refusal, not an empty result.

## Depends on
- `AR-V3-BETA-REVIEW-READ-01`

## Frozen inputs
- shared domain/API/analysis/events contract: `1.3.0`, unchanged
- AR v3 beta stage extension: `1.0.0`, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `e4001a2c21aabd0b5e1af4b97ea8169da26ecf48`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the group read has six Run IDs/states but no review material, and the new saved-review reader returns an internal document that also carries hashes and Blob pointers
### P-01 — read seams
- captured_at: 2026-10-23
- command: `rg -n 'class GroupView|def get_ar_v3_group|class V3SavedReview|def read_v3_saved_review' src/auditmanager/runs/v3_group.py src/auditmanager/runs/v3_review_reader.py`
- captured_output: `GroupView.members` carries six scope/run/state pins; `read_v3_saved_review` verifies and returns the full internal document for one terminal Run.
- interpretation: a safe six-scope projection must whitelist user-facing fields and retain one outcome per durable member.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/runs/v3_group_review.py`
- `tests/integration/runs/test_v3_group_review.py`
- `docs/program/tasks/AR-V3-BETA-GROUP-REVIEW-01.md`
- `docs/program/AR-V3-BETA-GROUP-REVIEW-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots
- `contracts/**`, migration head, root dependencies/lockfiles, composition root and global styles
- router, React, provider transports, normative map/source/set data, product VERSION
- `origin/main`, tag and deployment host

## Non-goals
- Adding the public API/UI contract; a subsequent integration task owns that synchronized seal.
- Selecting, editing or approving any normative citation or numerical verdict.
- Real PostgreSQL/S3 acceptance on this host.

## Deliverables
- Six-scope aggregate with explicit pending, failed, review-available or review-refused state.
- User-safe projection that excludes internal digests, Blob IDs, model reply and prompt payload.
- Focused tests and result note.

## Required tests
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_group_review.py -x --tb=short`
- expected: all pass, handoff path check passes; full make gate deferred by R-135.

## Integration contract
The service reads the six durable members in canonical F1/F2/A1/A2/S1/S2 order. It calls the saved-review reader only for `published` or `partial` members and reports a typed verification refusal per member if that reader rejects. It never fabricates a review for failed or pending Runs. It rereads group membership at the end to refuse a mixed-time answer. A later API response should be built from this projection, not the internal artifact document.

## Failure/idempotency/security cases
- A group that changes during the read refuses as a whole; a single corrupt completed member stays visible with explicit refusal status.
- Each member's Run ID, scope and state are preserved. No internal Blob pointer, provider payload or numeric conclusion escapes in the projection.
- Reads make no DB writes or provider calls and do not require an installed pack.

## Rollback / feature flag
Uncalled read service changes no served behavior. Remove it if the public review API is abandoned; no migration.

## Handoff
- changed files: result note
- commands/results: result note
- known limits: public contract/UI and target stand acceptance remain
- integration notes: projection is the only source for a future group review response
