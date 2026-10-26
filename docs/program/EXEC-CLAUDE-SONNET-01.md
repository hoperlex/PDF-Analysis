# EXEC-CLAUDE-SONNET-01 — the subscription command also serves claude-sonnet-5

**Source base:** `cecf8668` (`origin/main` after the 0.8.2 publication `8f86ddfd`). No contract, migration, `VERSION` or stand change.

## Result

`tools/executor-runner/claude_answer.py` serves `claude-opus-5` by default and `claude-sonnet-5` with
`--model claude-sonnet-5`. The model is fixed by the command line and never read from the task: the task
must name it, the CLI is started with it, and the CLI's own `modelUsage` must name it and nothing else.
An `authorized_keys` line or agent configuration written before this change keeps serving Opus.
A stand has Sonnet as a second `ssh_command` connection with its own key and `command=` line (README §F).

## Changed paths

| Path | Reason |
| --- | --- |
| `tools/executor-runner/claude_answer.py` | `ALLOWED_MODELS`, `DEFAULT_MODEL`; the model is a parameter from `read_task` to `ssh_reply`; `--model` accepted once, from the two pins only |
| `tools/executor-runner/README.md` | sections E and F describe `--model` and the second connection for Sonnet |
| `tools/executor-runner/agent.claude-ssh.example.toml` | one comment on the Sonnet setting |
| `tests/unit/executor_runner/test_claude_answer.py` | the fake CLI takes the served model; seven new tests |
| `tests/unit/executors/test_claude_answer_envelope.py` | the stand's wire agrees for a Sonnet connection, and rejects the other model |
| `docs/program/tasks/EXEC-CLAUDE-SONNET-01.md`, `docs/program/EXEC-CLAUDE-SONNET-01.md` | task and this record |

## Checks

| Check | Result |
| --- | --- |
| the existing adapter tests before touching them | 32 passed, 1 failed: the one test that pinned the source text `MODEL = "claude-opus-5"` (updated); the default is unchanged |
| adapter and wire tests | 40 passed (33 before) |
| all `tests/unit/executor_runner` and `tests/unit/executors` | 628 passed, 5 failed: the known `test_ssh_forced_command.py` cases that also fail on `origin/main` |
| real Claude Code 2.1.310, subscription login, Sonnet | `modelUsage` key exactly `claude-sonnet-5`; probe-shaped task 2.4 s, run-shaped task with a schema 3.1 s, both read by the stand's own `_reply`, identity `ok`, cost `null` |
| real call, no `--model` (Opus default) | probe 1.8 s, run 3.2 s, identity `ok`, cost `null` |
| an Opus task sent to a `--model claude-sonnet-5` command | exit 1, `claude_answer: model_mismatch`, no CLI started |
| mutations of `claude_answer.py` (six edits, each restored byte-for-byte) | each made at least one test fail: CLI always started with the default, task compared with the default, reported model compared with the default, envelope naming the default, any `--model` value accepted, a repeated `--model` accepted |
| `tests/contract/program`, `test_doc_prose_facts.py`, `test_readme.py` | 77 passed |
| `git diff --check` | exit 0 |

## Limits

- Not run: a stand with a Sonnet connection (the operator's check, README §F with the second line). The
  stand's SSH adapter is model-agnostic (the pin and gateway model are per connection), which is why no
  stand code changes; that was read from `ssh_adapter.py`, not exercised against a stand here.
- Opus and Sonnet connections on one account share its subscription and its limits.
- The five `test_ssh_forced_command.py` failures are unchanged and unrelated.
