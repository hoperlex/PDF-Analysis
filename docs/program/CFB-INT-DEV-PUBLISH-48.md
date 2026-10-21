# CFB-INT-DEV-PUBLISH-48 — saved OCR region evidence on dev

The published development base is
`394a728f8a6f64ecb849f98fccdad687b79f282a`. The completed W56b source
`ca1696fe16f51ebd9c754f90ecaaf920797a3c24`, based on dev46, was
cherry-picked without conflict as `8da19305`. Its five paths are disjoint
from dev47's W54/W57b paths; this integration adds only its task and report.

The new unserved read-only service obtains one Run's saved recognised-text
and portal-block documents from successful source and geometry stages. It
validates their references, aggregate size, Blob bytes and canonical document
identity, binds a quote to a checked OCR region on a stored textless page,
then repeats the Attempt, Run, Version and both StageResult checks. The
caller retains the transaction and must perform a fresh authority check
before any later effect. Narrow exports expose the completed pure binder
through `analysis.public`.

## Checks

- New saved OCR region, pure binder, analogous saved TEXT/crop, analysis
  boundary and programme governance suites: **79 passed**.
- Python compilation, frozen API SHA-256, exact seven-path diff,
  `git diff --check` and clean-tree technical handoff are checked before
  publication. The API SHA-256 remains
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`.
- Remote ref fast-forward and exact-SHA readback are recorded after this
  report is committed. R-135 defers the complete beta `make gate`.

The source tests use fake Run, Version, Job and Blob ports. They do not
establish persisted DB/S3 acceptance. The reader checks outer Blob references
and canonical documents, not the original portal markdown or block-list
members named by inner digest fields. No citation status, provider model,
cost policy, finding write, served route, corpus import or beta acceptance is
claimed. No public contract, migration, dependency, composition root, global
style, production DB/S3, credential, deployment workflow, `origin/main` or
tag changes are included. The only changed files are the seven task allowlist
paths; the unserved additive code can be corrected with a forward commit.
