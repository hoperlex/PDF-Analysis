# Task EXEC-SSH-01 — SSH: run headless Claude Code or a command, and tunnel to an HTTP model

task_id: EXEC-SSH-01

## Outcome

An administrator creates an SSH connection in «Подключения». The application generates
an ed25519 key pair: it seals the private half at once and shows only the public half,
with the `authorized_keys` line to install. That line includes `restrict` and the forced
command. Then «Проверить» runs.

**«Проверить» on the worker:**

1. On a first contact it reads the host key and shows its fingerprint. The administrator
   confirms it, and the confirmed fingerprint goes into a new revision. From then on the
   key is pinned, and a changed host key is refused as `host_key_changed`.
2. It runs the profile once.

**Two connection shapes:**

- **`ssh_command`.** The task JSON goes to the remote command's stdin, and the answer is
  read from stdout. There are two profiles:
  - `claude_code_headless` runs Claude Code with no built-in or MCP tool, JSON output and
    the pinned model (plan T-7), authenticated with an **API key**, metered (plan T-8);
  - `custom_command` runs a recognition script.
- **`http_api` over `transport: ssh_tunnel`.** The worker opens a short-lived local
  forward to the remote HTTP model for the duration of a call. Everything else is
  `EXEC-HTTP-01`.

## Depends on

- `EXEC-HTTP-01` — merged (the resolver seam and probes on the worker).
- `EXEC-AGENT-01` — merged. The two share `executors/**`, `tools/executor-runner/**`, the
  connections widget and the runbook, so they run one after the other.

## Frozen inputs

- base commit: `origin/dev` at the integrator's freeze, after `EXEC-HTTP-01`;
- `generateExecutorSshKey` and `executor_secret.public_material`, as `EXEC-SEAL-01`
  sealed them. This task changes no contract or migration;
- plan §2.1 (`ssh_command`; the `ssh_tunnel` transport), §4.3 T-6, T-7, T-8, §5
  (`R-133` for `ssh_command`);
- Claude Code CLI reference and headless docs (`code.claude.com/docs/en/cli-reference`,
  `.../headless`), read 2026-10-22:
  - `-p`, `--output-format json`, `--model`, `--max-turns`;
  - `--tools ""` disables all built-in tools;
  - `--disallowedTools "mcp__*"` removes MCP tools;
  - `--bare` reads no OAuth credential and needs `ANTHROPIC_API_KEY`;
  - the JSON output's model key is not spelled out, so capture it first.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/executors/**`
- `src/auditmanager/api/**`
- `infra/deploy/Dockerfile.api`
- `tools/executor-runner/**`
- `tests/integration/executors/**`
- `tests/unit/executors/**`
- `tests/fixtures/sshd/**`
- `web/src/widgets/executor-connections/**`
- `web/src/features/manage-executor-connection/**`
- `web/src/entities/executor-connection/**`
- `web/tests/**`
- `docs/program/DEPLOYMENT_RUNBOOK.md`
- `docs/program/EXEC-SSH-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**` and the generated client.
- Dependency and lock files: the worker uses the OpenSSH client binary through
  `subprocess`; there is no `paramiko` or `asyncssh`.
- `infra/deploy/compose.server.yml`.
- The composition root, global styles, `CURRENT_STATE.md`, `DEBT_REGISTER.md`, refs, tags
  and the stand.

## Non-goals

- No long-lived tunnels, no agent forwarding, no jump hosts.
- No password authentication.
- No ssh from the `api` process: the `api` only generates and seals the key pair.
- No paid call. The headless profile is proven with a stub `claude` script on the test
  `sshd`, and a real `claude -p` run is a manual check recorded in the report.

## Work

0. **Capture the facts.** On a machine with Claude Code installed, capture
   `claude --version` and `claude -p "hi" --output-format json | jq 'keys'`. Keep the
   output in the report and write the parser for the model key that version emits. If
   there is no model key, use `--output-format stream-json --verbose` and read
   `system/init`. Never infer the model.
1. **`Dockerfile.api`.** Install `openssh-client`, and record the image-size delta.
2. **Executor code.**
   - Key generation is `EXEC-SEAL-01`'s. This task uses the sealed private half, bound
     to `host:port`, and never generates a key itself.
   - Revisions carry a profile token only, never command text: the forced command on
     the remote machine decides what runs, so a stolen admin session cannot choose a
     command.
   - Host-key scan and pin: the scan runs only in the probe, never in the call path.
   - The command runner: `ssh -i <tmpfs 0600 file> -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=<pinned file> -p <port> <user>@<host>`.
     The key file is unlinked after the call. There is a timeout, stdout and stderr are
     bounded, and stderr is scrubbed before it is stored.
   - The tunnel runner: `ssh -N -L 127.0.0.1:<ephemeral>:<target>`, ready-checked, and
     closed after the call.
3. **`tools/executor-runner/ssh-forced-command.sh`.** The remote side of
   `claude_code_headless`:
   - it reads one task JSON from stdin;
   - it runs `claude -p --bare --tools "" --disallowedTools "mcp__*" --output-format json --max-turns 1 --model <pinned>`,
     with the prompt from the task;
   - it prints the result JSON.

   `ANTHROPIC_API_KEY` comes from the remote user's protected environment file, never
   from the command line. The runbook gives the `authorized_keys` line, with `restrict`,
   `command=` and a dedicated user.
4. **Tests against an `sshd` test container** (`tests/fixtures/sshd/`):
   - a key the server refuses;
   - an unknown host key;
   - a changed host key;
   - a command timeout;
   - a stub-`claude` answer with the right model, and one with the wrong model
     (`model_identity_mismatch`);
   - a tunnel to a stub HTTP model.

   The sentinel test shows the private key never appears in a response, an event or a
   log.

## Deliverables

The code, the Dockerfile change, the forced-command script, the test fixture, the runbook
section, and the report `docs/program/EXEC-SSH-01.md`.

## Required tests

- command: `python3 -m pytest -q tests/unit/executors tests/integration/executors -k ssh` on the lane's own containers, plus the `sshd` fixture
- expected: all passed.
- command: `docker build -f infra/deploy/Dockerfile.api .` (the image builds; the size delta is recorded)
- expected: success.
- `infra/**` is `AGENTS.md` §8 case 3; the integrator records the gate decision under
  `R-135`.

## Integration contract

Two adapter factories are registered for the kinds `ssh_command` and `http_api` +
`ssh_tunnel`; the resolver is unchanged. The stand needs the new image, then the
operator's `authorized_keys` install on the remote machine.

## Failure/idempotency/security cases

- No TOFU in the call path.
- The private key is on disk only on the worker's tmpfs, for the length of one call.
- Each call refuses a host whose key differs from the pin.
- Remote stderr is truncated and scrubbed.
- The forced command refuses any client-supplied command (`SSH_ORIGINAL_COMMAND` is
  ignored).

## Rollback / feature flag

Remove the route to the SSH connection. Revert the merge, and the image drops
`openssh-client` on the next build.

## Handoff

- changed files: tabulated with the reason for each;
- commands/results: each with its exit status;
- known limits: no persistent tunnel, so each call pays the latency of an SSH handshake;
- integration notes: the operator steps on the remote machine.
