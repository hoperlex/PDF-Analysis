# REAL-IP-EDGE-01 — the per-address throttles count the client, not the host nginx

Debts `D-144` (the web tier's guest bucket) and `D-191` `E-3` (the registration and, since
`HARDEN-AUTH-EDGE-01`, the token-exchange zone), found again by a peer review on 2026-10-21.
Base `origin/dev` ef3c348a. Lane branch `agent/real-ip-edge-01`. Operator steps are in
`DEPLOYMENT_RUNBOOK.md` ("Behind a host nginx — the client address") and the mechanism in
`infra/deploy/README.md` ("The client address").

## 1. The defect, and what was measured

Deployed path: browser → host nginx 1.24.0 (TLS, outside the repository,
`proxy_pass http://127.0.0.1:8080`) → this stack's proxy container. The container accepts every
connection from one peer, so `$binary_remote_addr` is one value for every visitor and each
`limit_req` zone (6 r/min, burst 10) is one bucket for the world; the web tier's guest bucket keys
the `X-Real-IP` the proxy writes from `$remote_addr` and shared the blindness.

Measured here, 2026-10-21, pinned `nginx:1.27-alpine@sha256:65645c7b…` on a user-defined bridge
(`docker network create`, removed afterwards), published as `127.0.0.1:<port>:8080`:
`curl http://127.0.0.1:<port>/ -H 'X-Forwarded-For: 1.2.3.4'` was answered with
`peer=172.29.0.1 xff=1.2.3.4` — the bridge **gateway**, not `127.0.0.1`. (`W49-EDGE-01.md`, its second finding, saw
`172.17.0.1` on the default bridge.)

## 2. What changed

| Where | What |
|---|---|
| `proxy/nginx.conf` | http level, once: `real_ip_header X-Forwarded-For; real_ip_recursive on;` and **no** `set_real_ip_from`. Comment on the key rewritten. |
| `proxy/tls-server.conf` | nothing executable — a note that it inherits the http-level rule (nginx loads both files in one `http`). |
| `proxy/trusted-proxies.sh` (new, mode 100755) | `/docker-entrypoint.d/26-trusted-proxies.sh`; turns `ALPHA_TRUSTED_PROXY_CIDRS` into `conf.d/trusted-proxies.conf` (`set_real_ip_from` per entry) or into nothing; validates (IPv4/IPv6 address or CIDR, prefix 1..32/1..128, **no** `/0`, no names, no `all`, no `unix:`, nothing that is not a literal); a bad value exits 2 and stops the container; an empty one removes a file an earlier start wrote; `--check` validates only. |
| `compose.server.yml` | proxy: one more read-only mount of the script, `environment: ALPHA_TRUSTED_PROXY_CIDRS: ${…:-}` (default empty). |
| `deploy.sh` | guard `trusted-proxies-well-formed`: a non-empty value is checked by the same script (`--check`) before the first `docker` call. |
| `env/alpha.env.example` | `#ALPHA_TRUSTED_PROXY_CIDRS=` with the discovery command and the host-side requirement. |
| docs | README section, runbook subsection (value, host line, UNVERIFIED list, rollback). |

**Why a hook and not the image's `envsubst` templates:** `set_real_ip_from` takes one address per
directive, so a list needs a loop, and the value is pasted into a configuration file so it needs a
validator that fails closed; `envsubst` gives neither. The static `nginx.conf` stays the reviewed
artefact (the rule), the generated file carries only the facts of one host (the peers).
**Why http level:** the TLS body is a copy that must not drift (`test_proxy_tls_path.py`); a rule
at http level is inherited by both server blocks and needs no second copy.
**Why the default cannot be exploited:** with no `set_real_ip_from`, `ngx_http_realip_module`
acts on no request, so `X-Forwarded-For` is never read — shown live, not read off the source.

## 3. The rule, as driven

From a peer in the list: the client is the rightmost `X-Forwarded-For` address that is not itself
trusted (`real_ip_recursive on`); an address to the left of it is never read. From any other peer:
the header is ignored. Two header lines are one chain (last line first). An unparsable value names
nobody (the peer is used). `$remote_addr` is replaced for the request, so `$binary_remote_addr`,
the `X-Real-IP` sent upstream and the access log carry the client. Consequence stated in the docs
and pinned by a test: a host nginx that forwards a client-written chain unchanged lets the client
choose its bucket (“attacker, victim” charges the victim) — the host must set the header
(`$remote_addr`, strictest) or append to it (`$proxy_add_x_forwarded_for`, also safe).

## 4. Tests — `tests/integration/composition/test_real_client_address_at_the_edge.py`

Live (host nginx 1.24.0 via the credential-gate harness, real script output, loopback sources
127.0.0.1/2): untrusted/empty and “peer not in the list” → eleven forged `X-Forwarded-For` values
share one bucket, the twelfth is `429`, the application is told the peer; trusted → independent
buckets per named client in both zones, IPv6 clients, garbage header; chains: forged head, trusted
hops, “attacker, victim”, two header lines; both server bodies (`plain`, `tls`); an untrusted peer
beside a trusted one. Image (pinned image, compose’s mounts, busybox `sh`, `nginx -T`): empty and
unset → `syntax is ok`, no `set_real_ip_from`; list → the two lines loaded from
`conf.d/trusted-proxies.conf`; bad value → non-zero exit, no `syntax is ok`. Compose
(`docker compose config --format json`): value and mount rendered, empty by default. Static: the
rule once at http level, no `set_real_ip_from` anywhere in the two files, mode 100755 in git,
example commented out, docs name the variable, the host line and UNVERIFIED.

Every guard is shown failing (`MUTATIONS` 9 static + 7 live, `HOOK_MUTATIONS` 8, plus the
`deploy.sh` guard deleted from a copy in `test_deploy_script_refusals.py`).

## 5. Not verified, and limits

* The stand itself was not touched or read: its network name and gateway, its host nginx lines and
  the userland-proxy setting are **UNVERIFIED**; the operator procedure reads the gateway from the
  running network.
* `reload-proxy.sh` (not in this lane’s grant) tests a changed configuration in a throwaway
  container **without** the proxy’s environment, so it validates `nginx.conf` with an empty trust
  list; a changed value reaches the container through compose recreating it, and `deploy.sh`’s
  guard validates the value first.
* The gateway can change when the network is recreated; the failure is the old shared bucket,
  never a believed client.
* No numbers are claimed beyond what the tests drive; the figures 6 r/min and burst 10 are the
  existing zones’, unchanged.
* `infra/**` changed: under `AGENTS.md` §8 a `main` publication needs the full gate or an owner
  waiver naming the tip SHA.
