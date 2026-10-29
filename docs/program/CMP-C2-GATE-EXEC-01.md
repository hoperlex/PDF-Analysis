# CMP-C2-GATE-EXEC-01 — executor list-boundary assertion repair

Task: [`CMP-C2-GATE-EXEC-01`](tasks/CMP-C2-GATE-EXEC-01.md). Frozen API `1.11.0` (176 paths / 198 operations / 517 schemas); migration head `0040_comparison_ai_reports`. The gate on clean `9d868e62` was red and was not published.

## Failure and repair

The full gate passed frontend **3,653**, contract **1,310**, foundation **35**, and changed-context integration **7,797 passed / 28 skipped / 244 subtests**, but two executor tests failed. The shared PostgreSQL test database had more than 500 executor connections after repeated gate runs. `ExecutorRepository.list_connections` deliberately returns at most 500, with archived connections ordered after active ones. The archive test therefore lost its new archived connection from the list page. It now reads the two connections by ID through `connection_detail` and still proves the surviving connection is routed and the archived one is not.

The worker-bootstrap test used the length of the same 500-row page to count two newly created connections. It now compares unbounded table counts before creation and after replay, while its existing identity, probe, route and image assertions remain. No executor application code, query limit or fixture state was changed.

## Verification

- Before edit, the two exact focused cases reproduced **2 failures**: the archived ID was missing from the list and the page lengths stayed at 500.
- After edit, both edited integration modules passed **35/35** on the shared C2 PostgreSQL stack.
- The complete gate on a new clean SHA is still required before any `origin/dev` fast-forward. The failed `9d868e62` gate had no `GATE OK` and gave no result for the canonical remainder.

Only `tests/integration/executors/test_executor_commands.py`, `tests/integration/executors/test_http_operations.py`, this report and its task changed. Contracts, migrations, application source, dependencies/lockfiles, composition root, global styles, infrastructure and remote refs were untouched. The module flag remains off by default.
