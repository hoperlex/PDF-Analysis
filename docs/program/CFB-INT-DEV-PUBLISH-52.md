# CFB-INT-DEV-PUBLISH-52 — W54 PDF slot ingress guard

The published development base is
`ef802c112cd2b61de5ee9aa701739b04eb2d7f36`. The completed W54 source
`281cf44918a5f1349a2d8aaa9dd04a45cb46264e`, based on dev50, was
cherry-picked without conflict as `2f82c1a9`. Its four paths are disjoint
from dev51's W56b reader and test. This integration adds only its task and
report.

The W54 importer now compares PDF custody slots in the validated manifest
with document rows' exact `(norm_document_id, source_document_ref)` pairs
before database or S3 access. The source task reproduced a prior refusal
gap with three self-consistently re-signed synthetic bundles: a missing,
wrong or extra PDF slot reached a forbidden database connection. Those
cases now refuse before storage access. The existing manifest guard already
rejects duplicate identical slots.

## Checks

- Bounded offline bundle and programme governance selection: **167 passed,
  20 deselected**. The source task separately reported 17 focused and 151
  offline bundle passes; a reversing mutation restored the forbidden DB
  connection in the new test.
- Python compilation, frozen API SHA-256, exact six-path diff,
  `git diff --check` and clean-tree handoff are checked before publication.
  API SHA-256 remains
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`.
- Remote fast-forward and exact-SHA readback are recorded after this report
  is committed. R-135 defers the complete beta `make gate`.

This structural guard does not prove source PDF byte provenance. Complete
source checksums, repair, embedding build, qualified bundle and DB/S3 import
remain open. No actual stand import, public contract, migration, dependency,
composition root, global style, W56/W57 source, credential, deployment
workflow, `origin/main` or tag change is included. Only six task allowlist
paths change. A reviewed forward commit is the rollback route; no data
migration or runtime flag is needed.
