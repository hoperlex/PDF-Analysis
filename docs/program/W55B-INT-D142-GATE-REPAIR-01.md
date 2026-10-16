# W55B-INT-D142-GATE-REPAIR-01 — Attempt-specific publication assertion

## Finding

The fourth full `make gate` of clean W55b candidate `d3acd511c608dbff94d448b95ebb826cf5437c75` had no `GATE OK`: 4168 passed, one D-142 integration test failed, three skipped, then the changed-context battery was interrupted. The retained log is `.local/gates/w55b-main-repaired-d3acd511.log` in the candidate worktree, SHA-256 `0d509389c2db1968c3161b04edc533e39c35c8be3b44df5ef4c60d8f77d4b174`.

Read-only inspection of the retained gate database found two publication rows for the failed test's original Run `run_01M520GYYY97JSS2576FR08B2X` and Blob `blob_3EPGR9G9YR0B7JKVS3ZA1T2MX4`. The crashed Attempt `att_01M520GYZC9WYNKHR0QWEDJMP7` was `abandoned`; the durable carrier's next Attempt `att_01M520HP9MBYK7W9B69PE8R2GN` was `bound`. Both rows use stage `source_preparation` and role `prepared_page_inventory`. The source migration defines the primary key as `(attempt_id, stage_id, blob_id, blob_role)`. A Run and Blob alone do not identify a publication after reclaim.

## Change

The test now captures the crashed Attempt before expiring its lease and captures the separately started rerun's current Attempt after publication. The D-142 state checks query by the complete publication key. The adjacent live-Attempt assertion uses the same selector. Reconciliation-report, abandoned-event and Blob-availability checks remain intact.

Only the integration test and this task/report change. No production code, contract, migration, fixture, composition, dependency, release ref or tag changes.

## Verification

- Container-free collection: 20 tests in `test_durable_effect_boundaries.py` collected.
- Python compilation: passed.
- `git diff --check`: passed.
- Governance: `tests/contract/program/test_wave_governance.py` — 16 passed.
- Fresh isolated PostgreSQL/S3 lane `auditmanager-w55b-d142-repair-01` on ports 57480/61080/61081: `make up`, `make check-services migrate check-db check-storage` passed; migration head `0021_portal_bundles`.
- `pytest -q tests/integration/runs/test_durable_effect_boundaries.py -k d142`: 2 passed, 18 deselected in 5.56 seconds.
- `make down` stopped only this lane after validation; its disposable volumes remain available for a rerun.
- Complete `make gate` on the integrated exact candidate: integrator-owned and still required.

## Integration and limits

Cherry-pick the exact task commit into the main-release candidate. The D-142 test should pass whether the durable carrier reclaims the original Run or leaves it terminal before the assertion. This patch supplies no `origin/main` authority, deployment claim or successful full-gate evidence. The prior failed log cannot be counted as a gate pass.
