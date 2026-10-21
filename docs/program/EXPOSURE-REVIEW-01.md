# EXPOSURE-REVIEW-01 - what a stranger on the internet can reach

Beta criterion B8, owner ruling `R-29` clause 2. Lane `agent/exposure-review-01`, base `origin/dev`
`06591a52`, probe run 2026-10-21 05:15-05:21 UTC from a development host. Read-only: no
configuration, no credential, no POST. This document changes nothing else.

## Verdict

**Not clean: six items need an owner decision (E-1 to E-6).** What is closed is closed as designed: no
unintended port answers, no product data or API description is readable without a credential,
no CORS, no source maps, no secret-pattern hit in the public login bundles. The open points are one conditional
account takeover window (E-1), a cookie without `Secure` and no HSTS on the live origin (E-2), and
four weaknesses behind the TLS terminator that the repository does not contain (E-3 to E-7).
Every fix below is an `infra/**` or owner-side change; per `R-29` none was made here.

## Findings, by severity

### E-1 HIGH (critical if the live `admin` still has the seeded password): `admin`/`password` + public sign-in

FACT (tree). Migration `0006` seeds login `admin`, password `password`
(`db/migrations/versions/20260922_0006_app_user.py:99-100`); `0015` grants that login the `admin`
role (`20261005_0015_accounts_roles_registration.py:78`). The pair is published in code
(`src/auditmanager/access/policy.py:101`). `issueToken` answers without a credential
(`src/auditmanager/api/security.py:236-238`), and both public routes to it exist: `POST /api/v1/auth/token`
and the BFF form `POST /bff/v1/session` (`web/src/app/bff/v1/[...path]/route.ts:1194`). A credential
minted for an account on its seeded password reaches `issueToken`, `changePassword`, `getMe` (`security.py:263-265`),
and `changePassword` is the act that takes the account: whoever completes it first owns an admin.
The sign-in brake (5 failures per 900 s, 300 s block, `src/auditmanager/access/repository.py:171-187`)
slows guessing; it does nothing against a known pair.
`docs/program/RELEASE-0-7-0-DEPLOY-STEPS-01.md` ("Optional wipe", `R-140`) returns the stand to the
seeded `admin` only and puts "First sign-in: change the default password" as step 5, after the push,
the workflow, `verify-deployed.sh` and the public probe. `R-141b` (newer than this lane's base, `origin/dev` `8ab75ce1`) now
rules the wipe before the push, and `STAND-NORMS-IMPORT-RUNBOOK-01.md` (`origin/dev`, section 0 item 5) likewise has the seeded `admin` sign in
only after it. The origin is public for that whole span (live: `/login` 200, probes A1, R3). `infra/deploy/readiness.sh:128-152` can name accounts still on the
seeded password, but nothing in `deploy.sh`/`verify-deployed.sh` calls it.
NOT PROBED: whether the live `admin` is still on `password`. Only a sign-in with that pair could tell;
that is credential guessing and is out of this lane's rules.
DECIDE / RECOMMEND. (1) Now, on the host: run the `default-credential` check of `infra/deploy/readiness.sh`
(it runs `python -m auditmanager.access.check` in the api image); expect `access-check OK no default credentials`.
(2) If the optional wipe is chosen, move the first sign-in and password change to immediately after
`reset.sh` finishes and before the push, in the same sitting, or close the public origin at the host
server block for that window. (3) Longer term (contract/migration slot, owner's call): do not ship a
usable fixed seed password on a public stand (a one-time random seed printed by the migration, or no
sign-in for the seed login until an operator sets a secret).

### E-2 MEDIUM: session cookie is issued without `Secure`, and the live origin sends no HSTS (measured)

FACT (live). A request carrying an inert random `am_session` cookie draws
`Set-Cookie: am_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0` over HTTPS: no `Secure` (probes I1, I2).
No `Strict-Transport-Security` header on any answer from the origin (R1, A1-A7). Port 80 does answer
`301` to the same path on https (R3, J1), so a browser that already holds the name is redirected;
a browser that does not (first visit, typed `http://`, stripped link) sends its first request in clear.
FACT (tree). `Secure` is decided by the first `X-Forwarded-Proto` (`web/src/app/bff/session/store.ts:719-726`),
for the clearing cookie and the real one alike (`route.ts:396`, `route.ts:851`). The container proxy
overwrites that header with `$scheme` of its own plain listener, i.e. `http`
(`infra/deploy/proxy/nginx.conf:143`); only the in-tree TLS block would say `https` (`tls-server.conf:95`).
The live TLS terminator is a different nginx (`Server: nginx/1.24.0 (Ubuntu)`, not the pinned 1.27-alpine)
whose config is not in the tree (E-7). The real cookie is inferred from the same code path, not captured
(capturing it needs a sign-in). Forging `X-Forwarded-Proto: https` changed nothing (I2): not a client-controlled downgrade.
CONSEQUENCE. The cookie and the sign-in form post can cross the network in clear on a first plain-HTTP
visit; with an active network attacker no HSTS means the redirect can be stripped. `HttpOnly` and `SameSite=Strict` hold.
RECOMMEND. (a) Host terminator: add `Strict-Transport-Security` for this one name (a year-long promise for
the name, the commitment `tls-server.conf:43-50` already describes); (b) make `Secure` reach the web tier: forward the
terminator's `X-Forwarded-Proto` through the container proxy (trusted-peer `map` in `nginx.conf`), or put the terminator on
the in-tree TLS listener. (b) is an `infra/**` change that needs the gate. Owner confirms (a) as a commitment.

### E-3 MEDIUM (inference, unmeasured): every caller shares one throttle bucket behind the terminator

FACT (tree). Both guest throttles key on the container proxy's TCP peer: the edge zone uses `$binary_remote_addr`
(`nginx.conf:59-64,80-86`), the web tier uses `X-Real-IP` that the proxy sets from `$remote_addr`
(`nginx.conf:141`, `web/src/app/bff/session/guest-throttle.ts:60-61`). Neither file has `set_real_ip_from`/`real_ip_header`.
FACT (live). Public traffic reaches the stack through a host nginx (E-2). INFERENCE: the proxy's peer is then the terminator
for every client, so registration (6/min, burst 10) and BFF sign-in/registration (10, +1 per 6 s) are one global bucket:
one stranger can exhaust sign-in and registration for everybody, and per-address limits do not exist. Proving it needs POSTs.
Read-only check for the owner on the host: `docker logs <instance>-proxy-1 --tail 5` shows the remote address of recent requests.
RECOMMEND. If confirmed: forward the client address from the terminator and trust it in the container proxy
(`real_ip_header X-Forwarded-For` + `set_real_ip_from <terminator>`), or record that the stand's throttle is global.

### E-4 MEDIUM-LOW: the sign-in exchange has no edge throttle on the direct API path

FACT. The rate-limit map has exactly two entries, both registration calls (`nginx.conf:80-84`; pinned by
`tests/contract/test_proxy_rate_limits.py`). `POST /api/v1/auth/token` is proxied by `location /api/v1/`
(`nginx.conf:218-232`) with an empty key, so it is unthrottled per address, and each call spends one PBKDF2 derivation
(600 000 iterations, `0006:104`; about 0.11 s, `repository.py:164`) even for an unknown login (`registrations.py:36-38`). The browser door is bucketed, the
API path is not (`route.ts:1196` refuses the exchange only under `/bff/v1`). The per-account brake lets an attacker who
sends five wrong passwords every five minutes keep `admin` shut; the code says so (`repository.py:180-185`). Not exercised (POST).
DECIDE / RECOMMEND. Is direct script access to `POST /api/v1/auth/token` from the internet an intended surface?
If not, refuse it at the edge (only the BFF form is needed by the product); if yes, add `POST:/api/v1/auth/token` to the map.
Either is an `infra/**` change. The operator unlock tool is `src/auditmanager/access/unlock.py`.

### E-5 LOW: a stranger can make nginx buffer up to 260 MiB before the 401

FACT (tree). Two public locations take `client_max_body_size 260m` (`nginx.conf:263-280`: `/api/v1/projects/*/documents[...]`
and `/bff/v1/projects/*/documents[...]`); nginx's default request buffering applies (no `proxy_request_buffering`, `limit_conn` or
size directive anywhere in `infra/deploy/proxy/*.conf`), and authorization happens only in the API or BFF afterwards. Disk is the scarce
resource on the stand. `client_body_timeout 120s` bounds a slow client, not volume. The terminator's own body cap is unknown (E-7).
Not exercised. RECOMMEND. Accept for the alpha or add an edge connection limit; record in the debt register either way.

### E-6 LOW / owner to confirm: the host's default site is a different application

FACT (live, outside this tree). `https://135.106.164.147/` (bare IP, certificate mismatch, `-k`) answers `200`, title
"СУ-10: Smart-Допуск | Единый портал охраны труда", 321 619 bytes, `Access-Control-Allow-Origin: *`, its own `x-ratelimit-*` (J3, J5);
`http://135.106.164.147/` answers `301` to it (J2). So the stand shares a host and a terminator with another application; this
lane cannot tell whether that exposure is intended. One GET of its root page was made to read the title; nothing else of it was touched.
RECOMMEND. Owner confirms it is intended and that the two share no secrets, certificates or admin access; the stand's blast radius includes it.

### E-7 LOW: the TLS terminator and the firewall are not in the repository

FACT. `grep -rIl -i "certbot\|letsencrypt\|let's encrypt\|1\.24\.0" docs infra .github scripts` finds nothing; `MAIN_AUTODEPLOY_POLICY.md:32` records
the address only. Live: TLS 1.3 (X25519, AES-256-GCM) and TLS 1.2 accepted, Let's Encrypt `CN=audit.135.106.164.147.sslip.io`, valid
2026-10-01 to **2026-12-30**, SAN matches, chain verifies; HTTP/2; banner discloses `nginx/1.24.0 (Ubuntu)`. TLS 1.1 was not tested (the local client
refuses it). Nine compose-file ports all time out from outside (G, below): dropped by a firewall or bound to loopback; this lane cannot tell which.
RECOMMEND. Commit a sanitised copy of the host server block (HSTS, body cap, rate limits, `server_tokens`, `real_ip`) under `infra/` or a runbook
section so the next review can read it; confirm the renewal timer before 2026-12-30.

### E-8 LOW (documentation): stale statements say the origin or the API description is unauthenticated

`compose.server.yml:344-349`, `env/alpha.env.example:99-103` and `DEPLOYMENT_RUNBOOK.md:75-80` say `/bff/v1` "serves every operation ... with no credential";
`deploy.sh:953-956` says `/api/v1/openapi.json` "needs no credential" while the guard at `:967-999` demands `401`. Live today: `/bff/v1/*` 401 without a session
(C), `/api/v1/openapi.json` 401 (B). They describe the 2026-09-22 state and mislead anyone judging exposure from the text. RECOMMEND: mark them historical (`infra/**`, gate).

### E-9 INFO, accepted by ruling: registration is open and discloses existing logins

`POST /api/v1/registrations` answers `login_taken`/`request_pending` (`registrations.py:14-18`, accepted in the contract text of `submitRegistration`);
the queue caps at 100 pending (`registrations.py:103`) and an administrator must clear it; the login page invites "Подать заявку на доступ" and hints that a "старый логин"
works for a legacy account (probe A1 text). Edge throttle: E-3.

## Confirmed as intended (tree and live agree)

- Only the proxy publishes a port, bound to `127.0.0.1` unless `ALPHA_BIND_ADDRESS` says otherwise (`compose.server.yml:357-358`, `D-49`).
- `/healthz`, `/readyz`, `/metrics`, `/docs`, `/redoc`, `/openapi.json` at the root: Next 404 (D). Under `/api/v1`: the three documentation routes and the document answer
  `401` (R-31, `app.py:65-100`, guard test `test_the_documentation_routes_are_behind_the_seam.py`); the health plane is on a second, unpublished port (`serve.py:90-93`, `nginx.conf:16-19`).
- Exactly three operations carry `security: []` in `contracts/api/v1/openapi.json` (`issueToken`, `submitRegistration`, `readRegistrationStatus`); the other 78 inherit `bearerAuth`;
  the served register equals that set (`security.py:236-238`, `tests/integration/api/test_authorization.py:553`). Every other operation probed answers the declared `401`.
- No CORS anywhere (`grep` of `src web/src infra`: none; `nginx.conf:1-12`); a foreign-Origin preflight gets no `Access-Control-*` (F).
- Four security headers on every answer incl. 401/404 (`nginx.conf:169-172`; live R1, R2, K; absent only on the port-80 `301`). `X-Powered-By` is off (`web/next.config.mjs:13`).
- Static assets: `/_next/static/*` only, immutable, no `.map`, no `sourceMappingURL`, no `public/` directory; 14 public chunks contain no `AUDITMANAGER_*`, `Bearer`, `sk-`, host or port strings (E).
- The web cannot be used as an unauthenticated API: no session -> 401 (`route.ts:1243`); the exchange and the two public registration operations are refused to browsers under `/bff/v1` (`:1196-1197`).

## Part 1 inventory (static)

| Surface | Evidence | Intended |
|---|---|---|
| Published port: proxy `${ALPHA_BIND_ADDRESS:-127.0.0.1}:${ALPHA_HTTP_PORT}:8080` | `compose.server.yml:357-358`; example `8080` `alpha.env.example:93`, bind commented `:117` | yes; public only if the operator sets `0.0.0.0` |
| TLS overlay: `${ALPHA_BIND_ADDRESS:-127.0.0.1}:${ALPHA_HTTPS_PORT:-443}:8443`, loaded only with a cert pair | `proxy/compose.tls.yml:51`, `enable-tls.sh:54-58` | yes; `0.0.0.0` also publishes plain HTTP, no redirect (`tls-server.conf:36-41`, `readiness.sh:170-195`) |
| postgres, s3 (9000/9001), api (8000/8001), worker, web (3000) | no `ports:` (`compose.server.yml:77-78,99-123,224,239,287-325`; `Dockerfile.web:65`, `Dockerfile.api:100` only `EXPOSE`) | yes |
| Dev and promotion stacks | `infra/local/docker-compose.yml:58-59,92-94`, `infra/promotion/compose.yml:57-58`: `127.0.0.1` only | yes; not deployed |
| In-container binds | `serve.py:50` `0.0.0.0` on the compose network only | yes |
| nginx `= /api/v1` and `/api/v1/` -> `api:8000`, prefix stripped | `nginx.conf:213-232` | yes; all auth is in the API |
| nginx upload regexes `/api/v1/projects/*/documents[/*/versions]`, `/bff/v1/...` -> `260m` | `nginx.conf:263-280` | yes; pre-auth cost E-5 |
| nginx `@rate_limited` 429 JSON envelope | `nginx.conf:290-293` | yes |
| nginx `/` -> `web:3000` (everything else) | `nginx.conf:296-298` | yes |
| `/healthz`, `/readyz` not proxied | `nginx.conf:16-19` | yes |
| `issueToken`, `submitRegistration`, `readRegistrationStatus` (`security: []`) | openapi `/auth/token`, `/registrations`, `/registrations/status`; `security.py:236-238` | yes (`R-56`) |
| Public screens `/login`, `/register`, `/register/submitted`, `/403` | `web/src/shared/config/screen-registry.ts:257-284`; all others redirect to `/login?next=` | yes |
| BFF doors `POST /bff/v1/session`, `/session/end`, `/session/password`, `/registration`; `GET /bff/version` needs a session | `route.ts:1172-1188`, `bff/version/route.ts:10-14`; cross-site posts refused `route.ts:538-545` | yes |
| `/_next/image` (Next built-in), `/_next/static/*` | live D/E; `next.config.mjs` configures no `images` | yes; Next 15.5.25 (`web/package-lock.json`), CVE audit out of scope |
| Rate limits | edge 6/min burst 10 on the two registration calls only (`nginx.conf:80-86,224`); BFF bucket 10, +1 per 6 s, shared by session and registration doors (`guest-throttle.ts:44,47`); account brake 5/900 s -> 300 s (`repository.py:171-187`) | partly: E-3, E-4 |
| Default account | `admin`/`password`, forced change before any other operation (`R-50`, `security.py:263-265`) | by ruling; window E-1 |
| Headers | set: nosniff, `X-Frame-Options DENY`, CSP `frame-ancestors 'none'` only, `Referrer-Policy same-origin` (`nginx.conf:169-172`); HSTS only in `tls-server.conf:76`; none of: full CSP, Permissions-Policy, COOP/CORP | by design (`C-18`); HSTS gap E-2 |
| Secrets in env examples | all marked disposable; `deploy.sh:329-361` refuses the shipped four; `provider.env` kept out of `--env-file` | yes |
| SSH forced-command keys (`receive-bundle.sh`, `copy-serve.sh`) | credentialed; not an unauthenticated surface | out of scope |

## Part 2 live probe, reproducible

Target `https://audit.135.106.164.147.sslip.io` (`$H`), resolves to 135.106.164.147. Template, one request per row:
`curl -sS [-I | -X METHOD] --max-time 20 -D - -o /dev/null "https://$H<path>" [-H ...]`.
102 HTTP requests (GET/HEAD/OPTIONS), 9 single connect tests, 2 TLS-only handshakes, over about 6 minutes; at most 7 requests to
any one URL (`/login`, for the TLS and CORS checks), usually 1-2. No body, no `Authorization`, no fuzzing, no retries on failure.
Two requests (I1, I2) carry a random 64-hex `am_session` value that names no session; I2 adds a forged `X-Forwarded-Proto: https`.
Every response carries `server: nginx/1.24.0 (Ubuntu)`; "env" = the 401/404 `ErrorEnvelope` JSON. The four security headers were read on rows R1, R2, K (below) and on the API 404.

| ID | Request | Status | Relevant headers / result |
|---|---|---|---|
| R1 | HEAD `/` | 307 | `location: /login?next=%2F`; no HSTS, no Set-Cookie |
| R2,R4,R5 | GET/HEAD `/login` with `-v`; `--tls-max 1.2` | 200 | TLS 1.3 / AES-256-GCM / X25519, h2; TLS 1.2 also 200; cert as E-7 |
| s_client | `openssl s_client -connect $H:443` | - | subject/SAN `audit...sslip.io`, issuer Let's Encrypt `YE1`, to 2026-12-30 |
| - | `--tlsv1.0 --tls-max 1.1` | - | refused by the local OpenSSL; not a server result |
| R3, J1 | HEAD `http://$H/`, `http://$H/api/v1/openapi.json` | 301 | `Location: https://$H<same path>`; no security headers on the 301 |
| A1-A4 | GET `/login`, `/register`, `/register/submitted`, `/403` | 200 | no Set-Cookie; HTML only |
| A5,A7,D | GET `/`, `/projects`, `/norms` | 307 | `location: /login?next=<path>` |
| A6,D | GET `/admin`, `/admin/` | 404, 308 | no root `/admin` screen; `308` to `/admin` |
| B | GET `/api/v1/{openapi.json,docs,redoc,docs/oauth2-redirect,projects,system/version,me,users,norms/search,execution/workers,registrations,projects/prj_01ARZ3NDEKTSV4RRFFQ69G5FAV/documents}` | 401 | env `authentication_required`, `x-correlation-id: cid-...`, `content-type: application/json` |
| B | GET `/api/v1/{healthz,readyz,metrics,auth/token,'',/,projects/not-an-id,projects/prj_01ARZ3...}` | 404 | env `not_found` (the exchange is POST-only; a GET is a 404, not a 405) |
| B,H | HEAD `/api/v1/projects`, `/api/v1/openapi.json` | 404 | API routes are GET-only; no information |
| C | GET `/bff/v1/{projects,registrations,registrations/status,system/version,me}` | 401 | env (Russian text), `x-correlation-id: web-...` |
| C | GET `/bff/v1/{auth/token,session,registration}` | 404 | env `not_found`; doors answer POST only |
| C | GET `/bff/version` | 401 | empty body, `cache-control: no-store` |
| D | GET `/{healthz,readyz,metrics,docs,openapi.json,redoc,robots.txt,favicon.ico,sitemap.xml,.env,.git/HEAD,server-status,actuator/health}`, `/api/v1/metrics` | 404 | Next HTML 404 (about 12.6 KB), API env for the last |
| D | GET `/_next/static/`, `/_next/`, `/_next/image` | 308, 308, 400 | no directory listing; image optimiser wants `url` |
| E | GET 14 chunks of `/login`; GET/HEAD one chunk; HEAD its `.js.map` | 200, 200, 404 | `cache-control: public, max-age=31536000, immutable`; 0 `sourceMappingURL`; secret-pattern scan 0 hits |
| F | OPTIONS `/api/v1/{projects,auth/token,registrations}` with `Origin: https://evil.example`, `Access-Control-Request-Method: POST`, `-Headers: authorization,content-type` | 404 | env; no `Access-Control-*` |
| F | same, `/bff/v1/{projects,session}` | 204 | `allow: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT`; no `Access-Control-*` |
| F | same, `/login`, `/` | 400 | empty; no `Access-Control-*`. GET with foreign Origin on `/api/v1/projects` 401, `/login` 200: no ACAO |
| I1 | GET `/bff/v1/projects` + inert `am_session` | 401 | `set-cookie: am_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0` (no `Secure`) |
| I2 | same + `X-Forwarded-Proto: https` | 401 | identical cookie: header not trusted from the client |
| J2 | HEAD `http://135.106.164.147/` | 301 | `Location: https://135.106.164.147/` |
| J3,J5 | HEAD, GET `-k https://135.106.164.147/` | 200 | other application (E-6); HSTS `includeSubDomains`, `access-control-allow-origin: *` are its own |
| J4 | HEAD `https://135.106.164.147/` (verify) | - | certificate name mismatch, no request sent |
| K | GET `/api/v1/projects`, `/bff/v1/projects`, `/nonexistent-page`, one static chunk | 401, 401, 404, 200 | `nosniff`, `X-Frame-Options DENY`, CSP `frame-ancestors 'none'`, `Referrer-Policy same-origin` on all four; no HSTS |
| G | `curl --connect-timeout 3 http://$H:{8080,31500,8443,3000,8000,8001,5432,9000,9001}/` | timeout x9 | no direct port answers; filtered or loopback-bound |

Ports 22 and any port outside the compose files were not tested; a port scan was out of the brief.

## Not covered

POST-only behaviour (throttles, body buffering, E-3/E-4/E-5 are tree facts plus inference); the live `admin` password state; real `am_session` flags; TLS 1.0/1.1
and cipher ordering of the terminator; host firewall and sshd; renewal of the certificate; dependency CVEs (Next 15.5.25, Node 24, nginx 1.24.0); the other
application on the host (E-6); data at rest and the session volume (`R-51`); the dev host stacks.
