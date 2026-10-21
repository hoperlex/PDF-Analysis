# HARDEN-AUTH-EDGE-01 -- the credential exchange is counted per address, and a stranger is refused before the upload body is read

Lane of the 2026-10-21 programme, beta criterion `B8`. Debts `D-192` (`EXPOSURE-REVIEW-01.md`
`E-4`, `E-5`) and `D-193` (`E-8`). Base `origin/dev` `ff58bdd1`. Branch `agent/harden-auth-edge-01`.
Everything here is inside the repository; the host's TLS terminator and firewall (`E-1`, `E-2`,
`E-3`, `E-6`, `E-7`) are not touched.

**`infra/**` changed.** A publication of this to `origin/main` needs the full gate
(`AGENTS.md` section 8, case 3, and `MAIN_AUTODEPLOY_POLICY.md`).

## 1. What changed

| Finding | Change | Where |
|---|---|---|
| `E-4` | `POST /api/v1/auth/token` is counted per client address: a second `map` and `limit_req_zone` (`token_exchange`, 6 a minute, burst 10, `nodelay`, status 429, the `rate_limited` envelope), applied in `location /api/v1/` and repeated in the API upload location, as the registration limit is | `infra/deploy/proxy/nginx.conf`, `tls-server.conf` |
| `E-5` | Each of the two 260 MiB upload locations carries an `auth_request` to an internal location that asks the addressed tier one authenticated read (`GET /me` on the API, `GET /bff/v1/me` on the web tier). A 401 is answered at once with the catalog's `authentication_required` envelope (`@authentication_required`) and the body is never read | same two files |
| `E-8` | The four stale statements are rewritten as history with today's behaviour (401) beside them | `compose.server.yml`, `env/alpha.env.example`, `deploy.sh`, `docs/program/DEPLOYMENT_RUNBOOK.md` |

## 2. Decisions

1. **A zone of its own for the exchange.** The registration budget and the exchange budget cannot
   spend each other. The rate is the registration rate: a script exchanges once per run, and the
   only in-tree caller of this path through the proxy is
   `tests/e2e/pc01/journey/verify-acceptance.mjs` (one call per acceptance). The journey signs in
   through the browser form (`POST /bff/v1/session`), and the web tier reaches the API on the
   compose network, so neither crosses this limit (`grep -rn "auth/token" tests scripts infra`).
   The per-account brake is untouched.
2. **The browser sign-in route is not added to the edge.** `POST /bff/v1/session` is not a separate
   nginx location: it falls under `location /` and meets the web tier's own bucket
   (`guest-throttle.ts`). `E-4` is about the direct API path. Adding a `limit_req` to `location /`
   would be a decision about the web tier's door and about the shared-bucket question `E-3`.
3. **`auth_request`, not a presence check, not `proxy_request_buffering off`.** A check that the
   `Authorization` header or the cookie is merely present is passed by `Bearer x`, and then nginx
   still buffers 260 MiB. Turning request buffering off moves the volume to the application (and to
   the web tier's memory for the BFF path). `auth_request` runs in the access phase, before the
   content phase reads the body, on both paths, with the caller's own headers, so it sees what the
   application will. It decides "is this credential live", never "may it upload to this project".
4. **`client_max_body_size 260m` in the two internal locations is required.** A subrequest shares
   the request's headers and nginx compares the DECLARED length with the cap of the location it
   enters. Measured with the line missing: `client intended to send too large body: 272629760
   bytes ... subrequest: "/_edge/credential/api"`, the check answers 413, and `auth_request` turns it
   into a 500 for every legitimate upload. A body declared above 260 MiB is still refused 413 at the
   upload location, before the access phase, without a body read.
5. **Method-agnostic.** A subrequest cannot see the method it stands for, so `GET listDocuments`
   on the same path costs one extra `getMe` too. Accepted; named in the nginx comment.

## 3. Proof

### 3.1 Before and after, one real nginx, a stub application that records what reaches it

`curl -X POST --data-binary @bundle.bin` of a sparse 260 MiB file (272 629 760 bytes), no
credential, against `/api/v1/projects/prj_.../documents`. Before is `origin/dev`'s `nginx.conf`,
after is this tree's; the harness is `running()` in
`tests/integration/composition/test_edge_credential_gate.py`.

| | status | bytes uploaded before the answer | time | the application saw an upload |
|---|---|---|---|---|
| before | 401 | 272 629 760 | 0.37 s | yes |
| before, 260 MiB declared and no body sent | no answer in 3 s | | | |
| after | 401 | 1 835 008 | 0.005 s | no |
| after, 260 MiB declared and no body sent | 401 | 0 | 0.006 s | no |

### 3.2 The live scenarios (`test_*_live`), on two nginx builds

`nginx/1.24.0 (Ubuntu)` (the host binary, started by the test with its own prefix and pid) and
`nginx/1.27.5` (the pinned `nginx:1.27-alpine`, through a wrapper script in
`AUDITMANAGER_NGINX_BIN`): all four live tests pass on both.

For each of the API and the web upload paths: no credential with 260 MiB declared and no body sent,
a chunked body with a partial chunk, a wrong credential with 1 MiB of the 260 MiB on the wire, and
the other tier's credential each get the 401 envelope (JSON, `authentication_required`, a 32-digit
`correlation_id`, the four security headers) with no temporary body file and no upload request at
the application; four refusals cost exactly four credential reads, none carrying a body or a
declared length; an authenticated 3 MiB upload arrives whole at the application's own path
(prefix stripped on the API path); an authenticated `GET` on the path passes; a body declared at
260 MiB + 1 is refused 413; and `/_edge/...` is 404 from outside.
For the exchange: eleven calls pass (ten plain and one spelled `/api/v1//auth/token?x=1`), the
twelfth gets 429 with the `rate_limited` envelope; eleven registrations still pass afterwards and
their twelfth is 429; `GET /api/v1/me`, `GET /api/v1/auth/token` and `POST /api/v1/projects` are not
counted.

### 3.3 Every new guard shown failing

`test_each_static_guard_can_fail` (20 mutations of the two files, each shown to leave a
problem), `test_each_live_credential_guard_can_fail` (10) and `test_each_live_throttle_guard_can_fail`
(6) run the same functions as the real checks on a mutated copy. The live ones include: either
upload location stops asking (nginx waits for the body and nothing answers), the API location asks
the web tier, the 401 left as nginx's HTML page, the credential location not internal (200 from
outside), the credential location without its cap (500), the declared length forwarded, a different
read asked, the exchange limit removed from the prefix or from the TLS body, the exchange key
renamed, widened to every POST, made the default, or the zone keyed by the registration map.
In `tests/contract/test_proxy_rate_limits.py` 8 mutations were added and 6 retargeted for the
two-zone shape; in `tests/e2e/test_upload_limit_headroom.py` the credential locations are part of
the chain with their own controls; `test_exposure_text_is_current.py` goes red on the four old
texts (taken from `git show origin/dev:...`) and green on the new ones, and on 5 re-inserted stale
sentences, 4 removed corrections and 4 changed code paths.

### 3.4 Configuration validity

`nginx -t` on the pinned image with `nginx.conf` as `conf.d/default.conf`, and with
`tls-server.conf` beside it as `conf.d/tls.conf` plus a throwaway certificate pair: both
"test is successful", exit 0. `bash -n infra/deploy/deploy.sh` is clean.

## 4. Check commands (the rows' own)

* `D-192`: `.venv/bin/python -m pytest -q tests/integration/composition/test_edge_credential_gate.py
  tests/contract/test_proxy_rate_limits.py tests/e2e/test_upload_limit_headroom.py
  tests/integration/composition/test_proxy_tls_path.py` (needs an `nginx` binary for the live
  half; without one it is skipped with the reason, and the static half still holds).
* `D-193`: `grep -rn 'no credential' infra/deploy` prints only five true statements (the health plane
  twice, the stranger-callable registration calls, and the two refusal messages that say a `200`
  is the defect); `.venv/bin/python -m pytest -q tests/integration/composition/test_exposure_text_is_current.py`.

## 5. Risks and known limitations

* `E-3` is unchanged: behind the host terminator every caller may share one bucket, so the new
  exchange budget may be global (6 a minute for direct API sign-ins; the browser door and the
  journey are not affected). That decision stays with the owner/host.
* If the addressed tier is down, the credential check answers 500 and the upload is refused with it
  (it used to be a 502 after a full body read). Failing closed is deliberate.
* The nginx 429 for the exchange is outside the OpenAPI document, like the registration one
  (`EDGE_ONLY_CODES`); the catalog's `rate_limited` note still names only the registration calls.
  Wording for the contract slot, not changed here.
* Scope beyond the grant, each forced by a guard that pins the thing changed: `tests/contract/test_proxy_rate_limits.py`
  (pinned exactly one map, one zone and one `limit_req`), `tests/e2e/test_upload_limit_headroom.py`
  (refused any `client_max_body_size` outside the two upload locations),
  `tests/integration/composition/test_proxy_tls_path.py` (one `proxy_set_header Host`), and
  `docs/program/DEPLOYMENT_RUNBOOK.md` (one of the four statements named by `D-193`).
  `tests/e2e/prove_the_headroom_guard_can_fail.py` was already unrunnable on `origin/dev` (it asserts
  a 25 MiB pre-check literal; the file says 250 MiB); its two helpers were retargeted so they
  mutate the right block once it is repaired, and are shown here only through `nginx_limits`.
* Not run: the browser journey, a database suite, a stack. `tests/integration/composition/test_api_token_channel.py`
  and `test_settings_defaults.py` need the lane's `.env` and database; they fail the same way
  without this change.
