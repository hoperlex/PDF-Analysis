STATUS: 5/5 done except the sshd container run, pending gate END (12:19 +05)

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

| Command | Result |
| --- | --- |
| `nice -n 19 python3 -m pytest -q -p no:cacheprovider tests/unit/executors/test_ssh_transport.py tests/unit/executors/test_claude_output.py tests/integration/executors/test_ssh_sshd.py` | exit 0, **148 passed, 15 skipped** in 5 s (the 15 are `test_ssh_sshd.py`, skipped: `EXEC_SSHD_PORT` unset) |
| Mutation checks (seven edits of `ssh_transport.py`, each restored): key mode 0644, `StrictHostKeyChecking=no`, no stderr redaction, no tunnel terminate, 255-gate removed, `sent=False` on timeout, key directory not removed | each made at least one test fail; restored byte-for-byte |
| Real `ssh` client, no server (scratch run): closed port, unresolvable name, blackhole address with a 4 s deadline | `unreachable`/`False`, `unreachable`/`False`, `timeout`/`False` (nothing sent) |
| `ssh-keygen -F` on the lines we write; `ssh-keygen -lf` against `host_key_fingerprint` | port 2222 `[host]:2222` found; port 22 bare host found, `[host]:22` NOT found; fingerprint equal |

**Not run (pending gate END, dispatcher instruction):** building the fixture image, starting the
`exec-ssh-sshd` container, and `tests/integration/executors/test_ssh_sshd.py` against it. The
fixture files and the forced command are syntax-checked with `sh -n` only (`jq` is not on this
host, so `forced-command.sh` has never been executed); expect a first-run fix or two there.
Also not run: `docker build` of `Dockerfile.api` (so the image-size delta is not measured; Debian
bookworm `openssh-client` is a few MB installed), `make`, `npm`, the full suite.

**To run later:** `eval "$(tests/fixtures/sshd/up.sh)"`, then
`python3 -m pytest -q -p no:cacheprovider tests/integration/executors/test_ssh_sshd.py`, then
`tests/fixtures/sshd/down.sh`.

## Open points

1. **Key format.** OpenSSH 9.6 cannot read an ed25519 key in PKCS#8 form (`BEGIN PRIVATE KEY`):
   `ssh-keygen -y` says `invalid format`. The key `generateExecutorSshKey` seals must be in
   OpenSSH form (`cryptography`: `PrivateFormat.OpenSSH`, header `BEGIN OPENSSH PRIVATE KEY`).
2. **Pin of another key type.** A server that presents a different key *type* than the pinned one
   makes ssh print "No <TYPE> host key is known ... Host key verification failed", which is
   classified `host_key_unpinned` (refused either way; `host_key_changed` is only the "HAS CHANGED"
   banner).
3. **Work 0 is open.** The `modelUsage` key of `claude -p --output-format json` was not captured
   (no `claude` binary on this host); `claude_output.py` documents what to confirm and where to
   change it.
4. **Tunnel readiness** connects once to the remote target and closes; harmless for HTTP.
5. **`known_hosts_line` for port 22** is the bare host, not `[host]:22` (see above).
6. **OpenSSH version.** The option `KbdInteractiveAuthentication` needs OpenSSH 8.7+ (bookworm has
   9.2); an older client fails loudly with exit 255 (`protocol_error`).
