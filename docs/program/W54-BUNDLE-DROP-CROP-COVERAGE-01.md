# W54-BUNDLE-DROP-CROP-COVERAGE-01 — crop inventory bound to source checksums

**Date:** 2026-10-16. **Base:** published `origin/dev` `95de4f6b4e10a8b60f57ae84ab66156917c7b96c`. **Task:** `tasks/W54-BUNDLE-DROP-CROP-COVERAGE-01.md`.

## Result

The actual `write_bundle` path now hashes the bytes of `crops_index.json` against the operator-supplied `SHA256SUMS`, then compares every indexed crop PDF path with every crop PDF path in that listing. Both checks run before `out.mkdir` or an `incomplete-*` staging directory. An index that omits a listed crop or changes without a matching checksum refuses. The existing exporter still hashes every placed PDF/crop object against its listed digest, derives the snapshot identity, writes and verifies the bundle as before.

This fixes a reproduced omission: before the change, a synthetic source with one index entry and its crop file removed, but the original sums unchanged and still naming that crop, exported successfully with **4 instead of 5 custody slots**. The new tests first failed on the original code in all three variants (omitted crop with original index digest, omitted crop with updated index digest, unrelated index byte change), then passed with the guard. The variant with updated index digest specifically proves the complete path-set check; the unrelated byte change proves the index hash check.

The read-only check of the real W54 source found a 7,037,392-byte index with matching SHA-256, 28,246 unique indexed crop paths and 28,246 crop paths in the frozen listing, with zero differences. The implemented guard also accepted that real index: 674 document slugs and 28,246 crop paths. The real source and listing were not modified; no actual bundle was exported.

## Checks

- Before implementation: targeted tests **3 failed**, each because `write_bundle` did not raise `BundleRefused`.
- After implementation and after the reversing mutation: `tests/integration/norms/bundle/test_export_offline.py` **17 passed**. The additional case refuses an index omitted from the supplied sums.
- Wider bounded bundle suite, excluding PostgreSQL cases: **147 passed, 20 deselected** in 3.30 seconds.
- Reversing mutation changed only `if indexed != listed:` to `if False:` temporarily; the omitted-crop test with an updated index checksum failed as expected (**1 failed**), and the original source was restored before the final suite.
- `python3 -m compileall -q src/auditmanager/norms/bundle/export.py tests/integration/norms/bundle/test_export_offline.py`: exit **0**.
- Direct `governance_findings` on the task: `[]`; `git diff --check`: exit **0**. Exact changed-path proof is recorded at close.

## Contracts, limits and integration

The exporter gains two refusal checks against its existing input listing, using existing `drop_file_unsummed`, `drop_file_differs` and `drop_crops_differ` reason codes. The bundle format, public API/domain/event contracts, migration head, root dependencies/lock, composition root and global styles do not change. W54/W55 plan, source sums, API, error catalogue and stage registry retain the frozen hashes named in the task.

This guard binds the index and complete crop inventory to the **supplied** listing. The W54 operator preflight separately pins that listing's digest; the complete source `sha256sum -c`, repaired snapshot, embedding build, bundle verifier and DB/S3 publication still remain separate checks/actions. The content-addressed object placer reuses an already placed digest without re-reading a later source path with that same expected digest, so this guard does not replace the complete source checksum pass. No credential, paid provider call, PostgreSQL, S3, stand or heavy restore was used here. The 121-page `claude-opus-5` repair remains blocked by the absent proxy credential, and the repaired qualified snapshot and complete embedding checkpoint remain absent.

Exactly four paths changed: `src/auditmanager/norms/bundle/export.py`, `tests/integration/norms/bundle/test_export_offline.py`, this task and this report. The integrator may fetch and cherry-pick the clean local commit. Revert that commit for rollback; no data rollback or runtime feature flag applies.
