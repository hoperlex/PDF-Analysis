# CFB-INT-DEV-PUBLISH-58 — W56b persisted OCR and W57b catalogue custody

The published development base is
`44a2ceec616b8f03194080d4d117dfeec9e0e8ef`. The completed W56b source
`a1d90d207f7e15ba31cc4d0894248d7b0a1c4a58` was cherry-picked as
`7b2036d0`; the completed W57b source
`6380e3af39073aaa8258874ec43cf34da030c9a1` was cherry-picked as
`cd12fe4d`. Both are additive, disjoint from each other and the W54 dev57
guard. This integration adds only its task and report.

The W56b test exercises a saved OCR quote and region from a current running
Attempt with real PostgreSQL StageResults and two S3 Blobs, and checks that a
forged execution token refuses. The test stops before provider dispatch and
does not change runtime code. The W57b reader checks the verified retrieval
set, pinned snapshot, confirmed catalogue custody, Blob metadata and bounded
object bytes, then repeats Attempt and SQL pin checks before returning data
and independent facts to the existing pure catalogue validator. It remains
unserved.

## Checks

- The W56b source ran its targeted real PostgreSQL/S3 acceptance on an
  isolated migrated 0023 instance: **1 passed in 1.32s**. That disposable
  instance and volumes were removed after the test. Earlier host setup
  failures occurred before test execution and are recorded in its source
  report.
- The combined W57b catalogue input/query and programme governance suites:
  **47 passed**. Five warnings arose from cleanup of shared
  `/tmp/pytest-of-root/garbage-*` directories; there were no test failures.
- Python compilation, frozen API SHA-256, exact nine-path diff,
  `git diff --check` and clean-tree handoff are checked before publication.
  API SHA-256 remains
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`.
- Remote fast-forward and exact-SHA readback are recorded after this report
  is committed. R-135 defers the complete beta `make gate`.

The W56b test does not prove cross-process lease expiry or served OCR
citations. W57b reader tests use fake ports; real 0023 PostgreSQL/S3 custody
for the catalogue, a qualified W54 corpus, 0024, B3.5 and an authorized
download remain unverified. No public contract, migration, dependency,
composition root, global style, W54/W58 source, credential, deployment
workflow, `origin/main` or tag change is included. Only nine task allowlist
paths change. A reviewed forward commit is the rollback route; no data
migration or runtime flag is needed.
