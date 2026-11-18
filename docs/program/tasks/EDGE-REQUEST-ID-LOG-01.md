# Task EDGE-REQUEST-ID-LOG-01 — the proxy logs the request ID it returns

- **Owner:** pdf-analysis-18. The owner approved the port and its publication to `origin/dev` and `origin/main` by poll on 2026-11-18.
- **Source:** `task/w52-edge-correlation-log` (`8a0976322`, `W52-DEBT-EDGE-LOG-129-01`, 2026-10-09). The branch never reached dev and was 4 510 commits behind. It is kept in `.local/archive/branch-cleanup-2026-11-18/unmerged-branches.bundle`.
- **Base:** `origin/dev` = `origin/main` = `42fc92a4b` (0.31.1).

## Outcome

The proxy's own 401 and 429 envelopes return `"correlation_id":"$request_id"`. Both listeners (`nginx.conf` on 8080 and `tls-server.conf` on 8443) now log that value in one format, `auditmanager_correlation`:

```text
$remote_addr [$time_local] "$request_method $uri" $status $body_bytes_sent request_id=$request_id
```

An operator who holds the envelope finds the line with `docker compose logs proxy | grep request_id=<id>`. The format logs no query string, header, credential or body. The image's `main` format logged the full `$request` with the query string.

## Paths

- `infra/deploy/proxy/nginx.conf`: the `log_format` at http level, and `access_log` in the server block.
- `infra/deploy/proxy/tls-server.conf`: `access_log` in the server block.
- `tests/contract/test_proxy_request_correlation_log.py`.

`acme-challenge.conf` is unchanged: it serves no refusal envelope.

## Change from the 2026-10-09 branch

The log goes to `/dev/stdout`, not `/var/log/nginx/access.log`. In the pinned image (`nginx:1.27-alpine`) the second path is a symlink to `/dev/stdout`, so production is identical. The difference shows in `tests/integration/composition/test_edge_credential_gate.py`, which runs the server blocks under a local nginx on the host. There the old path would write test requests into the host's real `/var/log/nginx/access.log`: the host nginx also serves another application. As a non-root user, it would fail to open the file at all.

The `access_log` stays at server level. A second http-level `access_log` would add a line per request beside the image's `main` line instead of replacing it, and the contract test refuses one.

## Checks

- `pytest tests/contract/test_proxy_request_correlation_log.py`: the guard, and each of its refusals shown able to fail.
- `pytest tests/contract/test_proxy_rate_limits.py tests/contract/test_proxy_security_headers.py tests/integration/composition/test_edge_credential_gate.py`.
- `nginx -t` in the pinned image with both files loaded.
- `git diff --check`.

Results on 2026-11-18, all on this candidate's tree:

- `git diff --check` passed.
- The four test files: **126 passed** in 29 s. That count includes `test_edge_credential_gate.py` against a real local nginx.
- The new guard on the base tree `42fc92a4b` reports three problems: no format, and no access log in either server. It is green on the candidate.
- `nginx -t` in `nginx:1.27-alpine@sha256:65645c7b…` with `nginx.conf` and `tls-server.conf` loaded passes on the candidate and on the base. The run used a throwaway self-signed certificate, with `api`/`web` mapped to loopback.
- Live probe: the candidate `nginx.conf` ran in the pinned image, and 12 `POST /api/v1/registrations` were sent. The 429 envelope's `correlation_id` `530ee465843c3a8b6dc21a6c204cdc42` appeared in `docker logs` as `"POST /api/v1/registrations" 429 296 request_id=530ee465843c3a8b6dc21a6c204cdc42`.

Not run: `make gate`. This change touches only the proxy's log lines, which the checks above cover directly.

## Rollback

Revert the commit. No data, contract, migration or application code depends on the log format.

## Enumerator ownership
- enumerated_set_changed: no

## Captured premise evidence
- premise: in the pinned proxy image, `/var/log/nginx/access.log` is a symlink to `/dev/stdout`, and the image's own `nginx.conf` sets `access_log ... main` at http level before including `conf.d`

### P-01 — the pinned image's log paths
- captured_at: 2026-11-18
- command: `docker run --rm --entrypoint sh nginx:1.27-alpine@sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10 -c 'ls -la /var/log/nginx; grep -n -E "access_log|include|log_format" /etc/nginx/nginx.conf'`
- captured_output:
  ```text
  lrwxrwxrwx    1 root     root            11 Apr 16  2025 access.log -> /dev/stdout
  lrwxrwxrwx    1 root     root            11 Apr 16  2025 error.log -> /dev/stderr
  15:    include       /etc/nginx/mime.types;
  18:    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
  22:    access_log  /var/log/nginx/access.log  main;
  31:    include /etc/nginx/conf.d/*.conf;
  ```
- interpretation: `/dev/stdout` reaches the same stream as the image's access log. A server-level `access_log` replaces the inherited http-level `main` line for that server instead of adding a second line.

## Historical evidence
- correction_mode: none

## Publication authority
- development_target: origin/main
- origin_main_authority: delegated release integrator EDGE-REQUEST-ID-LOG-01
- owner_instruction: the owner's poll of 2026-11-18 answered «Да, dev и сразу main» for this port. The same checked SHA goes to `origin/dev`, then fast-forwards `origin/main`. This happens after a live-run check and a notice to the peer session that published 0.31.1.
