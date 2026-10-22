STATUS: 5/5 unit tests green (148), sshd integration written, container run pending gate END (12:15 +05)

# EXEC-SSH-TRANSPORT - progress and report

Lane `agent/exec-ssh-01`, base `c00b276a` (EXEC-SEAL-01 contract). Standalone SSH transport for
executor connections: the transport half of `EXEC-SSH-01` Work 1-4. Owner rulings: R-144e (elapsed
time governs), R-144b (basic functional checks only). Standard library plus the OpenSSH client
binary; no `paramiko`, no `asyncssh`.

## Files (all inside the allowed paths)

| File | What |
| --- | --- |
| `src/auditmanager/executors/ssh_transport.py` | `SshEndpoint`, `known_hosts_line`, `host_key_fingerprint`, `private_key_file`, `build_ssh_argv`, `scan_host_key`, `run_command`, `open_tunnel`, `ssh_destination`, `scrub_stderr`, `SshFailure` |
| `src/auditmanager/executors/claude_output.py` | `parse_claude_output` -> `(result_text, reported_model)`, `ModelIdentityError` |
| `infra/deploy/Dockerfile.api` | `openssh-client` added to the runtime stage's `apt-get install` line (comment updated) |
| `tests/unit/executors/test_ssh_transport.py` | fake `ssh` / `ssh-keyscan` on PATH: argv, key mode and unlink, every outcome, `sent`, scrub, tunnel, destinations |
| `tests/unit/executors/test_claude_output.py` | one model, none, two, stream-json, conflicts, unsuccessful runs, garbage |
| `tests/integration/executors/test_ssh_sshd.py` | against the fixture container; skipped unless `EXEC_SSHD_PORT` is set |
| `tests/fixtures/sshd/**` | Dockerfile, `sshd_config`, `forced-command.sh`, `entrypoint.sh`, `rotate-host-key.sh`, `up.sh`, `down.sh`, README |

No `executors/__init__.py` was created (the module is importable as a namespace sub-package of
`auditmanager`, and the repository's `--import-mode=importlib` needs no test `__init__.py`).

## Behaviour worth knowing

- **Exit status 255 is the only ssh diagnosis.** Stderr is classified only when ssh exits 255; a
  remote script that prints "Permission denied" and exits 1 is `protocol_error`, `sent=True`,
  with `exit_status=1`.
- **`sent`.** `False` for failures ssh reports before authentication completes (host key, key
  refused, unreachable, connect timeout). `True` for a wall-clock timeout, a keep-alive loss
  ("Timeout, server ... not responding"), output over the bound, a non-zero remote status and an
  unrecognised 255 (plan 3: outcome-unknown).
- **The connect phase gets a deadline shorter than the call** (`min(10, timeout_s - 1)`), so a stuck
  connect is ssh's "Connection timed out" (`timeout`, `sent=False`) and not our kill (`sent=True`).
- **No TOFU in the call path.** No pin, or a malformed pin: `host_key_unpinned` before any process
  starts. The known-hosts file holds exactly the pin; `GlobalKnownHostsFile=/dev/null`; `-F /dev/null`.
- **Known-hosts form.** `[host]:port keytype base64`, except for port 22, where OpenSSH files the
  bare host (`[host]:22` never matches; checked with `ssh-keygen -F`). The stored/returned host-key
  value is `keytype base64`; `scan_host_key` returns that, and any ssh-keyscan/known-hosts style line
  is accepted and normalised (key type and blob consistency checked).
- **No remote command is ever named**; the forced command decides. Neither key nor task is on argv.
- **Key file.** Private (0700) directory under `/dev/shm`, key 0600, removed in a `finally`; the
  system temp directory is used (with a log warning) only if `/dev/shm` is unavailable.
- **Environment.** ssh gets `PATH`, `LC_ALL=C`, `LANG=C` and `HOME=<private dir>` only (no agent
  socket, no proxy or parent secrets).
- **Tunnel.** Readiness is a TCP connect to the local port; the readiness connect reaches the remote
  target once and closes. A taken port is retried with another (3 attempts). Exit terminates the PID
  this call started (SIGTERM, SIGKILL after 5 s).

## Commands and results

(see the end of the file; filled in as they were run)
