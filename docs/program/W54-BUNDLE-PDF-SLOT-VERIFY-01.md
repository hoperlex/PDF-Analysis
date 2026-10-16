# W54-BUNDLE-PDF-SLOT-VERIFY-01 — PDF custody slots match document rows

**Date:** 2026-10-16. **Base:** published `origin/dev` `ee70edaa56c30255558873cb9f0a777daa11ee58`. **Task:** `tasks/W54-BUNDLE-PDF-SLOT-VERIFY-01.md`.

## Result

The actual `import_bundle` path now compares the exact set of PDF custody slots `(norm_document_id, anchor)` with `(norm_document_id, source_document_ref)` from the verified row files. A missing, wrong or extra PDF anchor refuses with `bundle_source_slots_invalid` before reading database state or reaching S3. Crop slots and the bundle format are unchanged.

The defect was demonstrated with a small synthetic bundle. One PDF object and its slot were removed, then manifest counts, binding digest, `SHA256SUMS` and bundle directory digest were all recomputed. The old manifest validator accepted it and the old importer reached the test stand's forbidden database connection. The two other re-signed variants changed a PDF anchor and added an extra PDF anchor; they also reached the database before the fix. All three now refuse before that boundary.

## Checks

- Before the implementation: the three targeted cases failed because the importer reached `Untouchable.engine.connect` instead of refusing.
- After implementation and after restoring the reversing mutation: `tests/integration/norms/bundle/test_import_refusals_offline.py` **17 passed**.
- Bounded bundle suite excluding PostgreSQL cases: **151 passed, 20 deselected** in 3.31 seconds.
- Reversing mutation temporarily skipped the new row-to-PDF-slot call; the missing-PDF case failed with the same forbidden database connection (**1 failed**). Source restored before the final focused suite.
- `python3 -m compileall -q src/auditmanager/norms/bundle/stand.py tests/integration/norms/bundle/test_import_refusals_offline.py`: exit **0**.
- Direct task governance: `[]`; `git diff --check`: exit **0**. Exact changed-path proof is recorded at close.

## Contracts, limits and integration

`bundle_source_slots_invalid` is an internal bundle refusal reason, not a new public error-catalogue member. Bundle format `auditmanager-norm-bundle/1`, public API/domain/event contracts, migration head, root dependency/lock, composition root and global styles do not change. W54/W55 plans, API, error catalogue, source sums and stage registry retain the frozen hashes named in the task.

The check proves structural binding between each row and its PDF custody anchor. It cannot prove that a self-signed PDF object is the original source PDF; complete source checksums and the qualified producer chain remain necessary. The 121-page `claude-opus-5` repair lacks a proxy credential, so no repaired qualified snapshot, complete embedding checkpoint or DB/S3 corpus publication is claimed. No paid provider call, real source read/export, PostgreSQL, S3, stand or heavy restore occurred in this lane.

Exactly four paths changed: `src/auditmanager/norms/bundle/stand.py`, `tests/integration/norms/bundle/test_import_refusals_offline.py`, this task and this report. The integrator may fetch and cherry-pick the clean local commit. Revert that commit for rollback; no data rollback or runtime flag applies.
