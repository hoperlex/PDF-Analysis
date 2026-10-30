# CMP-STAGE-RUN-01

Implemented durable single and ordered batch stage comparisons. Seven step receipts, immutable pins and effective repair revision survive worker restarts. Expert commands are keyed and audited; cancellation requests child work and shared AI cancellation in the caller transaction. Resume preserves completed receipts. Batch pause serialises with launch and stops new launches.

Changed files: `comparison/stage_run/{__init__,service,handler,batch}.py`, focused `tests/integration/comparison/stage_run/test_lifecycle.py`, task and this report.

Checks: focused lifecycle SQL tests **4 passed** on isolated PostgreSQL at migration0042. They cover keyed replay, deterministic child receipts and full progression, cancellation/resume and batch controls. Compile and `git diff --check` passed. No full gate or heavy window; deferred by owner to2026-10-31.

Contracts: consumes1.13.0/0042; no shared contract, migration, lockfile, composition or global style edits. Root must export and wire chain/batch factories, API adapters and inject AI, repair, graphics and review. No remote publication from this lane. Module flag gates commands and claims; completed evidence is retained.

Known limits: full browser acceptance and integrated provider progression remain tomorrow’s work. Handler deliberately pauses when a required provider is absent.
