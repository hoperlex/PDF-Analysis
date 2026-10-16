# Task W55B-INT-D142-GATE-REPAIR-01 — identify D-142 publication by Attempt

## Outcome

The D-142 integration test verifies settlement of the crashed Attempt even when the durable carrier claims the same Run again before the assertion.

## Depends on

- `W54-WORKER-01` (durable carrier and reclaim path).
- `W55B-SEAL-01` (frozen W55b contracts and migration `0021_portal_bundles`).
- `W55B-INT-CLOSE` (development candidate).
- `W55B-INT-GATE-TIMEOUT-01` (exact test-only base candidate).

## Frozen inputs

- Base commit: `d3acd511c608dbff94d448b95ebb826cf5437c75`.
- Domain candidate revision 12; API 47 paths / 54 operations / 123 schemas; error catalog 24.
- Analysis, comparison and event contracts as sealed by `W55B-SEAL-01`.
- Migration head: `0021_portal_bundles`.
- Fourth full `make gate` log: `.local/gates/w55b-main-repaired-d3acd511.log`, SHA-256 `0d509389c2db1968c3161b04edc533e39c35c8be3b44df5ef4c60d8f77d4b174`; no `GATE OK`, 4168 passed / 1 failed / 3 skipped before interruption.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the base D-142 helper queries only Run and Blob and fails with `.one()` when reclaim creates another Attempt-scoped row

### P-01 — the failed assertion selected an incomplete identity

- captured_at: 2026-10-16
- command: `git show d3acd511c608dbff94d448b95ebb826cf5437c75:tests/integration/runs/test_durable_effect_boundaries.py | sed -n '844,855p'`
- captured_output:
  ```text
  def _publication_state(factory, run_id: str, blob_id) -> tuple[str, bool]:
      with factory() as observer:
          state, abandoned_at = observer.execute(
              text(
                  "SELECT state, abandoned_at FROM analysis_artifact_publication "
                  "WHERE run_id = :run_id AND blob_id = :blob_id"
              ),
              {"run_id": run_id, "blob_id": str(blob_id)},
          ).one()
      return str(state), abandoned_at is not None


  ```
- interpretation: the base helper assumes one publication per Run and Blob. The retained gate database instead contains two rows for the failed test's Run and Blob: original Attempt `att_01M520GYZC9WYNKHR0QWEDJMP7` was `abandoned`; reclaimed Attempt `att_01M520HP9MBYK7W9B69PE8R2GN` was `bound`. The schema's primary key is Attempt-scoped, so both rows are valid. The rerun reached `published` before this assertion.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `tests/integration/runs/test_durable_effect_boundaries.py`
- `docs/program/tasks/W55B-INT-D142-GATE-REPAIR-01.md`
- `docs/program/W55B-INT-D142-GATE-REPAIR-01.md`

## Forbidden hotspots

- `contracts/**`, migrations, root dependencies and lockfiles, composition root, global styles, other tests and fixtures, `CURRENT_STATE.md`, release refs and tags.

## Non-goals

- No change to production reconciliation, reclaim, Blob identity or publication schema.
- No test-data reset, contract reseal or deployment.

## Deliverables

- Attempt-specific D-142 test assertion and focused validation.
- Short evidence and verification report.

## Required tests

- Run the repaired D-142 test against a disposable PostgreSQL/S3 lane after the integrator releases resources.
- Run focused module/container-free collection, governance checks and `git diff --check`.
- The integrator runs complete `make gate` on the exact resulting main candidate; this task does not claim a gate result.

## Integration contract

The test records the original crashed Attempt before lease reclaim and checks its publication row by the complete Attempt-scoped key. It separately checks the successful rerun's current Attempt. A later carrier claim of the original Run cannot make either assertion ambiguous.

## Failure/idempotency/security cases

- A publication missing for the captured Attempt still fails; an incorrect state or absent abandonment timestamp still fails.
- The existing reconciliation report and artifact-abandoned event checks remain.
- No secrets or object-store bytes are copied into task evidence.

## Rollback / feature flag

- Revert this test-only commit; no feature flag or data migration is required.

## Handoff

- The integrator cherry-picks the exact clean commit and reruns the full gate before considering publication.
