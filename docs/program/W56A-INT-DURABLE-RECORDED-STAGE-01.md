# W56A-INT-DURABLE-RECORDED-STAGE-01 — recorded stage port

## Result

`run_recorded_v2_stage` is an unactivated port for a saved, running AR v2
recorded run under current Job/Attempt authority. It loads verified source
artifacts before taking Attempt row locks; then it commits a call intent before
the only fixture read. A complete reply becomes a canonical `model_call` row
with exact request/response hashes, usage and `cost_micros=NULL`, `cost_basis=
estimated`. This is explicitly unknown estimated cost because W56a has no
verified model/price pin; no zero or v1 rate is invented.

The port builds the reviewed observation bytes, publishes through the existing
durable Blob intent/verification flow, reads the exact Blob bytes back, seals a
registry-bound `StageResult`, and commits the stage result and Blob binding in
one transaction. The Job repository rejects a second text-stage effect for the
run before preparing another call. Truncated/salvaged replies retain their
call record but cannot publish a successful stage artifact.

## Changed files

- `src/auditmanager/analysis/public.py` — additive exports of existing AR v2
  replay/call/artifact/seal types and the Blob role mapper;
- `src/auditmanager/jobs/repository.py` — current-Attempt duplicate-call guard
  and nullable cost insertion, preserving the existing numeric path;
- `src/auditmanager/runs/recorded_v2_stage.py` — new, unactivated durable port;
- `tests/integration/runs/test_v2_recorded_durable_stage.py` — exact replay,
  effect order, readback/duplicate/truncation refusals and nullable/live cost
  regressions;
- `docs/program/tasks/W56A-INT-DURABLE-RECORDED-STAGE-01.md`;
- this report.

## Checks

- Focused port, executor preflight and existing AR v2 artifact/call/seal suite:
  **45 passed**.
- Program governance suite: **16 passed**; direct task findings: `[]`.
- Python compilation, frozen plan/contract/provider SHA-256 comparisons,
  `git diff --check` and exact six-path ownership check: passed.
- `ruff` was unavailable in the worktree interpreter (`No module named
  ruff`); no lint pass is claimed. No PostgreSQL/S3 service or complete
  `make gate` was run under R-135 and the concurrent W55b release gate.

## Contracts and limits

No contract, migration, provider lock, v1 stage, executor runtime path,
composition root, finding publisher, recording, root dependency/lock file,
global style, remote ref or tag changed. Numeric `cost_usd` still converts to
micros exactly as before; a recorded fixture with no price now retains NULL,
which the existing run cost summary marks unmeasured.

This port does not select a terminal, publish findings, activate AR v2, start
or heartbeat the Attempt, or define retry/recovery for an incomplete reply.
If parsing fails after the fixture read, the prepared call effect remains for
reconciliation rather than being falsely completed. If Blob publication fails
after call completion, the call remains truthful and no success StageResult is
written. A previous uncertain effect blocks a new replay until reconciliation.
Focused tests use fake DB/Blob boundaries; real PostgreSQL/S3 transaction and
failure recovery acceptance remains for the separate executor activation task.

## Integration instruction

Take only the six task-owned paths. The future executor owner must call this
port only under a committed current recorded Attempt with a live lease
heartbeat, keep the v1 path unchanged, and own failures, terminal selection,
grounding/finding publication and real DB/S3 acceptance before activation.
Do not interpret this development port as a W56a release or beta verdict.
