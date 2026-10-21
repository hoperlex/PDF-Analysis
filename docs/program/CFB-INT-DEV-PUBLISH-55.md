# CFB-INT-DEV-PUBLISH-55 — W57b certified XLSX chain

The published development base is
`100307cecc47056005d79e388b2dde1a8e4c99ed`. The completed W57b source
`1adf7a6a1ad20048b15e154a3dd79d88685e555a`, based on dev53, was
cherry-picked without conflict as `28452a98`. Its four paths are disjoint
from dev54's W54 importer and fixture changes. This integration adds only
its task and report.

The unserved XLSX use case now composes the existing Run/page preflight,
injected findings-public certified citation read, citation source projection
and package renderer inside a caller-owned read transaction. It checks the
persisted Run, Version, state, profile, normative snapshot and retrieval set
against the preflight and citation read and rereads the Run pin before
returning bytes. It does not authorize the caller, open a transaction or
serve an HTTP route.

## Checks

- New composition, certified sources, XLSX package and programme governance
  suites: **49 passed**. Pytest emitted five warnings while cleaning unrelated
  shared `/tmp/pytest-of-root/garbage-*` directories; there were no test
  failures.
- Python compilation, frozen API SHA-256, exact six-path diff,
  `git diff --check` and clean-tree handoff are checked before publication.
  API SHA-256 remains
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`.
- Remote fast-forward and exact-SHA readback are recorded after this report
  is committed. R-135 defers the complete beta `make gate`.

The tests use controlled inputs and inspect real XLSX package bytes, but do
not establish live Run/Blob custody, qualified corpus or authorized download.
The W57b 0024 seal, route/role and independently passing LibreOffice B3.5
probe remain open. No public contract, migration, dependency, composition
root, global style, W54/W56 source, credential, deployment workflow,
`origin/main` or tag change is included. Only six task allowlist paths
change. A reviewed forward commit is the rollback route; no data migration
or runtime flag is needed.
