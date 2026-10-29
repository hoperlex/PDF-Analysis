# CMP-ZIP-FIX-01 — Unicode Path service-prefix repair

Task: [`CMP-ZIP-FIX-01`](tasks/CMP-ZIP-FIX-01.md). Input review: [`CMP-ZIP-SEC-01`](compare/CMP-ZIP-SECURITY-REVIEW.md). Frozen API `1.11.0` (176 paths / 198 operations / 517 schemas), migration head `0040_comparison_ai_reports`.

## Finding and repair

The set policy already refused a raw member name beginning with exact `__MACOSX/`. A CRC-valid Info-ZIP Unicode Path could instead display that prefix over a harmless raw `ordinary.pdf` header. The displayed path passed the traversal check and the raw PDF-kind check, so the archive was accepted. The owner chose to retain rejection of these service records.

Two new adversarial cases cover that alias in the outer ZIP and inside the one permitted nested ZIP. Before the policy edit, both failed with `the archive was accepted` (`/tmp/cmp-zip-fix-red.log`). `LevelJudge` now applies the same exact prefix check to the decoded displayed name and returns the existing `comparison_zip_member_kind` constraint. The raw-name check remains in place; no case-folded prefix rule was added. The portal bundle's default policy and shared parser were not edited.

## Verification

- Red regression before source edit: **2 failed**, 100 deselected, in 0.65 s.
- After source edit: all `tests/unit/ingest/comparison_zip/`, including the portal-policy differential suite, **185 passed in 4.76 s** (`/tmp/cmp-zip-fix-green.log`).
- Governance, `git diff --check` and exact changed-file proof are recorded in the task Handoff. No live archive upload or fuzzing campaign is claimed.

## Remaining boundary

This repair closes the reader policy gap found by the agent review. D-262 remains open because the first C3 upload caller does not exist yet. `CMP-STAGE-PAIR-01` must bound the raw compressed upload and admission/concurrency, check disk readiness, use the set policy or stricter bounds, and validate every PDF before storing it. The module flag remains off by default. The C2 publication candidate does not include this C3 repair; integration occurs after C2 is fast-forwarded to `origin/dev`.

Only `comparison_zip/policy.py`, its adversarial test, this report, its task and the D-262 row changed. No contract, migration, root dependency/lockfile, composition root, global style, portal reader, shared parser or infrastructure file changed.
