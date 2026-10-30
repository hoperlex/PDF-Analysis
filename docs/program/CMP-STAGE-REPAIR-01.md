# CMP-STAGE-REPAIR-01

Implemented one-cycle HIGH deterministic automatic repair, immutable before/after proof, atomic effective revision update and reset of steps2–7. Undo writes a new expert revision and queues deterministic recomputation in the same transaction through the new `StageTextRecomputeService.start_in_session` seam. AI runs pause for renewed consent after undo. Later manual maps make repairs superseded and prevent stale undo.

Changed files: `comparison/stage_repair/service.py`, `comparison/stage_text/recompute.py`, `tests/integration/comparison/stage_repair/test_service.py`, task and this report.

Checks: focused PostgreSQL tests **2 passed**: actual automatic swap, proof/confidence, atomic undo/receipt replay and manual supersession. Compile and `git diff --check` passed. Full gates deferred by owner.

Contracts: consumes1.13.0/0042; no shared contract, migration, dependency, composition or style edits. Integration root wires `advance`, `page` and keyed `undo`. Raw evidence remains immutable.

Known limits: score matrix is capped4096; above that only title proof is considered and unchecked text scoring is explicit. Supersession is derived from latest map for reads/undo; previous events remain append-only. Module flag gates callers.
