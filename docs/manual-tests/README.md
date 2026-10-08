# Manual checkpoint tests

The manual runbook is required checkpoint evidence. Run it **after automated gates** from a clean checkout and local state, preferably with a tester other than the implementation author.

## General procedure

1. Checkout exact checkpoint candidate commit.
2. Record the commit SHA, contract versions, migration head, and tool/runtime versions.
3. Clean or create a separate local test namespace; do not use the author's accumulated database.
4. Run the documented bootstrap and development commands.
5. Follow the runbook from top to bottom.
6. For every step record `PASS/FAIL/BLOCKED`, the observed result, and a safe evidence reference.
7. Stop and clean up as the runbook directs.
8. Save the report using `MANUAL_TEST_REPORT_TEMPLATE.md`.

## Evidence rules

- Commit only synthetic or anonymized fixtures to Git.
- Do not commit tokens, cookies, presigned URLs, production documents, or raw provider payloads.
- A screenshot is acceptable only when it contains no sensitive data.
- For asynchronous failures, record `correlation_id` and `run_id/job_id/attempt_id`, without secrets.
- Manual success cannot compensate for a failing automated gate.

## Expected command surface after CP-01

The exact commands are selected and recorded in `W1-INT-00`, but their meaning must remain stable, for example:

```text
make bootstrap
make dev
make test
make test-contract
make test-integration
make test-e2e
make stop
```

Runbooks rely on what these commands do. If a different task runner is chosen, one CP-01 owner updates the documentation.
