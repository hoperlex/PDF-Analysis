# Task EXEC-CLAUDE-SSH-01 — Claude Opus subscription over SSH, in both directions

task_id: EXEC-CLAUDE-SSH-01

## Outcome

The pinned `claude-opus-5` can serve `text_analysis` from the owner's machine on the owner's
subscription login, in either direction, with one command (`claude_answer.py`):

- **Stand starts the session** (the owner's choice of 2026-10-26: the production stand connects
  by SSH): an `ssh_command` connection whose forced command is `claude_answer.py --ssh-envelope`.
- **Machine calls the stand** (the fallback if the stand cannot reach the machine): an existing
  `pull` agent through an outbound SSH forward, as `EXEC-CODEX-SSH-01` does for Codex.

The administrator pins `claude-opus-5`, marks the connection `not_metered`, probes it and
routes work through the existing UI. No API key is involved.

## Depends on

- `EXEC-PULL-01` — completed pull channel.
- `EXEC-AGENT-01` — completed agent client.
- `EXEC-CODEX-SSH-01` — the same transport shape, already on `origin/dev`.

## Frozen inputs

- base commit: `4e6b0b4d4eeb4fc93d5209db248ed773bf7c3318` (`origin/dev` at task start);
- contract `1.5.0`, migration head `0032_ar_v3_run_group`; no contract or migration change;
- `R-143f` (the owner's subscription session may serve stand tasks; it kept an API key for the
  headless SSH profile), `R-143g` (sessions and agents run on the pinned `claude-opus-5` or
  `claude-sonnet-5`), `R-144`;
- the owner's poll answer of 2026-10-26: the production stand starts the SSH session, and the
  session authenticates with the subscription login, not an API key. This departs from the
  headless-profile clause of `R-143f`; the integrator records it as a ruling;
- the installed Claude Code `2.1.310` flags `-p`, `--output-format json`, `--json-schema`,
  `--tools`, `--strict-mcp-config`, `--no-session-persistence`, `--disable-slash-commands`,
  `--setting-sources` (read from `claude --help` on the machine that ran this task).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the base serves a pull agent and a Codex command, and has no Claude command
- captured_at: 2026-10-26
- command: `git grep -n -l -e 'claude_answer' -e 'codex_answer' 4e6b0b4d4eeb4fc93d5209db248ed773bf7c3318 -- tools/executor-runner`
- captured_output:
  ```text
  4e6b0b4d4eeb4fc93d5209db248ed773bf7c3318:tools/executor-runner/README.md
  4e6b0b4d4eeb4fc93d5209db248ed773bf7c3318:tools/executor-runner/agent.codex-ssh.example.toml
  4e6b0b4d4eeb4fc93d5209db248ed773bf7c3318:tools/executor-runner/agent.example.toml
  4e6b0b4d4eeb4fc93d5209db248ed773bf7c3318:tools/executor-runner/codex_answer.py
  ```
- interpretation: no `claude_answer` exists; the existing `pull`/`agent` kind carries a
  `claude-opus-5` revision (`PINS` already holds it) without an enum, schema or
  migration change.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

Publish only the clean, tested fast-forward of this task on `origin/dev`, by the
integrator.

## Allowed paths

- `tools/executor-runner/claude_answer.py`
- `tools/executor-runner/agent.claude-ssh.example.toml`
- `tools/executor-runner/README.md`
- `tests/unit/executor_runner/test_claude_answer.py`
- `tests/unit/executors/test_claude_answer_envelope.py`
- `tests/unit/executors/test_model.py`
- `docs/program/tasks/EXEC-CLAUDE-SSH-01.md`
- `docs/program/EXEC-CLAUDE-SSH-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependency and lock files;
- `src/auditmanager/**`, global styles, `web/**`, `infra/**`, `docs/program/P02_LOCK.json`
  and `docs/program/CURRENT_STATE.md`;
- `origin/main`, tags and the deployment host.

## Non-goals

- No new API operation, enum, profile, migration or stand code: the stand's SSH adapter is used as it is.
- No change to `ssh-forced-command.sh` or to the API-key route (section C stays as it is).
- No image tasks: the CLI runs with no tool and cannot open a file.
- No credential, token, SSH key or host name committed to the repository.
- No stand-side action and no change to this machine's accounts, `authorized_keys` or sshd: the
  connection, key, host-key confirmation and probe are the operator's, from README section F.

## Deliverables

- A bounded Claude command adapter for the existing `agent` protocol, with synthetic tests
  for success, model mismatch, extra model, failed or unfinished turn, denied tool, missing
  or non-object answer, malformed output, image tasks and a missing CLI.
- An example agent configuration and the operator instructions (README sections E and F).
- One real synthetic call of the installed CLI, reported separately from the fake-CLI tests.

## Required tests

- command: `python -m pytest -q -p no:cacheprovider tests/unit/executor_runner/test_claude_answer.py tests/unit/executor_runner/test_readme.py tests/unit/executors/test_model.py tests/unit/executors/test_claude_answer_envelope.py`; expected: pass.
- command: `python -m pytest -q -p no:cacheprovider tests/unit/executor_runner tests/unit/executors`; expected: pass except five `test_ssh_forced_command.py` cases that already fail on the base (a stale stub, see the report).
- command: `python -m pytest -q -p no:cacheprovider tests/contract/program`; expected: pass.
- command: `git diff --check`; expected: exit 0.

## Integration contract

The adapter reads one JSON task from stdin and prints the bare schema-valid JSON answer on
stdout. It starts the CLI only for the exact pinned model, in a private temporary directory
outside any repository, with no tool, no MCP server, no slash command, no settings source,
no `CLAUDE.md` or auto-memory, and an environment reduced to an allow-list. It accepts the
CLI's result only when the turn succeeded, no tool was denied, `modelUsage` names the pinned
model alone, and the answer is present (`structured_output` as an object when the task has a
schema, `result` as non-empty text when it has none). Any other outcome exits nonzero with a
fixed reason word.

- Default (pull agent): prints the bare answer JSON; the agent sends it with
  `identity_basis: declared` and `cost_basis: unmetered`.
- `--ssh-envelope` (forced command): prints one line `{"model","output_text","stop_reason",
  "input_tokens","output_tokens","reported_cost_usd"}`, the envelope `ssh_adapter._reply` reads. The
  model is the CLI's reported one (`identity_basis: reported`), the token counts come from
  `modelUsage`, and the cost is `null` (the CLI's list-price estimate is not a charge).

## Failure/idempotency/security cases

- Only one task is read; the model must match the pin before the CLI starts.
- No task text, token or CLI output is echoed on an error; task text is never on argv.
- An inherited `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN` and the
  runner token are removed from the CLI's environment.
- Removing the tunnel, losing the SSH session or revoking the token makes the pull agent fail
  or stop under its existing retry and lease rules.

## Rollback / feature flag

Revoke the pull token or remove the route to stop use at once. Revert this task's files to
remove the command; no data migration is involved.

## Handoff

- changed files: the allowed paths above;
- commands and results: `docs/program/EXEC-CLAUDE-SSH-01.md`;
- known limits: the stand-side tunnel, token, probe and PDF journey are operator checks;
- integration notes: README sections E and F list the steps; publish only a tested fast-forward
  to `origin/dev`; register the owner's 2026-10-26 subscription answer as a ruling.
