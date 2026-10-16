# W56A-INT-RECORDED-ACTIVATION-01 — explicit executor bridge result

**Base:** published `origin/dev=b9f1c149f004851de89a2fcc615618068e794bde`.
The task owns the executor bridge only; normal API/worker composition still
selects v1 and supplies no AR v2 fixture configuration.

## Result

`execute_run` now recognizes a persisted Run carrying either registered AR v2
identity. Before any Run, Job or Blob effect, it requires the matching registered
profile and bundle, a concrete offline `RecordedAdapter`, recorded provider
configuration with no API key, and explicit `fixture/<id>` plus generation
settings. A mismatch fails closed. A v1 Run remains on its existing four-stage
route and rejects stray v2 fixture inputs.

For an accepted v2 Run, the existing Job/Attempt and running Run commit precedes
the three deterministic stages. The existing durable recorded text port records
one exact replay; the saved merge port follows; the publication gate reads back
saved evidence and performs final finding and Run/Job/Attempt writes in one
caller-owned transaction. The executor returns the gate's selection and counts.
If preparation halts, it calls the gate to fail the incomplete Run without
replaying a fixture or merging findings.

## Changed files

- `src/auditmanager/runs/executor.py` — selected branch, early refusal and port order;
- `tests/integration/runs/test_v2_recorded_executor_bridge.py` — route, refusal,
  v1 preservation and halted-stage checks;
- `docs/program/tasks/W56A-INT-RECORDED-ACTIVATION-01.md` — task grant;
- this report.

## Checks

- Focused bridge, preflight, durable text, saved merge and programme governance:
  **58 passed in 0.31s** without services;
- direct task governance: `[]`;
- Python compilation and `git diff --check`: passed;
- API, error catalog, analysis registry, provider lock, W56 plan and code-first
  frozen SHA-256 values remained identical to the task;
- the previously integrated publication gate passed 15 real PostgreSQL/MinIO
  tests on dev17. This bridge has **not** had a service-backed end-to-end test.
  An attempted local run of that gate suite had 42 container-free passes and 13
  setup errors because `DATABASE_URL` was unset; no service was started while
  the integrator's W55b full gate owns the host lane.

## Contracts and limitations

No contracts, migrations, provider lock, recordings, repositories, composition
root, API, global styles or main/dev ref were changed. The explicit fixture
parameters are a library caller capability, not a served setting. There is no
verified AR v2 live model/price pin or production fixture selection; worker and
API callers do not supply the new parameters and cannot start a v2 Run through
this bridge yet. The current stage ports deliberately reject truncated or
salvaged replies until a separate partial-coverage policy exists. Errors after
an Attempt/call boundary follow existing carrier rollback/crash reconciliation;
the executor never falls back to a live call.

## Integrator handoff

Cherry-pick this owned commit after dev17. Run a focused persisted-Run service
acceptance on an isolated PostgreSQL/MinIO lane once W55b gate releases the
services, verifying a real recorded fixture, all five StageResults, one call,
saved Blob readback and a single terminal publication. A separate task must
own composition/config and the model-pin decision before serving activation.
The code-first `R-135` full gate remains deferred to the final beta candidate.
