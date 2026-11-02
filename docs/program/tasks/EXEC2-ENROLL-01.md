# Task EXEC2-ENROLL-01 — enrollment grants, the runner-token exchange, agent health, the package route and moving an agent

## Outcome
An administrator creates an enrollment for a pull connection and gets a one-time secret and a copyable command. Running the command on Ubuntu registers an agent that gets its own runner token. The connection then shows the agent's version, detected CLIs and sanitised auth states, and whether it is online. Doing the same on another host moves the agent: the old token can be revoked once the new agent is online.

## Depends on
- EXEC2-SEAL-1

## Frozen inputs
- domain contract: unchanged
- API contract: 1.15.0, frozen by `EXEC2-SEAL-1`
- analysis/comparison/event contract: unchanged
- migration head: `0046`, created by `EXEC2-SEAL-1`; this task adds no migration
- base commit: `integration/exec2` after the `EXEC2-SEAL-1` merge
- architecture: `docs/architecture/adr/ADR-0026-executor-capacity-enrollment-groups.md` decisions 4, 5, 6, 9, 18; plan `docs/program/dispatch/EXEC2-PLAN.md`; rulings `R-149a`…`R-149f`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: there is no enrollment facility, and the runner token already records when it was last seen

### P-01 — no enrollment code exists
- captured_at: 2026-11-02
- command: `git grep -c -i enroll origin/dev -- src contracts tools`
- captured_output:
  ```text
  origin/dev:contracts/analysis/v1/stage-registry.json:1
  exit=0
  ```
- interpretation: the only match is the unrelated «Worker enrollment» text of the analysis stage registry.

### P-02 — last-seen bookkeeping on the runner token
- captured_at: 2026-11-02
- command: `git grep -n 'last_seen_at' origin/dev -- src/auditmanager/executors/runner_repository.py`
- captured_output:
  ```text
  origin/dev:src/auditmanager/executors/runner_repository.py:42:    "revoked_by, last_seen_at, last_seen_address"
  origin/dev:src/auditmanager/executors/runner_repository.py:108:    last_seen_at: datetime | None
  origin/dev:src/auditmanager/executors/runner_repository.py:170:        "revoked_at", "revoked_by", "last_seen_at", "last_seen_address")})
  origin/dev:src/auditmanager/executors/runner_repository.py:253:            "UPDATE executor_runner_token SET last_seen_at = clock_timestamp(), "
  origin/dev:src/auditmanager/executors/runner_repository.py:254:            "last_seen_address = :address WHERE token_id = :id AND (last_seen_at IS NULL "
  origin/dev:src/auditmanager/executors/runner_repository.py:256:            "OR last_seen_at < clock_timestamp() - make_interval(secs => :every))"
  exit=0
  ```
- interpretation: freshness can be read from `last_seen_at`; health extends the same row.

The integrator re-runs every premise command on the actual base before dispatch (`EXEC2-PLAN.md` section 6) and corrects line numbers; a premise that no longer holds stops the dispatch.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/executors/enrollment.py`
- `src/auditmanager/executors/enrollment_repository.py`
- `src/auditmanager/executors/agent_package.py`
- `src/auditmanager/executors/public.py`
- `src/auditmanager/api/routers/executor_enrollment.py`
- `src/auditmanager/api/app.py`
- `src/auditmanager/api/security.py`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/proxy/tls-server.conf`
- `tests/contract/test_proxy_rate_limits.py`
- `scripts/recovery/grant_classification.py`
- `tests/unit/executors/test_enrollment.py`
- `tests/unit/executors/test_agent_package.py`
- `tests/integration/executors/test_enrollment.py`

## Forbidden hotspots
- `contracts/**`, generated models and client, the migration head, root dependency/lock files and global styles (owned by the stage's SEAL task)
- `src/auditmanager/shared/errors/**`: EXEC-2 adds no error code (ADR-0026 decision 18)
- paths another EXEC-2 task owns in the same stage (`EXEC2-PLAN.md` section 5)
- `src/auditmanager/executors/runner*.py` (`EXEC2-PULL-01`)
- `tools/executor-runner/**` (`EXEC2-AGENT-01`)

## Non-goals
- no path A (stage 2)
- no UI (stage 1 `EXEC2-WEB-CAP-01` and stage 2 `EXEC2-WEB-WIZARD-01`)

## Deliverables
- Grant: hash only, 15 minutes, single use, bound to the connection. A new grant revokes the previous unredeemed one. Journal events carry no secret.
- `POST /runner/enroll`: the exchange is idempotent within its window and refused after redemption; the grant reaches no task operation.
- `POST /runner/health`: stores only the sanitised enumerations of ADR-0026 decision 5, under the runner channel's throttle.
- `GET /runner/agent-package/{version}`: serves the package `EXEC2-AGENT-01` builds into the image, by exact version, with its sha256. It builds the copyable command for path B: download, `sha256sum -c`, then `install.sh` with the secret in an environment variable.
- The enrollment and package routes are registered in `api/app.py` and get their principal kinds in `api/security.py`; the proxy throttles both (per address).
- Moving an agent: issuing an enrollment for a connection that already has an online agent is allowed and journalled. Revoking the old token stays the existing operation.
- Tests for B2 §11 items 2, 7 and 8 (server half).
- Remove `executor_enrollment` from `SEALED_NOT_YET_WRITTEN` in `scripts/recovery/grant_classification.py` once this task writes it; move `THROTTLED_OPERATIONS` in `tests/contract/test_proxy_rate_limits.py` with the new proxy throttles; command types and event names are the ones SEAL-1 registered (`issue_executor_enrollment`, `executor.`-prefixed events).

## Required tests
- command: not run in EXEC-2 (`R-149d`); write the tests below and mark those that need PostgreSQL with the suite's existing database marker
- expected: B2 §11 tests 2, 7 and 8 (server half) exist

## Integration contract
- `EXEC2-AGENT-01` calls `POST /runner/enroll` and `POST /runner/health` exactly as the 1.15.0 contract says
- `EXEC2-ENROLL-SSH-01` reuses the grant and the exchange unchanged

## Failure/idempotency/security cases
- expired, replayed or revoked grant: typed refusal; nothing issued
- the secret is never in argv of the generated command, in a log line or in an error detail
- the package route refuses path traversal and unknown versions

## Rollback / feature flag
Additive and administrator-initiated. Reverting the merge removes the routes; issued runner tokens stay valid.

## Handoff
- changed files: the lane lists them; it does not run git, and the integrator commits exactly the allowed paths it changed
- commands/results: generation commands run and their result; no test, build, typecheck, lint, database, browser or model run (`R-149d`)
- known limits: every acceptance test named above is unexecuted
- integration notes: what the next consumer of this task may rely on
