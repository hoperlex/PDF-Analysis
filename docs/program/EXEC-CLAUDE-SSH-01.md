# EXEC-CLAUDE-SSH-01 — Claude Opus subscription over SSH, in both directions

**Source base:** `4e6b0b4d` (`origin/dev`). **Contract:** `1.5.0`, migration head
`0032_ar_v3_run_group`; no contract, migration, enum or stand-code change.

## Result

One command, `tools/executor-runner/claude_answer.py`, lets the pinned `claude-opus-5` serve
`text_analysis` from the owner's machine on the owner's **subscription login** (`R-143f`,
`R-143g`). No pin was added: `claude-opus-5` was already in `P02_LOCK.json`.

| Entry point | Direction | Stand kind | What the stand records |
| --- | --- | --- | --- |
| `claude_answer.py --ssh-envelope` (README F) | the stand connects by SSH and starts the session; the owner's choice of 2026-10-26 | `ssh_command`, profile `custom_command`, `not_metered` | `identity_basis: reported`: the CLI's own `modelUsage` names the model |
| `claude_answer.py` as `[command].argv` of the pull agent (README E) | the machine opens an outbound SSH forward to the stand and pulls tasks; the fallback if the stand cannot reach the machine | `pull`, client `agent`, `not_metered` | `identity_basis: declared` |

The subscription answer departs from the `R-143f` clause that kept an API key for the headless
SSH profile. It rests on that ruling's premise that no commercial use is foreseen, and the
integrator should record it as a ruling. `ssh-forced-command.sh` (the API-key profile, README C)
is unchanged.

## Changed paths

| Path | Reason |
| --- | --- |
| `tools/executor-runner/claude_answer.py` | one bounded task to one `claude -p` turn: fixed model, no tool, allow-listed environment, task text on stdin only; the pull answer, or with `--ssh-envelope` the stand's reply envelope |
| `tools/executor-runner/agent.claude-ssh.example.toml` | pull-agent settings for the loopback SSH forward |
| `tools/executor-runner/README.md` | file-table row; section E (machine calls the stand) and section F (stand starts the session) |
| `tests/unit/executor_runner/test_claude_answer.py` | fake CLI: success and every fail-closed case, both modes |
| `tests/unit/executors/test_claude_answer_envelope.py` | the stand's `_task`, this command and the stand's `_reply` and identity check agree |
| `tests/unit/executors/test_model.py` | an `agent` revision on `claude-opus-5` with `not_metered` is accepted |
| `docs/program/tasks/EXEC-CLAUDE-SSH-01.md` | task boundary |
| `docs/program/EXEC-CLAUDE-SSH-01.md` | this record |

## Checks

| Check | Result |
| --- | --- |
| `claude --version` on this machine | `2.1.310 (Claude Code)`, the binary of the VSCode extension; `claude` is not on `PATH`, hence `--claude` |
| real CLI, synthetic `{ok: boolean}` schema, subscription login | exit 0 in 3 s; `structured_output` `{"ok": true}`; `modelUsage` keys exactly `["claude-opus-5"]`; `terminal_reason` `completed`; `permission_denials` `[]` |
| real pull-mode run (`claude_answer.py --claude <binary>`) | exit 0 in 3.0 s; a schema-valid object on stdout, stderr empty |
| real `--ssh-envelope` runs, task built by the stand's own `_task`, reply read by the stand's own `_reply` | probe-shaped task without a schema (the plain-text prompt): exit 0 in 2.6 s, the answer `да`, `identity ok`, cost `null` (the first run, with the JSON prompt, answered the probe question with a JSON description of it, which is why the plain prompt exists); run-shaped task with a schema: exit 0 in 3.4 s, `identity ok`, cost `null`, a schema-valid object as `output_text` |
| `CLAUDE.md` canary in the working directory, default flags | read: the model followed the file's rule (`ok: false`) |
| same canary with `--setting-sources ""` alone, or with the three `CLAUDE_CODE_*` switches alone | not read: `ok: true` in both |
| new adapter, README, model and wire tests | 63 passed |
| all `tests/unit/executor_runner` and `tests/unit/executors` | 592 passed, 5 failed: `test_ssh_forced_command.py`, the same five on a clean `origin/dev`. Cause read from the code, not changed here: that test's stub `claude` prints `modelUsage: {"claude-opus-5": {}}` and `ssh-forced-command.sh` now requires integer `outputTokens`, so it exits 65 "claude returned an incomplete answer" |
| `tests/contract/program`, `test_doc_prose_facts.py`, `test_surface_counts_in_prose.py` | 105 passed |
| mutation checks of `claude_answer.py` (eighteen edits, each restored byte-for-byte) | each made at least one test fail: model check removed or loosened, API key or runner token passed, tools enabled, task text on argv, denials ignored, `is_error` ignored, images accepted, `--bare` added, list-price cost reported, schema optional in pull mode, stand image envelope accepted, cache tokens dropped, usage type check dropped, JSON prompt for a plain task, stand size ceiling ignored, empty text accepted |
| `git diff --check` | exit 0 |

One mutation survived on the first pass (`is_error`, caught only by `subtype` because the fake set
both); a `flag_only` case was added and it now fails.

## What this closes

`ssh-forced-command.sh` and `claude_output.py` both say the JSON key that carries the model must be
captured from the installed Claude Code. It is `modelUsage`, a map whose only key is the served
model id, spelled as the pin (`claude-opus-5`). A real call with `--max-turns 1` and
`--json-schema`, as the API-key forced command passes them, also ends `success` (a schema answer
takes two turns and still counts as one). Both facts were seen without `--bare`, under the
subscription login; the API-key path itself was not run, because no API key was available.

## Limits

- **Not connected yet.** The stand-side steps (README F: the connection and its key, the line in
  `authorized_keys`, the host-key confirmation, the probe, the route and one test-data analysis) and
  the machine-side steps (a dedicated account with its own Claude login, `/opt/pdf-analysis`, the
  `claude` binary for that account) were not done: they need the stand's public key, the owner's
  interactive login for the new account and the owner's go-ahead for changes to this host's
  accounts and sshd. No stand address or credential was available to this task.
- Reachability of this machine's sshd from the stand is unknown: `sshd` listens on `0.0.0.0:22`
  here, but nothing in this task could test the path from the stand or its firewall.
- The user-level `~/.claude/CLAUDE.md` does not exist on this machine, so only the project-level
  file was exercised; both go through the same loader, and the command runs in an empty temporary
  directory under a reduced environment.
- The extension's `claude` binary lives under `/root`; another account cannot use it. The dedicated
  account needs its own Claude Code installation.
- The CLI prints a list-price estimate (`total_cost_usd`, `costUSD`, `costBasis: list`) for a
  subscription run. The command never reports it, so the stand's meter shows no spend.
- A `modelUsage` that lists a second model (a helper the CLI chose) fails the task as
  `claude_model_mismatch`, by design.
- A task with an image is refused (`image_input_unsupported`): the CLI runs with no tool and cannot
  open a file. The stage that sends crops is not active.
- A subscription's availability and limits are the account's. A lost SSH session fails the call
  under the stand's existing retry rules.
- `test_ssh_forced_command.py` already fails on the base (see Checks); this task did not touch it.
