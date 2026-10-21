# W54-D127-REPLAY-INTEGRITY-01 — persisted-window verification on replay

## Result

The original `W54-EMBED-01` implementation already verifies full window coverage and computes `norm-embedding-set/2` from stable document/chunk keys when first inserting a build. A separate replay defect remained: `ensure_build` compared the newly supplied digest and counts with the immutable completion row, then returned `created=False` without reading the stored windows. A `DELETE` of one `norm_embedding` row can leave the completion row present, so the replay could certify incomplete storage.

The repository now streams and recomputes the persisted-window metadata digest and chunk/window counts on both insertion and exact replay. It raises `NormEmbeddingConflict` if any differs. The existing `created=False` response is retained only for a build whose stored metadata still matches. No schema or contract changes are needed.

## Files and checks

- `src/auditmanager/norms/embedding_repository.py` — shared read-back after the new-build and replay branches.
- `tests/integration/norms/embedding/test_repository_offline.py` — regression deletes a stored window while retaining the completion row.
- This report and `docs/program/tasks/W54-D127-REPLAY-INTEGRITY-01.md` — bounded task/evidence.
- Before the repair, the new regression failed: `Failed: DID NOT RAISE NormEmbeddingConflict` (1 failed in 0.64 s).
- After the repair: `PYTHONPATH=src:. /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/norms/embedding/test_repository_offline.py -p no:cacheprovider` → **13 passed in 5.25 s**.
- Direct task governance returned `[]`; `git diff --check` passed. The final commit contains only the four task-allowed paths.

## Contracts, limits and integration

Contracts, migration head, root dependencies/lockfiles, composition, global styles and served behavior are untouched. Replays now pay one streamed read of all persisted window metadata, which is appropriate for this explicit build verification path; it does not load vectors or the model and does not rehash vector bytes. The repository still depends on its caller's transaction for commit/rollback. The complete DB-backed `tests/integration/db/test_norm_embeddings_migration.py`, live corpus build and full gate were not run while the separate W55b gate owned the host resource slot. Those remain integrator checks when resources permit. This commit does not claim corpus qualification, DB/S3 publication or D-127 register closure.

Integrator: cherry-pick the exact clean source commit, run the focused DB case and eventual complete gate in an assigned resource window, and keep W54 promotion dependent on the repaired snapshot, full embeddings and qualified bundle. Roll back by reverting this one commit; no data migration or flag is involved.
