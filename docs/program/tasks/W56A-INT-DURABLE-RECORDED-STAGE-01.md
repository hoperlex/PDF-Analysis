# Task W56A-INT-DURABLE-RECORDED-STAGE-01 — persisted recorded AR v2 text stage port

task_id: W56A-INT-DURABLE-RECORDED-STAGE-01

## Outcome

One unactivated run-side port replays the exact saved AR v2 request under a
current Attempt, records the call with unknown monetary cost, publishes and
reads back its canonical observation Blob, then binds a successful StageResult
to that same Attempt. No success row may precede the call or Blob verification.

## Depends on

- `W56A-INT-RECORDED-SOURCE-READ-01` — completed saved source reader;
- `W56A-INT-RECORDED-CALL-FACTS-01` — completed response usage facts;
- `W56A-INT-RECORDED-STAGE-RESULT-01` — completed pure stage seal;
- `W56A-INT-RECORDED-ARTIFACT-PREP-01` — completed canonical bytes;
- `W56A-INT-RECORDED-PREFLIGHT-BIND-01` — completed registered preflight.

## Frozen inputs

- base commit: `6d6cec7cae3847696dabcb9f1a08846cefdcd58a`
- source branch at dispatch: `origin/dev`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd` (read-only);
- analysis public boundary SHA-256 `5f4b17477118a75b131255d6dcec3829a141bd8be25fd732ee836c020802103c`;
- JobRepository SHA-256 `ccc9bf8c145f21d7eb9518cf9918418ace6371cae487821fb23a9309cad1136b`;
- migration head `0022_findings_v2`; StageResult contract v1 and stage registry v1.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the checked AR v2 source, response, artifact, call facts and stage
  seal exist, but no durable AR v2 stage caller exists; the canonical call cost
  is nullable in DB yet the job writer currently casts it to float.

### P-01 — missing port and nullable cost boundary

- captured_at: 2026-10-16
- command: `git rev-parse HEAD && git ls-tree -r --name-only HEAD src/auditmanager/runs/recorded_v2_stage.py && rg -n 'cost_micros.*bigint NULL|int\(round\(float\(call\["cost_usd"\]\)' db/migrations/versions/20260910_0002_pc01_schema.py src/auditmanager/jobs/repository.py`
- captured_output:
  ```text
  6d6cec7cae3847696dabcb9f1a08846cefdcd58a
  db/migrations/versions/20260910_0002_pc01_schema.py:831:            cost_micros      bigint NULL,
  src/auditmanager/jobs/repository.py:904:                "cost_micros": int(round(float(call["cost_usd"]) * 1_000_000)),
  ```
- interpretation: DB can honestly retain an unpriced recorded fixture call,
  while the current job writer needs a narrow nullable-cost adaptation.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/public.py`
- `src/auditmanager/jobs/repository.py`
- `src/auditmanager/runs/recorded_v2_stage.py`
- `tests/integration/runs/test_v2_recorded_durable_stage.py`
- `docs/program/tasks/W56A-INT-DURABLE-RECORDED-STAGE-01.md`
- `docs/program/W56A-INT-DURABLE-RECORDED-STAGE-01.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, existing v1 stage and artifact,
executor runtime path, run repository/commands, composition root, findings,
API, recordings, root dependency/lock files, global styles, `CURRENT_STATE.md`,
refs, tags and remote branches.

## Non-goals

No activation in `execute_run`, provider selection, live model/price claim,
synthetic cost, finding publication, terminal selection, partial/truncated
coverage, new schema or full beta gate. An unpriced fixture is not a free
measured call; its canonical `cost_micros` stays NULL and estimated.

## Deliverables

Additive analysis public exports, nullable recorded-cost writer preserving v1
numeric behavior, a run-side durable recorded stage port, focused tests and
this task/result report.

## Required tests

- focused recorded stage and nullable-cost regression suite — pass;
- existing recorded replay/artifact/call/seal and v1 job tests — pass;
- Python compilation, direct governance, frozen hashes, whitespace and exact
  allowed-path proof — pass;
- full `make gate` deferred under R-135 while W55b release gate runs.

## Integration contract

The later executor supplies current Job/Attempt authority, an actual recorded
adapter, saved run ID, fixture model ID and generation settings. The port reads
saved source refs, journals call intent before replay, retains an unpriced
canonical call and publishes through the existing durable publication store.
It reads back exact Blob bytes before sealing and commits the StageResult with
the artifact binding. The executor still owns run terminal, finding gate,
retries and recovery policy; it must never activate this port for live mode.

## Failure/idempotency/security cases

Wrong run/attempt/profile/mode, existing recorded stage effect, missing
recording, malformed reply, truncated result, Blob mismatch or stale authority
fails closed. A committed call may remain if later publication fails, as
truthful partial evidence; no stage success is committed in that case.

## Rollback / feature flag

Revert the six owned paths before runtime wiring. This port is unactivated, so
no data rollback or feature flag is needed.

## Handoff

- changed paths/checks/limits: accompanying report;
- contracts: none;
- next: integrator takes exactly the six owned paths and separately grants
  executor activation, recovery and PostgreSQL acceptance work.
