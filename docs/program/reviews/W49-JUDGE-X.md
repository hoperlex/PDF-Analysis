# W49-JUDGE-X — attacker entry point, author-independent verdict

Report-only. Repository artifact in English. The owner hand-back is in Russian.

- **Subject SHA:** `1b259556a98e529ecf7378c335fa85b1c9a426b3` (branch `integration/w49`,
  merge "rate-limit the two public registration operations at the proxy").
- **Judge branch:** `agent/w49-judge-x`.
- **Role:** independent attacker. Not an author of anything under test. This file is the only
  path this task writes.

This first commit is the **black-box pass**: it was written before reading
`docs/program/dispatch/W49-PLAN.md`, the `docs/program/W49-*` lane/QA reports, or
`docs/program/reviews/**`. Inputs before this pass were `AGENTS.md`, this task file
(`git show 1b25955:docs/program/tasks/W49-JUDGE-X.md`),
`docs/program/dispatch/OPERATING_CONSTRAINTS.md` §1–§10, and the code, contracts and
migrations at the subject SHA as needed to drive the stand. The cross-examination and the
**verdict** follow in the second commit.

---

## 1. Environment

A stand built from the subject on isolated ports; the public alpha stand was never driven.

| Component | Detail |
|---|---|
| Worktree | `/root/projects/PDF-Analysis/.local/worktrees/w49-judge-x` at `1b25955` |
| Foundation instance | `gate-w49jx` (`.env` = copy of w49-int's with instance/ports/db/bucket renamed; secrets unchanged) |
| PostgreSQL | container `gate-w49jx-postgres-1`, `127.0.0.1:56610`, image `auditmanager-foundation-local-postgres-pgvector:17.11-v0.8.6-8ee86c9` (pinned) |
| MinIO / mc | `gate-w49jx-s3-1` `127.0.0.1:60210`/`60211`; init `gate-w49jx-s3-init-1` |
| Migration head | `0015_accounts_roles_registration` (applied clean; `0014` is the frozen base W49-ACCESS-01 moved) |
| API | subject `infra/deploy/serve.py` under the worktree venv, `AUDITMANAGER_API_PORT=8770`, health `8771`, bind `127.0.0.1`, `AUDITMANAGER_PROVIDER_MODE=recorded`, a disposable `AUDITMANAGER_API_TOKEN`. Reported `wired, operations=34`. |
| BFF | subject `web/` under `next dev` (Next 15.5.25), `127.0.0.1:3000`, `AUDITMANAGER_API_UPSTREAM=http://127.0.0.1:8770`; tested both with `AUDITMANAGER_BEHIND_PROXY=1` and unset |
| Proxy | `nginx:1.27-alpine` (pinned digest, image already present) running the subject's `infra/deploy/proxy/nginx.conf` mounted read-only, private docker network `w49jx-net2`, published only to `127.0.0.1:8090`, throwaway upstream aliased `api`/`web` |

Ports taken for the stand were checked free with `ss -ltn` before use: 8770, 8771 (API);
3000 (BFF); 8090 (proxy, loopback only). `free -g` was checked before every build/start and
stayed above the 2 GB floor (3–5 GB available; a second judge ran in parallel on its own
instance `gate-w49jy`).

### Setup commands (all exit 0)

```
git -C /root/projects/PDF-Analysis worktree add .../w49-judge-x -b agent/w49-judge-x 1b25955   # 0
make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12                                            # 0
npm --prefix web ci                                                                            # 0
make up                                                                                        # 0 (postgres+minio healthy)
make migrate                                                                                   # 0 (-> head 0015; seeded 'admin' default-credential warning as designed)
```

Test fixtures were inserted **directly into the disposable DB** (never into the tracked
tree): a 4×2×2 matrix of accounts (role set {none,expert,admin,both} × profile
{complete,incomplete} × credential {default,changed}) plus one archived account, all hashed
at the real `ITERATIONS=600_000` so the timing probe is not skewed; plus 50 known accounts
and 50 pending requests for the timing probe. The seeded `admin`/`password` row is the
migration's own public default. No credential, cookie or provider body appears in this report.

---

## 2. What was attacked, and what happened

### 2.1 Privilege escalation — every operation × role set × profile state × credential

Driven two ways against the live API.

**(a) Representative matrix.** Each of the 16 matrix accounts issued a credential; a
representative operation in each tier was called: `getMe` (reachable by the default and
incomplete registers too), `listProjects` (any complete account), `createProject` (expert),
`listRegistrations` (admin). Every cell matched the register exactly:

- **Default credential** (`*/*/default`): everything but `getMe` → `403 permission_denied
  required_capability=password_changed`. This includes the admin rows — a default-credential
  admin is refused `listRegistrations`.
- **Incomplete profile, non-default** (`*/incomplete/changed`): `listProjects` /
  `createProject` / `listRegistrations` → `403 permission_denied profile_completed`.
- **Complete, non-default:** `none` reads but cannot write (`403 role:expert`) or administer
  (`403 role:admin`); `expert` writes (createProject `422` = authz passed) but not administer
  (`403 role:admin`); `admin` administers (`listRegistrations 200`) but **cannot** create a
  project (`403 role:expert` — the admin role does not imply expert); `both` does all.
- Check **order** is standing → default-credential → profile → role: an account that is both
  seeded and incomplete answers `password_changed`, not `profile_completed`.

**(b) Full 34-operation sweep** (operation list taken from the served `/openapi.json`):

- as a **role-less complete** account: every `EXPERT` op → `403 role:expert`, every `ADMIN`
  op → `403 role:admin`, every any-complete op reachable (`200`/`404`-on-dummy-id), the three
  open ops reachable. **Violations: NONE.**
- as an **expert complete** account: every `ADMIN` op → `403 role:admin`, expert ops reachable.
  **Violations: NONE.**
- as a **default-credential admin**: every op → `403 password_changed` **except** `getMe`
  (`200`) and `changePassword` (reached) — i.e. exactly the default register. `updateMyProfile`
  is refused `password_changed`, correctly (it is in the incomplete register, not the default
  one). **No escalation.**

**No role, profile or credential state reaches an operation outside its register.**

### 2.2 Credential forgery (escalation by forging identity/roles)

Roles are never carried in the credential; they are read from the account row every request.
Forgery attempts against `listRegistrations`:

| Forged credential | Result |
|---|---|
| genuine role-less token, payload `sub` rewritten to the admin uid, original tag | `401 authentication_required` |
| same, re-signed with a guessed key | `401` |
| two-part token (no tag) | `401` |
| `am1.<body>.<tag>` (old format prefix) | `401` |
| genuine admin token, `ver` (epoch) bumped, original tag | `401` |

Every forgery fails at the signature/format check before any row is read. No privilege
escalation by forgery.

### 2.3 Default credential against the new operations

A credential for an account still on its seeded/reset password reaches only
`{issueToken, changePassword, getMe}`. Against the three new administrator registration
operations:

```
default-admin GET  /registrations                 -> 403 permission_denied password_changed
default-admin POST /registrations/{id}/approve     -> 403 permission_denied password_changed
default-admin POST /registrations/{id}/reject      -> 403 permission_denied password_changed
```

Default credential against the new operations: refused.

### 2.4 Enumeration via `conflict_reason`

`submitRegistration` (unauthenticated) answers:

```
submit new login                        -> 201 pending
submit a login with a pending request   -> 409 conflict  conflict_reason=request_pending
submit a login an active account holds  -> 409 conflict  conflict_reason=login_taken
```

So an unauthenticated caller can learn that a login is (a) already registered or (b) already
applied for. This is a real account-existence oracle. It is **documented and accepted**:
`src/auditmanager/access/registrations.py`'s module docstring states "That `login_taken` and
`request_pending` tell a submitter that a login is known is an accepted limitation the plan
registers." `queue_full` is global and discloses nothing about a login. Classed **register**
(see §3, finding R-1) — not a new defect.

### 2.5 Enumeration via timing — the exchange and the status read

Measured over the loopback stand, 600_000-iteration hashes on every row, fresh fixtures so
the account/request brake (allowance 5) was never tripped. A no-derivation control (`422`)
measured ~1 ms, confirming the PBKDF2 derivation is the dominant term.

Sequential batches (n=50 each):

```
exchange: KNOWN login + wrong password   median 122.8 ms  (p10 115, p90 148, stdev 12.9)
exchange: UNKNOWN login                   median 125.2 ms  (p10 117, p90 148, stdev 12.1)
status:   KNOWN pending request + wrong   median 131.6 ms  (p10 118, p90 157, stdev 23.6)
status:   UNKNOWN login (no request)      median 123.7 ms  (p10 119, p90 144, stdev 11.8)
```

The ~8 ms gap on the status read looked like the extra `_note_a_failed_read` UPDATE that
runs only when a request exists. **Interleaved re-measurement** (alternating each sample,
n=100, to cancel machine drift from the parallel judge) collapsed it:

```
status median delta (has-request − none)       = +2.8 ms
exchange median delta (known − unknown)         = +2.0 ms
```

The exchange delta (+2.0 ms) occurs where there is **no** DB-write asymmetry at all, so ~2–3 ms
is measurement noise, not a signal. **No usable timing oracle** on either path: the
`spend_a_verification` equalization holds empirically. (Doc-accuracy nit R-2 in §3: the status
read's "its timing says nothing" is true in practice; a residual per-login request-existence
side-channel exists only in principle, is swamped by noise, and would disclose only the
already-accepted `request_pending` fact.)

### 2.6 Flooding to the 100-request cap

- **Through `/api/v1/` directly (nginx edge).** `limit_req` keyed by `$binary_remote_addr`,
  `rate=6r/m burst=10 nodelay`: a fresh bucket admitted **11** requests, then `429`. The 429
  body is the `rate_limited` `ErrorEnvelope` — `error_code=rate_limited`, catalog message,
  unique `correlation_id` (nginx `$request_id`), `retryable:true`, **no `details`, no
  credential**, `content-type: application/json`. At 6/min after the burst, filling the
  100-pending `queue_full` cap from one address takes ~15 min, which is the designed brake.
- **Through the BFF (`/bff/v1/registration`).** Token bucket capacity 10, refill one per 6 s:
  first 10 admitted, then `303 ?refusal=throttled`. The bucket is spent **before** the body is
  read or anything is forwarded.
- **From two addresses.** The nginx key is the TCP peer, so two genuine peers get two buckets;
  behind the default `127.0.0.1` binding + tunnel all direct callers share one bucket (could
  not spoof two distinct loopback peers — see §4). The BFF keys by `X-Real-IP` when behind the
  proxy, so two proxied addresses get two buckets.

Only the two exact registration POSTs are throttled — see §2.7.

### 2.7 The nginx map matches exactly the two registration POSTs, and cannot be bypassed

Each experiment on a freshly restarted proxy (zone reset):

```
EXP-A  POST /api/v1/registrations x16                 -> 11 pass, then 429
EXP-B  POST /api/v1/projects, GET /api/v1/registrations,
       POST /api/v1/runs, PUT /api/v1/me  (x15 each)  -> 0 throttled; registration bucket still full after
EXP-C  alternating POST /registrations + /registrations/status -> 11 total across BOTH (one shared bucket)
EXP-D  POST /api/v1/registrations, a different X-Forwarded-For each time -> 11 pass, then 429 (XFF ignored)
EXP-E  POST /api/v1//registrations (double slash)     -> counted; canonical then 429 (same key)
       POST /api/v1/registrations?x=1                 -> counted (query ignored in key)
EXP-F  POST /api/v1/REGISTRATIONS (upper-case)         -> counted (map is case-insensitive); canonical then 429
```

The key is `$request_method:$uri` matched whole; everything but the two registration POSTs
yields the empty string and is never accounted; `$uri` normalisation (double slash, query
string, case) folds to the same bucket, so none of those is a way around the limit. The
administrator's `GET /registrations` and the approve/reject POSTs are never throttled.

### 2.8 A rejected applicant learning anything at sign-in

API `readRegistrationStatus` and BFF `/bff/v1/session` end-to-end:

```
status read: pending + right pair      -> 200 pending
status read: pending + wrong password  -> 401 authentication_required
status read: unknown login             -> 401 authentication_required
reject a request (reason recorded)     -> 200 rejected (reason only in the admin's view)
status read: rejected + right pair     -> 401 authentication_required   (reason NOT disclosed)
status read: approved + right pair     -> 401 authentication_required

BFF sign-in: PENDING  applicant, right pw -> 303 /login?refusal=pending
BFF sign-in: REJECTED applicant, right pw -> 303 /login?refusal=credentials   (== a stranger)
BFF sign-in: APPROVED applicant, right pw -> 303 /projects (signs in)
BFF sign-in: STRANGER (unknown login)     -> 303 /login?refusal=credentials
BFF sign-in: PENDING  applicant, WRONG pw -> 303 /login?refusal=credentials
```

A rejected applicant sees exactly what a stranger sees (`credentials`); the rejection reason
is never disclosed to the applicant. Only a caller who proves the password of a **pending**
request learns `pending`. Correct per `R-56` and its 2026-10-06 addendum.

### 2.9 Forged `refusal` and forged `X-Forwarded-For`

- **Forged `refusal`.** The `refusal`/`outcome` values are a closed server-side union
  (`credentials|validation|unconfigured|upstream|pending|throttled`, and the registration set),
  chosen by the BFF and placed in a same-origin redirect query. A client cannot make the BFF
  emit a value outside the set, and the only forgery available — a user hand-typing
  `/login?refusal=…` — changes nothing but what that user's own browser renders. No boundary is
  crossed; it is cosmetic.
- **Forged `X-Forwarded-For`.** Ignored at both tiers. At nginx the throttle key is the peer
  address, so a varying XFF (EXP-D) never wins a fresh bucket. At the BFF, with
  `BEHIND_PROXY=1` the key is `X-Real-IP` (XFF never read) — a varying XFF on one `X-Real-IP`
  stays throttled; with the flag unset every request shares one bucket and a varying **forged
  `X-Real-IP`** (14 distinct values) still shares one bucket (10 then throttled). A client-written
  address cannot fragment or reset either bucket.

### 2.10 The BFF catch-all

```
POST /bff/v1/registrations          (no session)   -> 404 not_found
POST /bff/v1/registrations/status   (no session)   -> 404 not_found
POST /bff/v1/registrations          (+admin cookie) -> 404 not_found
POST /bff/v1/registrations/status   (+admin cookie) -> 404 not_found
POST /bff/v1/auth/token                             -> 404 not_found
GET  /bff/v1/registrations          (no session)    -> 401 authentication_required
GET  /bff/v1/registrations          (+admin cookie) -> 200   (forwarded; admin allowed)
GET  /bff/v1/registrations          (+role-less)     -> 403  (forwarded; API refuses non-admin)
POST /bff/v1/registrations/{id}/approve (+admin)     -> forwarded (404 no-such-request, i.e. past the BFF)
POST /bff/v1/registrations/{id}/approve (+role-less) -> 403  (API refuses non-admin)
```

Bypass attempts on the two public ops (all refused, no path reaches `submitRegistration` with
a session credential): upper-case `/Registrations` → `404`; trailing slash and double slash →
`308` to the canonical path (which is itself refused); `GET /registrations/status` → `404`.
The catch-all refuses **exactly** the two public registration operations by method and path,
with or without a session, and forwards the administrator's registration operations, which the
API still gates behind the `admin` role.

### 2.11 Incidental hardening observed

- An **archived** account cannot even obtain a credential: `issueToken` answers the generic
  `401 authentication_required`, the same as a wrong password — no existence oracle.
- The served `/openapi.json` is itself behind the seam (any complete account); an
  unauthenticated fetch is `401`.

---

## 3. Findings

No release-blocking finding. No must-fix-before-merge finding. The items below are **register**
class — known, accepted, or deployment-dependent limitations, recorded with path:line,
consequence and reproduction.

**R-1 — account-existence oracle via `conflict_reason` (register; accepted).**
`src/auditmanager/access/registrations.py:200`–`235` (the `submit` conflict checks) returns
`conflict_reason=login_taken` / `request_pending` to an unauthenticated caller. Consequence: a
stranger can test whether an e-mail is registered or has a pending application. Already
accepted and registered (module docstring; `W49-PLAN.md` §3.3, per the docstring). Reproduction:
`POST /api/v1/registrations` with a known vs unknown login (§2.4). No change requested.

**R-2 — status-read timing claim is marginally overstated (register; doc nit).**
`src/auditmanager/access/registrations.py` docstring ("It performs exactly one PBKDF2
derivation on every path … so its timing says nothing"). The derivation is equalized and the
claim holds in practice (measured residual +2.8 ms, inside ~12 ms noise), but a request *does*
run an extra `_note_a_failed_read` UPDATE that an unknown login does not, so the two paths are
not byte-for-byte equal in work. The residual would disclose only the already-accepted
`request_pending` fact and is not measurable above noise on this host. Reproduction: §2.5.

**R-3 — BFF guest throttle trusts `X-Real-IP` only behind the deployment flag
(register; deployment-dependent).** `web/src/shared/config/proxy-trust.ts` +
`web/src/app/bff/session/guest-throttle.ts`. With `AUDITMANAGER_BEHIND_PROXY=1` (set by
`infra/deploy/compose.server.yml` on the `web` service) the per-client key is `X-Real-IP`.
A party with **direct** network access to the web container could forge `X-Real-IP` to win a
fresh guest bucket per request. Mitigated by the deployment: the `web` service publishes no
port, and nginx *sets* (overwrites) `X-Real-IP` from `$remote_addr`, so a client-supplied copy
through the edge is discarded. Verified: behind the flag a varying XFF stays throttled; without
the flag a varying forged `X-Real-IP` still shares one bucket (§2.9). The residual risk is a
property of the network boundary, not of this code.

**R-4 — distributed flood can reach `queue_full` (register; accepted DoS tradeoff).**
`src/auditmanager/access/registrations.py:MAX_PENDING_REQUESTS=100` + the per-address edge
throttle. Enough distinct peer addresses can fill the global 100-pending queue and have
`submitRegistration` answer `queue_full` to everyone until an administrator drains it. Bounded,
visible, `retryable:true`, and reasoned as acceptable in `infra/deploy/proxy/nginx.conf` (the
rate "is what the pending-request cap needs … about a quarter of an hour … time for an
administrator to notice"). No compromise of confidentiality or integrity.

---

## 4. Untested questions / limits

1. **Two genuinely distinct peer addresses at the nginx edge** were not produced — the stand
   drives nginx over one loopback peer, so "two addresses = two buckets" at the edge is argued
   from the key being `$binary_remote_addr` (empirically XFF cannot fragment it) rather than
   measured with two source IPs. The BFF two-address case *was* measured (distinct `X-Real-IP`).
2. **The real alpha compose stack end to end** (built API/web images + the proxy + the
   `web-sessions` volume + TLS overlay) was not built; memory budget and a parallel judge made
   the three-image build imprudent. The API was the subject's `serve.py` under the venv; the BFF
   was `next dev` (not a production `next build`); nginx ran the subject's `nginx.conf` verbatim.
   Behaviours that depend on the production bundle (e.g. secret non-inlining into `.next/`) were
   not re-verified here.
3. **TLS server block** (`tls-server.conf`, `compose.tls.yml`) was not exercised; no certificate
   on the host, and the HTTP `nginx.conf` is the always-loaded file.
4. **`exportRunCsv`, upload and run bodies** were only probed to the authorization boundary
   (403/422), not with real documents/runs; product-data isolation beyond the role register is
   out of this task's scope.
5. **Full queue fill to 100** was not run to completion (it needs ~15 min of sustained traffic);
   the throttle that enforces the pace, and the `queue_full` conflict, were both confirmed.

---

## 5. Cross-examination (second commit)

Written after the black-box pass was committed (`b24dc29`), against
`docs/program/dispatch/W49-PLAN.md` §3 and the lane reports
`W49-EDGE-01`, `W49-BFF-01`, `W49-ACCESS-01c`, `W49-SEAL-01{a,b,c}`. The peer judge's review
(`W49-JUDGE-Y`) is **not present in the subject tree** (`1b25955`) — it runs on a parallel,
unmerged branch — so cross-examination is against the plan and the lane reports, which this
task names. Other worktrees were not touched.

### 5.1 The plan's claims, checked against the black-box evidence

Every design claim my pass could reach is confirmed:

- The three registers and `OPERATION_ROLES` (§3.2), and the evaluation **order** signature/expiry
  → standing → default-credential → incomplete-profile → roles — confirmed by the 34-op sweep and
  the matrix (§2.1).
- "No role lives in the signed token" (§3.2) — confirmed: role is read from the row; forgery of
  identity/epoch fails closed (§2.2).
- `is_default_credential` = "must change password", reaching only `{issueToken, changePassword,
  getMe}` (§3.1/§3.2) — confirmed (§2.3).
- Constant-work timing for the exchange and the status read (§3.3) — confirmed empirically; no
  usable oracle (§2.5).
- "A rejected applicant sees nothing at sign-in" (§3.3, `R-56` addendum) — confirmed end to end
  (§2.8).
- `rate_limited` is edge-only, answered as an `ErrorEnvelope`, catalog grows by exactly one code
  (§3.4) — the envelope and status confirmed (§2.6); the catalog delta was not independently
  recounted (it is the seal lane's measured number).
- The BFF catch-all refuses exactly the two public ops and forwards the admin's, and the guest
  bucket keys on `X-Real-IP`/shared, never `X-Forwarded-For` (§3.5) — confirmed (§2.9, §2.10).

### 5.2 The EDGE lane's own open questions, re-examined as an attacker

The edge lane (`W49-EDGE-01` §5) listed eleven open questions. Three bear on security; I
re-examined each.

- **OQ-1 — the deployed proxy does not pick up a changed `nginx.conf` (ELEVATED).** The proxy
  bind-mounts `./proxy/nginx.conf` as a **single file**; `deploy.sh` keeps the proxy container,
  and `.github/workflows/deploy-auto.yml` updates the tree with `git checkout --detach`, which
  replaces the file with a **new inode**. A single-file bind mount is pinned to the inode present
  at container start, so the running container keeps serving the **old** config, and
  `reload-proxy.sh`'s `nginx -s reload` reloads the old file; only a container
  restart/recreate re-resolves the mount. `verify-deployed.sh` checks that the proxy answers, not
  what it loaded. **Consequence:** after an ordinary auto-deploy of W49, the two public
  registration endpoints are served with **no throttle** — the wave's headline edge control is
  absent — on a green gate and a passing deployed check. This is the "control present in the file,
  absent in the running system" trap. I could not re-measure the inode behaviour in my own
  scratch (it is under `/tmp`, invisible to the snap Docker daemon per OPERATING_CONSTRAINTS §1,
  so the mount degraded to a directory); it is a well-documented Docker single-file bind-mount
  property and the lane measured it rigorously under `.local/`. Scope: this does not block the
  merge or the `origin/dev` publication; it is a **release-blocker for the live deployment**
  (`origin/main` / the alpha host), which must recreate the proxy on `infra/deploy/proxy/**`
  changes and add a throttle probe to `verify-deployed.sh` before the W49 edge control can be
  trusted. See finding **B-1**.
- **OQ-6 — trailing slash not counted at the edge (RESOLVED, not a bypass).** `POST
  /api/v1/registrations/` yields a `$uri` the map does not match, so it is not throttled and is
  proxied. But the API answers it `307` to the slashless spelling and **does not create a
  request** — I verified directly against the API: `POST /registrations/` → `307`, and the login
  was never stored (its status read returned the generic `401`). Only the slashless spelling
  creates a request, and that spelling **is** throttled. So the unthrottled trailing-slash path
  cannot fill the queue. `POST /registrations//status` → `404`; `//` elsewhere is merged by
  nginx's `merge_slashes` and **is** counted (§2.7 EXP-E).
- **OQ-5 / OQ-2 (confirmed, benign).** The case variant `POST /api/v1/REGISTRATIONS` is counted
  (map is case-insensitive) and the app 404s it, so it only spends the caller's own budget
  (§2.7 EXP-F). On the default `127.0.0.1` binding all direct callers appear as the bridge
  gateway and share one bucket — so "flooding from two addresses" through `/api/v1/` is one
  shared budget on the shipped binding, stricter than per-address, and only a publicly bound host
  sees distinct peers.
- **OQ-3 (register).** The served document declares no `429` on the two operations; a generated
  client meets an undeclared status. The body conforms to `ErrorEnvelope`, so the client's decoder
  still classifies it; declaring it is the contract owner's call at the next reseal. Finding R-5.
- **OQ-4 (register).** `$request_id` is on the 429 body but in no access log, so an operator
  cannot trace a throttle event — operational, log-format change outside the lane's grant.

### 5.3 The BFF lane

- **Open question 1 was ruled by the integrator** (`W49-BFF-01` §4, resolution note): the plan's
  "refuse the whole `registrations` segment" was wrong because it closed the administrator's
  `listRegistrations`/`approve`/`reject` to the screens that need them; the catch-all now refuses
  **only** the two public ops. My black-box pass confirms the corrected behaviour is the one
  shipped at `1b25955` (§2.10): the two public POSTs are `404` with or without a session, and the
  admin ops are forwarded and gated by the API's `admin` role.
- **BFF Q4 (register, confirmed).** The exchange, the status read and `submitRegistration` are
  forwarded carrying the deployment's `Authorization: Bearer <secret>` header, which those
  `security: []` operations ignore. I confirmed the forward attaches it. It travels web→api
  inside the compose network only (never to the browser — that was the `W37CERT4-3` / §4.7 defect,
  already fixed), and is registered as a debt. Not a new finding.

### 5.4 The ACCESS lane's status-read open question

`W49-ACCESS-01c` (and the module docstring) frame "answer `rejected` with the reason, or answer
`None`" as an **open question** the lane could not close, and ship the conservative `None`
(generic `401`). The plan records that the **owner ruled** this on 2026-10-06 (§3.3: "A rejected
applicant sees nothing at sign-in … the applicant will learn of a rejection by mail once SMTP
exists"). So the behaviour the code ships is the owner's final decision; the lane report's "open
question" framing is a documentation lag, not an undecided behaviour. My pass confirms the shipped
behaviour matches the ruling (§2.8). No action beyond letting the ACCESS-01c note catch up.

---

## 6. Verdict

**PASS on the merged application code, with one release-blocker scoped to the live deployment.**

The identity wave's authorization, enumeration, throttle-configuration, forgery-resistance and
BFF-boundary behaviour are, as merged at `1b259556`, correct and match the controlling plan:

- No privilege escalation anywhere across every operation × role set × profile state × credential
  — proven by a full 34-operation sweep and a 4×2×2 matrix, and by failed credential forgery.
- The default credential is confined to `{issueToken, changePassword, getMe}`, including against
  the new administrator registration operations.
- Enumeration is bounded to the already-accepted `conflict_reason` disclosure; the exchange and
  the status read show no usable timing oracle.
- A rejected applicant learns nothing at sign-in; only a prover of a pending request learns
  `pending`.
- The nginx map throttles exactly the two public registration POSTs and nothing else, keyed by the
  peer address and immune to forged `X-Forwarded-For`, with no normalisation/case/trailing-slash
  bypass; the 429 is the `rate_limited` envelope with no sensitive detail.
- The BFF catch-all refuses exactly the two public operations with or without a session and
  forwards the administrator's, which the API gates by role; the guest bucket cannot be reset by a
  client-written header.

**Findings by class:**

- **Release-blocking (deployment): B-1** — the auto-deploy will not load the new `nginx.conf`, so
  the W49 edge throttle is absent on the deployed stand until the proxy container is recreated, and
  `verify-deployed.sh` does not detect it (§5.2 OQ-1). This is a deploy-process gap, not a defect
  in the merged application files, and it does not block the `origin/dev` publication. It **must**
  be closed — recreate the proxy on `infra/deploy/proxy/**` changes and add a throttle probe to
  the deployed check — before W49 is published to `origin/main` / the live host, or the wave ships
  its central new control switched off behind a green gate. The edge lane measured and flagged it;
  the integrator owns the fix (a `W49-FIX` candidate, or an explicit pre-deploy step under
  `MAIN_AUTODEPLOY_POLICY`).
- **Must-fix-before-merge:** none.
- **Register** (known/accepted/deferred): **R-1** `conflict_reason` existence oracle (accepted,
  §2.4); **R-2** status-read timing claim marginally overstated but true in practice (§2.5);
  **R-3** BFF `X-Real-IP` trust is deployment-boundary dependent (§2.9); **R-4** distributed flood
  can reach `queue_full` (accepted debt, §2.6/§3); **R-5** `429` undeclared in the served document
  (contract-owner call, §5.2 OQ-3); plus the already-registered BFF Q4 service-token forward
  (§5.3) and the ACCESS-01c documentation lag on a now-ruled question (§5.4).

**Untested questions** are listed in §4; the most material is that the live compose stack and the
auto-deploy's proxy-reload path were reasoned about and (for B-1) relied on the edge lane's own
measurement rather than rebuilt here, and that two genuinely distinct peer addresses at the nginx
edge were not produced.

The integration contract opens `W49-FIX` only for release-blocking findings; **B-1 is the one such
finding**, and it is a deployment-activation gap rather than an application-code defect.
