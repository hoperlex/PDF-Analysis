# executor-runner - clients of the executor pull channel and the SSH profile

These tools let a machine that is not the stand answer the stand's model calls
(`R-143`, plan `docs/program/dispatch/EXECUTOR-CONNECTIONS-PLAN.md`). The stand never connects
to them: a runner calls the stand over HTTPS (`RUNNER_API.md`), and an SSH profile is the one
case where the stand connects out.

| File | What it is |
| --- | --- |
| `RUNNER_API.md` | The binding wire contract the stand implements (`EXEC-PULL-01`). |
| `runner_client.py` | Standard-library HTTP client of that contract, shared by the two clients below. |
| `mcp_bridge.py` | Stdio MCP server for a Claude Code session: tools `claim_task`, `submit_answer`, `report_failure`. |
| `workspace/` | The dedicated Claude Code workspace: settings that deny every built-in tool, and the loop skill. |
| `agent.py`, `agent.example.toml`, `pdf-analysis-agent.service` | Unattended agent (command or local OpenAI-compatible model) and its systemd unit. |
| `ssh-forced-command.sh` | Remote side of the `claude_code_headless` SSH profile. |

Python: the bridge and the client need 3.9+, `agent.py` needs 3.11+ (`tomllib`); written for
those and tested on 3.12 only. No dependency is installed. Tests:
`python3 -m pytest -q -p no:cacheprovider tests/unit/executor_runner`.

## A. A Claude Code session in VSCode (profile `claude_code_session`)

The session is your own interactive session under your own login (`R-143f`). It runs on
`claude-opus-5` or `claude-sonnet-5` (`R-143g`), selected with `/model`, and nothing else.

### 1. On the stand

In «Исполнители → Подключения» create a `pull` connection with client `claude_code_session`
and the pinned model, issue a runner token (it is shown once) and route «Анализ текста» to the
connection.

### 2. Make the workspace a folder of its own

```bash
cp -r tools/executor-runner/workspace ~/pdf-analysis-runner-workspace
```

Keep it **outside any git repository**. Claude Code also reads `CLAUDE.md` files and skills from
the parent directories up to a repository root, so a workspace left inside this repository
would load the project's instructions into a session that is meant to see nothing else. The
copy holds exactly two files: `.claude/settings.json` (a bare `deny` rule for every built-in
tool, plus `mcp__claude_ai_*` and `mcp__plugin_*`, and an `allow` rule for the bridge's tools
only) and `.claude/skills/pdf-analysis-runner/SKILL.md` (the loop).

Plan T-7 in one sentence: a document that tells the session to run a command or read a file
finds neither tool, because a permission rule removed them; that is not left to the skill's
prose.

### 3. Register the bridge

Run this **from inside the workspace copy** (local scope is stored per project path):

```bash
cd ~/pdf-analysis-runner-workspace
read -rs RUNNER_TOKEN        # paste the token, press Enter; nothing is echoed or kept in history
claude mcp add --env "PDF_ANALYSIS_RUNNER_TOKEN=$RUNNER_TOKEN" --transport stdio --scope local \
  pdf-analysis-runner -- python3 <path-to-repo>/tools/executor-runner/mcp_bridge.py --origin https://<stand>
unset RUNNER_TOKEN
```

The general form is
`claude mcp add --env PDF_ANALYSIS_RUNNER_TOKEN=… --transport stdio pdf-analysis-runner -- python3 <path>/mcp_bridge.py --origin <stand>`.
Another option (`--transport`) must sit between `--env` and the name, or the CLI reads the name
as one more `KEY=value` pair. `--` separates Claude's options from the server command.

**Warning: the token is stored in clear.** Local scope writes it into `~/.claude.json` under
this workspace's path, readable by anyone who can read your home directory (`chmod 600
~/.claude.json`), and it is briefly visible in the process list while `claude mcp add` runs.
The token belongs to one connection, expires (30 days by default) and can be revoked at once
(section 7). The bridge itself never writes it anywhere and removes it from everything it
prints.

`--origin` is the stand's `https://` origin with no path. `http://` is accepted only for a
loopback host, or with `--allow-insecure-http` on a closed test network.

### 4. Trust the workspace once, from the CLI

The VSCode extension does not write the project-trust flag. Open a terminal in the workspace,
run `claude`, accept the trust dialog, and leave. Until then the project's `permissions.allow`
rule is not applied (the deny rules apply regardless, and the skill pre-approves the bridge's
tools for its own turn). Then `claude mcp list` in that directory shows `pdf-analysis-runner`,
and `/mcp` inside a session shows it connected.

### 5. Open the folder and pick the model

Open `~/pdf-analysis-runner-workspace` as the VSCode folder. In the Claude Code panel run
`/model` and choose `claude-opus-5` or `claude-sonnet-5`; the id must be that exact string
(the skill compares it with the task's `model` and refuses to answer as a different model).

Recommended: a clean profile. The workspace removes the built-in tools and the claude.ai and
plugin connectors, but an MCP server you configured yourself at user scope remains callable by
a prompt-injected session. Start VSCode from a shell that exports
`CLAUDE_CONFIG_DIR=$HOME/.claude-runner` (log in once more there) or disable those servers in
`/mcp`. `/mcp` must list `pdf-analysis-runner` and nothing else.

### 6. Manual check (do it before the first real task)

In a session in the workspace, ask it to:

1. run `ls` with the Bash tool: it must be unavailable or denied;
2. read `/etc/hostname` with the Read tool: it must be unavailable or denied;
3. list the tools it has: only `mcp__pdf-analysis-runner__*` (and `Skill`, `ToolSearch`).

If any of the three succeeds, stop: the settings did not load (check `/status` for the project
settings source, `claude doctor` for rejected rules, and that you opened the *copy*).
Re-check after every Claude Code upgrade: the deny list names today's built-in tools and a
new tool would need a new line (`tests/unit/executor_runner/test_workspace.py` lists them).

Then run «Проверить» on the connection in the UI, type `/pdf-analysis-runner` in the session,
and watch the probe task be claimed and answered; the connection shows «на связи».

### 7. Running, stopping, revoking

- Start the loop with `/pdf-analysis-runner`; stop it with Esc. An idle loop re-polls every
  two minutes (one short model turn each) and uses your session: stop it when you are done.
- Each task stays in the session's context. After many tasks, `/clear` and start the skill
  again. A task claimed before that returns to the queue when its claim lapses.
- The bridge extends a claim by itself while you answer. If the claim is lost or the deadline
  passes, `submit_answer` says so and the skill drops the task.
- Claude Code limits an MCP tool result to 25 000 tokens (`MAX_MCP_OUTPUT_TOKENS`); a text
  result over 50 000 characters is saved to a file, which this workspace cannot read. A task
  that large cannot be served by a session: the stand should keep `text_analysis` payloads
  smaller, or use the agent.
- **Revoke:** press «Отозвать токен» on the connection (the runner then gets 401 and stops),
  then `cd ~/pdf-analysis-runner-workspace && claude mcp remove pdf-analysis-runner`, which also
  deletes the token from `~/.claude.json` (verify with `grep -c PDF_ANALYSIS_RUNNER_TOKEN
  ~/.claude.json`, which must print 0).

## B. The unattended agent (client `agent`)

For a recognition machine or a box with a local model, behind NAT, with no open port.

```bash
sudo install -d /opt/pdf-analysis-agent /etc/pdf-analysis-agent
sudo install -m 0644 agent.py runner_client.py /opt/pdf-analysis-agent/
sudo install -m 0644 agent.example.toml /etc/pdf-analysis-agent/agent.toml    # then edit it
```

Follow the header of `pdf-analysis-agent.service` for the service user, the environment file
(mode 0600, owned by root, read by systemd before privileges drop) and `systemctl enable --now`.
The token lives only in that file; the config refuses a key named `token`, `secret`,
`password` or `api_key`.

- `mode = "command"`: the task document goes to the command's stdin
  (`task_id`, `model`, `system`, `user_text`, `output_schema`, `claim_expires_at`,
  `deadline_at`); the command prints ONE JSON document on stdout that validates against
  `output_schema`, and exits 0. Anything else fails the task with a typed reason
  (`command_failed`, `command_bad_output`, `answer_not_json`, `timeout`).
- `mode = "endpoint"`: a local OpenAI-compatible `/v1/chat/completions` server (Ollama
  `http://127.0.0.1:11434/v1/chat/completions`, vLLM, llama.cpp). `response_format =
  "json_schema"` passes the task schema to servers that constrain decoding.
- `[model] declared` is the exact pinned id this agent answers as; a task that pins another
  model is failed as `model_mismatch` before any work. It is an assertion: declare only what
  is true (`R-133` records it as `declared`, not `reported`).
- `agent.py --config agent.toml --max-tasks N` stops after N claimed tasks. Exit codes: 0
  normal stop, 2 configuration error, 3 token rejected (401: revoked or expired, the unit does
  not restart-loop on 2 or 3). `journalctl -u pdf-analysis-agent` shows the log; it holds task
  ids and timings, never the token or the payload.
- Revoke: the same «Отозвать токен» button; the agent exits 3 at its next call.

## C. SSH profile `claude_code_headless`

`ssh-forced-command.sh` is the remote forced command (header of the file: the one-line
`authorized_keys` entry with `restrict,command=`, the dedicated user, the API-key environment
file `~/.config/pdf-analysis/claude.env` with mode 0600, the requirements). It never uses a
subscription login (plan T-8). Its first real run is a paid call and is `EXEC-SSH-01`'s manual
check; the JSON key that carries the model must be captured from the installed Claude Code
before the stand parses it (the header explains how).

## Known limits

- No `claude` CLI was available on the host that built this: the settings syntax, the MCP
  handshake and the skill were checked against the documentation (code.claude.com settings,
  permissions, CLI reference; modelcontextprotocol.io 2025-11-25 and 2026-07-28), and the bridge
  is tested over its stdio against a fake server, but **not against a real Claude Code
  session**. Section A.6 is the acceptance test of that half.
- A session's id as Claude Code shows it may differ in form from the pin (for example a session may report `claude-sonnet-5-5`
  while the lock pins `claude-sonnet-5`). The skill fails closed;
  if `/model` shows another spelling, the owner decides before anything is relaxed.
