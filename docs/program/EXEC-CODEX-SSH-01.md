# EXEC-CODEX-SSH-01 — Codex subscription over an outbound SSH forward

**Source base:** `f7d30053` (`integration/beta-main`). **Dev integration base:**
`17d1aea3` (`EXEC-INT-DEV-01`). **Contract:** `1.0.0`, API
87/99/284, migration head `0031_executor_pull_channel`; no contract or migration change.

## Result

The owner answered that the stand cannot initiate SSH to this machine. The
existing `ssh_command` kind therefore cannot carry this connection. The new
variant uses the existing `pull` client `agent`: this machine opens an SSH local
forward to the stand's loopback-only proxy, and the agent pulls its tasks
through that forward. `codex_answer.py` answers each task with the locally
ChatGPT-authenticated Codex CLI. The stand sees a `pull` revision with model
`gpt-6-sol`, billing `not_metered` and `identity_basis: declared`.

`gpt-6-sol` is added to `P02_LOCK.json`. Its recorded $2 input / $10 output per
million tokens are OpenAI's Standard API reference rates, not a charge for a
subscription run. The runner must be configured `not_metered`. OpenAI Docs
confirm both the [ChatGPT sign-in option for local Codex
CLI](https://learn.chatgpt.com/docs/auth) and the [JSONL, output-schema and
last-message options for `codex exec`](https://learn.chatgpt.com/docs/non-interactive-mode).
The [model page](https://developers.openai.com/api/docs/models/gpt-6-sol)
records the exact model ID and reference rates.

## Changed paths

| Path | Reason |
| --- | --- |
| `tools/executor-runner/codex_answer.py` | one bounded task to one Codex CLI turn, fixed model, fixed tool/sandbox options, JSON-only answer |
| `tools/executor-runner/agent.codex-ssh.example.toml` | pull-agent settings for the loopback SSH forward |
| `tools/executor-runner/README.md` | operator steps for login, tunnel, token, probe and route |
| `docs/program/P02_LOCK.json` | `gpt-6-sol` pin and rate reference |
| `docs/program/DEPLOYMENT_RUNBOOK.md` | cross-reference from the runner channel |
| `tests/unit/executor_runner/test_codex_answer.py` | fake CLI success and fail-closed cases |
| `tests/unit/executors/test_model.py` | complete pin set and `not_metered` agent revision |
| `docs/program/tasks/EXEC-CODEX-SSH-01.md` | task boundary |
| `docs/program/EXEC-CODEX-SSH-01.md` | this record |

## Checks

| Check | Result |
| --- | --- |
| `codex --version`; `codex login status` | `codex-cli 0.162.0-alpha.17.2`; `Logged in using ChatGPT` on this machine |
| new adapter and model tests | 31 passed |
| full `tests/unit/executor_runner` and `tests/unit/executors/test_model.py` with loopback sockets permitted | 141 passed |
| dev candidate: all `tests/unit/executors` and `tests/unit/executor_runner` with loopback sockets permitted | 506 passed |
| dev candidate: program governance and direct-pin contract checks | 19 passed |
| `make gate-preflight` on the clean dev candidate | refused before tests: worktree has no `.venv/bin/python` |
| real Codex CLI, synthetic `{ok: true}` schema and prompt | exit 0, output exactly `{"ok":true}` |
| `python3 -m py_compile` of adapter and test | exit 0 |
| `agent.load_config` on the Codex SSH example | accepted; loopback origin, `command` mode, exact model and 540-second timeout |
| `git diff --check` | exit 0 |

The first full pull-client test attempt ran in the default sandbox and failed
45 local `socket()` calls with `PermissionError`; the same selected suite passed
when loopback fixture sockets were permitted. The first real Codex command
attempt failed before model output because a file-size resource limit also
applied to Codex's own state files. The adapter now bounds its JSONL output by
monitoring the temporary file, and the repeated real synthetic call passed.
The dev gate was not started: its preflight refused the isolated worktree's
missing runtime venv, and the host's 4497 MiB free disk was below the preflight's
6144 MiB threshold. Development publication uses this task's bounded checks
under `R-135`, as `EXEC-INT-DEV-01` did; this is not full-gate evidence for main.

## Integration and limits

The Codex commit was cherry-picked onto `origin/dev` after its pull-channel
integration. This dev candidate does not carry the unrelated beta branch changes.
The source candidate remains available at `1515221a`.

The app server cannot call this machine. On the owner machine, open the
forward with a dedicated key limited to the stand's loopback proxy, then run
`agent.py` with the example configuration and a token issued in «Исполнители →
Подключения». Probe, route and run one test-data analysis as the README says.
The real stand tunnel, token, probe and PDF journey remain operator checks;
no stand address or credential was available in this task. A lost SSH tunnel
stops claims until it returns; the runner's existing lease and retry rules
apply. The adapter deliberately uses one CLI turn per task, so subscription
availability and latency still need the real probe.

The Codex CLI JSONL stream does not independently report the selected model.
The wrapper fixes `--model gpt-6-sol` and rejects a task that asks for another
model, while the pull protocol records the wrapper's model as **declared**. It
does not claim a stronger `reported` identity or infer a dollar amount from
subscription usage. The temporary directory is private; task content and
answer are removed at exit. An inherited API key and runner token do not enter
the Codex child environment. No app contract, migration head, root dependency
or lockfile, composition root, global styles or `infra/**` path changed.

To stop: revoke the token or remove the route. To roll back the code: revert
these task-owned files after the route is removed. No data migration is needed.
