# CFB-INT-DEV-PUBLISH-50 — W54 duplicate source custody

The published development base is
`04ffe00ee9fa81dac1f1009ebd0c674307d975bd`. The completed W54 source
`3b28e265e988f20a82ac02fc62e45c7575ecf3ab`, based on dev47, was
cherry-picked without conflict as `51bb3881`. Its four paths are disjoint
from the intervening W56b and state-summary integration. This task adds
only its task and report.

The exporter previously accepted a second source path with an expected SHA
already present in its object map without reading that second file. The
source task reproduced that defect on a synthetic changed PDF/crop path.
Now each duplicate-digest source path is hashed before it receives a custody
slot; a missing or changed path refuses, while equal bytes still share one
bundle object. This protects the local export boundary but does not replace
the operator's complete source checksum run.

## Checks

- Bounded offline bundle and programme governance selection: **164 passed,
  20 deselected**. The source task separately reported 18 focused and 148
  offline bundle passes plus a reversing mutation that failed the new test.
- Python compilation, frozen API SHA-256, exact six-path diff,
  `git diff --check` and clean-tree handoff are checked before publication.
  API SHA-256 remains
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`.
- Remote fast-forward and exact-SHA readback are recorded after this report
  is committed. R-135 defers the complete beta `make gate`.

Repeated source files incur one additional read. No actual W54 bundle,
repair, embedding checkpoint, DB/S3 import or beta acceptance is claimed.
No contract, migration, dependency, composition root, global style, W56/W57
source, credential, deployment workflow, `origin/main` or tag changes are
included. Only the six task allowlist paths change. A reviewed forward
commit is the rollback route; no data migration or runtime flag is needed.
