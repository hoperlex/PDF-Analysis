# Task W54-SNAPSHOT-01 — The corpus snapshot loader writes reliability-aware rows, imports snapshots with ids, and keys snapshots by the segmentation profile

## Outcome
The corpus snapshot loader writes reliability-aware rows, imports snapshots with ids, and keys snapshots by the segmentation profile (D-126).

## Depends on
- `W54-FREEZE-01`, `W54-SEAL-01`, `W54-CUSTODY-01`, `W54-REPAIR-01` (merged on `integration/w54`)

## Frozen inputs
- domain contract: after `W54-SEAL-01`
- API contract: after `W54-SEAL-01`
- analysis/comparison/event contract: unchanged
- migration head: `0019_execution_workers`
- base commit: the REPAIR merge on `integration/w54`

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
- Exactly the `W54-SNAPSHOT-01` grant in `docs/program/dispatch/W54-PLAN.md` §4 Stage B item 3, plus `docs/program/W54-SNAPSHOT-01.md`.

## Forbidden hotspots
- any path outside the grant; contracts and migrations; `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand, `.local/norms/corpus/**` (read-only)

## Non-goals
- embedding, bundle; any heavy full-corpus load (that is `W54-CORPUS-OPERATE-01` in a window).

## Deliverables
- Per plan §3.4 and §4 Stage B item 3: D-126 (`content_key` includes the segmentation profile); the reliability-aware profile and its invariant; the loader and repository write `norm_paragraph.text_reliability` and `norms_snapshot.unreliable_count` (REPAIR's handback: today only `repair_count` is written, and loading the repaired snapshot would break); the `characters-v1` refusal; `import_snapshot(rows with ids)` with replay and conflict tests and the row digest.

## Required tests
- command: container-free tests now; DB-backed `tests/integration/norms/**` and `tests/integration/db/test_norms_corpus_migration.py` loader cases are heavy steps on PostgreSQL `57150`, S3 `60750/60751` for the integrator's window — list exact commands.
- expected: exit 0; each new behaviour has a test that fails without the change.

## Integration contract
The integrator merges after reading the diff and the report and runs the listed heavy steps in the window.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; never touch the stand, published refs or other worktrees; no container before the window; never write under `.local/norms/corpus`.
