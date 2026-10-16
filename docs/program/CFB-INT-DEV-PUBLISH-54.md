# CFB-INT-DEV-PUBLISH-54 — W54 semantic row ingress guard

The published development base is
`110d632343b35d77b9d55a5c8ae453bbeca14ef5`. The completed W54 source
`2396a9e437830660ae8e3140d8e6ab4ff18a7755`, based on dev52, was
cherry-picked without conflict as `ecea566d`. Its five paths are disjoint
from dev53's W57b diagnostic tool. This integration adds only its task and
report.

The bundle importer now calls the existing complete
`validate_snapshot_rows` function after reading and hashing rows but before
any DB/S3 action. A checksum-consistent bundle with forged paragraph count
reached a forbidden database connection in the source task's pre-change
reproduction; it now refuses with internal `bundle_rows_invalid`. The
source task also corrected its synthetic fixture from unsupported paragraph
kind `clause` to the declared `body` kind, so normal fixture rows pass the
same validator. Transactional validation remains in place.

## Checks

- Bounded offline bundle and programme governance selection: **169 passed,
  20 deselected**. The source task separately reported 19 focused and 153
  offline passes plus a reversing mutation that restored the forbidden DB
  connection.
- Python compilation, frozen API SHA-256, exact seven-path diff,
  `git diff --check` and clean-tree handoff are checked before publication.
  API SHA-256 remains
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`.
- Remote fast-forward and exact-SHA readback are recorded after this report
  is committed. R-135 defers the complete beta `make gate`.

The source tests use tiny synthetic bundles and a forbidden-storage fake.
They do not prove source PDF bytes, real stand DB/S3 import, repair, embedding
build or qualified corpus publication. No public contract, migration,
dependency, composition root, global style, W56/W57 source, credential,
deployment workflow, `origin/main` or tag change is included. Only seven
task allowlist paths change. A reviewed forward commit is the rollback
route; no data migration or runtime flag is needed.
