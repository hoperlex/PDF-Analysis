# W54-BUNDLE-DUPLICATE-SOURCE-VERIFY-01 — verify each deduplicated source path

**Date:** 2026-10-16. **Base:** published `origin/dev` `394a728f8a6f64ecb849f98fccdad687b79f282a`. **Task:** `tasks/W54-BUNDLE-DUPLICATE-SOURCE-VERIFY-01.md`.

## Result

The bundle export's content-addressed object placer now hashes a later source path before reusing an object already placed for the same expected SHA-256. It compares that path's bytes with the operator-supplied `SHA256SUMS`; a changed or unreadable path refuses before its custody slot is appended. Equal-byte paths still share one bundle object, preserving the existing four-object/five-slot synthetic case.

The defect was reproducible without a database or source corpus: two synthetic source paths had the same listed digest, and changing the path processed second still let `write_bundle` succeed with five slots. The row IDs in this fixture are generated, so their sort order varies. The focused test selects the later path from the actual row IDs; a reversing mutation that bypassed its hash made that test fail as intended.

## Checks

- Focused `tests/integration/norms/bundle/test_export_offline.py`: **18 passed** after restoring the mutation.
- Bounded bundle suite excluding PostgreSQL cases: **148 passed, 20 deselected** in 3.38 seconds.
- Reversing mutation replaced only the duplicate branch's source-file hash with the expected digest; the focused changed-source test failed as expected (**1 failed**). The source was restored before both passing suites.
- `python3 -m compileall -q src/auditmanager/norms/bundle/export.py tests/integration/norms/bundle/test_export_offline.py`: exit **0**.
- Direct task governance: `[]`; `git diff --check`: exit **0**. Exact changed-path proof is recorded at close.

## Contracts, limits and integration

The exporter reuses existing `drop_file_differs` refusal semantics. Bundle format `auditmanager-norm-bundle/1`, public API/domain/event contracts, migration head, root dependency/lock, composition root and global styles do not change. The W54/W55 plans, API, error catalogue and stage registry retain the frozen hashes named in the task.

The change adds a source-file read for each duplicate digest; export I/O can increase when many source paths share bytes. The exporter checks against the **supplied** sums, while the W54 operator preflight pins that listing's digest; this check does not replace complete source `sha256sum -c`, repaired snapshot qualification, embedding build or bundle verification. No real corpus export, credential, paid provider call, PostgreSQL, S3, stand or restore was used. The repaired qualified snapshot, complete embedding checkpoint and DB/S3 publication remain absent.

Exactly four paths changed: `src/auditmanager/norms/bundle/export.py`, `tests/integration/norms/bundle/test_export_offline.py`, this task and this report. The integrator may fetch and cherry-pick the clean local commit. Revert that commit for rollback; no data rollback or runtime flag applies.
