# CFB-INT-DEV-PUBLISH-53 — W57b XLSX diagnostic probe

The published development base is
`eaf58965cd8bedc229f464866e3d5768b1f05797`. The W57b source
`34b74ef0827da9078271ba1384e4757a8b8689f3`, based on dev47, was
cherry-picked without conflict as `fad2c095`. Its four paths are disjoint
from intervening W54, W56b and state-summary work. This integration adds
only its task and report.

The new unserved rehearsal script writes local rendered XLSX bytes to a
temporary directory, invokes a bounded isolated LibreOffice import and
compares both worksheet names and semantic nonempty cell values in the
converted workbook. It refuses formula elements, malformed input, import
failure and changed values. It does not expose an API or change the XLSX
writer.

## Checks and open acceptance

- Focused fake-runner and programme governance suites: **20 passed, one
  opt-in real LibreOffice test skipped**.
- Python compilation, frozen API SHA-256, exact six-path diff,
  `git diff --check` and clean-tree handoff are checked before publication.
  API SHA-256 remains
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`.
- The source task ran the opt-in real check three times with bounded profile,
  XDG and home isolation. All exited `1` before producing an imported
  workbook; the last two captured the `javaldx` warning. Peak process-tree
  RSS was about 163 MiB while host available RAM remained above 5 GiB.
  **W57b B3.5 remains failed/unverified.** These failures are not counted
  as a passing check or rerun during this integration.
- Remote fast-forward and exact-SHA readback are recorded after this report
  is committed. R-135 defers the complete beta `make gate`.

The current host does not distinguish LibreOffice setup failure from XLSX
incompatibility. A future task must resolve that cause and run the probe on
final export bytes. No qualified corpus, 0024 seal, XLSX route/role, actual
export or beta acceptance is claimed. No contract, migration, dependency,
composition root, global style, W54/W56 source, credential, deployment
workflow, `origin/main` or tag change is included. Only six task allowlist
paths change. A reviewed forward commit is the rollback route; no data
migration or runtime flag is needed.
