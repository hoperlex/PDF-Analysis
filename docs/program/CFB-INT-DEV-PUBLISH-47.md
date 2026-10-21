# CFB-INT-DEV-PUBLISH-47 — source-bound W54 export and W57b XLSX citations

The published development base is
`95de4f6b4e10a8b60f57ae84ab66156917c7b96c`. Reviewed source commits
`b616f85a` and corrected `50edcd0c` were cherry-picked without conflict
as `40077ecf` and `74eb8b82`. The superseded W57b source SHA `7217b1dc`
was not applied. The eight source paths are disjoint; this integration adds
only its task and report.

The W54 bundle exporter now verifies the `crops_index.json` bytes against
the supplied `SHA256SUMS` and compares the complete set of crop PDF paths
before creating an output or staging directory. A synthetic omission that
previously yielded four instead of five custody slots now refuses. A
read-only check found that the real W54 index and frozen listing agree on
all **28,246** crop paths. This does not replace full source file checksums,
the missing repair, embedding build or qualified DB/S3 publication.

The W57b adapter carries certified canonical and member citations into the
existing XLSX package source. A test reads actual `sheet2.xml` bytes and
finds both citation rows in the norm columns; explicit certified zero
leaves them blank. Reader provenance, consistent transaction, route/role,
0024 seal and real corpus remain future work.

## Checks

- Combined W54 export, W57b XLSX/package/preflight, citation-reader and
  programme governance selection: **103 passed**.
- Frozen API SHA-256 remains
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
  exact ten-path diff and `git diff --check` pass.
- Clean-tree technical handoff and remote ref readback are recorded after
  this report is committed. R-135 defers the complete beta `make gate`.

No public product contract, migration, root dependency, composition root,
global style, served API/UI, production DB/S3, credentials, deployment
workflow, `origin/main` or tag changes are included. No bundle publication,
XLSX download, beta acceptance or deployed v0.6.0 change is claimed.
