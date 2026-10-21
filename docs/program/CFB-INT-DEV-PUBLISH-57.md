# CFB-INT-DEV-PUBLISH-57 — W54 build ingress

The published development base is
`1b2da15da657c6eade0b87739478bde0e5001e94`. The completed W54 source
`58a7ab6f6170cab89f6d92fb3bb6cd8243cfc4d5`, based on dev54, was
cherry-picked without conflict as `05234105`. Its four paths do not overlap
the intervening W57b composition or state documentation. This integration
adds only its task and report.

The bundle importer now streams the complete verified embedding build before
its first DB or S3 operation. It checks document references, canonical order,
vector units, chunk and window counts, and the declared embedding-set digest.
The existing transactional build insertion and readback still run after
custody. This makes a self-consistently re-signed malformed build refuse
before an external effect.

## Checks

- Bounded offline bundle and programme governance suites: **172 passed, 20
  deselected**. Pytest emitted five warnings while cleaning shared
  `/tmp/pytest-of-root/garbage-*` directories; there were no test failures.
- Python compilation, frozen API SHA-256, exact six-path diff,
  `git diff --check` and clean-tree handoff are checked before publication.
  API SHA-256 remains
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`.
- Remote fast-forward and exact-SHA readback are recorded after this report
  is committed. R-135 defers the complete beta `make gate`.

The test bundle is synthetic. The real corpus build has not been parsed in
this candidate; this guard adds a second streaming build pass during import,
whose elapsed time remains unmeasured on the complete corpus. No qualified
snapshot, paid repair, real DB/S3 import or corpus publication is claimed.
No public contract, migration, dependency, composition root, global style,
W56/W57 source, credential, deployment workflow, `origin/main` or tag change
is included. Only six task allowlist paths change. A reviewed forward commit
is the rollback route; no data migration or runtime flag is needed.
