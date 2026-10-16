# CFB-INT-DEV-PUBLISH-60 — W57b real catalogue and text pages

The published development base is
`2b0a8a04a7ef2ce050e3ec3df9dd5414c68651be`. The completed real-service
test `ab956e94e0c150498d9e0b8140f8a5335569b9cb` was cherry-picked as
`dfad863a`; the completed pure page bridge
`6ebecf347348a212a2fa9c8c9f5c16e7fe9e5546` was cherry-picked as
`fa49ec18`. Their seven additive source paths do not overlap. This
integration updates the first-read state and adds only its task and report.

The W57b catalogue reader passed a targeted test with real migration-0023
PostgreSQL and S3: a synthetic verified set, both confirmed custody bindings,
canonical catalogue bytes and current Run/Attempt/Lease were used. The test
checked exact bytes, SHA-256 and pinned facts, then verified that a forged
token and a stale Attempt refuse before S3 reading. The pure page bridge maps
the saved text layer to ordered `ReferencePage` values and checks the caller's
Version and page count, Unicode offsets and exact document concatenation.
An empty text-layer page remains unread without shifting later evidence.

## Checks

- Source real PostgreSQL/S3 acceptance on isolated 0023 instance:
  **1 passed in 0.77s**. The source test removed its temporary bucket, and
  the isolated instance and disposable volumes were removed afterward.
- Combined offline catalogue, text-page, reference-pipeline, programme
  governance and documentation fact suites: **143 passed**. Pytest emitted
  five warnings while cleaning shared `/tmp/pytest-of-root/garbage-*`
  directories; there were no test failures.
- Python compilation, frozen API SHA-256, exact ten-path diff,
  `git diff --check` and clean-tree handoff are checked before publication.
  API SHA-256 remains
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`.
- Remote fast-forward and exact-SHA readback are recorded after this report
  is committed. R-135 defers the complete beta `make gate`.

The real-service test uses synthetic data and does not qualify the W54
corpus. The bridge trusts its caller to supply authenticated text bytes and
independently pinned Version facts; no served W57b caller or finding
publication is added. Reviewed unparsed slugs, 0024, B3.5 and beta
acceptance remain open. No public contract, migration, dependency,
composition root, global style, W54/W56/W58 source, credential, deployment
workflow, `origin/main` or tag change is included. Only ten task allowlist
paths change. A reviewed forward commit is the rollback route; no data
migration or runtime flag is needed.
