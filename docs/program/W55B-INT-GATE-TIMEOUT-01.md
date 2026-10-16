# W55B-INT-GATE-TIMEOUT-01 — serving-carrier gate timeout correction

## Diagnosis

The clean `6d63802ab465a0317839c9b57abd5e90f3d91769` candidate's third full gate failed at `test_serving_lifespan_dispatches_an_ordinary_run_adapter_submission`: `gated.entered.wait(timeout=30)` returned false. The gate had reached 2,196 passed, 3 skipped and this one failure. Its dedicated PostgreSQL/S3 volumes were fresh. A read-only query of that gate's PostgreSQL database linked the failed fixture's project `prj_01M51W079RX6CMMF72DEP86Q5C` to Run `run_01M51W07FWNFJVXDA1HGG6N21C`.

The worker claimed that Run about one second after creation. `source_preparation` took 18,761 ms and `page_geometry_extraction` took 19,160 ms. `text_analysis` began only at 08:07:45.520 UTC, after those stages and after the 30-second wait. The Run then published, with its Job and Attempt succeeded. Eight source-preparation stage rows in the gate database ranged 17,484–21,983 ms; eight geometry rows ranged 17,807–21,774 ms. The test deadline could expire before the provider barrier was reached even with a functioning dispatcher. This is the observed cause of this failure; the full gate has no `GATE OK` on this SHA.

## Change

The single serving-lifespan assertion now waits up to 120 seconds for the same event. If it expires, it includes the authenticated public Run status in the assertion, including completed stages. Its existing `finally` still releases the provider barrier and restores parked Jobs. No other deadline, production path, or contract changed.

## Verification

| Check | Result |
| --- | --- |
| `pytest -q tests/contract/program/test_wave_governance.py` | 16 passed |
| `pytest --collect-only -q tests/integration/composition/test_the_run_leaves_the_request_thread.py::test_serving_lifespan_dispatches_an_ordinary_run_adapter_submission` | 1 collected |
| Python AST parse of changed test | passed |
| `git diff --check` | passed |

The database-backed test and complete `make gate` are reserved for the integrator's dedicated service lane. No service or Docker container was started by this task.

## Integration and rollback

Cherry-pick the single clean commit onto the W55b main candidate, then run the changed test against its dedicated PostgreSQL/S3 lane and a complete `make gate` on the exact final SHA. This task has no publication authority and makes no deployment claim. If the changed test still times out, use its Run status and stage list to identify where progress stopped rather than increasing the bound again without evidence.

Rollback is a revert of this test-only commit. No migration, data repair, feature flag or recovery command is needed.

## Path and contract proof

The changed tracked paths are this report, its task and `tests/integration/composition/test_the_run_leaves_the_request_thread.py`. `contracts/**`, migrations, root dependencies and lockfiles, composition root, global styles, `CURRENT_STATE.md`, provider recordings, refs and tags are untouched. There are no new or modified contracts.
