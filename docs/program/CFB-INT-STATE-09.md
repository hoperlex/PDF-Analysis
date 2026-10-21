# CFB-INT-STATE-09 — integrated preparation state

The current-state entry now records three local development commits:

- `b236b6bc` binds the recorded AR v2 request to versioned source artifacts and keeps a separate source-binding digest; 10 focused tests passed.
- `187654be` obtains XLSX display labels from a version-bound, verified portal companion; 33 focused tests passed. A durable per-finding citation source and export policy are still absent.
- `2a0a4d98` checks a local W54 dump, copy record, inventory and mirrored object bytes together before an isolated restore; 36 recovery tests passed. It performs no restore or S3 readback.

Only `CURRENT_STATE.md`, this report and the task were changed. No public contract, migration, application code, remote ref or deployment state changed in this documentation task. The three code tasks' own reports record their exact paths and tests.

Checks: frozen plan hash and migration head matched; direct task governance and exact-path/whitespace checks passed. No complete gate was run under R-135. W54 restore verification remains resource-gated; the last watcher ended with about 2 GiB of free disk rather than the required 6 GiB.

The integrator should retain these as unactivated preparations, continue the separately owned runtime and citation tasks, and remeasure W54's disk, RAM and CPU floors before the pending dump restore check. Rollback is a documentation revert.
