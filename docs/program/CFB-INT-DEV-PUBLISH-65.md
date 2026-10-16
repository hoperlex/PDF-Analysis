# CFB-INT-DEV-PUBLISH-65 — offline custody and boundedness guards

The published development predecessor is
`a09721a5895a0aff93d08f203fe1bedbbffffb8a` (dev64). Four disjoint source
commits were reviewed and cherry-picked: W58 FIFO mirror refusal
`9d01a939cc3d3563d5514300d2f5f962508e732a`, W56a seeded Run PDF
attestation `ed485d1c30f1c1618709d99d1db93cf120fca2cb`, W59 carryover
bounds `4a21a675bed82723275aaf1d0600da711eee113d`, and W56b selective
crop read `d7c9e8d02801102f5b0271ecc554a2d168210fef`.

## Result and checks

- W58 object seal and source-mirror retry open candidate paths without
  blocking on a FIFO and refuse nonregular objects. Both bounded regressions
  reproduced the hang before the fix.
- W56a's offline evaluator checks a published recorded Run, its immutable
  Version's single source PDF manifest entry, bounded saved Blob bytes and
  digest against one explicit seeded bundle. The original portal ZIP remains
  a separate local-fixture check.
- W56b checks every saved crop reference and complete portal/crop metadata,
  binds their source digest to the Version manifest, then opens, hashes and
  decodes only the selected PNG under current Attempt, Run, Version and stage
  fences. It makes no claim about unread sibling PNG bytes.
- W59 refuses more than 200 decision carryover matches or selected offers
  before per-item work; a valid 200-item batch is deterministic.
- Combined focused offline suites, ALR-05, programme governance and API
  documentation facts: **438 passed**. Five pytest warnings came from stale
  shared `/tmp/pytest-of-root/garbage-*` cleanup; no test failed.
- Source tasks: W58 **167 recovery + 16 governance**, W56a **27 focused +
  16 governance**, W56b **46 focused + 18 architecture/governance**, W59
  **103 comparison + 18 architecture/governance**. The W56a committed fixture
  check counted 10 bundles, 21 issues and 7 controls.
- Frozen API, stage registry, error catalogue and 0023 migration SHA-256s
  match dev64. Owned compilation, exact 25-path diff, whitespace, clean-tree
  handoff and remote fast-forward/readback are checked before publication.
  R-135 defers the complete beta `make gate`.

## Boundaries

No contract, migration, root dependency, composition root, global style,
served API/UI, provider, corpus, DB/S3, deployment workflow, `origin/main` or
tag changed. W56a has no measured model baseline or recorded response proof;
W56b has no model, citation, provider/effect or publication policy. W59's
future caller still needs an authoritative current snapshot and transactional
expert confirmation. W58's real recovery drill and W54's qualified DB/S3
corpus publication remain open. Host free disk and available memory were
below the 6 GiB restore floor during this integration. No beta or live
service acceptance is claimed.

Only the task's 25 exact allowed paths change. A reviewed forward commit is
the rollback route; no migration or runtime feature flag is involved.
