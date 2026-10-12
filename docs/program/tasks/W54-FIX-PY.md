# Task W54-FIX-PY — The bundle proves its rows came from the named drop and ledger, reconciles objects before discard, and maps storage failures to a refusal

## Outcome
The bundle proves its rows came from the named drop and ledger, reconciles objects before discard, and maps storage failures to a refusal.

## Depends on
- `W54-JUDGE-A`, `W54-JUDGE-Y` (`docs/program/reviews/W54-JUDGE-{A,Y}.md`)

## Frozen inputs
- domain contract: after `W54-SEAL-01`
- API contract: after `W54-SEAL-01`
- analysis/comparison/event contract: unchanged
- migration head: `0019_execution_workers`
- base commit: the judges' record commit on `integration/w54`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: none

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/norms/bundle/**`, `src/auditmanager/norms/{repository,__main__,corpus_source}.py`, `src/auditmanager/norms/repair_journal/**`, `src/auditmanager/norms/custody/**` (reconciler call only), `src/auditmanager/runs/executor.py` (Y-F5 only), `tests/integration/norms/{bundle,repair,custody}/**`, `tests/integration/norms/test_*.py` touched by these, `tests/integration/runs/test_d141_final_transaction_keeps_the_lease.py`, `docs/program/W54-FIX-PY.md`

## Forbidden hotspots
- any path outside the grant; contracts and migrations; `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand, `.local/norms/corpus/**`

## Non-goals
- JUDGE-Y F4 (a contract reseal; registered), JUDGE-A F7 (rehearsal), F8 (registered).

## Deliverables
- JUDGE-Y F1 (in `write_bundle` recompute the base key/digest from rows + drop `results.md` and require equality; require `with_segmentation_profile(repaired_snapshot(base, ledger), profile)` equals `content_key`/`content_digest`; require each ledger `crop_sha256` equals the bundled crop; in `validate_snapshot_rows` check key terms and 12-hex against counts and `content_digest`), Y-F2 (manifest `SnapshotFacts` equal the imported rows), Y-F3 (one `SHA256SUMS` parser; record the sums SHA-256 in the repair journal header and ledger; export compares it), Y-F5 (read the gate's artifacts before the `advance`), JUDGE-A F2 (run the custody reconciler — point HEAD per confirmed admission — in import step 5 or `report` when a store is available; nonzero exit on any incident, so the shell discard stays gated), A-F5 (`StorageError` → `EXIT_REFUSED` with a reason).

## Required tests
- command: container-free tests now (`bash -n`, `shellcheck -x`, the refusal suites with `docker` stubbed, non-postgres pytest); DB/S3-backed cases are the integrator's window step — list exact commands.
- expected: exit 0; each fix has a test that fails without it.

## Integration contract
The integrator merges after reading the diff and the report.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; no containers; never touch the stand, published refs or other worktrees.
