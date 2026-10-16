# CFB-INT-DEV-PUBLISH-51 — W56b source-digest custody

The published development base is
`ee70edaa56c30255558873cb9f0a777daa11ee58`. The completed W56b source
`adf43d6adb76c687e964062dc000087755ca74e4`, based on dev48, was
cherry-picked without conflict as `e25cbd3d`. Its four paths are disjoint
from the intervening state summary and W54 exporter correction. This
integration adds only its task and report.

The unserved saved OCR-region reader now requires one markdown and one
structured-companion source entry in the exact Version manifest. It checks
their role, media type, size, Blob identity and SHA-256 before derived Blob
reads, then compares the saved recognised-text and portal-block inner source
digests to those manifest entries. The second Attempt, Run, Version and
StageResult fence remains in place. A self-consistent derived Blob from a
different portal source now refuses instead of returning a candidate.

## Checks

- Saved OCR region, pure OCR candidate and programme governance suites:
  **63 passed**.
- Python compilation, frozen API SHA-256, exact six-path diff,
  `git diff --check` and clean-tree handoff are checked before publication.
  API SHA-256 remains
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`.
- Remote fast-forward and exact-SHA readback are recorded after this report
  is committed. R-135 defers the complete beta `make gate`.

The new tests use fake document and Blob ports. Matching manifest digests
establishes content identity, not original Blob availability or persisted
DB/S3 acceptance. No W56b citation/model/budget policy, finding write,
served route, corpus import or beta acceptance is claimed. No public
contract, migration, dependency, composition root, global style, W54/W57
source, credential, deployment workflow, `origin/main` or tag changes are
included. Only six task allowlist paths change. A reviewed forward commit
is the rollback route; no data migration or runtime flag is needed.
