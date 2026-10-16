# W57B-INT-CATALOGUE-DB-S3-ACCEPT-01 — real catalogue custody acceptance

Base `85d9936a8faacc00df3687b32ba51797439f2736` (`origin/dev` dev58).
The focused test runs `load_verified_catalogue` against real migration-0023
PostgreSQL and S3. It creates a synthetic one-document verified set with a
complete one-window embedding build, two confirmed custody bindings, available
Blob metadata and actual set/catalogue objects. The Run has a current
Job/Attempt/Lease. The returned bytes equal the canonical catalogue, the
SHA-256 and pinned snapshot facts match, and the pure catalogue validator
accepts them. A forged token is rejected with `EXECUTION_TOKEN_INVALID` and a
noncurrent Attempt with `STALE_ATTEMPT`, both before any S3 object read.

## Checks

- `make up` and `make migrate` on isolated instance
  `auditmanager-w57b-cat-accept-01`: passed, revision `0023_norm_citations`.
- Targeted real PostgreSQL/S3 test after the final test assertions:
  **1 passed in 0.77s**.
- Python compilation: passed. Frozen API, stage registry, domain IDs, errors,
  migration and catalogue-query SHA-256 values matched the task.
- Task governance: **16 passed**, with five concurrent pytest `/tmp` cleanup
  warnings. Exact-path and whitespace checks are recorded at handoff.
- Full `make gate`: deferred by R-135 for the intermediate code candidate.
- `make down` stopped only the assigned instance; its two disposable volumes
  were removed. The temporary S3 bucket was deleted by the test itself.

## Changed files

- `tests/integration/norms/references/test_catalogue_input_db_s3_accept.py`
- `docs/program/tasks/W57B-INT-CATALOGUE-DB-S3-ACCEPT-01.md`
- `docs/program/W57B-INT-CATALOGUE-DB-S3-ACCEPT-01.md`

## Limits and integration

This proves the reader's real SQL joins, Blob stream, exact byte digest and
current Attempt fencing for synthetic data. It does not prove a qualified W54
corpus, reviewed unparsed-slug inventory, served W57b route, 0024 schema,
reference-resolution result, XLSX B3.5 or beta acceptance. It is one
transactional local run, not a cross-process lease-expiry drill.

Integrate only the three-file test commit after dev58. No runtime, contract,
migration, composition root, root dependency, UI or remote ref changed.
Rollback is deletion of the three files; no product data migration applies.
