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
| `agent.py`, `agent.example.toml`, `pdf-analysis-agent.service` | Unattended agent (single-model: a command or a local OpenAI-compatible model; or **host mode**, section B0) and its systemd unit. |
| `host_mode.py`, `api_answer.py` | Host mode of the agent: the catalogue, the model book, the recount and the snapshot, the slots, the dispatch; and the direct API answerers (Anthropic Messages, OpenAI Responses, OpenRouter chat completions). |
| `install.sh`, `detect.py`, `package.py` | The installer of the agent on Ubuntu LTS (both install paths, section B1; `--upgrade` to host mode), the detection of the `codex` and `claude` CLIs with the access of their login and of the key file, and the builder of the deterministic agent package the stand serves. |
| `ssh-forced-command.sh` | Remote side of the `claude_code_headless` SSH profile. |
| `codex_answer.py`, `agent.codex-ssh.example.toml` | Codex CLI answer command and pull-agent example over an outbound SSH forward. |
| `claude_answer.py`, `agent.claude-ssh.example.toml` | Claude Code CLI (`claude-opus-5` by default, or `claude-sonnet-5` with `--model`) on the owner's subscription: the pull agent's answer command (section E) and, with `--ssh-envelope`, the forced command of a stand-initiated SSH connection (section F). |

Python: the bridge and the client need 3.9+, `agent.py` needs 3.11+ (`tomllib`); written for
those and tested on 3.12 only. No dependency is installed. Tests:
`python3 -m pytest -q -p no:cacheprovider tests/unit/executor_runner`.

## A. A Claude Code session in VSCode (profile `claude_code_session`)

The session is your own interactive session under your own login (`R-143f`). It runs on
`claude-opus-5` or `claude-sonnet-5` (`R-143g`), selected with `/model`, and nothing else.

### 1. On the stand

In «Исполнители → Подключения» create a `pull` connection with client `claude_code_session`
and the pinned model, then issue a runner token with «Выпустить токен» (it is shown once, with
a copy button). Route «Анализ текста» to the connection after the successful probe in step 6.

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
For an image-capable session add `--accept-images` after `<stand>`; the bridge then
fetches and verifies each claimed PNG and returns it as MCP image content alongside
the task text. Check one image task in the session before using this mode for runs.
The bridge serves one image per task unless it is started with `--max-images N` (1 to 8,
only with `--accept-images`); it tells the stand that number when it claims, and the stand
never hands it a task with more. A task with several images returns them in order after the
text, with `image_references` naming each by its opaque crop reference (or portal block), and
a notice that the session answers only if it can see all of them and otherwise reports
`image_input_unsupported`. Claude Code limits the size of one MCP tool result, so a task of
many large crops is for the agent (section C), not for a session.
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
- **Revoke:** press «Отозвать» beside the token on the connection's card and confirm (the runner then gets 401 and stops),
  then `cd ~/pdf-analysis-runner-workspace && claude mcp remove pdf-analysis-runner`, which also
  deletes the token from `~/.claude.json` (verify with `grep -c PDF_ANALYSIS_RUNNER_TOKEN
  ~/.claude.json`, which must print 0).

## B. The unattended agent (client `agent`)

For a recognition machine or a box with a local model, behind NAT, with no open port.

### B0. Host mode: one agent per server, no model at install (`HOSTS-AGENT-01`)

A **host agent** is one process with one **host token**. It serves every model its machine can reach and tells the stand
which it verified; the stand's catalogue says which models matter, and the stand decides where a run goes (`RUNNER_API.md`
section 10). Nothing is chosen at install, and nothing is declared: no `[model]` section.

What it finds, with the access of each (the status commands of the CLIs, run as the service user):

| Provider | Found when | Access |
| --- | --- | --- |
| claude_code | the `claude` CLI is installed | `subscription` (a claude.ai login) or `api` (a login with an API key); read from `claude auth status` |
| codex | the `codex` CLI is installed | `subscription` (a ChatGPT login) or `api` (an API-key login); read from `codex login status` |
| anthropic_api, openai_api, openrouter_api | the key is in the key file | `api` |

A CLI that is not signed in is reported `login_required`; one signed in by a method the agent cannot name is reported
`unknown` and serves nothing. Only these sources are looked at: no other environment variable, home directory or user's file.

**The key file** `/etc/pdf-analysis-agent/keys.env` (change it with `[host] key_file`) holds the optional API keys, one
`NAME=value` per line: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY` (other lines are not read). It is read only
when it is a regular file of **mode 0600 owned by the service user** (`pdf-agent`); otherwise it is ignored and the journal
says why. The installer never creates, reads or copies it. A key goes into one header of one HTTPS request to its provider and
nowhere else: it is not in the agent's or any child CLI's environment, not in a report, a log or an answer (the environment
passed to `claude` and `codex` is a short allowlist with a second guard behind it that drops every name ending `_API_KEY`,
`_TOKEN`, `_SECRET` or `_PASSWORD`). **A call through a key sends the document text to that provider**; that is a path out of
the stand and the owner's decision (`D-291`, `R-143c`), so put a key there only for that.

```bash
sudo install -m 0600 -o pdf-agent -g pdf-agent /dev/null /etc/pdf-analysis-agent/keys.env    # then edit it
```

**The recount.** Every 60 s the agent detects cheaply (CLI present, version, login, the key file; no model is called) and
sends a report with each cycle, which is the host's pulse. The snapshot in it is rebuilt only when something changed. A
*minimal model call* is made for each catalogue model of a provider whose login, key, CLI version or access changed, for a
new catalogue model, every six hours for a verified model (`[host] probe_interval_seconds`) and every 15 minutes for a failed
one. A model is `verified` only when that call succeeded **and** the model that answered is the requested one or one the
catalogue accepts (`accepted_reported`). The agent claims only while some model is verified and a slot is free, and it
**refuses a task whose model it does not report as verified** for that provider and access (`model_not_available`).

**Slots** (concurrent calls per provider, tasks and checks together): 1 on a subscription login, 2 on an API login or key;
set them in `[slots]` of `agent.toml` (`claude_code = 1`, `anthropic_api = 2`, ...).

**A claim is extended only while the call produces output** (stdout or stderr bytes of the CLI, a streamed chunk or keep-alive
of an API response) within `[host] activity_window_seconds` (600, owner ruling `R-153p`; it was 120). A hung CLI or API call lets
its claim lapse, is stopped and frees its slot. Codex prints its events when an item completes, so a Codex call that reasons
silently for longer than the window is treated as hung. The window is deliberately **equal to the stand's stall window**
(`ATTEMPT_STALL_SECONDS` of `jobs/lease.py`, 600 s): a call silent that long is fenced by the stand at the moment the agent stops it. A
host whose `agent.toml` names `activity_window_seconds` keeps that value until the line is removed.

Answers carry the `provider`, the `access`, the model the CLI or API **reported** (exactly) and `usage`. The Claude Code
command takes `--effort`; Codex gets `-c model_reasoning_effort="<effort>"`; the APIs get the effort in their own parameter
(`output_config.effort` for Anthropic, `reasoning.effort` for OpenAI and OpenRouter). **No answer cap reaches any model** (owner
ruling `R-153n`, restoring his instruction of 2026-11-06; the task carries no `max_output_tokens`): the Claude Code command is run
without `CLAUDE_CODE_MAX_OUTPUT_TOKENS` and the variable is removed from its environment if the agent inherited it; the Codex command
has no such limit; OpenAI Responses and OpenRouter get no output-token parameter; Anthropic Messages requires `max_tokens`, so it gets
64000, the largest Claude answer the repository records (`api_answer.ANTHROPIC_MAX_OUTPUT_TOKENS`). The one exception is the availability
probe (`PROBE_MAX_OUTPUT_TOKENS`, 4096), which is not an analysis answer and reaches an API provider only. A call is bound by its task's time. The service stays one process; `journalctl -u pdf-analysis-agent` shows the recount (`probe:`), the catalogue and
the reason a key file was ignored. `sudo -u pdf-agent -H python3 /opt/pdf-analysis-agent/detect.py --host` shows what the agent
would report, without calling a model.

### B1. Install it with `install.sh` (the universal agent, `EXEC2-AGENT-01` and `HOSTS-AGENT-01`)

`install.sh` is the one installer of both paths of ADR-0026 decision 6: the administrator pastes the command the
stand prints for an enrollment (path B, the **terminal one-liner**), or the stand's worker runs the same script over SSH with
`sudo -n` (path A, **SSH**). It needs Ubuntu LTS, systemd and `python3` 3.11 or newer (Ubuntu 24.04), and runs as root from the
directory the package was unpacked into. The package is built by `package.py` into the API image and served by
version (`GET /runner/agent-package/{version}`); the command checks its sha256 before unpacking.

**Path B, the terminal one-liner** (a host agent; the model is not part of the command):

```bash
cd "$(mktemp -d)" && curl -fsSL -o agent.tar.gz https://<stand>/api/v1/runner/agent-package/<version> \
  && echo '<sha256>  agent.tar.gz' | sha256sum -c - && tar -xzf agent.tar.gz \
  && AUDITMANAGER_ENROLLMENT_SECRET=<secret> AUDITMANAGER_STAND_ORIGIN=https://<stand> \
     sudo --preserve-env=AUDITMANAGER_ENROLLMENT_SECRET,AUDITMANAGER_STAND_ORIGIN \
     bash install.sh
```

**Path A, SSH** (the stand's worker, as the SSH user with passwordless `sudo -n`, after it has copied the package and
checked its digest): the same script, with the secret and the origin in the environment of the one `sudo` command and the
digest on the command line,

```bash
AUDITMANAGER_ENROLLMENT_SECRET=<secret> AUDITMANAGER_STAND_ORIGIN=https://<stand> \
  sudo -n --preserve-env=AUDITMANAGER_ENROLLMENT_SECRET,AUDITMANAGER_STAND_ORIGIN \
  bash install.sh --package agent.tar.gz --sha256 <sha256>
```

Both end the same way: the service runs, the host reported its CLIs, and the steps that are the administrator's are printed:
signing a CLI in as the service user, and the optional key file (B0).

What it does, in order: refuses wrong input before changing anything; creates or reuses the service user
`pdf-agent` (home `/var/lib/pdf-analysis-agent`, mode 0700); installs the agent under `/opt/pdf-analysis-agent`;
writes `/etc/pdf-analysis-agent/agent.toml` (host mode: `[executor] mode = "host"`, no model) and the environment file `agent.env` (mode
0600, root); exchanges the one-time secret for a runner token (`agent.py --enroll-only`, which stores the token in
`agent.env`); installs the unit and starts it. The service never restarts on exit 2 (configuration, including a
missing token) or exit 3 (a refused token).

- **The secret** is read only from `AUDITMANAGER_ENROLLMENT_SECRET`: never an argument (`--secret` is refused),
  never echoed, logged or written, removed from the installer's environment at once. A grant lasts 15 minutes and
  is single use.
- **Which model and CLI answer: none is chosen.** A host agent serves what it finds (B0). The old installer refused a fresh
  install without a model; that refusal is gone. `--model ID` (or `AUDITMANAGER_AGENT_MODEL`) still installs the **single-model
  agent** of `EXEC2-AGENT-01`, bound to one connection (section B1b below). `--cli` belongs to that agent only.
- **`--upgrade`** converts an installed single-model agent to host mode. It needs a **new** enrollment secret (issue it in the
  stand's «Подключить сервер»: the installed token belongs to one connection) and is refused, before anything changes, without
  it or without an install. It keeps the service user, its home, every path and the origin; writes the host `agent.toml` (the old
  one stays as `agent.toml.pre-host`); replaces the token **only after** the new enrollment succeeded (if it fails the single-model
  agent is left as it was); and restarts the service. On an agent that is already a host agent it only updates the files. The stand
  decides whether the old connection may be retired (a connection used by rules or comparisons keeps it until they move).
- **Signing the CLI in is yours, and happens as the service user**: `sudo -u pdf-agent -H codex login --device-auth`
  or `sudo -u pdf-agent -H claude auth login`. The installer never copies a credential from any account, and a CLI
  signed in only under another account is reported `login_required`, never borrowed.
- **Rerun** is safe: unchanged files are left, an existing `agent.toml` and `agent.env` are kept (so the runner
  token and the configured mode keep working; `--reconfigure` writes `agent.toml` again), the service restarts only
  after a change. The same secret again inside its window is the stand's idempotent repeat: it revokes the token it minted before and
  returns a fresh one, and only the newest is stored. A secret the stand has spent, or one redeemed from another
  host, keeps the installed token.
- **`--uninstall`** removes the service, unit, code, `agent.toml` and `agent.env`. It never touches an installed
  CLI, any login or `keys.env`, and leaves the service user and its home; revoke the token in the stand UI.
- `--package FILE --sha256 DIGEST` verifies an archive before anything is installed (path A uses it).

#### B1b. The single-model agent (`--model`)

```bash
... AUDITMANAGER_AGENT_MODEL=<gateway_model> sudo --preserve-env=AUDITMANAGER_ENROLLMENT_SECRET,AUDITMANAGER_STAND_ORIGIN,AUDITMANAGER_AGENT_MODEL bash install.sh
```

The agent must declare exactly the model its connection pins (`gateway_model`) and the stand refuses an answer from another,
so with a model the command carries it (`AUDITMANAGER_AGENT_MODEL` or `--model`). A model no answer command serves is refused (exit 64).
The CLI follows from the model: `claude-opus-5` and `claude-sonnet-5` are answered by Claude Code (`claude_answer.py`), `gpt-6-sol` by
Codex (`codex_answer.py`). `AUDITMANAGER_AGENT_CLI` / `--cli` may only confirm that; a contradiction is refused. A CLI the
service user does not have yet does not stop the install: the agent reports `installed=false` and the installer prints the
install and login step. A rerun without a model keeps the configured one; a different model is applied only with `--reconfigure`.

The agent reports to the stand (`POST /runner/health`, `RUNNER_API.md` section 9) at start, every ten minutes and whenever detection changes
(it detects every 60 s):
its package version, concurrency, profile, and for `claude` and `codex` whether they are installed, their version
and their login state. The state comes only from the CLI's own command, run as the service user: `codex login
status` and `claude auth status` (exit status only for this report; the output, which may name an account, is never reported). A
Claude Code older than 2.1.268, a timeout or an unexpected answer is reported `unknown`. Paths, tokens and account
names are never reported. `PDF_ANALYSIS_CLI_DIRS` (absolute directories, colon-separated) replaces the directories
searched when a CLI lives under a non-standard prefix; set `PATH` to match for the answer command.

### B2. By hand

```bash
sudo install -d /opt/pdf-analysis-agent /etc/pdf-analysis-agent
sudo install -m 0644 agent.py runner_client.py detect.py host_mode.py api_answer.py /opt/pdf-analysis-agent/
sudo install -m 0644 agent.example.toml /etc/pdf-analysis-agent/agent.toml    # then edit it
```

Follow the header of `pdf-analysis-agent.service` for the service user, the environment file
(mode 0600, owned by root, read by systemd before privileges drop) and `systemctl enable --now`.
The token lives only in that file; the config refuses a key named `token`, `secret`,
`password` or `api_key`.

- `mode = "host"`: the host agent of section B0 (no `[model]`, no command; the sections `[host]`, `[slots]` and `[api]` are
  described at the end of `agent.example.toml`). The key file is optional.
- `mode = "command"`: the task document goes to the command's stdin
  (`task_id`, `model`, `system`, `user_text`, `output_schema`, `claim_expires_at`,
  `deadline_at`); the command prints ONE JSON document on stdout that validates against
  `output_schema`, and exits 0. Anything else fails the task with a typed reason
  (`command_failed`, `command_bad_output`, `answer_not_json`, `timeout`, `codex_timeout`).
  `[command].timeout_seconds = 0` uses the remaining server task deadline; a positive value
  can shorten it. The command receives `PDF_ANALYSIS_COMMAND_DEADLINE_MONOTONIC` so the
  Codex wrapper uses that same budget. Timeout exit status 124 is reported as `codex_timeout`;
  no unknown-outcome retry is added.
- `mode = "endpoint"`: a local OpenAI-compatible `/v1/chat/completions` server (Ollama
  `http://127.0.0.1:11434/v1/chat/completions`, vLLM, llama.cpp). `response_format =
  "json_schema"` passes the task schema to servers that constrain decoding. Set
  `[endpoint].accept_images = true` only for a model that accepts an OpenAI Chat
  `image_url` data URL. The agent verifies each PNG and sends all of them, in the task's order,
  in the user message. `[endpoint].max_images` (1 to 8, default 1, above 1 only with
  `accept_images = true`) is what the agent tells the stand it serves in one task; the stand
  never hands a task with more, and an agent that is nevertheless handed one fails it with
  `image_input_unsupported` instead of answering from some of the images.
- `[model] declared` is the exact pinned id this agent answers as; a task that pins another
  model is failed as `model_mismatch` before any work. It is an assertion: declare only what
  is true (`R-133` records it as `declared`, not `reported`).
- `agent.py --config agent.toml --max-tasks N` stops after N claimed tasks. Exit codes: 0
  normal stop, 2 configuration error, 3 token rejected (401: revoked or expired, the unit does
  not restart-loop on 2 or 3). `journalctl -u pdf-analysis-agent` shows the log; it holds task
  ids and timings, never the token or the payload.
- Revoke: the same «Отозвать» button; the agent exits 3 at its next call.
- `[runner] concurrency` (1 to 8, default 1) is how many tasks this process works at once. It needs the
  connection's «Заданий в работе» (`max_claimed_tasks`) to be at least as large: with the stand's
  limit of one, the stand hands the agent its one held task again, and the agent, which keeps the ids of the
  tasks it is working on, does not start that task a second time and waits at least 5 s before it claims
  again. The agent claims only when a local slot is free.
- **Run one agent process per token** (v1). The agent names itself in every claim with a random
  `runner_instance_id` (new at each start), and the stand hands a task it already holds only back to the
  instance that took it; a restarted agent therefore waits at most one claim lease (120 s) for the task its
  predecessor held. Two processes presenting one token are not a supported setup (`RUNNER_API.md`, section 8).

## C. SSH profile `claude_code_headless`

`ssh-forced-command.sh` is the remote forced command (header of the file: the one-line
`authorized_keys` entry with `restrict,command=`, the dedicated user, the API-key environment
file `~/.config/pdf-analysis/claude.env` with mode 0600, the requirements). It never uses a
subscription login (plan T-8). Its first real run is a paid call and is `EXEC-SSH-01`'s manual
check; the JSON key that carries the model must be captured from the installed Claude Code
before the stand parses it (the header explains how).

## D. Codex subscription from this machine, through an outbound SSH forward

Use this when the stand cannot reach this machine by SSH. The machine opens one
SSH connection **to** the stand and forwards a local loopback port to the stand's
loopback-only proxy. `agent.py` uses its existing `pull` protocol on that port;
`codex_answer.py` invokes this machine's Codex CLI. No listener is opened to
the network on this machine. The transport is SSH; the executor kind is `pull`
with client `agent`, not `ssh_command`.

1. On this machine, install Codex CLI and run `codex login` under the dedicated
   runner account, completing the ChatGPT browser sign-in. `codex login status`
   must say `Logged in using ChatGPT`; an API-key login uses API billing instead.
   The current adapter pins `gpt-6-sol`, and the stand's revision must name that
   exact model. Keep the runner account separate from a development account.
2. On the stand, create a `pull` connection with client `agent`, model/pin
   `gpt-6-sol`, billing `not_metered`, answer deadline at least 600 seconds and
   one claimed task. Issue a runner token. Do not route the connection until
   the agent is running and a probe returns `ok`.
3. Give the runner account an SSH key allowed to forward only to the stand's
   loopback proxy. A dedicated `authorized_keys` line can use
   `restrict,port-forwarding,permitopen="127.0.0.1:31500"` (substitute the
   stand's actual `ALPHA_HTTP_PORT`). Pin the stand's SSH host key in the local
   `known_hosts`; never disable host-key checking. Open the forward in a terminal:

   ```bash
   ssh -N -T -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
     -L 127.0.0.1:31501:127.0.0.1:31500 -i <runner-ssh-key> <runner@stand>
   ```

4. Copy `agent.codex-ssh.example.toml` outside this repository, set the
   absolute `codex_answer.py` path and local port, then start `agent.py` in a
   second terminal under the same dedicated account. Supply the token only in
   `PDF_ANALYSIS_RUNNER_TOKEN` (as in section B). The agent's origin must be
   `http://127.0.0.1:31501` with no path. Plain HTTP here is loopback traffic
   inside the authenticated SSH forward.
5. In «Исполнители → Подключения», press «Проверить». An `ok` probe proves the
   forward, token, local CLI and a schema-shaped answer. Then route «Анализ
   текста» and run one test-data analysis. Revoking the token or removing the
   route stops new work.

The adapter sends the task through stdin, writes schema and output only in a
private temporary directory, runs `codex exec --json --output-schema` with
`--ephemeral`, `--ignore-user-config`, `--sandbox read-only`, shell tool and web
search disabled, and refuses failed, rerouted, tool-using or malformed turns.
It has no separate 510-second timer or response/event byte ceiling. Use
`[command].timeout_seconds = 0` to let the server task deadline bound the CLI. On timeout,
only elapsed time, event counts/types, a thread id and byte counts reach the journal;
the task fails as `codex_timeout`, rather than a generic command failure. Input and image
guards still apply. Successful command and endpoint answers are read whole and answer
submissions have no application byte ceiling; endpoint `max_tokens` is no longer sent.
Response-token figures are estimates, not output caps. Model/context limits still belong
to the provider.
The CLI's output does not prove the served model independently; the local
command declares the model selected by `--model`, and the stand records that
as `identity_basis: declared`. Keep the account and its Codex authentication
private. The connection is `not_metered`; the app does not convert subscription
usage into an invented dollar amount. A subscription's availability and limits
are the account's, so a real probe is required before routing.

For a separate saved-crop image task, set `[command].accept_images = true` only
when the command accepts `local_images` in the task JSON. The agent downloads each of the
claim's PNGs (up to eight, 16 MiB each and 32 MiB together; a crop is named by its blob id,
and two crops with the same bytes are downloaded once) over the same authenticated channel,
checks its size and SHA-256, passes private temporary files to `codex_answer.py`, and removes
them when the command ends. `codex_answer.py` attaches them in order with one
`codex exec --image` each and names them in the prompt. `[command].max_images` (1 to 8,
default 1, above 1 only with `accept_images = true`) is what the agent tells the stand it
serves; the stand never hands a task with more. Text-only commands, endpoints and MCP
sessions without their image opt-in refuse image tasks.
Direct and VPN HTTP connections carry the selected PNGs, in order, as OpenAI Chat or Anthropic
Messages image blocks. SSH command and SSH tunnel connections carry them too (section F).
A remote command installed before several images existed refuses a task of several (it reads
the task's `image` member as one object), so it is never answered from part of the evidence.
The W56b image
stage will produce these tasks after its prompt and evidence policy is approved;
the current «Анализ текста» route does not send images.

## E. Claude Opus subscription from this machine, through an outbound SSH forward

Use this when the stand cannot reach this machine by SSH (the same shape as section D, with
Claude Code in place of Codex). The machine opens one SSH connection **to** the stand and
forwards a local loopback port to the stand's loopback-only proxy. `agent.py` pulls its tasks
through that forward; `claude_answer.py` answers each one with this machine's Claude Code CLI
under the owner's own subscription login (`R-143f`). The executor kind is `pull` with client
`agent`, not `ssh_command`; the API-key profile of section C is the separate, stand-initiated
route.

1. On this machine, run `claude` once under the dedicated runner account and sign in with the
   subscription (`/login`). Prefer a profile of its own: `export CLAUDE_CONFIG_DIR=$HOME/.claude-runner`
   before that first run and in the agent's environment, so the runner's login and settings are not
   the development account's. `claude auth status` must name the subscription, not an API key.
   The command serves `claude-opus-5` unless it is started with `--model claude-sonnet-5` (the two pins of `R-143g`;
   no other value is accepted). The stand's revision must name that exact model; add `--model claude-sonnet-5` to
   `argv` for Sonnet.
   The `--bare` mode of the CLI is deliberately not used: it reads only an API key, never the login.
2. On the stand, create a `pull` connection with client `agent`, model/pin `claude-opus-5`, billing
   `not_metered`, answer deadline at least 600 seconds and one claimed task. Issue a runner token.
   Do not route the connection until the agent is running and a probe returns `ok`.
3. Give the runner account an SSH key allowed to forward only to the stand's loopback proxy, pin the
   stand's host key in the local `known_hosts`, and open the forward exactly as in section D step 3
   (`restrict,port-forwarding,permitopen="127.0.0.1:<ALPHA_HTTP_PORT>"`; never disable host-key checking).
4. Copy `agent.claude-ssh.example.toml` outside this repository, set the absolute `claude_answer.py`
   path, the absolute path of the `claude` binary (`--claude`, needed when it is not on the agent's
   `PATH`) and the local port, then start `agent.py` in a second terminal under the same account.
   Supply the token only in `PDF_ANALYSIS_RUNNER_TOKEN` (as in section B).
5. In «Исполнители → Подключения», press «Проверить». An `ok` probe proves the forward, the token, the
   local CLI and a schema-shaped answer. Then route «Анализ текста» and run one test-data analysis.
   Revoking the token or removing the route stops new work.

The adapter sends the task through stdin (the task text is never on the command line) to
`claude -p --output-format stream-json --verbose --include-partial-messages --model <the served model> --tools ""
--strict-mcp-config --no-session-persistence --disable-slash-commands --setting-sources "" --json-schema <schema>`
(plus `--effort <level>` when the task names one, see section F), in a
private temporary directory outside any repository, with an environment reduced to `HOME`, `PATH`,
locale, `CLAUDE_CONFIG_DIR`, proxy and certificate variables plus three switches that keep `CLAUDE.md`
files, auto-memory and non-essential traffic out. An inherited `ANTHROPIC_API_KEY`,
`ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN` and the runner token never reach the CLI.
The CLI writes newline-delimited JSON (`stream-json`); the command reads it as it grows and takes the last
`result` line as the report. This channel keeps one wall-clock deadline of 510 seconds and prints no
heartbeat; a stream that ends without a `result` line fails the task with `claude_no_result`.

It accepts the result only when the CLI reports a successful, tool-free turn whose `modelUsage` names
the served model (`claude-opus-5` or, with `--model`, `claude-sonnet-5`) and nothing else; a different or additional model, a denied tool, a failed or
unfinished turn, or a missing or non-object `structured_output` fails the task with a fixed reason.
That report is the CLI's own, so this route is stronger than section D, but the pull protocol still
records the model as **declared** (`identity_basis: declared`): the stand has no way to check it. The
connection is `not_metered`; the app does not turn subscription usage into a dollar amount, and the
account's availability and limits are the subscription's, so a real probe is required before routing.
Image tasks are refused (`image_input_unsupported`): the CLI runs with no tool and cannot open a file.

## F. Claude Opus subscription, the stand starts the session over SSH

Use this when the stand can reach this machine's sshd (the owner's answer of 2026-10-26: the
production stand connects by SSH and raises the session itself). It is the `ssh_command` kind of
`EXEC-SSH-01`, with `claude_answer.py --ssh-envelope` as the forced command, authenticated by the
owner's **subscription login** instead of the API key of section C. That is an owner decision
that changes `R-143f` for this route (`headless SSH keeps an API key`): it rests on `R-143f`'s
premise that no commercial use is foreseen. If the product is ever offered to others, return this
connection to the API-key profile of section C.

1. On this machine, create a dedicated low-privilege account (for example `pdfa`) and install Claude
   Code for it. Sign in as that account with `claude` and `/login` (the subscription, not an API key;
   `claude auth status` must say so). Do not reuse a development account's login. Nothing in the
   account's environment may set `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN` or
   `CLAUDE_CODE_OAUTH_TOKEN`; the adapter drops them anyway.
2. Install the command where the account cannot edit it:
   `sudo install -d -m 0755 /opt/pdf-analysis && sudo install -m 0755 claude_answer.py /opt/pdf-analysis/`
   (a copy from this repository; re-install after every change to it).
3. On the stand, in «Исполнители → Подключения», create an `ssh_command` connection: this machine's
   public name, port 22, user `pdfa`, profile `custom_command` (the `claude_code_headless` profile is
   the API-key one), model/pin `claude-opus-5`, billing `not_metered`. With this command the connection's timeout
   does not bound a call (see «A call lives while the session is alive» below): a stand that reads the command's
   signs of life lets a call run up to 2 hours and cuts it after 10 minutes of silence.
   Generate the key: the application shows the public half and the line
   `restrict ssh-ed25519 AAAA… auditmanager:<connection id>`.
4. Put that line in `~pdfa/.ssh/authorized_keys` with the forced command added to its options:

   ```text
   restrict,command="/usr/bin/python3 /opt/pdf-analysis/claude_answer.py --ssh-envelope --claude /home/pdfa/.local/bin/claude" ssh-ed25519 AAAA… auditmanager:<connection id>
   ```

   `restrict` switches off forwarding, agent, X11 and the terminal; `command=` makes sshd run only this,
   whatever the client asks for. Replace the `claude` path with `command -v claude` of that account
   (sshd gives the command a minimal `PATH`, so the path is absolute). `~pdfa/.ssh` and the file must
   be owned by `pdfa` and not writable by others.

   **Sonnet** is a second connection, not a setting of the first: one command line serves one model. Create
   another `ssh_command` connection with model/pin `claude-sonnet-5` (its own key, its own line) and put
   `--model claude-sonnet-5` before `--claude`:

   ```text
   restrict,command="/usr/bin/python3 /opt/pdf-analysis/claude_answer.py --ssh-envelope --model claude-sonnet-5 --claude /home/pdfa/.local/bin/claude" ssh-ed25519 AAAA… auditmanager:<id of the Sonnet connection>
   ```

   Both lines may sit in the same account's `authorized_keys`. They share that account's subscription and its limits.
5. Press «Проверить». On first contact the stand shows the host key fingerprint instead of calling:
   compare it with `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub` on this machine, confirm it, and
   press «Проверить» again. An `ok` probe proves reachability, the pinned host key, the forced command,
   the login and the reported model. Then route «Анализ текста» and run one test-data analysis.
   Removing the line from `authorized_keys`, or the route, stops use at once.

The stand sends one task JSON on stdin and reads one JSON line on stdout:
`{"model","output_text","stop_reason","input_tokens","output_tokens","reported_cost_usd"}`. The same
CLI boundary as section E applies (no tool, no MCP server, no `CLAUDE.md`, task text never on the
command line, environment allow-list), and the same acceptance rule: the CLI's own `modelUsage` must
name `claude-opus-5` and nothing else, so the stand records the model as **reported**. With a schema
in the task the answer is the structured object; the probe sends none and gets plain text.
`reported_cost_usd` is always `null`: the CLI prints a list-price estimate for a subscription run, and
the connection is `not_metered`. A task with an image is refused (`image_input_unsupported`); the
stage that sends crops is not active. (`ssh-forced-command.sh` reads the stand's `image` member
as one `{"media_type","data"}` object, or a list of up to eight, 32 MiB of PNG together, and
passes every image to the CLI as an image block; the reply envelope command above serves none.)

**A call lives while the session is alive** (`AR-V3-LIVENESS-01`). Nothing limits the model's thinking,
effort or turns. The command runs the CLI with `--output-format stream-json --verbose --include-partial-messages`
and judges the call by its stream, not by one short deadline:

- *Heartbeat.* In `--ssh-envelope` mode the command writes one line to **stderr** when the CLI starts and then
  every `HEARTBEAT_SECONDS` (30) while it runs, exactly
  `pdf-analysis-forced-command: hb <elapsed_seconds> <events> <output_tokens>`: three non-negative decimal
  integers (seconds since start, stream lines read so far, the latest `output_tokens` of a `message_delta` or `0`)
  and nothing else; never task text, schema, key or model output. A stand that knows the line takes it as a sign of
  life; an older stand ignores stderr. If the line cannot be written (the stand hung up) the CLI is stopped.
- *Stall.* No new byte in the stream for `STALL_SECONDS` (600) ends the call: `claude_stalled`.
- *Hard cap.* `SSH_HARD_CAP_SECONDS` (7140, 60 seconds below the stand's 7200-second ceiling) ends the call at the
  latest: `claude_timeout`. The old fixed 840-second deadline is gone. The stream file may reach 64 MiB
  (`MAX_STREAM_BYTES`, thinking deltas are many), the `result` line 8 MiB; more is `claude_output_too_large`.
- *Effort.* The task may carry `effort`, one of `low`, `medium`, `high`, `xhigh`, `max`; it is passed as
  `--effort <value>`. Any other value fails the task with `invalid_effort`; with no `effort` the flag is not
  passed and the CLI keeps its default. No `--max-turns`, `--max-budget-usd` or thinking cap is ever set.

The acceptance rule is unchanged and applies to the last `result` line: a successful, completed, tool-free turn
whose `modelUsage` names the served model and nothing else, with a `structured_output` object when the task has a
schema. A stream with no `result` line is `claude_no_result`; lines that are not JSON objects are skipped and are
never a report. The reasons the command prints on failure are fixed words.

## Known limits of the Claude profiles

- No `claude` CLI was available on the host that built this: the settings syntax, the MCP
  handshake and the skill were checked against the documentation (code.claude.com settings,
  permissions, CLI reference; modelcontextprotocol.io 2025-11-25 and 2026-07-28), and the bridge
  is tested over its stdio against a fake server, but **not against a real Claude Code
  session**. Section A.6 is the acceptance test of that half.
- A session's id as Claude Code shows it may differ in form from the pin (for example a session may report `claude-sonnet-5-5`
  while the lock pins `claude-sonnet-5`). The skill fails closed;
  if `/model` shows another spelling, the owner decides before anything is relaxed.
