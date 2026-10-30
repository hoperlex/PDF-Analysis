# CMP-STAGE-TEXT-RECOMPUTE-01 — durable deterministic recomputation

Task: [`CMP-STAGE-TEXT-RECOMPUTE-01`](tasks/CMP-STAGE-TEXT-RECOMPUTE-01.md). The owner instructed on 2026-10-30 to finish functional code and publish dev today, deferring full gates and heavy windows to tomorrow. This lane ran only focused implementation checks.

## Implemented

- The expert-only keyed POST creates a durable `stage_chain_run` with deterministic steps 2 and 3 and enqueues a `stage_text_recompute` comparison work item in the same transaction. Exact replay returns the original run even after source changes; a second request while that revision has a live recompute receives that run. The work dedupe key contains the run ID, so completion before queue finalization cannot strand the next run.
- The registered worker reads complete ready profile archives, verifies pinned versions and the exact profile-list digest, computes connected sheet groups, and publishes the whole evidence batch under the work attempt's lease fence. It checks the current map and locks source document rows before validating latest versions. Missing archives, stale inputs and invalid evidence fail explicitly.
- Two-step runs are distinguished from future seven-step runs by their command type. The handler refuses a foreign project or another run type. A completed run seals a genuinely empty result; missing or failed evidence still refuses.
- The fragment GET is the immutable pair catalogue, allowing historical difference IDs to resolve after later map/version changes. Revision evidence reads require a completed deterministic run. Currentness comes from the selected run's pins/stale status, rather than deleting historical references from a read.
- Independent connected sheet groups are compared separately. The worker admits up to 512 pages and 20,000 fragments; each connected many-to-many group retains its explicit bounded comparison budget. Hints remain nonbinding; raw differences remain immutable.

## Focused evidence

- Stage Text and handler-registry unit checks: **33 passed**.
- Stage Text PostgreSQL, real HTTP and C3 composition checks: **78 passed**. These cover keyed enqueue/replay, one live run, worker completion, a true empty seal, missing archive, stale revision, atomic evidence, historical reads and the completed-run/before-work-finish race.
- One existing Starlette deprecation warning. Whitespace check passed. No full gate, whole-suite run or live model call was performed or claimed.

## Integration and limits

Merge after `CMP-STAGE-TEXT-READ-01`; the five Stage Text operations now serve under `versions,stages`. Full seven-step start/cancel/resume and browser masks remain the later C4/runtime/UI slices. Reverse-direction hints await the C4 seal. Large connected many-to-many groups can refuse their compute budget. Contract `1.12.0` and migration `0041` remain unchanged; shared changes are the owned adapter and handler registry only. No root lock, global style, deployment or remote ref was changed by this lane.
