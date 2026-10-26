# EXPOSURE-REVIEW-02 - what a stranger, an expert, an administrator and the host operator can reach in the tree as it would be deployed to production

Plan item `PROD-15` (`PRODUCTION-READINESS-PLAN-01.md`), debt row `D-217`, owner ruling `R-29` clause 2. Successor of
[`EXPOSURE-REVIEW-01.md`](EXPOSURE-REVIEW-01.md) (2026-10-21, `origin/dev` `06591a52`), which probed the live origin and read the tree of its day.
Lane `agent/prod-15-exposure-review-02`, task [`PROD-15-EXPOSURE-REVIEW-02`](tasks/PROD-15-EXPOSURE-REVIEW-02.md), base `9a28f09f`
(`integration/ar-close-1026`, 2026-10-26; migration head `0033_ar_v3_cite_stage_id`, `VERSION` 0.8.2, contract 1.6.0, 92 paths / 104 operations).

**Documents only.** This review read code, configuration and tests; it made no request to any host, started no container, opened no database and
changed no file but this one and its task file. It therefore says what the **tree** does. What the live stand does today (the host nginx, the
live `admin` password, the firewall) is not observable from here and is listed in section 8 as `could not verify`.

## 0. Verdict

**Not clean for a production release with client documents: 2 HIGH (both conditional on a fact the tree cannot show), 7 MEDIUM, 10 LOW, 2 INFO.**
The counts, the three most serious items and the order of fixes are filled in sections 4 and 9 and repeated in the commit message. (This section is
completed last; if it still says "in progress" below, the lane was interrupted.)

STATUS OF THIS DOCUMENT: in progress (section 1 written first so that an interrupted lane loses nothing).

## 1. Method, scope, and decisions of the lane

* **Read, not run.** Every finding below was verified by opening the file at the line quoted. The only things executed were: a Python script that
  sweeps `contracts/api/v1/openapi.json` against the authorization registers (section 3.1); a local `openssl ciphers` listing; a local SQLAlchemy
  behaviour check on an in-memory SQLite engine; a local check that a child process of the same uid reads its parent's `/proc/<pid>/environ`; and
  the no-database tests `tests/contract/test_proxy_rate_limits.py`, `tests/contract/test_proxy_security_headers.py` and
  `tests/unit/access/test_access_check_gate.py` (101 passed). No database test was run (`tests/integration/api/**` needs PostgreSQL and MinIO).
* **Accepted risks are cited, not re-reported:** `A-1` (manual backups; the latest pre-migration copy fetched to the development host), `A-2` (client
  documents and provider terms; `R-146f`, `R-146n` item 4 not accepted), `A-3` (no scans), `A-4` (one host), `A-5`/`A-7` (sections), `A-6` (MinIO
  source build and no inventory), `A-8` (one operator). A finding is reported only where it goes beyond the sentence of the accepted risk, and then it
  says how.
* **Positions.** *anonymous* = a stranger on the internet; *expert* = a signed-in account with the `expert` role (or a stolen session of one);
  *any account* = any active, complete account (also role-less or admin-only); *runner* = the holder of a runner token; *admin* = an account with the
  `admin` role; *operator* = a person with root or the `docker` group on the host (can read every secret by design; findings at this position are
  reported only where a log, a volume or a process boundary gives more than the position needs).
* **Dependencies of the plan item.** `PROD-15` depends on `PROD-01`, `PROD-02`, `PROD-04`, `PROD-06`, `PROD-11`. `PROD-01`, `PROD-02` and
  `PROD-06` are in the tree and were read as built (unobserved on a host, `D-227`, `D-229`, `D-230`). `PROD-04` (database roles) is not in the tree: the
  review says what the tree does today and what the plan item will change. `PROD-11` (removal of AR v1/v2) is not built: the AR v2 routes are still
  served. The review is therefore **repeated at `PROD-17`**; section 9 lists what to re-check.
* **Decided by the lane** (the owner asked for no questions; each is small and reversible):
  1. The task text names `E-1 ... E-7`; the predecessor also carries `E-8` (stale text) and `E-9` (open registration). All nine are in section 2.
  2. Finding identifiers are `F-01 ...`, not `E-nn`, so that nothing is confused with the predecessor's numbering.
  3. Severity is rated on impact *if the stated position is reached*; where reaching it needs a fact the tree cannot show (the live `admin` password,
     an exploitable advisory), the finding is marked "conditional" and rated on the impact, not discounted.
  4. `git merge integration/ar-close-1026` was a no-op: the worktree was created from the tip (`9a28f09f`) and the tip already contains the PROD-02/03
     gates, `JUDGE-FIXES-F2-01`, the project-erase core (`scripts/recovery/project_erase.py`) and `PROD-11D-V3-GROUP-QUEUE-01`.
  5. `docs/program/DEBT_REGISTER.md` and every other file are untouched; the proposed rows are section 10 of this file.

## 2. EXPOSURE-REVIEW-01: every finding, its present status, and what changed in the tree

Legend: **closed** = the tree no longer has the defect and a test or guard shows it; **narrowed** = part of it is gone, the rest is named; **open** = unchanged;
**moved** = the tree changed but the remaining exposure sits outside the tree (the live host, an owner decision) or in another item. "Unobserved" = built in
the tree, never run on a host.

| Id (sev. then) | Status now | What changed in the tree (file:line opened) | What is left |
| --- | --- | --- | --- |
| **E-1** HIGH: `admin`/`password` + public sign-in | **narrowed in the tree; moved for the live stand** | `PROD-02`: `src/auditmanager/access/check.py:139-256` adds `--gate` (one read-only SELECT of the active `admin` row, `:164-167`, verified against `SHIPPED_DEFAULT_PASSWORD` by `:197-208`); `infra/deploy/deploy.sh:1442-1485` guard `default-credential-gate` ends the deploy with `[default_credential]` (exit 3) and recreates the proxy without the 443 overlay; `infra/deploy/lib/proxy-listeners.sh` (`listeners_gate_run`, `listeners_https_wanted`, `listeners_withhold_https`) is the one decision point; `verify-deployed.sh:507` (exit 8), `reset.sh:417-429` and `copy-serve.sh:985-999` (`restore-db` also raises every `token_epoch`) call the same gate. 101 no-database tests pass, among them `tests/unit/access/test_access_check_gate.py`. | The seed is still in the migrations: `db/migrations/versions/20260922_0006_app_user.py:98-99` (`SEED_LOGIN = "admin"`, `SEED_PASSWORD = "password"`), granted `admin` by `20261005_0015_accounts_roles_registration.py:78`, published in `src/auditmanager/access/policy.py:101`; recommendation (3) of the predecessor (no usable fixed seed) was not taken, `R-146z` chose the gate. The gate shuts only **the stack's own 443 listener** (`F-01`): the plain application port stays on loopback in every case, and until the host nginx is replaced (`PROD-01` cutover, `D-227` item 2) the public door is that nginx, which no gate controls. The gate knows one login and one password (`check.py:156`, `:164-167`); a temporary password issued by an administrator is a warning line only (`R-146z`). |
| **E-2** MED: cookie without `Secure`, no HSTS | **narrowed in the tree; open on the live stand (unobserved)** | The in-stack TLS block sends `Strict-Transport-Security "max-age=31536000"` (`infra/deploy/proxy/tls-server.conf:83`) and tells the web tier the truth: `X-Forwarded-Proto $scheme` is `https` on the 8443 listener (`tls-server.conf:102`), and `web/src/app/bff/session/store.ts:719-726` (`requestIsSecure`) reads it, so the cookie is `Secure` (`store.ts:699-715`). The plain 8080 listener still says `http` (`nginx.conf:257`) by design (loopback tunnel). A client-forged `X-Forwarded-Proto` is overwritten by nginx on both listeners. | Nothing in `deploy.sh` or `verify-deployed.sh` asserts HSTS, the cookie flag or the four headers on the served name (`rg -n -i "nosniff\|X-Frame\|set-cookie\|cookie" infra/deploy/verify-deployed.sh infra/deploy/deploy.sh` finds no assertion; `verify-deployed.sh:438` checks certificate life only): `F-17`. The live stand keeps the old behaviour until the cutover. |
| **E-3** MED: one throttle bucket behind the terminator | **closed in the tree for the in-stack terminator; narrowed otherwise** | `infra/deploy/proxy/nginx.conf:63-64` (`real_ip_header X-Forwarded-For; real_ip_recursive on`) acts only for peers listed by `ALPHA_TRUSTED_PROXY_CIDRS` through `proxy/trusted-proxies.sh` (default none). With a certificate name the stack is the first hop (public 443 is published straight to the container), so `$remote_addr` is the client; `deploy.sh:471-500` guard `trusted-proxies-empty-with-name` refuses a trust list together with a name (`D-229` item 4). The web tier keys on `X-Real-IP` set from `$remote_addr` (`nginx.conf:255`, `web/src/app/bff/session/guest-throttle.ts:52-53`); `X-Forwarded-For` is read by nothing in `src/` or `web/src/` (`rg -i "x-forwarded-for" src web/src` finds comments only). | Before the cutover the trust list is an operator setting that must match the host nginx. Whether Docker NAT preserves the client address on the live host (no userland proxy for IPv4) was not observed (section 8). |
| **E-4** MED-LOW: no edge throttle on `POST /api/v1/auth/token` | **closed** (`D-192`) | `nginx.conf:145-150` (map `$token_exchange_client`, zone `token_exchange` 6 r/m) and `:341` (`limit_req zone=token_exchange burst=10 nodelay`), repeated in `tls-server.conf:127`; `tests/contract/test_proxy_rate_limits.py` passes. | The BFF sign-in door `POST /bff/v1/session` goes through `location /` (`nginx.conf:503-505`) with no `limit_req`; it has the web tier's in-memory bucket only (`guest-throttle.ts:44-47`, 10 + 1 per 6 s, 10 000 tracked clients), and every attempt still costs the API one PBKDF2 (`F-18`). The per-account brake can still be aimed at any account (`F-09`, `D-75`). |
| **E-5** LOW: nginx buffers 260 MiB before the 401 | **closed for strangers** (`D-192`); **narrowed** for accounts | `nginx.conf:384-410`: both upload locations run `auth_request` (`:399`, `:407`) against `getMe` through two `internal` locations (`:456-478`); a 401 is answered before any body byte (`@authentication_required`, `:484-487`). In the API, `BodyCapMiddleware._front_door` (`src/auditmanager/api/routers/multipart.py:377-382`) refuses a request with no signed, unexpired, un-revoked bearer before the slot and the body; `MAX_CONCURRENT_UPLOADS = 2` (`multipart.py:76`). | The pre-check proves a live credential, not the `expert` role: any active account (role-less, admin-only, or one on a temporary password, all of which `getMe` admits) still has up to 260 MiB spooled before the `403`. No `limit_conn` anywhere (`F-10`; `D-165` stays open). |
| **E-6** LOW: the host's default site is another application | **moved (owner)** | The stack now needs ports 80 and 443 itself: `deploy.sh` guard `public-ports-free` asks the kernel's listener table (`D-229` item 1, fixed). The cutover therefore stops the other application (`D-227` item 2, runbook step 2 stops there until the owner names a date). | Whether the other application is intended, shares secrets, certificates or admin access with the stand: owner. Nothing in the tree changes who can reach it. |
| **E-7** LOW: terminator and firewall not in the repository | **closed in the tree for the terminator (unobserved); open for the firewall** | `infra/acme/` (`Dockerfile`, `entrypoint.sh`, `compose.acme.yml`, `export-pair.sh`, `check-served.sh`, `client.pin`), `infra/deploy/proxy/acme-challenge.conf` (no `proxy_pass`: `:15-19`, `:34-54`), `tls-server.conf` (TLS 1.2/1.3 only, `:77`), `compose.tls.yml` (443 published only by overlay), `verify-deployed.sh:438` (fails under 14 days), `D-229` item 3 (the ACME client is on a network shared only with the proxy, `compose.acme.yml:49-53,69,97`). | `infra/acme/client.pin` still reads `ACME_CLIENT_APK_VERSION=UNRESOLVED` and the build refuses until someone with a network resolves it (`D-227` item 1); nothing alerts on a failed renewal (`D-227` item 4); the host firewall is still not in the tree and `compose.server.yml:394-404` itself records that Docker-published ports bypass `ufw`. TLS cipher policy: `F-16`. |
| **E-8** LOW: stale text says the origin/API need no credential | **closed** (`D-193`) | `rg -n "no credential" infra/deploy` now finds only true uses (`compose.server.yml:241` the health plane, `nginx.conf:69`, `deploy.sh:1525`, `verify-deployed.sh:162`, `README.md:234`). | - |
| **E-9** INFO: registration open, discloses existing logins | **unchanged (accepted by ruling)**; one new aspect | `POST /api/v1/registrations` and `/status` are still two of exactly three `security: []` operations (section 3.1); `MAX_PENDING_REQUESTS = 100` (`src/auditmanager/access/registrations.py:111`). | `R-146al` says the users are the organisation's employees: the open door has no product need after the first accounts and no switch to close it; a single address fills the 100-slot queue in about a quarter of an hour (`nginx.conf:103-111`): `F-19`. |

**"Confirmed as intended" list of the predecessor, re-checked.** Still true in the tree: only the proxy publishes ports (now up to three: loopback application port, public 80
for the challenge, public 443 behind the gate: `compose.server.yml:420-421`, `infra/acme/compose.acme.yml:112`, `proxy/compose.tls.yml:90`); `/healthz` and `/readyz` are not
proxied (`nginx.conf:16-19`); exactly three operations carry `security: []` (section 3.1); no CORS; `poweredByHeader: false` (`web/next.config.mjs:13`). Not re-probed live: static assets,
source maps, secret patterns in the public bundles.

**Surfaces added since the predecessor** (all read in section 3): the runner channel (5 operations under `/api/v1/runner/tasks/`, migration `0031`), the AR v3 routes
(4 operations under `/api/v1/ar-v3-beta/`, `getArV3BetaPackStatus` among them), release notes (`getProductVersion`, `listReleases`, `markReleaseNotesRead`), the executor connection
administration (`createExecutorConnection` ... `issueRunnerToken`, `revokeRunnerToken`, `generateExecutorSshKey`), the public challenge port 80 and gated 443, the ACME client, the access audit
events, migration `0033`, and (not yet merged to a wrapper) the project-erase core.
