# CMP-C2-GATE-REM-01 — canonical remainder repair

Task: [`CMP-C2-GATE-REM-01`](tasks/CMP-C2-GATE-REM-01.md). Frozen API `1.11.0` (176 paths / 198 operations / 517 schemas); migration head `0040_comparison_ai_reports`. The full gate on clean `531f9cb0` was diagnostic red and was not published.

## Failure and repair

Frontend lint/typecheck and all **3,653** Vitest tests, contract **1,310** with 19,283 subtests, foundation **35**, and changed-context integration **6,593 passed / 12 skipped / 244 subtests** passed. The canonical remainder then showed one executor journey assertion that assumed its new `text_analysis` route was the first item in the installation's route list. A pre-existing C2 `comparison_pair_check` route preceded it. The test now selects the `text_analysis` route by work kind and proves its primary connection is the connection this journey just created. Its own connection detail, response-shape and secret checks are unchanged.

The same remainder showed 12 setup errors in `tests/integration/exports/test_xlsx_v3_run.py`, all from its reused `probe_database` fixture. That fixture spawned `python -m alembic` with a clean environment and no `PYTHONPATH`; the child could not import this checkout's `auditmanager` package. It now passes only this checkout's absolute `src` path to that child. The disposable database still migrates to `head`; no migration, application bootstrap or export assertion changed.

The remainder was interrupted after these diagnostic failures (**2 failed, 1,647 passed, 23 skipped, 12 errors** at the stop). Its second failure, an HTTP comparison-upload `CancelledError`, happened after SIGINT. A focused repeat of that exact HTTP test without interruption passed **1/1**, so it is not counted as a confirmed product failure. The interrupted run gives no claim about the unexecuted canonical tests.

## Verification

- Before edit: executor journey **1 failed** on route ordering; XLSX fixture **1 setup error** with `ModuleNotFoundError: auditmanager`.
- After edit: executor journey **1 passed**; full XLSX export module **12 passed**; both edited modules together **28 passed**. The HTTP repeat passed **1**.
- Task governance **16 passed** before source edit; final governance and `git diff --check` are recorded in the task Handoff.
- A new clean publication commit needs another complete `make gate` with literal `GATE OK`; no C2 development ref is updated by this repair task.

Only `tests/integration/executors/test_executor_surface.py`, `tests/integration/runs/test_v3_saved_text_layer_probe.py`, this report and its task changed. The frozen contracts, migration head, application source, root dependencies/locks, composition root, global styles, infrastructure and remote refs were untouched. The module flag still defaults to `none`.
