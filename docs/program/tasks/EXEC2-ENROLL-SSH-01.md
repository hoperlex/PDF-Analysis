# Task EXEC2-ENROLL-SSH-01 — path A: install the agent over SSH from the UI, executed by the worker

## Outcome
From the UI an administrator enters host, port and user, and gives SSH access by a stand-generated key or a pasted private key. They see and confirm the host-key fingerprint, then confirm an install summary. The worker runs the same `install.sh` over that connection, and the agent registers through the same enrollment. Afterwards the stand's key is removed from the host and destroyed. A failed install can be retried without creating a second connection.

## Depends on
- EXEC2-INT-1

## Frozen inputs
- domain contract: unchanged
- API contract: 1.15.0, frozen by `EXEC2-SEAL-1`
- analysis/comparison/event contract: unchanged
- migration head: `0046`, created by `EXEC2-SEAL-1`; this task adds no migration
- base commit: `integration/exec2` after `EXEC2-INT-1` is on `origin/dev`
- architecture: `docs/architecture/adr/ADR-0026-executor-capacity-enrollment-groups.md` decisions 6, 7, 18; plan `docs/program/dispatch/EXEC2-PLAN.md`; rulings `R-149a`…`R-149f`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: a pull connection holds no secret, and the probe runner is the worker-side pattern to follow

### P-01 — pull connections hold no sealed secret
- captured_at: 2026-11-02
- command: `git grep -n '"pull": (),' origin/dev -- src/auditmanager/executors/model.py`
- captured_output:
  ```text
  origin/dev:src/auditmanager/executors/model.py:114:    "pull": (),
  exit=0
  ```
- interpretation: the install key needs its own purpose (`agent_install_key`, created by SEAL-1) on the install session, not on the pull connection.

### P-02 — the worker-side runner pattern
- captured_at: 2026-11-02
- command: `git grep -nE '^(class|def) ' origin/dev -- src/auditmanager/executors/probe_runner.py`
- captured_output:
  ```text
  origin/dev:src/auditmanager/executors/probe_runner.py:56:class ProbeRunner:
  origin/dev:src/auditmanager/executors/probe_runner.py:217:def runner_for(
  exit=0
  ```
- interpretation: `ProbeRunner` and `runner_for` are the shape to copy for an install runner.

The integrator re-runs every premise command on the actual base before dispatch (`EXEC2-PLAN.md` section 6) and corrects line numbers; a premise that no longer holds stops the dispatch.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/executors/agent_install.py`
- `src/auditmanager/executors/agent_install_runner.py`
- `src/auditmanager/executors/agent_install_repository.py`
- `src/auditmanager/api/routers/executor_enrollment.py`
- `src/auditmanager/bootstrap/composition.py`
- `src/auditmanager/executors/queries.py`
- `scripts/recovery/grant_classification.py`
- `tests/unit/executors/test_agent_install.py`
- `tests/integration/executors/test_agent_install.py`

## Forbidden hotspots
- `contracts/**`, generated models and client, the migration head, root dependency/lock files and global styles (owned by the stage's SEAL task)
- `src/auditmanager/shared/errors/**`: EXEC-2 adds no error code (ADR-0026 decision 18)
- paths another EXEC-2 task owns in the same stage (`EXEC2-PLAN.md` section 5)
- `src/auditmanager/executors/ssh_transport.py` beyond reuse through its public functions

## Non-goals
- no password authentication
- no arbitrary command text from the UI
- no persistent SSH after install

## Deliverables
- The install-session state machine: requested → scanning → awaiting_host_key → installing → succeeded or failed, with a sanitised reason.
- The worker runner: host-key scan and confirmation compare (no TOFU); upload of the package on stdin; `sudo -n install.sh`; then removal of the stand's `authorized_keys` line and the secret.
- Composition wiring of the runner in the worker.
- Tests for B2 §11 item 1 (scripted SSH host).
- `ExecutorConnection.secrets` never lists an `agent_install_key` row (`executors/queries.py`); remove `executor_agent_install` from `SEALED_NOT_YET_WRITTEN`; command types `create_executor_agent_install` and `confirm_executor_agent_install_host_key` as SEAL-1 registered them.

## Required tests
- command: not run in EXEC-2 (`R-149d`); write the tests below and mark those that need PostgreSQL with the suite's existing database marker
- expected: B2 §11 test 1 exists against a scripted SSH endpoint

## Integration contract
- the agent produced by path A is byte-identical to path B's for the same version

## Failure/idempotency/security cases
- a changed host key between scan and install: refused
- sudo needs a password: failed with a clear reason, no partial agent
- a retry reuses the connection and a fresh enrollment

## Rollback / feature flag
Opt-in per administrator action; reverting removes the runner. The agent installed so far stays and can be uninstalled.

## Handoff
- changed files: the lane lists them; it does not run git, and the integrator commits exactly the allowed paths it changed
- commands/results: generation commands run and their result; no test, build, typecheck, lint, database, browser or model run (`R-149d`)
- known limits: every acceptance test named above is unexecuted
- integration notes: what the next consumer of this task may rely on
