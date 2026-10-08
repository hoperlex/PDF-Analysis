# W52-DEBT-CODE-128F10 — executor handoff

Task: `docs/program/tasks/W52-DEBT-CODE-128F10.md`. Exact code base:
`bd7cb62a70e758c4b88c44e8e664ddfb90977cb3`; dispatch commit `ffe20ab`.
This repairs D-128 F-10 only.

`ReconciliationReport` now carries one `unattributed_blobs` category for Blob rows
without manifest or Attempt-scoped analysis intent. The dead `orphan_objects` and
`unpublished_records` fields and their `OrphanObject` type are removed. The replacement
`UnattributedBlob` name does not infer a pre-0014 origin: current document uploads
interrupted before version commit enter the same category. Available but detached
rows now use a point `head_object` check instead of always claiming their bytes exist.
`reject_unpublished` still refuses a row without Attempt authority; its existing
refusal token is retained, avoiding a separate error-detail change.

Changed files: `src/auditmanager/ingest/reconciliation.py`,
`src/auditmanager/ingest/__init__.py`,
`tests/integration/ingest/test_reconciliation.py`,
`tests/integration/ingest/test_reconciliation_rules_with_no_guard.py`,
`tests/integration/runs/test_durable_effect_boundaries.py`,
`tests/unit/ingest/test_reconciliation_report.py`, and this report.

Basic checks: the pure report test passed (1/1), Python compilation of all changed
Python files passed, frontend lint passed, and `git diff --check` passed. The edited
PostgreSQL/MinIO integration tests were not run because the owner deferred temporary
stand and QA evidence under D-139; the full gate remains D-140. Their updated cases
cover interrupted current uploads, missing objects and available rows whose bytes
have disappeared.

No wire contract, migration, dependency/lock, router, composition root or global
style changed. This does change the internal Python report field and public export;
the repository's consumers were updated, but an untracked external importer would
need to use `UnattributedBlob`/`unattributed_blobs`. The integrator may merge this
clean branch to `origin/dev` after exact ancestry and basic checks. Rollback is the
code commit's revert; no feature flag.
