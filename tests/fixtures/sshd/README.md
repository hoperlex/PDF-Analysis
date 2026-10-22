# Test sshd for the executor SSH transport

A throwaway Alpine container with OpenSSH, used by `tests/integration/executors/test_ssh_sshd.py`
(`EXEC-SSH-01`). It is not deployed and holds no secret: the keys are generated per run.

What it is:

- key-only authentication for one account, `runner` (no password, no keyboard-interactive);
- the account's `authorized_keys` line is the shape the runbook installs on a real machine:
  `restrict,port-forwarding,permitopen="127.0.0.1:8080",command="/usr/local/bin/forced-command.sh" <key>`.
  `restrict` switches off the pty and agent/X11 forwarding; `command=` runs the script whatever the
  client asks for; `permitopen` allows exactly one forward, to the stub model;
- `forced-command.sh`: reads one JSON object on stdin and echoes it as
  `{"ok":true,"echo":...,"ssh_original_command":"..."}`. Optional input fields: `sleep_s`,
  `stderr_text`, `stdout_bytes`, `exit_status`, `claude_model` (answers like
  `claude -p --output-format json` with that one model in `modelUsage`);
- a stub HTTP model on `127.0.0.1:8080` inside the container (`GET /ok.json` returns
  `{"model":"stub-model","ok":true}`), reachable only through the tunnel;
- `rotate-host-key`: replaces the host key and reloads sshd (the "changed host key" case).

## Run

```sh
eval "$(tests/fixtures/sshd/up.sh)"        # build, generate keys, start; prints the env
python3 -m pytest -q -p no:cacheprovider tests/integration/executors/test_ssh_sshd.py
tests/fixtures/sshd/down.sh                # remove the container and image
```

`up.sh` publishes the container on `127.0.0.1:52222` (override with `EXEC_SSHD_PORT`) under the name
`exec-ssh-sshd` (`EXEC_SSHD_CONTAINER`). The test reads:

| Variable | Meaning |
| --- | --- |
| `EXEC_SSHD_PORT` | Host port of the container. **The test is skipped unless this is set.** |
| `EXEC_SSHD_STATE` | Directory with `client_key` (accepted) and `refused_key` (not installed). |
| `EXEC_SSHD_HOST` | Optional, default `127.0.0.1`. |
| `EXEC_SSHD_CONTAINER` | Optional, default `exec-ssh-sshd`; used by `docker exec ... rotate-host-key`. |

The host-key rotation test needs the `docker` CLI and skips without it. Run it on its own: it
changes the container's host key, so any pin made earlier stops matching.
