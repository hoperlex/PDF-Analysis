# CFB-INT-DEV-PUBLISH-61 — saved W57b text and XLSX import evidence

The published development base is
`2fe82f40f4ac2bf82f9778c28b2fd2a2b8e8deab`. The completed saved-text
source `f581e7fc78e4235d0a936e0ee2f09a3bb5a0db93` was cherry-picked as
`e1132a6c`; the immutable synthetic LibreOffice acceptance addendum
`233c6e9cf570e1949f0d5bb9be4b6a6b59e97604` was cherry-picked as
`52101d7a`. Their eight paths are disjoint. This integration updates the
first-read state and adds only its task and report.

The new unserved reader loads one saved `prepared.text_layer` from a current
Run/Attempt under a caller-owned transaction. It checks Version identity and
page count, the succeeded source StageResult, an explicit Blob byte ceiling,
exact size/SHA-256 and canonical JSON, then repeats Attempt and persisted-row
checks. A pure validator was factored from W56b's text-window preparation;
W56b still partitions only after that validation. The reader returns the
validated text layer and independent Version facts for the W57b page bridge.

The XLSX addendum records two successful real LibreOffice imports outside
sandbox, including the deterministic W57b workbook with all 54 nonempty
cells equal after reimport. The unchanged opt-in test passed in 0.95 seconds.
The original three constrained failures remain in the historical report; the
same `javaldx` warning appeared in successful runs. This establishes only
the independent **synthetic** import/cell probe.

## Checks

- Combined W57b saved-text, existing W56b text, page bridge, XLSX probe
  offline, programme governance and documentation fact suites:
  **173 passed, 1 deselected** (the opt-in real LibreOffice test). Five
  warnings arose from cleanup of shared `/tmp/pytest-of-root/garbage-*`
  directories; there were no test failures.
- The source addendum ran that opt-in test outside sandbox on unchanged
  probe/test bytes: **1 passed in 0.95s**. The script/test SHA-256 values
  remain `b5800e371fea6c51a2d8912837f4ba451b5ede49d250530de4dc769eb79472f9`
  and `b35d28f22ba5318a3ae79fa5fd91707ca7c15c22b0dd9ef2dbbb4654a55acb69`.
- Python compilation, frozen API SHA-256, exact eleven-path diff,
  `git diff --check` and clean-tree handoff are checked before publication.
  API SHA-256 remains
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`.
- Remote fast-forward and exact-SHA readback are recorded after this report
  is committed. R-135 defers the complete beta `make gate`.

The saved-text reader uses fake ports in its focused tests; real DB/S3
custody and served W57b publication remain open. The synthetic LibreOffice
probe does not establish the B3.5 live export, role, final rendered bytes or
qualified corpus. W57b 0024 and beta acceptance remain open. No public
contract, migration, dependency, composition root, global style, W54/W56/W58
source, credential, deployment workflow, `origin/main` or tag change is
included. Only eleven task allowlist paths change. A reviewed forward commit
is the rollback route; no data migration or runtime flag is needed.
