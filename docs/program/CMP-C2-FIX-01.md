# CMP-C2-FIX-01 — C2 integration repair

Task: [`tasks/CMP-C2-FIX-01.md`](tasks/CMP-C2-FIX-01.md). Base: `8fcdda42`; frozen API `1.11.0` (176 paths, 198 operations, 517 schemas), migration `0040_comparison_ai_reports`.

## Result

- The contract surface census excludes the bundled report fonts. The two prose phrases that accidentally claimed an operation count were corrected.
- The comparison worker binds the frozen executor connection revision and pinned model of each live AI job through its private key ring and destination policy. Pair check, sheet changes, specification and report factories receive the route source. A missing revision, pin mismatch or unreadable secret is a typed refusal. Recorded jobs do not open a live connection.
- The launch handler creates its database collaborators when it runs, so registry enumeration is free of I/O. AI sheet-change and report entries persist their series ID before the estimate and keep that ID while awaiting consent and at execution.
- A paused AI job with `overrun` or `route_changed` exposes the estimate of work left through the ordinary estimate read. Its digest is accepted by resume.
- Pull routes carry a call context populated only after the spend journal's prepared row exists. The runner task names the comparison attempt and call. Before creating the task, the pull adapter publishes each checked crop through the durable blob publisher under the descriptor's content-addressed ID.

## Checks

| Check | Result |
| --- | --- |
| `tests/contract/api_v1/test_surface_counts_in_prose.py` | 33 passed (also included in the final focused run) |
| `tests/unit/comparison` before the final pull extension | 1661 passed, 1 warning |
| Final focused comparison unit and contract run | 106 passed |
| Final pull route, image publication and spend caller unit tests | 76 passed |
| `tests/integration/comparison` in one process, before the last queue, estimate and pull edits | 867 passed, 1 warning |
| Queue integration on the final code | 5 passed, including persisted `series_id` on both AI entries |
| AI jobs, pair and sheet integration after the estimate fix | 196 passed, 1 warning |
| Spend/work integration after the pull fix | 147 passed |
| Pull context against a real claimed PostgreSQL attempt | 1 passed |
| `tests/integration/composition` before the pull fix | 1218 passed, 4 skipped, then stopped on the exact process when the candidate expanded |
| Full final-code suites | assigned to the exact-candidate `make gate` in `CMP-WAVE-C2-INT` |
| `git diff --check` | clean |

The local database and object store were used for the integration runs. The test parent was `/tmp/pytest-cmp-c2-fix-01`; all test outputs stayed outside the repository.

## UI-02 assumptions checked

The pair hint identifies its page by version and page number; AI change boxes are expressed in the page A coordinate system. The paused estimate now describes work left. Draft reports and paused reports expose their estimates, and the report adapter accepts Markdown bytes and streams PDF bytes. The queue now provides `series_id` on sheet-change and report entries. Overview steps 4, 6 and 7 remain derived through per-row reads until a later contract wave.

## Contracts and ownership

No frozen contract or migration changed. The only shared composition edit is the worker's comparison route builder and its call site, owned by this integration task. No root lockfile, global styles, web source, infrastructure or other composition branch changed. The integration task `CMP-WAVE-C2-INT` will own `origin/dev`; this task has no remote publication authority. `origin/main` has no authorization.

## Known limits for the integrator

- Pull crop blobs have no long-lived business row that references them after a runner task expires. The blob reference audit may report them as unreferenced; the recovery owner must define retention or cleanup. No live external model or runner call was made in these tests.
- The sealed API has no consent-renewal command for a `needs_consent` launch entry. The UI starts the step from its own dialog; the queue entry remains awaiting consent. A new operation belongs to a later seal.
- The overview's steps 4, 6 and 7 and the specification reason/profile fields remain contract-shaped follow-ups. This task changes no deterministic comparison evidence.

## Integration instruction

Run the complete gate on a clean exact SHA; it is the final-code rerun of the broad suites above. Publish only to `origin/dev` under the explicit `CMP-WAVE-C2-INT` task if the gate prints `GATE OK`. Do not update `origin/main` without the owner's separate direct instruction.
