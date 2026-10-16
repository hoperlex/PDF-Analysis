# W54-BUNDLE-ROW-VALIDATION-INGRESS-01 — semantic rows checked before custody

**Date:** 2026-10-16. **Base:** published `origin/dev` `eaf58965cd8bedc229f464866e3d5768b1f05797`. **Task:** `tasks/W54-BUNDLE-ROW-VALIDATION-INGRESS-01.md`.

## Result

The bundle importer now runs the existing `validate_snapshot_rows` after verifying the file and row digests and snapshot facts, before reading database state or admitting and dispatching Blobs. Semantic row failures become the existing internal `bundle_rows_invalid` refusal. The later transactional validation in `import_snapshot` remains unchanged.

A self-consistent forged bundle test increments one document's `paragraph_count`, then recomputes the row digest, manifest file digest, `SHA256SUMS` and bundle directory name. The manifest and row digests agree. Before the guard, import reached the `Untouchable.engine.connect` trap; with the guard, it refuses on the paragraph ordinal mismatch. The test does not read the real corpus or access DB/S3.

## Fixture correction

The old synthetic bundle fixture used paragraph kind `clause`, which is outside the frozen `ParagraphKind` vocabulary (`body`, `heading`, `table_row`). It now uses `body`; `validate_snapshot_rows(synthetic_rows())` passes. This changes digests generated from synthetic rows at test runtime. Search of the bounded bundle suite found no literal row digest or checksum golden value dependent on this fixture. No production corpus row or contract changed.

## Checks

- Before code, the forged bundle reached `Untouchable.engine.connect` instead of refusing; the new targeted test failed for that reason after the fixture was corrected.
- `test_import_refusals_offline.py`: **19 passed**.
- Bounded bundle suite, excluding PostgreSQL cases: **153 passed, 20 deselected** after the guard; repeated after a reversing mutation was restored: **153 passed, 20 deselected**.
- Reversing mutation removed only the new validator call: the forged bundle again reached `Untouchable.engine.connect` (**1 failed, 18 deselected**). The guard was restored.
- `python3 -m compileall -q` on three changed Python files and `git diff --check`: exit **0**.
- Direct task governance: `scripts/task_handoff.py` returned **CHECKS PASS** with a `git diff --check` check and proved exactly the five allowed paths.

## Contracts, limits and integration

No public API/domain/event contract, bundle format, migration, root dependency/lock, composition root or global style changed. The refusal reason already existed. The guard proves that row IDs, uniqueness, ordinal coverage, enum values and content key terms satisfy the same predicate later used by `import_snapshot`; it does not certify the source bytes or embedding build, and does not replace DB/S3-backed import tests.

There is still no repaired qualified snapshot or complete embedding checkpoint: the 121-page `claude-opus-5` repair lacks a proxy credential. No DB/S3 corpus publication, paid call, real import/export, restore, full gate or beta qualification occurred here.

The integrator can fetch and cherry-pick the local commit after reviewing the five allowed paths and run the release gate in its own window. Revert this commit for rollback; no data rollback or flag applies.
