# AR v3 beta current-Attempt preflight — development result

**Task:** [AR-V3-BETA-EXECUTE-PREFLIGHT-01](tasks/AR-V3-BETA-EXECUTE-PREFLIGHT-01.md). **Base:** published `origin/dev` `125efed23406f75b31e66c423e76d67fef381fd9`. **Target:** `origin/dev` only.

## Result

`resolve_v3_execution_binding` reads one six-Run member under a current Job/Attempt and matches its persisted group, Run and verified-set rows against the single server-installed reviewed pack. The projection carries project/version, profile/bundle, snapshot, provider mode, scope, map/set, composition/policy/pack and frozen-input pins. It rechecks Attempt authority after the database read and returns no data from a request-supplied SHA. It does not read a Blob or authorize a later provider call by itself.

The production pack registry remains empty. This read-only preflight therefore cannot activate v3 execution. The executor guard from the prior task remains in place.

## Changed files and checks

- `src/auditmanager/runs/v3_execution_binding.py` and `src/auditmanager/runs/public.py` — typed current-Attempt binding on the Run public seam.
- `tests/integration/db/test_ar_v3_run_group.py` — six-scope real-PostgreSQL resolution; no pack, replaced pack, foreign Run, fenced Attempt and zero model/stage effects.
- Task file, this report and `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md` — ownership and remaining boundary.

The real PostgreSQL group suite: **5 passed**. Focused guard/request suites: **32 passed**. `git diff --check` and exact allowed-path audit passed: **6 changed files, zero outside** the task. Full `make gate` remains deferred to the final beta candidate under `R-135`.

## Integration, risks and rollback

The full executor must call this function only after committing a Job/Attempt, then load the set Blob through the existing custody reader, build the sealed profile request and shared `ModelRequest`, commit provider-call intent before dispatch, and recheck Attempt/set authority after response. A binding cannot be cached across Attempts. No reviewed pack, real v3 model response, CITE StageResult or numerical conclusion is claimed.

No contract, migration, composition root, root dependency/lock file, global style, normative source/map, provider transport, Run executor, CITE publication, `origin/main`, tag or deployment host changed. The read-only preflight can be reverted before the full executor is installed; the prior fail-closed guard remains active.
