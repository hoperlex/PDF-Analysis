STATUS: 7/7 all deliverables done, 110 unit tests green, committed (11:57 +05)

# EXEC-TOOLS-01 - executor runner client tools (final report)

Lane `agent/exec-tools-01` (worktree `.local/worktrees/exec-tools`, base `24e15247`). It builds the
client halves of the pull channel and the SSH profile ahead of their server slices (owner ruling
`R-144e`): EXEC-PULL-01 Work 5, EXEC-AGENT-01 Work 1-2 and EXEC-SSH-01 Work 3. Python standard
library only; no dependency, contract, migration or `infra/**` file touched.

## Files (all inside the allowed paths)

| Path | Why |
| --- | --- |
| `tools/executor-runner/RUNNER_API.md` | Binding wire spec for EXEC-PULL-01: claim, extend, answer, fail; error mapping onto the repository `ErrorEnvelope`; cadence; open points. |
| `tools/executor-runner/runner_client.py` | Shared HTTP client: token only in the header, scrubbed everywhere, redirects refused, `http://` only for loopback, server-clock claim timing, typed errors, backoff. |
| `tools/executor-runner/mcp_bridge.py` | Stdio MCP server: `claim_task`, `submit_answer`, `report_failure`; background claim extension; dual-era handshake. |
| `tools/executor-runner/workspace/.claude/settings.json`, `.../skills/pdf-analysis-runner/SKILL.md` | The dedicated workspace (plan T-7) and the loop. |
| `tools/executor-runner/agent.py`, `agent.example.toml`, `pdf-analysis-agent.service` | Unattended agent (command and endpoint modes) and its systemd unit. |
| `tools/executor-runner/ssh-forced-command.sh` | Remote side of `claude_code_headless`. |
| `tools/executor-runner/README.md` | Setup, manual check, revocation, known limits. |
| `tests/unit/executor_runner/*` | 110 tests (fake runner server, fake OpenAI endpoint, stdio driver). |

## Commands and results

- `nice -n 19 python3 -m pytest -q -p no:cacheprovider tests/unit/executor_runner` -> **110 passed in 32 s**
  (bridge 19, agent 25, workspace 7, forced command 29 incl. shellcheck, README 5, client 25).
- `bash -n tools/executor-runner/ssh-forced-command.sh` -> exit 0; `shellcheck -s bash` -> exit 0.
- `systemd-analyze verify pdf-analysis-agent.service` -> no finding (also inside the test, skipped when absent).
- Each guard was shown failing under a mutation (token scrub removed, redirect following enabled, local
  model check removed, bare deny rule replaced by a scoped one, `mcp__*` deny added, command kill removed,
  model_mismatch check removed, 422 retried as another class, secret-key guard removed,
  `unset SSH_ORIGINAL_COMMAND` removed, `--tools ""` changed, env-file mode check disabled, model regex
  widened, README option-between-`--env`-and-name order broken): each named test went red, then the file
  was restored. No other test battery, docker, make or npm was run; every run was under `nice -n 19`.
- Forbidden hotspots: `git diff --name-only 24e15247..HEAD` lists only `tools/executor-runner/**`,
  `tests/unit/executor_runner/**` and this file. No `conftest.py`, no contract, no migration, no lock file.

## Deviations from the brief and decisions to confirm

1. **MCP handshake.** The current MCP revision (2026-07-28) has *no* `initialize`: per-request `_meta`
   and `server/discover`. Claude Code today still speaks the 2025-11-25 handshake. The bridge is
   dual-era: it answers `initialize` (echoes a supported version, else 2025-11-25),
   `notifications/initialized`, `ping`, `tools/list`, `tools/call`, and `server/discover` plus the
   `-32022` unsupported-version error for the modern era (`resultType: "complete"` on modern results).
2. **Wire shape: as briefed**, plus: errors use the repo `ErrorEnvelope` (`authentication_required`,
   `conflict`, `state_transition_not_allowed`, `validation_failed`, `model_identity_mismatch`,
   `rate_limited`, `dependency_unavailable`); `answer` and `fail` return `{"task_id","state"}`; a 422
   keeps the claim (the runner may correct and resubmit); the server must send `Date` (runners compute
   claim time left on the server's clock); redirects are not followed. `model` mismatch is
   `422 model_identity_mismatch`.
3. **`claim_task` waits up to 600 s** (default 60): the bridge loops 25 s polls inside one tool call so an
   idle session burns one model turn per wait, not per 25 s. The HTTP `wait_seconds` stays 0..25.
4. **No `extend` tool.** The bridge extends held claims in the background (about a third of the lease
   left); a lost claim makes `submit_answer` refuse locally. A `submit_answer` whose `model` differs
   from the claimed task's is refused locally (nothing sent).
5. **T-7 nuance from the docs.** Deny rules are not gated by workspace trust (only `permissions.allow`
   is), and VSCode ignores a project's `defaultMode`. The CLI trust step is still in the README (it
   applies the allow rule) but the deny list does not depend on it. The workspace must be **copied out of
   the repository**: Claude Code loads `CLAUDE.md` and skills from parent directories up to the repo root.
   Project settings cannot deny user-scope MCP servers by name: README recommends a clean
   `CLAUDE_CONFIG_DIR`. Deliberately not denied: `Skill` (starts the loop), `ToolSearch`,
   `WaitForMcpServers`; `EndConversation` cannot be removed.
6. **`--max-tasks N`** = stop after claiming N tasks (0 = unlimited); EXEC-AGENT-01's "bounded
   concurrency" is `[runner] concurrency` (1..8). Command mode: stdout **is** the answer document (no
   envelope), tokens are reported only in endpoint mode.
7. **`runner_client.py`** is shared, so the agent is deployed as two files.
8. **Forced command** needs `python3` on the remote (no `jq` on this host), uses
   `--system-prompt-file` (replaces the default prompt), `--no-session-persistence` and a 840 s timeout.
   The JSON model key was **not** captured (no `claude` here): EXEC-SSH-01 Work 0 stays open.
9. **No real Claude Code in this lane.** Settings syntax and the skill follow the docs read 2026-10-22;
   the bridge is tested over its stdio only. README A.6 (Bash and Read must be denied) is the acceptance.
10. **Model id spelling.** A harness session may report `claude-sonnet-5-5` while the lock pins
    `claude-sonnet-5`; the skill fails closed. The owner should read `/model` in the VSCode session.

## Open points for EXEC-PULL-01

- Implement `RUNNER_API.md` as written; change it only together with the clients and tests.
- Task states have no `failed` value today; `fail` needs a terminal outcome (wire ignores `state`).
- nginx sizing from the cadence: per runner about 2.4 claims/min + one extend per lease/3 + one
  answer per task, roughly 6 requests/min for one task at a time, up to about 30/min at concurrency 8;
  key the zone on the token, not the address.
- Keep `text_analysis` payloads under Claude Code's MCP output limit (25 000 tokens; text over
  50 000 characters is saved to a file the workspace cannot read), or serve them with the agent.
- Recommended: re-deliver an already held claim to the same token on a repeat `claim`.

## Open points for EXEC-SSH-01

- The stand's SSH runner writes one JSON object to the remote stdin with at least `model`, `system`,
  `user_text` (extra fields ignored) and reads Claude Code's JSON from stdout; exit 64 = bad task,
  78 = bad environment file, 127 = `claude` or `python3` missing.
- Capture `claude --version` and the `--output-format json` keys (Work 0) before writing the parser.
- The forced command is untested against a real `claude`; the stub test checks its argv and environment.
