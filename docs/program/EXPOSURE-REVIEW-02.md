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

## 3. The review by theme

Each theme lists what was read, what is sound, and the findings (`F-nn`, severity, position needed, evidence). Section 4 is the table of all findings; section 5 names the
ones that change who can reach the system.

### 3.1 Route groups and their authorization register

**How the seam decides.** One dependency, attached to the whole application (`src/auditmanager/api/app.py`, `_assemble`: `dependencies=[Depends(declare_correlation_id), build_authorization_dependency(...)]`),
runs before every handler, the four documentation routes included (they have no `operationId`, "an unreadable route is a closed route", `api/security.py:1054-1065`). Order, as read at `security.py:1137-1230`:
`operation in UNAUTHENTICATED_OPERATIONS` returns (`:1137`); `operation in RUNNER_OPERATIONS` authenticates a runner token and nothing else (`:1139-1148`); then signature and expiry of the `am2` credential, the account's
standing read from its row on every request (archived, unknown or stale `token_epoch` is one `authentication_required`), the default-credential register, the incomplete-profile register and finally
`OPERATION_ROLES` (`:1206-1209`: an operation named in no register is `permission_denied` for everybody). Roles are never carried in the credential.

**Totality, measured.** A script that reads `contracts/api/v1/openapi.json` (92 paths, 104 operations) and imports the three registers printed:
`{'open': 3, 'runner token': 5, 'any complete account': 6, 'expert': 15, 'admin|expert': 49, 'admin': 26}` = 104, `UNREGISTERED: 0`; the operations with `security: []` in the contract are exactly
`issueToken`, `submitRegistration`, `readRegistrationStatus`, which is `UNAUTHENTICATED_OPERATIONS` (`security.py:243-246`). The served-application sweeps that pin this at run time
(`tests/integration/api/test_role_register.py`, `test_authorization.py:625` `test_the_open_surface_is_exactly_the_register`, `tests/integration/executors/test_runner_seam.py`) need PostgreSQL and were **not run** here.

| Group | Operations | Credential | Who is let in | Reachable without a credential or by the wrong role? |
| --- | --- | --- | --- | --- |
| Exchange and registration | `issueToken`, `submitRegistration`, `readRegistrationStatus` | none | anyone | By design (`R-56`); per-address edge throttle (`nginx.conf:117-150`); a status read answers every pair it cannot prove with the exchange's own 401 (`routers/registrations.py`, `read_registration_status`). Residual: `F-09`, `F-18`, `F-19`. |
| Own account, release notes, product version | `getMe`, `updateMyProfile`, `changePassword`, `markReleaseNotesRead`, `getProductVersion`, `listReleases` | user credential | any active, complete account, roles or none | The subject is `request.state.subject` (verified), never a request field (`routers/releases.py`, `routers/me.py`). An account on the seeded/temporary password or with an incomplete profile reaches only `{getMe, changePassword}` / `{getMe, updateMyProfile, changePassword}` (`security.py:289-291`, `:316-318`). No gap. |
| Product reads (49) | listing, reading, streaming and export-preview of projects, documents, versions, blocks, runs, findings, decisions, norms, optimisation, **`getArV3BetaGroup`, `getArV3BetaGroupReview`, `getArV3BetaPackStatus`**, connections/routes/workers/queue (secret-free by schema) | user credential | `admin` or `expert` | A role-less account is refused (`required.isdisjoint(standing.roles)`, `security.py:1219-1223`, `R-80`). Inside the role there is no per-project check: one organisation, every expert reads every project (`R-146al`, by design). |
| Product writes (15) | `createProject`, `uploadDocument`, `uploadDocumentVersion`, `startRun`, **`startArV3BetaGroup`**, `appendDecision`, `carryOverDecision`, `classifyDocumentVersion`, `correctVersionClassification`, `uploadPriceList`, `setProjectVendorList`, `startOptimisationPass`, `decideOptimisationProposal`, `exportRunCsv`, `exportRunXlsx` | user credential | `expert` | An admin-only account is refused. `cancelRun`/`reauditRun` take `admin` or `expert` (`security.py`, `R-78`). Spend: `F-07`. |
| Administration (26) | users and registrations (`approve/rejectRegistration`, `listUsers`, `updateUser`, `archive/restore/purgeUser`, `resetUserPassword`), executor connections and routes (`create/revise/archiveExecutorConnection`, `setExecutorSecret`, `generateExecutorSshKey`, `requestExecutorProbe`, `setExecutorRoute`), **`issueRunnerToken`, `revokeRunnerToken`**, norm snapshot, execution controls | user credential | `admin` | Self-protection and last-admin rules are in `access/accounts.py` (`_refuse_self`, `_refuse_last_admin`). No gap found; account-level audit gaps: `F-14`. |
| Runner channel (5) | `claimExecutorTask`, `extendExecutorTaskClaim`, `submitExecutorTaskAnswer`, `failExecutorTask`, **`getExecutorTaskImage`** | runner token `amr_<8>_<43>` (own principal) | the token's connection only | A user credential presented here is `authentication_required`; a runner token presented anywhere else fails the `am2` signature check (`security.py:261-264`). Detail below. |

**The runner channel, read end to end** (`api/routers/runner.py`, `executors/runner.py`). Sound: the token shape is checked before any read (`runner.py:279-291`, regex `amr_[0-9a-z]{8}_[A-Za-z0-9_-]{43}`); the
value has 256 bits (`generate_token`, `:152-157`), is shown once and stored as SHA-256 only; comparison is `hmac.compare_digest` and a miss compares against a fixed digest; revoked, expired, archived-connection and
unknown tokens are the same `None`, so there is no oracle (`:279-303`); every task lookup is scoped to the token's connection and a foreign task is `not_found` (`_own_task`, `:311-317`); an image is served only for the
**live claim of this token and Attempt**, only when its `blob_id` is listed in that task's own payload, and the check is repeated after the Blob read (`claimed_image`, `:330-349`; the route returns `Cache-Control: no-store`);
an answer is idempotent, must declare the connection's pinned model, is validated against the task's `output_schema`, and a refusal leaves the claim as it was (`submit_answer`, `:426-459`); a failure reason is
control-stripped and cut at 512 characters (`:472-474`); token lifetime is 1 to 365 days (`api/schemas/models.py:3727`); issue and revoke append `executor.runner_token_issued/revoked` with the actor (`:221-231`, `:255-261`).
Findings: `F-06` (thread starvation by the long poll) and `F-20` (the runner declares the model and the answer text: nothing can verify either, and `R-133` cannot be enforced on this channel).

**AR v3 routes** (`routers/ar_v3_groups.py`, `runs/v3_group.py`). `startArV3BetaGroup` is `expert`; with no sealed pack installed it refuses `dependency_unavailable` (`v3_group.py:225-226`), so the paid path is closed until `PROD-12`. Group and review
ids are ULIDs (`ArV3RunGroupId`), not enumerable. `getArV3BetaPackStatus` answers `state` and, when installed, profile/bundle ids, `pack_sha256`, six scope ids and the reviewer attestation; its schema states
"No map, set or snapshot identity, digest of a scope, path or environment value is ever a property" (`contracts/api/v1/openapi.json`, `ArV3BetaPackStatus.description`). The start command creates a **new group of six Runs for each new idempotency key**
(`v3_group.py:202-330`; `INSERT INTO ar_v3_run_group` with a fresh `ArV3RunGroupId.new()`), with no per-version or per-user limit: `F-07`.

**Release notes and account routes.** Read only `subject.user_uid`; `listReleases` and `markReleaseNotesRead` cannot address another account. `getProductVersion` returns product/build/contract versions to any complete account, roles or none (INFO, `F-23`).

**Registration and users.** Described in `E-9` above. `approveRegistration` takes an `Idempotency-Key` and appends `access.role_granted` with the actor (`access/registrations.py:461`); the applicant's password is stored hashed until the decision.

**Verdict for 3.1: no operation is reachable without a credential beyond the three of the register, and none is reachable by the wrong role in the static sweep.**

### 3.2 Trust boundaries: what the nginx layers forward and set

Files: `infra/deploy/proxy/nginx.conf` (plain listener 8080; http-level maps, zones and `real_ip_*`), `tls-server.conf` (8443, copied beside it by `enable-tls.sh` only when a pair exists), `acme-challenge.conf` (8081, published as public 80).
The three server bodies are kept equal by `tests/integration/composition/test_proxy_tls_path.py` (not run here).

| What a client sends | What the proxy does | What it means |
| --- | --- | --- |
| `Host` | forwarded as `$http_host` (`nginx.conf:254`); `server_name _` on every listener | any name resolving to the host reaches the application; the API builds redirects from it and `proxy_redirect` re-prefixes them (`:329`, `:334`); cookies are host-only; no impact found. The 80 listener answers `301 https://$host$request_uri` (`acme-challenge.conf:51-53`): reflects only to the requester itself. |
| `X-Forwarded-For` | **appended to**, not replaced: `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for` (`:256`) | upstream sees `<client-written>, <peer>`. Nothing in `src/` or `web/src/` reads it (`rg -i "x-forwarded-for" src web/src`: comments only); `real_ip_header X-Forwarded-For` (`:63`) acts only for peers named in `ALPHA_TRUSTED_PROXY_CIDRS` (none by default; refused together with a certificate name, `deploy.sh:471-500`). |
| `X-Real-IP`, `X-Forwarded-Proto` | **overwritten** at server level on both listeners (`nginx.conf:255,257`; `tls-server.conf:98,102`) and again in both `_edge/credential` subrequests (`nginx.conf:463-465,474-477`) | not client-influenceable. The API takes the runner token's "last seen" address from `X-Real-IP` (`security.py:1275-1284`); the web tier keys its guest bucket on it (`guest-throttle.ts:52-53`). |
| `Authorization`, `Cookie` | passed through; the upload `auth_request` forwards the caller's own headers to `getMe` | as intended. The BFF forwards only `accept`, `content-type`, `idempotency-key`, `range`, `x-correlation-id` upstream and replaces the credential with the session's (`web/src/shared/api/credentialed-forward.ts:73-80`). |
| `X-Correlation-Id` | forwarded by the BFF allow-list; honoured by the API when it matches `^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$` (`routers/correlation.py`) | the id written into `audit_event.correlation_id` (`access/audit.py`) is caller-chosen: a collision with another request's id can confuse an investigation (INFO, `F-23`). |
| Body | 32 MiB default (`nginx.conf:212`); 260 MiB at the two upload regex locations (`:385`, `:404`), whose application cap is 251 MiB (`multipart.py:73`) | upload locations authenticate before the body (`E-5`); `client_body_timeout 120s` there only. |

**Rate limits.** Four `limit_req_zone`s of 1 MiB (about 16 000 addresses each): `guest_registration` and `token_exchange` (6 r/m, burst 10, per `$binary_remote_addr`; `nginx.conf:117-150`), `runner_channel` (60 r/m, burst 30, per token prefix)
and `runner_address` (300 r/m, burst 120) (`:188-200`), applied inside `location /api/v1/` and both API upload regexes (`:338-345`, `:391-394`). `location /` (the whole web tier and `/bff/v1/*`, sign-in included) has none (`:503-505`);
no `limit_conn` exists anywhere in `infra/deploy/proxy/*.conf`. **Headers.** The four security headers are set at server level with `always` on all three server bodies, HSTS `max-age=31536000` on 8443 only (`tls-server.conf:83`); no CSP beyond `frame-ancestors`
(decision `C-18`); no `server_tokens off` (`rg server_tokens infra` finds nothing): the nginx version is in every `Server:` header (`F-16`). **TLS.** `ssl_protocols TLSv1.2 TLSv1.3` (`tls-server.conf:77`), no `ssl_ciphers`, no stapling.
**The challenge listener has no `proxy_pass`** (`acme-challenge.conf`; `test_acme_overlay.py` pins it): a request to port 80 cannot reach the application, as `R-146s` requires.

Findings: `F-16` (cipher list and banner), `F-17` (no live assertion of the headers and the cookie flag), `F-18` (no limit on the web sign-in door), `F-10` (no `limit_conn`).

### 3.3 Secrets: where they live and who can read them

| Secret | Where it is | Who can read it | Notes |
| --- | --- | --- | --- |
| Deployment secret `AUDITMANAGER_API_TOKEN` = HMAC key of every user credential (`security.py:545`, `derive_signing_key`) | `infra/deploy/env/alpha.env` (host, mode 600 by instruction) -> env of **`api`** (`compose.server.yml:224`) **and `web`** (`:342`) | operator; any code running in `api` or `web` | `web/src` never reads it (`getApiToken` and `hasServerCredential` are called by tests only; `credentialed-forward.ts:73-80` says the BFF presents "a session's, never the deployment's signing key"). A forged `am2` credential for a known `usr_` id is a full takeover: `F-03`. |
| PostgreSQL password and `DATABASE_URL` | `alpha.env`; env of `postgres`, `migrate`, `release-notes`, `api`, `worker` (`compose.server.yml:74,159,176,203,275`) | operator; code in any of those | One URL for four services, and the user is the image's bootstrap **superuser** (`ADR-0021` line 41): `F-05`. |
| MinIO root credentials = the application's S3 keys | `alpha.env:214-215,224-225`; env of `s3`, `s3-init`, `api`, `worker` | operator; code in `api`/`worker` | The application holds the object store's root account; the server runs as root (`infra/minio/Dockerfile` has no `USER`): `F-21`, `A-6`. |
| Provider key (`PROXY_LLM_TOKEN` / `ANTHROPIC_API_KEY`) and the **private** key ring `AUDITMANAGER_SECRETS_KEYS` | `infra/deploy/env/provider.env` (host), `env_file` of **`worker` only** (`compose.server.yml:308-310`); the `api` "refuses to start with" the ring | operator; code in `worker` | Sound: a stolen administrator session or a compromised `api` can replace a connection's key but not read one (`compose.server.yml:230-234`); the stored connection key is X25519-sealed ciphertext bound to its destination, so editing a revision's address leaves the key unreadable (`executors/commands.py:176-179`); a database dump opens nothing (`provider.env.example:93-95`). `docker compose config` prints `alpha.env` values and, without `--no-env-resolution`, `provider.env` too (`provider.env.example:19-35`): an operator trap, documented. |
| Runner token | shown once in the `issueRunnerToken` response; SHA-256 only in the database | the administrator who issued it; the runner | prefix (12 characters) is shown to administrators and is the throttle key. |
| TLS private key, ACME account key | named volumes `certs` (written by `acme`, mounted read-only into `proxy`) and `acme-state` (mounted by `acme` alone) (`infra/acme/compose.acme.yml:26-30,98-100`) | operator; code in `acme` (account key) / `proxy` (pair) | Sound: the public-facing process never holds the account key. |
| Live user credentials (`am2`, at most 1 h) | `register.json` in volume `web-sessions` (`store.ts:343-345`: mode 600 in a 700 directory), mounted by `web` only | operator; code in `web` | `R-51`, accepted; they never reach a browser. |
| Executor SSH private key | sealed in the database; opened by the `worker`, written to a per-call directory (`executors/ssh_transport.py:283-296`), host key pinned (`StrictHostKeyChecking=yes`, no TOFU in the call path) | operator; code in `worker` | Sound design. |

**Logs, error envelopes, audit payloads.**
*Error envelope:* an unknown exception becomes `internal_error` "carrying nothing from the original" (`routers/errors.py:77-93`); detail keys are screened against the catalog's `safe_detail_keys`; the model provider's own error body is read (at most 4096 bytes,
`analysis/text/proxy.py:86,262`) and dropped (`http_adapter.py`: fixed sentences). *Audit payloads:* the six `access.*` events accept only allow-listed keys with value rules (`access/audit.py:86-110`, `:150-185`): never a password, digest, token, cookie, e-mail, name, IP or user agent;
`executor.*` events carry ids and the secret's `purpose` (`executors/commands.py:263-268`). *Logs:* nginx writes the image's default access format (no `log_format` in `infra/`): client address, request line with query, referer, user agent and the client-written `X-Forwarded-For`, never `Authorization` or `Cookie`;
the API writes uvicorn access lines and warnings that contain **logins and `usr_` ids** (`access/accounts.py:524-529,557,596-601,642-647`); the web tier logs paths only (`store.ts:246-311,349`). What can still carry client text or a secret into a log line: `F-12`. What leaves no log line at all: `F-13`.

Findings: `F-03`, `F-05`, `F-12`, `F-13`, `F-21`.
