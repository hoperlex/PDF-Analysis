# CFB-INT-DEV-PUBLISH-62 — real saved W57b PDF text acceptance

The published development base is
`8c0dc0e708332e73bd3dc5defdae9fa97665f4ac`. The completed test source
`6a884f0ab88f8720c34ec2ba73d355b17509c507` was cherry-picked as
`cb89819f`. Its three additive paths do not overlap dev61. This integration
updates the first-read state and adds only its task and report.

The test uses committed `image_only_with_block.zip` through public Document
and Blob ports. The production executor saves and binds `prepared.text_layer`
under the current Attempt. The W57b reader then fetches exact Blob bytes
from S3, returns two empty PDF text pages for a Version with nonempty OCR
markdown, and the page bridge marks both pages unread. A forged execution
token refuses before S3 access. The test stops before provider dispatch; no
model call, provider effect or finding is persisted.

## Checks

- Source targeted real migration-0023 PostgreSQL/S3 acceptance:
  **1 passed in 1.15s**. Its isolated instance and two disposable volumes
  were removed afterward.
- Combined offline saved-text/page-bridge, programme governance and
  documentation fact suites: **128 passed**. Five warnings arose from
  cleanup of shared `/tmp/pytest-of-root/garbage-*` directories; there were
  no test failures.
- Python compilation, frozen API SHA-256, exact six-path diff,
  `git diff --check` and clean-tree handoff are checked before publication.
  API SHA-256 remains
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`.
- Remote fast-forward and exact-SHA readback are recorded after this report
  is committed. R-135 defers the complete beta `make gate`.

The test is synthetic and unserved. It does not establish a qualified W54
corpus, a W57b stage that publishes normative findings, B3.5 live export,
0024 or beta acceptance. No runtime, public contract, migration, dependency,
composition root, global style, W54/W56/W58 source, credential, deployment
workflow, `origin/main` or tag change is included. Only six task allowlist
paths change. A reviewed forward commit is the rollback route; no data
migration or runtime flag is needed.
