# W54-BUNDLE-BUILD-PREFLIGHT-01 — complete build checked before custody

**Date:** 2026-10-16. **Base:** published `origin/dev` `100307cecc47056005d79e388b2dde1a8e4c99ed`. **Task:** `tasks/W54-BUNDLE-BUILD-PREFLIGHT-01.md`.

## Result

The importer now streams the verified build files before its first database or S3 call. It checks each decoded vector's unit norm, chunk and window order, references to document rows, chunk/window counts and the `norm-embedding-set/2` digest against the manifest. A failed check uses the existing internal `bundle_build_invalid` refusal. The original transactional `ensure_build` and stored-row digest read-back still run after custody, in their previous order.

The ingress pass retains one chunk, a digest state and document-reference set; it does not load the full build into memory. It adds one decode/digest pass to a successful import, so real-bundle runtime cost remains unmeasured. The preflight cannot verify windows against the database's canonical chunk text; `ensure_build` still performs that check in step 4.

## Reproduction and checks

Two small synthetic bundles were forged after export. One carries invalid vector base64; the other changes a window's `input_sha256` while retaining a valid vector. Both have their build-file hash, manifest hash, `SHA256SUMS` and directory name recomputed. Before the change, both passed byte verification and reached `Untouchable.engine.connect`. After the change, they refuse before DB/S3; an unchanged valid bundle passes ingress and reaches the same test database boundary.

- `test_import_refusals_offline.py`: **22 passed**.
- Bounded bundle suite, excluding PostgreSQL cases: **156 passed, 20 deselected**.
- Reversing mutation removed only the new preflight call: both forged bundles reached `Untouchable.engine.connect` again (**2 failed, 19 deselected**). The call was restored; final focused and bounded suites passed.
- `python3 -m compileall -q` for changed Python files and `git diff --check`: exit **0**.
- Direct task governance: `scripts/task_handoff.py` returned **CHECKS PASS** with `git diff --check` and proved exactly the four allowed paths.

## Contracts, limits and integration

No public API/domain/event contract, bundle format, migration, root dependency/lock, composition root or global style changed. No source corpus or existing bundle payload was altered. The 121-page `claude-opus-5` repair still lacks a proxy credential, and there is no repaired qualified snapshot, complete embedding checkpoint or DB/S3 corpus publication. No real DB/S3/stand, paid call, real import/export, restore or full gate ran in this lane.

The integrator may fetch and cherry-pick the clean local commit and run the release gate in its own window. Revert this commit for rollback; no data rollback or flag applies.
