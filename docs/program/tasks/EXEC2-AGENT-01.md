# Task EXEC2-AGENT-01 — one installer for both paths, a deterministic agent package, CLI detection and the health report

## Outcome
On Ubuntu LTS, `install.sh` installs or repairs the agent idempotently. It writes a `0600` environment file and a systemd unit, enrolls with the secret from the environment, and starts the service with `concurrency = 1`. The agent reports its version, detected CLIs and their official auth status. `--uninstall` removes the agent without touching CLI installations or their logins.

## Depends on
- EXEC2-SEAL-1
- EXEC2-PULL-01 (before the final `agent.py` step)

## Frozen inputs
- domain contract: unchanged
- API contract: 1.15.0, frozen by `EXEC2-SEAL-1`
- analysis/comparison/event contract: unchanged
- migration head: `0046`, created by `EXEC2-SEAL-1`; this task adds no migration
- base commit: `integration/exec2` after the `EXEC2-SEAL-1` merge
- architecture: `docs/architecture/adr/ADR-0026-executor-capacity-enrollment-groups.md` decisions 5, 6, 8; plan `docs/program/dispatch/EXEC2-PLAN.md`; rulings `R-149a`…`R-149f`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the runner directory holds an agent, wrappers and a hand-written unit, but no installer, package builder or detector

### P-01 — the runner directory today
- captured_at: 2026-11-02
- command: `git ls-tree --name-only origin/dev tools/executor-runner/`
- captured_output:
  ```text
  tools/executor-runner/README.md
  tools/executor-runner/RUNNER_API.md
  tools/executor-runner/agent.claude-ssh.example.toml
  tools/executor-runner/agent.codex-ssh.example.toml
  tools/executor-runner/agent.example.toml
  tools/executor-runner/agent.py
  tools/executor-runner/claude_answer.py
  tools/executor-runner/codex_answer.py
  tools/executor-runner/mcp_bridge.py
  tools/executor-runner/pdf-analysis-agent.service
  tools/executor-runner/runner_client.py
  tools/executor-runner/ssh-forced-command.sh
  tools/executor-runner/workspace
  exit=0
  ```
- interpretation: `install.sh`, a package builder and a CLI detector are new files; `agent.py` and the unit file are edited.

The integrator re-runs every premise command on the actual base before dispatch (`EXEC2-PLAN.md` section 6) and corrects line numbers; a premise that no longer holds stops the dispatch.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `tools/executor-runner/install.sh`
- `tools/executor-runner/detect.py`
- `tools/executor-runner/package.py`
- `tools/executor-runner/agent.py`
- `tools/executor-runner/agent.example.toml`
- `tools/executor-runner/runner_client.py`
- `tools/executor-runner/RUNNER_API.md`
- `tools/executor-runner/pdf-analysis-agent.service`
- `tools/executor-runner/README.md`
- `tests/unit/executor_runner/**`
- `infra/deploy/Dockerfile.api`

## Forbidden hotspots
- `contracts/**`, generated models and client, the migration head, root dependency/lock files and global styles (owned by the stage's SEAL task)
- `src/auditmanager/shared/errors/**`: EXEC-2 adds no error code (ADR-0026 decision 18)
- paths another EXEC-2 task owns in the same stage (`EXEC2-PLAN.md` section 5)
- in `src/auditmanager/bootstrap/adapters.py` and `src/auditmanager/api/routers/ports.py`, which three stage-1 lanes share: any function or class outside this task's own port; new code goes in a section headed with this task id, and the integrator merges the lanes one by one
- `src/auditmanager/**` (server side is `EXEC2-ENROLL-01`)
- `agent.py` before `EXEC2-PULL-01` is merged

## Non-goals
- no Windows or macOS
- no credential copying or VS Code automation
- no concurrency above one written by the installer

## Deliverables
- `install.sh`: the same for paths A and B. It verifies the package sha256, creates or reuses a dedicated service user, and states the CLI authorisation step for that user without copying credentials. It installs under fixed paths, keeps the existing exit-code semantics (no restart loop on configuration or token refusal), and supports `--uninstall` and rerun.
- `package.py`: a deterministic tarball (sorted entries, zero mtime and owner) and its sha256. Built into the API image by `infra/deploy/Dockerfile.api`, in the place the package route of `EXEC2-ENROLL-01` reads.
- `detect.py`: fixed detection routines for `codex` and `claude` (installed, version). Auth status comes only from the official CLI mechanism: `codex login status` for Codex. For Claude Code, verify the official command against current documentation at implementation; if none exists, the status comes from the real probe. Results are sanitised enumerations.
- `agent.py`: the health report on start and periodically. The enroll exchange runs on the first start when the environment carries a grant; the grant is removed from the environment file after redemption.
- Tests for B2 §11 items 3, 4, 5 and 8 (agent half).

## Required tests
- command: not run in EXEC-2 (`R-149d`); write the tests below and mark those that need PostgreSQL with the suite's existing database marker
- expected: B2 §11 tests 3, 4, 5 and 8 (agent half) exist; `bash -n install.sh` is not run (`R-149d`)

## Integration contract
- `EXEC2-ENROLL-SSH-01` runs this `install.sh` unchanged over SSH
- the package path inside the image is the one `EXEC2-ENROLL-01` serves

## Failure/idempotency/security cases
- rerun on a working install keeps its runner token
- a CLI authenticated only under another OS user is reported unavailable, never borrowed
- no token in argv, shell trace or log line

## Rollback / feature flag
The installer is opt-in. `--uninstall` and a token revocation undo an install.

## Handoff
- changed files: the lane lists them; it does not run git, and the integrator commits exactly the allowed paths it changed
- commands/results: generation commands run and their result; no test, build, typecheck, lint, database, browser or model run (`R-149d`)
- known limits: every acceptance test named above is unexecuted
- integration notes: what the next consumer of this task may rely on
