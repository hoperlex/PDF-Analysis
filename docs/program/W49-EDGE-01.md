# W49-EDGE-01 — proxy rate limit and the proxy flag

Task file: `docs/program/tasks/W49-EDGE-01.md`. Controlling plan: `docs/program/dispatch/W49-PLAN.md`
§3.5 ("Throttle for guests, at the proxy") and §4 `W49-EDGE-01`. Base: `2a31edf` on
`integration/w49` (the `W49-SEAL-01` merge, which added `rate_limited` to the catalog). Branch:
`agent/w49-edge-01`. Code commits `6e1cfc6` (the change) and `5ccb4e4` (one comment reworded, no
directive touched); this report is the next and last commit, and `make gate` runs once, at that
commit, after it is made. Its lines are in the hand-back, not here, because a
report cannot name the SHA it is part of.

Lane: worktree `.local/worktrees/w49-edge`, `FOUNDATION_INSTANCE=gate-w49edge`, ports 56590 /
60190 / 60191, checked free with `ss -ltn | grep -E ':(56590|60190|60191)\b'` (no output, exit 1)
before use. Every container this lane started is named `w49edge-*` and was removed by that exact
name; `docker ps -a --filter name=w49edge` was empty after each step.

## 1. What this delivers

**Premise P-01, re-measured first** on the base:
`grep -c 'limit_req' infra/deploy/proxy/nginx.conf infra/deploy/proxy/tls-server.conf` →
`tls-server.conf:0`, `nginx.conf:0` (exit 1). The premise held.

**`infra/deploy/proxy/nginx.conf`, http level, once** (lines 80–86), before the `server` block:

```nginx
map "$request_method:$uri" $guest_registration_client {
    default                             "";
    "POST:/api/v1/registrations"        $binary_remote_addr;
    "POST:/api/v1/registrations/status" $binary_remote_addr;
}

limit_req_zone $guest_registration_client zone=guest_registration:1m rate=6r/m;
```

**Both server bodies** (`nginx.conf` and `tls-server.conf`), inside the existing
`location /api/v1/` — no new `/api/v1` location:

```nginx
        limit_req zone=guest_registration burst=10 nodelay;
        limit_req_status 429;
        error_page 429 = @rate_limited;
```

and one new named location, identical in both:

```nginx
    location @rate_limited {
        default_type application/json;
        return 429 '{"contract_version":"1.0.0-draft.1","error_code":"rate_limited","message":"Too many requests of this kind arrived from this client within the throttle window. Nothing was created or changed; the same request may be sent again later.","correlation_id":"$request_id","retryable":true}';
    }
```

The message is `rate_limited`'s catalog `summary`, verbatim — the sentence the application itself
sends when no call site supplies one (`envelope.py`: "message defaults to the catalog summary"),
so the edge invents no wording. It passes `screen_message`. No `details`: the catalog declares
`safe_detail_keys: []` for this code.

**`infra/deploy/compose.server.yml`** — one line in the `web` service's `environment`, with its
reason as a trailing comment so the change stays one line:

```yaml
      AUDITMANAGER_BEHIND_PROXY: "1"  # W49-EDGE-01: no published port, so X-Real-IP is the proxy's and may key the guest throttle
```

Quoted, so the value is the string `1` whatever YAML does with a bare digit. Rendered by compose
itself (§2.4): `web '1'`, every other service unset.

**Rate and burst, and why.** `6r/m` sustained (one every ten seconds), `burst=10`, `nodelay`, one
bucket per client address shared by both calls.

* A person registers once, retries a refusal (a taken login, a validation error) a few times, and
  asks after the request now and then. Eleven at once (the first plus a burst of ten) leaves room
  for that and for a handful of colleagues behind one office address.
* The sustained rate is set against the pending-request cap (`MAX_PENDING_REQUESTS = 100`,
  `src/auditmanager/access/registrations.py:100`). Unthrottled, one address fills the queue as
  fast as the application can answer a hundred requests (not measured here); at one request per
  ten seconds after the burst it takes about fifteen minutes ((100 − 11) × 10 s), which is time
  for an administrator to notice. The throttle slows a single
  address; it does not stop a distributed flood, and bulk rejection is the registered debt for that
  (`W49-PLAN.md` §3.5, last sentence).
* `nodelay`, because a delayed request holds a connection open on the one published port while
  a refusal frees it, and the refusal says `retryable: true`.
* `1m` zone: nginx's own figure is about sixteen thousand 64-byte states per megabyte; when full,
  the least recently used state is dropped, so exhaustion resets the oldest bucket instead of
  refusing everyone.

Measured, not assumed (§2.3): from a fresh zone, twelve requests at once answer eleven
pass-throughs and one 429; eleven seconds later exactly one more passes and the next is refused.

**`tests/contract/test_proxy_rate_limits.py`** (new). Reads both proxy files and the compose file.
Expected map keys are **derived from the frozen OpenAPI document** (`operationId` in
`{submitRegistration, readRegistrationStatus}` → `METHOD:<servers[0].url><path>`), not written down
a second time. Every check is a function returning what is wrong, so the same function is shown
to fail. It checks:

* the `map` and the `limit_req_zone` exist exactly once, at http level, in `nginx.conf`, the zone
  counts the variable the map yields, and `tls-server.conf` declares neither;
* the map is keyed by `"$request_method:$uri"` and its entries equal `{default: "", <the two
  derived keys>: $binary_remote_addr}` exactly — a regex key, an extra key, `hostnames` or
  `include` all fail it;
* in each server body the `/api/v1` locations are exactly `location = /api/v1` and
  `location /api/v1/`; the latter holds one `limit_req` on the declared zone, `limit_req_status
  <catalog http>` and `error_page <catalog http> = @rate_limited`; none of the three appears
  anywhere else in the file;
* in each file, `@rate_limited` answers `application/json` with one `return <status> '<json>'`
  whose only variable is `$request_id`; status = catalog `http`; `error_code` = `rate_limited` and
  is a catalog code; `retryable` is the catalog's value; `contract_version` = catalog and schema
  const; `message` = catalog summary and passes `screen_message`; `correlation_id` is
  `$request_id`; the key set is exactly the schema's `required` (no `details`); the two
  locations are identical;
* the envelope validates against `error-envelope.schema.json` under a real Draft 2020-12
  validator, driven through the governance interpreter (`.venv/bootstrap/bin/python`, the only one
  holding `jsonschema`), failing closed if it is missing; a `retryable: false` control must be
  rejected by the same validator;
* `AUDITMANAGER_BEHIND_PROXY` appears once in the `web` service, under `environment`, with value
  `1`, and in no other service;
* `test_each_check_can_fail`: 18 in-memory mutations, each asserted to match the file before it is
  applied (§3.2).

## 2. Checks run

### 2.1 `nginx -t` in the pinned image — both files under `conf.d/`, throwaway pair at `/etc/nginx/tls/`

Image from `infra/deploy/compose.server.yml` `proxy.image`:
`nginx:1.27-alpine@sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10`
(already present locally, `docker image ls --digests nginx` shows that digest). The pair is
self-signed, one day, `CN=w49edge-throwaway.invalid`, generated under the worktree's ignored
`.local/` (Docker cannot see `/tmp`, OPERATING_CONSTRAINTS §1) and never committed:

```
openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj "/CN=w49edge-throwaway.invalid" \
  -keyout .local/w49edge-nginx/tls/privkey.pem -out .local/w49edge-nginx/tls/fullchain.pem
```

`tls-server.conf` is mounted as `conf.d/tls.conf`, the name `enable-tls.sh` copies it to.
`--add-host` is required because nginx resolves `proxy_pass` host names at load time and there is
no compose network here; without it the test stops at `host not found in upstream "api:8000"`,
which is about the environment, not the files.

```
$ WT=$PWD; docker run --rm --name w49edge-nginx-t \
  --add-host api:127.0.0.1 --add-host web:127.0.0.1 \
  -v "$WT/infra/deploy/proxy/nginx.conf:/etc/nginx/conf.d/default.conf:ro" \
  -v "$WT/infra/deploy/proxy/tls-server.conf:/etc/nginx/conf.d/tls.conf:ro" \
  -v "$WT/.local/w49edge-nginx/tls:/etc/nginx/tls:ro" \
  nginx:1.27-alpine@sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10 \
  nginx -t; echo "exit=$?"
/docker-entrypoint.sh: /docker-entrypoint.d/ is not empty, will attempt to perform configuration
/docker-entrypoint.sh: Looking for shell scripts in /docker-entrypoint.d/
/docker-entrypoint.sh: Launching /docker-entrypoint.d/10-listen-on-ipv6-by-default.sh
10-listen-on-ipv6-by-default.sh: info: can not modify /etc/nginx/conf.d/default.conf (read-only file system?)
/docker-entrypoint.sh: Sourcing /docker-entrypoint.d/15-local-resolvers.envsh
/docker-entrypoint.sh: Launching /docker-entrypoint.d/20-envsubst-on-templates.sh
/docker-entrypoint.sh: Launching /docker-entrypoint.d/30-tune-worker-processes.sh
/docker-entrypoint.sh: Configuration complete; ready for start up
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
exit=0
```

Run at `5ccb4e4`, the final code commit (first run at `6e1cfc6`, identical output).

**Controls — the same check must be able to fail on this arrangement** (`--entrypoint nginx`,
same mounts unless stated; full output; run at both code commits, identical):

1. map and zone also declared in the TLS file (a copy prefixed with nginx.conf's lines 80–86):
   ```
   nginx: [emerg] limit_req_zone "guest_registration" is already bound to key "$guest_registration_client" in /etc/nginx/conf.d/tls.conf:7
   nginx: configuration file /etc/nginx/nginx.conf test failed
   exit=1
   ```
   This is why the plan puts them in `nginx.conf` once.
2. both files, no certificate pair mounted:
   ```
   nginx: [emerg] cannot load certificate "/etc/nginx/tls/fullchain.pem": BIO_new_file() failed (SSL: error:80000002:system library::No such file or directory:calling fopen(/etc/nginx/tls/fullchain.pem, r) error:10000080:BIO routines::no such file)
   nginx: configuration file /etc/nginx/nginx.conf test failed
   exit=1
   ```
   So the green run above really loaded the TLS block.
3. `tls-server.conf` alone (no `nginx.conf`):
   ```
   nginx: [emerg] zero size shared memory zone "guest_registration"
   nginx: configuration file /etc/nginx/nginx.conf test failed
   exit=1
   ```
   The TLS body depends on the zone `nginx.conf` declares. That is safe because `enable-tls.sh`
   only ever copies it **beside** `default.conf`, which `compose.server.yml` always mounts.

### 2.2 Focused suites (worktree, at `5ccb4e4` plus this report)

```
$ .venv/bin/python -m pytest tests/contract/test_proxy_rate_limits.py \
    tests/integration/composition/test_proxy_tls_path.py \
    tests/integration/composition/test_session_register_volume.py \
    tests/contract/api_v1/test_surface_counts_in_prose.py tests/e2e/test_upload_limit_headroom.py -q
89 passed in 3.05s
$ .venv/bin/python -m pytest tests/contract -q -p no:cacheprovider \
    --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py \
    --ignore=tests/contract/test_validate_bootstrap.py
467 passed, 50 subtests passed in 12.59s
```

`test_the_two_server_bodies_do_not_drift` and
`test_every_api_location_puts_the_prefix_back_on_the_way_out` are in the first run and green.
`test_surface_counts_in_prose.py` is there because it reads `infra/deploy/**`: the new comments
were written to make no surface-count claim.

### 2.3 Dynamic probe — the configuration running, beyond what the task requires

Run at `6e1cfc6`. `5ccb4e4` changes comment lines only:
`git diff 6e1cfc6 5ccb4e4 | grep '^[-+][^-+]' | grep -v '^[-+]#' | wc -l` → `0`.

Same image and mounts as §2.1, detached as `w49edge-nginx-probe` with
`-p 127.0.0.1::8080 -p 127.0.0.1::8443` (random loopback ports; they were 32768/32769, then 32770
after a restart). The upstreams resolve to `127.0.0.1` inside the container, where nothing
listens, so a request the throttle lets through answers **502** and a refused one **429**. The
probe script, verbatim (it lived in the ignored `.local/`):

```bash
H=http://127.0.0.1:${PLAIN_PORT}; S=https://127.0.0.1:${TLS_PORT}
codes() { local m=$1 u=$2 n=$3; shift 3; local out=""; for _ in $(seq "$n"); do out+="$(curl -sk -o /dev/null -w '%{http_code}' -X "$m" "$@" "$u") "; done; echo "$m $u x$n: $out"; }
codes POST "$H/api/v1/registrations" 12 -H 'Content-Type: application/json' -d '{}'
curl -sk -D - -X POST "$H/api/v1/registrations" -H 'Content-Type: application/json' -d '{}'
codes POST "$H/api/v1/registrations/status" 2 -d '{}'
codes POST "$H/api/v1/projects" 15 -d '{}'      # and GET /registrations, approve, reject,
                                                # GET /registrations/status, POST /api/v1,
                                                # POST /bff/v1/registration, 15 each
codes POST "$H/api/v1//registrations?x=1" 2 -d '{}'   # and registration%73, REGISTRATIONS, registrations/
codes POST "$H/api/v1/registrations" 2 -H 'X-Forwarded-For: 203.0.113.9' -d '{}'
curl -sk -D - -X POST "$S/api/v1/registrations/status" -d '{}'
codes POST "$S/api/v1/projects" 3 -d '{}'
```

Output (`PLAIN_PORT=32768 TLS_PORT=32769`):

```
POST /api/v1/registrations x12: 502 502 502 502 502 502 502 502 502 502 502 429
HTTP/1.1 429 Too Many Requests
Server: nginx/1.27.5
Content-Type: application/json
Content-Length: 303

{"contract_version":"1.0.0-draft.1","error_code":"rate_limited","message":"Too many requests of this kind arrived from this client within the throttle window. Nothing was created or changed; the same request may be sent again later.","correlation_id":"d52fdff763b8df9be4d1f23b75841128","retryable":true}
POST /api/v1/registrations/status x2: 429 429
POST /api/v1/projects x15:                  502 (all fifteen)
GET  /api/v1/registrations x15:             502 (all fifteen)
POST /api/v1/registrations/reg_x/approve:   502 (all fifteen)
POST /api/v1/registrations/reg_x/reject:    502 (all fifteen)
GET  /api/v1/registrations/status x15:      502 (all fifteen)
POST /api/v1 x15:                           502 (all fifteen)
POST /bff/v1/registration x15:              502 (all fifteen)
POST /api/v1//registrations?x=1 x2: 429 429
POST /api/v1/registration%73 x2: 429 429
POST /api/v1/REGISTRATIONS x2: 429 429
POST /api/v1/registrations/ x2: 502 502
POST /api/v1/registrations x2 (X-Forwarded-For: 203.0.113.9): 429 429
HTTP/2 429
content-type: application/json
content-length: 303

{"contract_version":"1.0.0-draft.1","error_code":"rate_limited",...,"correlation_id":"562e93716c746162dd715d7391eda35e","retryable":true}
POST https://.../api/v1/projects x3: 502 502 502
```

(the fifteen-request rows are abridged here from fifteen literal `502`s each; the date header is
omitted). nginx's own log line for a refusal:
`limiting requests, excess: 11.000 by zone "guest_registration", client: 172.17.0.1, ... request: "POST /api/v1/registrations HTTP/1.1"`.

Refill, from a fresh zone (`docker restart w49edge-nginx-probe`, then one command):

```
fresh, 12 at once: 502 502 502 502 502 502 502 502 502 502 502 429
01:10:42
01:10:53
after 11 s: 502 429
```

Two earlier refill runs answered `502 502` after the wait; both started from a bucket that had
already drained for longer than eleven seconds between tool calls, which the leaky-bucket arithmetic
predicts, so the run was repeated from a fresh zone rather than read as either a pass or a failure.

The probe container was removed with `docker rm -f w49edge-nginx-probe`.

### 2.4 Compose renders the flag

```
$ docker compose --env-file infra/deploy/env/alpha.env.example -f infra/deploy/compose.server.yml \
    config --format json | python3 -c '<print services.*.environment.AUDITMANAGER_BEHIND_PROXY>'
api '<unset>'
migrate '<unset>'
postgres '<unset>'
proxy '<unset>'
s3 '<unset>'
s3-init '<unset>'
web '1'
```

Only that one field was printed; the rendered configuration (which substitutes the example
file's values in clear) was not.

### 2.5 `make gate`

Runs once, at the final commit (this report), with the tree untouched while it runs. Its literal
lines are in the hand-back.

## 3. Mutations

### 3.1 The four required mutations, each on a disposable copy

Copies built from the final code commit, outside the worktree, one per case (also run once at
`6e1cfc6`, with the same failure sets):

```
SHA=5ccb4e431da22b2576bceee6090c41acbab07309
git -C $WT archive $SHA pyproject.toml src contracts infra/deploy tests/conftest.py tests/support \
  tests/contract/test_proxy_rate_limits.py tests/integration/composition/test_proxy_tls_path.py \
  docs/program/P02_LOCK.json | tar -x -C /root/w49edge-mut/<case>
ln -s $WT/.venv /root/w49edge-mut/<case>/.venv
cd /root/w49edge-mut/<case> && PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest -p no:cacheprovider -q \
  tests/contract/test_proxy_rate_limits.py \
  "tests/integration/composition/test_proxy_tls_path.py::test_the_two_server_bodies_do_not_drift"
```

**Baseline (unmutated copy): `27 passed in 0.15s`**, `rootdir: /root/w49edge-mut/baseline`,
`configfile: pyproject.toml`; the copy's own source is what imports:
`/root/w49edge-mut/baseline/src/auditmanager/shared/errors/__init__.py`. The test file resolves the
files it reads from its own location, so in each copy it reads that copy's `infra/deploy`.

| Case | Mutation | Result |
|---|---|---|
| m1a | `limit_req` line deleted from `nginx.conf` | **4 failed, 23 passed**: `test_the_server_body_throttles_inside_the_one_api_location[nginx.conf]` — `'nginx.conf: \`location /api/v1/\` carries 0 limit_req lines'`; `test_the_whole_guard_is_green`; and the drift test |
| m1b | `limit_req` line deleted from `tls-server.conf` | **4 failed, 23 passed**: `...[tls-server.conf]` — `'tls-server.conf: \`location /api/v1/\` carries 0 limit_req lines'`; whole guard; drift test |
| m2 | map widened to every POST: `map $request_method $guest_registration_client { default ""; POST $binary_remote_addr; }` | **4 failed, 23 passed**: `test_the_map_and_the_zone_are_declared_once_in_the_file_nginx_always_loads` — `'the map is not keyed by "$request_method:$uri": \'map $request_method $guest_registration_client {\''` plus the entries mismatch; whole guard |
| m3 | the compose flag line deleted | **4 failed, 23 passed**: `test_the_web_service_runs_behind_the_proxy_flag` — `'the web service sets AUDITMANAGER_BEHIND_PROXY 0 times: []'`; whole guard |
| m4 | `"error_code":"rate_limited"` → `"error_code":"conflict"` in **both** files (so the drift test stays green) | **6 failed, 21 passed**: `test_the_refusal_is_the_catalog_rate_limited_envelope[nginx.conf]` — `"nginx.conf: error_code is 'conflict', not 'rate_limited'"`, the same for `tls-server.conf`, the schema validation (the schema pins `retryable: false` for `conflict`), whole guard |

In every mutated copy the in-memory self-test whose anchor text the mutation removed also fails,
with `the mutation matches nothing in <file>`; that is the anchor check working, not the guard,
and it is listed in the counts above. Every copy exited `1`.

**nginx accepts three of the mutated configurations**, which is why the static guard is the
thing that catches them — same command as §2.1 on each copy's two files:

```
### nginx -t on m1a-limit-gone-plain
nginx: configuration file /etc/nginx/nginx.conf test is successful
### nginx -t on m2-map-all-posts
nginx: configuration file /etc/nginx/nginx.conf test is successful
### nginx -t on m4-error-code-changed
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 3.2 The in-test mutations (`test_each_check_can_fail`, run by the gate)

Each one is asserted to match its file before it is applied, and the first problem it produces
was printed and read, so none is red for an incidental reason:

```
the limit removed from nginx.conf      -> nginx.conf: `location /api/v1/` carries 0 limit_req lines
the limit removed from tls-server.conf -> tls-server.conf: `location /api/v1/` carries 0 limit_req lines
the 429 handler removed from tls-server.conf -> tls-server.conf: `location /api/v1/` lacks 'error_page 429 = @rate_limited;'
the map widened to every POST          -> the map must yield the client address for exactly the registration calls ...
the map keyed on the method alone      -> the map is not keyed by "$request_method:$uri": ...
the zone declared again in tls-server.conf -> tls-server.conf declares an http-level throttle directive ...
the limit moved to server level in nginx.conf -> nginx.conf: a `limit_req` outside `location /api/v1/` would reach requests ...
a new /api/v1 location for the registration path -> nginx.conf: the /api/v1 locations must be exactly [...]
nginx's own 503 kept                   -> tls-server.conf: `location /api/v1/` lacks 'limit_req_status 429;'
the envelope's error_code changed      -> nginx.conf: error_code is 'conflict', not 'rate_limited'
the envelope's error_code outside the catalog -> tls-server.conf: error_code is 'too_many_requests', not 'rate_limited'
the envelope says retryable false      -> nginx.conf: retryable is False; the catalog pins True
the correlation id a fixed literal     -> nginx.conf: the body must interpolate $request_id and nothing else: []
the envelope gains a detail            -> tls-server.conf: the envelope carries [..., 'details', ...]; the schema requires [...]
the envelope served as nginx's default type -> nginx.conf: @rate_limited does not answer as application/json
the compose flag dropped               -> the web service sets AUDITMANAGER_BEHIND_PROXY 0 times: []
the compose flag set to 0              -> the web service must set AUDITMANAGER_BEHIND_PROXY to 1 in its environment; ...
the compose flag given to the api as well -> api sets AUDITMANAGER_BEHIND_PROXY; only the web tier reads it: ...
```

## 4. Contracts

None changed and none added. This lane consumes catalog revision 9's `rate_limited` (429,
`retryable: true`, category `policy`, `safe_detail_keys: []`) and the `ErrorEnvelope` v1 schema,
and the new test reads both rather than restating them. `contracts/**` is untouched.

## 5. Risks, known limitations and open questions

Open questions are questions; nothing below was decided by this lane.

1. **The deployed proxy does not pick up a changed `nginx.conf` on deploy — measured.** The proxy
   bind-mounts `./proxy/nginx.conf` as a single file, the deploy keeps the proxy container
   (`deploy.sh` header: *"`postgres`, `s3` and `proxy` ... keep their container IDs"*), and
   `.github/workflows/deploy-auto.yml` updates the tree with `git checkout --detach`. A single-file
   bind mount follows the inode, and a checkout replaces the file with a new one. Measured with the
   pinned image and a scratch repository under the worktree's `.local/`:
   ```
   container sees before checkout: version-A
   host file after checkout: version-B          (inode 4470598 -> 4470641)
   container sees after checkout (no restart): version-A
   container sees after docker restart: version-B
   ```
   So `reload-proxy.sh`'s `nginx -t` and `nginx -s reload` validate and reload the **old** file, the
   deploy succeeds, `verify-deployed.sh` (which checks that the proxy answers, not what it loaded)
   passes, and **the throttle is not there.** It applies to every earlier `nginx.conf` change as well.
   Not in this lane's grant (`deploy.sh`, `reload-proxy.sh`, the workflow). **Open question:** should
   the integration or deployment owner restart or recreate the proxy when `infra/deploy/proxy/**`
   changes, and should the deployed check probe for the throttle (for example, the twelfth `POST
   /api/v1/registrations/status` in a burst answering 429 with `error_code: rate_limited`)?
2. **Behind the default `127.0.0.1` binding every caller shares one bucket — measured.** nginx logged
   `client: 172.17.0.1` (the bridge gateway) for loopback requests: a loopback-published port is
   reached through Docker's proxy, so an SSH-tunnelled stand shows one peer for everyone. There the
   per-client throttle is one shared budget for all **direct** callers of `/api/v1/`. The browser's
   registration goes through `/bff/v1` to `http://api:8000` and never meets this limit. A
   publicly bound host (`ALPHA_BIND_ADDRESS`, iptables DNAT) shows real client addresses; not
   measured here.
3. **The OpenAPI document declares no 429** on `submitRegistration` or `readRegistrationStatus`
   (responses `201/409/422/500/503` and `200/401/422/500/503`). The catalog says the code is answered
   only by the edge, and the body conforms to `ErrorEnvelope`, but a client generated from the
   contract meets a status the contract does not list. **Open question** for the contract owner:
   declare it at the next reseal, or keep it edge-only and undeclared?
4. **The `correlation_id` is recorded nowhere.** `$request_id` is unique per request, but the image's
   stock `log_format main` does not include it, and the `limiting requests` error-log line carries no
   request id, so an operator cannot look the id up. Fixing that is an http-level `log_format` change,
   outside "no other proxy change". **Open question.**
5. **Map strings match without regard to case** (documented nginx behaviour). `POST
   /api/v1/REGISTRATIONS` is counted too (probe: `429 429`); it reaches no operation (routes are
   case-sensitive, so the application answers 404). The only effect is that hammering a case variant
   spends the caller's own budget. Exact case-sensitive regex keys would change that; the plan's
   string keys were kept.
6. **A trailing slash is not counted** (`POST /api/v1/registrations/` → 502 in the probe, so it was
   let through). According to the `Y-G` note in `nginx.conf`, the application answers a trailing-slash
   path with a redirect to the slashless spelling, and following that redirect is counted. Not
   re-measured against the application here.
7. **One budget for both calls and both listeners.** Status checks spend the same budget as
   submissions, and the plain and TLS servers share the zone (probe: the TLS listener refused after
   the plain one was exhausted). Both follow from the plan's one map and one zone.
8. **No `Retry-After`.** The contract declares no response headers (the reason `nginx.conf` gives for
   having no CORS), so none was added; `retryable: true` is the signal.
9. **Line references moved.** `W49-PLAN.md` §3.5 cites `nginx.conf:85` for `X-Real-IP`; that line
   is now the blank line between the map and the zone, and `X-Real-IP` is `nginx.conf:140`
   (`tls-server.conf:82` did not move). The plan is not this lane's to edit; a `W49-BFF-01` comment citing `:85` would be stale.
10. **The compose change is one line with a trailing comment.** The grant says "the one line"; the
    reason went into a trailing comment on that line, not into new lines. If the integrator reads the
    grant as "no comment", deleting the comment is the whole fix.
11. **Rate figures are judgement, not measurement of demand.** No traffic data exists for a
    registration flow that is new in this wave; §1 gives the reasoning.

## 6. Integrator

* Merge after `W49-BFF-01` (`W49-PLAN.md` stage D). The paths are disjoint from that lane's
  (`web/**`), so no textual conflict is expected. The web tier should read the flag as the string
  `"1"`, which is what compose passes (§2.4).
* After the merge, re-run `tests/contract/test_proxy_rate_limits.py` and
  `tests/integration/composition/test_proxy_tls_path.py` on the merged tree, and §2.1's `nginx -t`
  (needs a throwaway pair under a directory Docker can see).
* **Before calling the throttle deployed**, see §5.1: the proxy container must be restarted or
  recreated after the checkout, or it keeps serving the previous `nginx.conf`.
* Rollback: revert `5ccb4e4` and `6e1cfc6` (this report's commit is documentation only). No feature flag: the
  throttle is configuration, and reverting it is the off switch.

### Changed files and forbidden hotspots

```
$ git diff --name-only 2a31edf..HEAD
docs/program/W49-EDGE-01.md
infra/deploy/compose.server.yml
infra/deploy/proxy/nginx.conf
infra/deploy/proxy/tls-server.conf
tests/contract/test_proxy_rate_limits.py
```

All five are the task file's `allowed_paths`. `infra/deploy/compose.server.yml` changes by exactly
one added line (`git diff 2a31edf..HEAD -- infra/deploy/compose.server.yml` shows `1 +`), on `web`.
Not touched: `contracts/**`, root locks, `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`,
`PORT_REGISTRY.md`, every other path. No ref was pushed, merged or tagged. No credential is in this
report: the certificate pair was throwaway, self-signed and ignored by git, and §2.4 printed one
non-secret field only.
