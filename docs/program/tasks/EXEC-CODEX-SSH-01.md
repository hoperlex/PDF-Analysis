# Task EXEC-CODEX-SSH-01 — Codex subscription through an outbound SSH tunnel

task_id: EXEC-CODEX-SSH-01

## Outcome

On the owner's machine, an existing `pull` agent can fetch `text_analysis` tasks through
an outbound SSH local forward to the stand and answer them with a ChatGPT-authenticated
Codex CLI. The administrator pins `gpt-6-sol`, marks the connection `not_metered`,
probes it, and routes work through the existing UI. The agent sends no API key to the
stand and the stand opens no connection to the owner's machine.

## Depends on

- `EXEC-PULL-01` — completed pull channel on this base.
- `EXEC-AGENT-01` — completed agent client on this base.
- `EXEC-CANDIDATE-2-FINISH` — completed candidate validation on this base.

## Frozen inputs

- base commit: `f7d30053` (`integration/beta-main` at task start);
- contract `1.0.0`, API 87 paths / 99 operations / 284 schemas;
- migration head `0031_executor_pull_channel`;
- analysis, comparison and event contracts unchanged;
- `R-143` / `R-144`, `RUNNER_API.md`, and the existing `pull` client `agent`;
- OpenAI Docs: Codex CLI accepts ChatGPT subscription sign-in, `codex exec --json`,
  `--output-schema`, `--output-last-message`, `--sandbox read-only`, `--ephemeral`,
  and `--ignore-user-config` (links in the result record).

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: docs/program/P02_LOCK.json
- enumerator_owner: EXEC-CODEX-SSH-01
- totality_query: `python3 -c 'from auditmanager.analysis.public import pinned_models; print([p.model_id for p in pinned_models()])'`

## Captured premise evidence

- premise: the base serves a pull agent, and the SSH command's enum has no Codex profile
- captured_at: 2026-10-23
- command: `git grep -n -e 'SSH_PROFILES:' -e 'PULL_CLIENTS:' -e 'IDENTITY_BASIS_BY_KIND:' f7d30053 -- src/auditmanager/executors/model.py`
- captured_output:
  ```text
  f7d30053:src/auditmanager/executors/model.py:66:SSH_PROFILES: Final[tuple[str, ...]] = ("claude_code_headless", "custom_command")
  f7d30053:src/auditmanager/executors/model.py:67:PULL_CLIENTS: Final[tuple[str, ...]] = ("claude_code_session", "agent")
  f7d30053:src/auditmanager/executors/model.py:80:IDENTITY_BASIS_BY_KIND: Final[Mapping[str, str]] = {
  ```
- interpretation: the existing `pull`/`agent` kind can carry this command without an
  enum, schema or migration change; the subscription model still needs a pin.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

The development publication follows integration of the base's candidate changes.

## Allowed paths

- `tools/executor-runner/codex_answer.py`
- `tools/executor-runner/agent.codex-ssh.example.toml`
- `tools/executor-runner/README.md`
- `docs/program/P02_LOCK.json`
- `docs/program/DEPLOYMENT_RUNBOOK.md`
- `docs/program/tasks/EXEC-CODEX-SSH-01.md`
- `docs/program/EXEC-CODEX-SSH-01.md`
- `tests/unit/executor_runner/test_codex_answer.py`
- `tests/unit/executors/test_model.py`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependency and lock files;
- `src/auditmanager/bootstrap/**`, `src/auditmanager/executors/**`, global styles,
  `web/**`, `infra/**` and `docs/program/CURRENT_STATE.md`;
- `origin/main`, tags and deployment host.

## Non-goals

- No inbound SSH on the owner's machine, direct `ssh_command` connection, new API
  operation, or change to the release's executor protocol.
- No user credential, token, SSH key or host name committed to the repository.
- No deployment or change to `origin/main`.

## Deliverables

- A bounded Codex command adapter for the existing `agent` protocol, with synthetic
  tests for success, mismatch, malformed/failed output and tool use.
- Example agent configuration and exact SSH tunnel/operator instructions.
- The pinned Codex model with a documented API rate reference; the connection uses
  `not_metered`, so these rates are not charged for subscription calls.

## Required tests

- command: `../int-beta/.venv/bin/python -m pytest -q tests/unit/executor_runner/test_codex_answer.py tests/unit/executors/test_model.py`; expected: pass.
- command: `../int-beta/.venv/bin/python -m pytest -q tests/unit/executor_runner tests/unit/executors/test_model.py` with local loopback sockets permitted; expected: pass.
- command: `git diff --check`; expected: exit 0.
- command: `codex --version` and `codex login status`, without printing credentials;
  expected: installed CLI and ChatGPT sign-in. A real synthetic model call is reported
  separately from fake CLI tests.

## Integration contract

The adapter reads one JSON task from stdin and prints the bare schema-valid JSON answer
on stdout. It invokes Codex only with the exact pinned model, in a private temporary
directory, with no user configuration, shell tool or web search, and a read-only sandbox.
Any failed turn, tool event, malformed answer, missing/invalid schema or model mismatch
exits nonzero. The existing agent sends the answer with `identity_basis: declared` and
`cost_basis: unmetered`; it does not infer actual spend from subscription usage.

## Failure/idempotency/security cases

- Only one task is read; the model must match the pin before Codex starts.
- No task text, token or Codex output is echoed on an error.
- CLI writes only to a private temporary directory; the runner token and any inherited
  API key are removed from its environment.
- Removing the tunnel, losing the SSH session or revoking the token makes the pull
  agent fail/stop under its existing retry and lease rules.

## Rollback / feature flag

Revoke the pull token or remove its route to stop use immediately. Revert this task's
files to remove the runner profile and model pin; no data migration is involved.

## Handoff

- changed files: the exact allowed paths above that appear in the task report;
- commands/results: `docs/program/EXEC-CODEX-SSH-01.md`;
- known limits: the real stand/SSH/probe/run journey requires the owner's host and token;
- integration notes: merge this candidate after its parent beta candidate and use the
  README's outbound tunnel steps. Publish only a tested fast-forward to `origin/dev`.
