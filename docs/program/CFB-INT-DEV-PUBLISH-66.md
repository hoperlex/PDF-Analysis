# CFB-INT-DEV-PUBLISH-66 — bounded offline source and section checks

The published development predecessor is
`8c39b9e0dfd63da7d32d1a848e609ae2dd437a01` (dev65). Four disjoint
source slices were reviewed and integrated: W58 target listing bound local
commit `b8efe199`, W59 same-section pair
`ff33185a0b9366405cfa695379dbfe9ba149129a`, W56a local bundle binding
`c6d1d07713d58cff0f1933a4a2c4b90941d1e72c`, and W57b slug-list bound
`576bdefb78210e8cc252c4809885ba9a74c82fa6`.

## Result and checks

- W58's unactivated isolated target restore passes the sealed object count
  to every S3 listing. An oversized page or a chain of fresh, empty
  continuation tokens refuses; valid one-key pagination and retry work.
- W56a's offline evaluator checks the raw pinned seeded manifest and all ten
  local PDF/portal ZIP byte pairs, then joins one saved Run PDF attestation to
  the selected local bundle. The ZIP digest is local fixture evidence only.
- W57b's unserved reference chain checks an explicit slug tuple's basic
  shape, uniqueness and derived byte bounds before reading either Blob. After
  verified catalogue custody it also checks the snapshot document count;
  the catalogue validator still owns actual membership and pins.
- W59's pure comparison guard requires two exact ordered versions to share
  explicit P/R stage and confirmed section code. The future caller must
  establish saved expert confirmation and membership in the sealed catalogue.
- The combined focused offline suites, ALR-05, programme governance and API
  documentation facts passed: **593 passed**. A first broader command also
  collected one real PostgreSQL/S3 acceptance test; it failed because this
  lane has no `DATABASE_URL`. That test was excluded from the focused command
  and is not reported as passing. Five pytest warnings concern stale shared
  `/tmp/pytest-of-root/garbage-*` cleanup.
- Source tasks: W58 **185 recovery/governance**, W56a **27 focused + 18
  architecture/governance**, W57b **39 focused + 18
  architecture/governance**, W59 **178 comparison/sections + 18
  architecture/governance**. The frozen seeded generator check counted ten
  bundles, 21 issues and seven controls.
- Frozen API, stage registry, error catalogue and 0023 migration SHA-256s
  match dev65. Owned compilation, exact 19-path diff, whitespace, clean-tree
  handoff and remote fast-forward/readback are checked before publication.
  R-135 defers the complete beta `make gate`.

## Boundaries

No contract, migration, root dependency, composition root, global style,
served API/UI, provider, production corpus, DB/S3, deployment workflow,
`origin/main` or tag changed. W56a has no actual grounded plans, recorded
model response or measured baseline. W57b still lacks an independently
reviewed slug source and 0024 seal. W59 lacks persisted section
confirmations, an authorized reader and served comparison. W58's real
recovery drill and W54's qualified corpus publication remain open. Host disk
and available memory remained below the 6 GiB restore floor. No beta or
live service acceptance is claimed.

Only the task's 19 exact paths change. A reviewed forward commit is the
rollback route; no migration or runtime feature flag is involved.
