# W56A-INT-RECORDED-PUBLICATION-GATE-01 — result

**Base:** `origin/dev=08055ca094a9c3e4676a5907a0b3020f0bee4fb8` plus
completed saved-plan bridge source `9bf35ca9a2d5bd9dfdbbd44028270d82ffe6bfbd`
(local cherry-pick `ce9238c2`). The branch is local and has no publication
authority.

## Result

An unactivated run-side gate reads the verified saved observation and merge
Blobs before acquiring the Run lock. It rechecks the registered five-stage
plan, source bindings and the sole completed recorded call, refuses existing
publication rows, then writes findings and terminalizes Run, Job and Attempt
within one caller-owned transaction. It calls `finish_execution` last, so the
Lease heartbeat remains free during finding writes. A failed or missing
required stage reaches `failed` without a finding write. Zero findings may
reach `published`; the terminal Run and finished Attempt, not the row count,
form the durable publication marker.

## Changed files

- `src/auditmanager/runs/recorded_v2_publication.py` — gate and terminal policy;
- `src/auditmanager/jobs/repository.py` — read-only completed recorded call facts;
- `src/auditmanager/findings/public.py` — public saved-plan/writer surface and
  preexisting-publication read;
- `tests/integration/jobs/test_recorded_v2_publication_gate.py` — transaction,
  failure and retry tests;
- `docs/program/tasks/W56A-INT-RECORDED-PUBLICATION-GATE-01.md` — task contract;
- this report.

## Checks

- focused saved-plan/v2 writer/merge suite: **34 passed**;
- container-free gate order/failure selection: **2 passed**;
- program governance suite: **16 passed**; direct task governance: `[]`;
- all six frozen SHA-256 inputs match the task; Python compilation and
  `git diff --check`: passed;
- real PostgreSQL/MinIO: pending an isolated test lane. The preexisting root
  `.env` points at an unavailable database; W55b's separate gate lane is
  running and must not be reused. The service suite now covers failed-stage
  finalization, observation-only prior rows, three saved-call/source provenance
  mutations, and a second transaction changing a StageResult during Blob read.
  A concurrent zero-finding contender must lose the terminal CAS after the
  first transaction commits.
  No service-backed acceptance is claimed yet.

## Contracts and limitations

No contract, migration or active executor change. Rejected proposals remain
diagnostics in the saved artifact and the returned count; this task creates no
diagnostic DB row. The served run path still uses its prior executor until a
separate activation grant. Callers must commit once after the gate returns or
roll back the complete transaction on error. A retry after a committed terminal
is refused before allocating IDs; the command/run read surface supplies the
persisted outcome.

StageResult UPSERT precedes `jobs.bind_artifacts` in the current stage writer.
Those calls must remain in one rollback-on-error transaction; a delayed bind
against a terminal Run then fails through current Attempt authority, rolling
back its earlier UPSERT. The gate rechecks committed stage rows under the Run
lock. This writer atomicity is an activation prerequisite.

## Integrator handoff

Integrate only after the saved-plan bridge on the exact dev candidate. Prove
the focused real PostgreSQL/MinIO tests at head `0022_findings_v2` before
claiming this task complete; then grant executor activation separately. The
gate branch touches only the six task-owned paths above. The earlier
cherry-pick contributes the seven bridge-owned paths without editing them.
