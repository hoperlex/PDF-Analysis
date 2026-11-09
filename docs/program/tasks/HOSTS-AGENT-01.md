# Task HOSTS-AGENT-01 — the executor agent becomes a host agent

## Outcome
One agent process per machine, with one host token, installs without being told a model, finds every official CLI and API key file on the machine, reports which models it has verified, recomputes that on a schedule, answers tasks for any catalogue model with the exact model and effort the stand sends, and keeps its claim alive only while the CLI is producing output. The package still installs by one terminal command and over SSH. Agents on legacy per-connection tokens keep working.

## Depends on
- HOSTS-SEAL-1

## Frozen inputs
- domain contract: 1.45.0, owned by `HOSTS-SEAL-1`; frozen here
- API contract: 1.45.0 (host token, `reportRunnerHealth` host report, `claimExecutorTask` with a host token); frozen here. If the generated schema cannot carry something the agent needs, the lane reports it to the integrator and does not invent a field
- analysis/comparison/event contract: 1.45.0, including `contracts/analysis/v1/model-catalogue.json`
- migration head: `0062_hosts_stage_models`, unchanged by this task
- base commit: `8f76b4ed6daadad95f9c001e2c2c0dca717aad2d`
- the dispatcher replaces the base by the tip carrying `HOSTS-SEAL-1` at dispatch (`HOSTS-PLAN.md` §5)
- architecture: `docs/architecture/adr/ADR-0028-hosts-and-stage-models.md` decisions 1, 2, 4, 9, 16, 17; rulings `R-153a`, `R-153d`, `R-149b`; the earlier `ADR-0026` decisions 4–8 on enrollment, health and the installer

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `tools/executor-runner/package.py` (`PACKAGE_FILES`)
- enumerator_owner: HOSTS-AGENT-01
- totality_query: `python3 -c "import sys; sys.path.insert(0, 'tools/executor-runner'); import package; print(sorted(package.PACKAGE_FILES))"`

## Captured premise evidence
- premise: the agent allows two Claude models and packages nine files

### P-01 — the model allowlist and the package list
- captured_at: 2026-11-09
- command: `grep -n "ALLOWED_MODELS = \|^PACKAGE_FILES = " tools/executor-runner/claude_answer.py tools/executor-runner/package.py`
- captured_output:
  ```text
  tools/executor-runner/claude_answer.py:44:ALLOWED_MODELS = ("claude-opus-5", "claude-sonnet-5")
  tools/executor-runner/package.py:44:PACKAGE_FILES = {
  ```
- interpretation: `claude_answer.py` rejects every model but two; the catalogue replaces the allowlist. `PACKAGE_FILES` is a closed dictionary «never a glob»: every new file enters it, and `tests/unit/executor_runner/test_agent_package.py` holds it.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `tools/executor-runner/**`
- `tests/unit/executor_runner/**`
- `tests/integration/executors/test_agent_e2e.py`
- `tests/integration/executors/test_agent_install.py`
- `tests/integration/executors/test_runner_bridge_e2e.py`
- `tests/integration/executors/test_runner_client_wire.py`

## Forbidden hotspots
- `src/auditmanager/**`: the stand side of the protocol is `HOSTS-BACKEND-01`; the package is built from `tools/executor-runner/` by `package.py` and served unchanged
- the rest of `tests/integration/executors/**`, which `HOSTS-BACKEND-01` owns
- `contracts/**`, `db/migrations/**`, root dependency/lock files
- the install-session scripts of the stand (`src/auditmanager/executors/agent_install*.py`)

## Non-goals
- no change to what the stand stores or decides: availability, cooldown bookkeeping, slots and system connections are `HOSTS-BACKEND-01`
- the refusal of `--upgrade` for a pull agent whose connection rules or comparisons use is the stand's (`HOSTS-BACKEND-01`, until `HOSTS-CMP-01`); the script only honours the answer
- no model call from a test; no network
- no change to the SSH forced-command agents (`ssh-forced-command.sh`, `agent.*-ssh.example.toml`) beyond the model allowlist they share
- the SSH connection «kzSonnet» on production is not touched

## Deliverables
- **Host mode.** One process, one host token; `install.sh` takes no model. A legacy per-connection configuration still runs unchanged.
- **Discovery, explicit sources only:** `claude --version` and `claude auth status`; `codex login status`; the API key file of the service. Never environment scraping, never a credential path in a report. The key file is accepted only at mode 0600 owned by the service user, and the agent says so when it refuses one.
- **Catalogue.** The agent takes the catalogue from the stand (as the 1.45.0 contract delivers it) and reports which models it verified, per provider and access.
- **Recompute.** Every 60 s the CLI, its version and its login are checked without a model call; one minimal call per model on a change and every 6 h. The report is sent with the heartbeat and stored only when it changed. After a real refusal (access, quota, «no model») the agent reports it and stops offering that pair for 15 minutes.
- **Responders.**
  - `claude_answer`: catalogue models, `--effort`;
  - `codex_answer`: the three Codex models, reasoning effort;
  - new API responders for Anthropic, OpenAI and OpenRouter that read the key file (`R-153d`) and answer only catalogue models. API access is `metered`.
  - The exact `model_id` and `effort` come from the task; the agent holds no local capability mapping (`ADR-0028` decision 18).
- **Keys.** An API key never appears in a report, a log, a task payload or the environment of a child CLI; the child environment is an allowlist and a test proves it.
- **Slots and liveness.** Concurrency per provider follows the stand's slots (defaults: subscription 1, API 2). The task carries the cell timeout; the agent extends its claim only while the CLI produced output in the last 120 s, within the 7200 s ceiling.
- **Install.** The terminal command with a 15-minute grant and the SSH path A keep working; `--uninstall` and the exit-code semantics are unchanged. `README.md`, `RUNNER_API.md` and the example configuration describe host mode.
- **Package.** New files enter `PACKAGE_FILES`; the archive stays deterministic.

## Required tests
- command: with the project's Python (`FOUNDATION_PYTHON` in the `Makefile`, the venv), `-m pytest tests/unit/executor_runner -q` and `-m pytest tests/integration/executors/test_agent_e2e.py tests/integration/executors/test_agent_install.py tests/integration/executors/test_runner_bridge_e2e.py tests/integration/executors/test_runner_client_wire.py -q` if they need no service, otherwise write and mark them
- expected: pass. Cases: fake CLIs (installed, logged out, missing); a report only when something changed; keys never in a child environment; a 0600 key file accepted and a 0644 one refused; the claim extended only while there is output and a silent CLI is not extended; every file of `PACKAGE_FILES` present in the archive

## Integration contract
- The stand relies on: the host report fields of contract 1.45.0; the agent claiming with a host token; a task carrying exact `model_id`, `effort`, answer limit and timeout; a refusal reported with a class (`access`, `quota`, `no_model`).
- `HOSTS-INT-1` bumps the package version through `VERSION`; this task does not.

## Failure/idempotency/security cases
- an unreadable, wrongly owned or wrongly moded key file is refused with a sanitised reason and never read
- a claim that cannot be extended ends as the stand's lease semantics say; the agent never reuses a task id in work (`ADR-0026` decision 3)
- no secret in any report; each guard has a test that fails without it

## Rollback / feature flag
Revert the lane. Legacy per-connection agents are unchanged, and the stand serves host mode only when a host token exists.

## Handoff
- changed files: the lane lists them; it does not run git
- commands/results: the focused tests above; no network, container or model run
- known limits: no live check on `adm1.hlab.kz` (owner act)
- integration notes: the new `PACKAGE_FILES` entries; the report fields consumed
