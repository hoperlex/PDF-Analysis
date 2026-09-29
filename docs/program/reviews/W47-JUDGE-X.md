# W47-JUDGE-X — the wave's close, from the attacker's entry point

Judge `W47-JUDGE-X`. Worktree `/root/w47j`, branch `agent/w47-judge-x`, merged tip `44937fe`.
Lane `gate-w47j` (PostgreSQL `56430`, S3 `60030/60031`). I judge; I repair nothing. Every
probe is reverted; the seeded row is restored to default after each destructive test.

**Method.** Per `docs/program/dispatch/W47-JUDGES.md` §"X starts from the attacker", I brought
the stack up in my lane and attacked it with the seeded account (`admin`) on its shipped
default password (`password`) **before reading one line of the diff, the commit log,
`W47-LOCK.md` or the dispatch brief.** Section 1 below was written and committed before I read
any of those. Section 2 is the post-diff verification.

## How the stack was brought up (no diff knowledge)

- `make up` (lane services), `make migrate` (schema to head `0011`, seeds `admin`/`password`).
- API: `infra/deploy/serve.py` under `.venv`, `AUDITMANAGER_PROVIDER_MODE=recorded`, bound
  `127.0.0.1:8000` (health `8001`), DATABASE_URL/S3 from `.env`, a self-chosen
  `AUDITMANAGER_API_TOKEN`.
- Web/BFF: `next dev` on `127.0.0.1:3100`, `AUDITMANAGER_API_UPSTREAM=http://127.0.0.1:8000`,
  same `AUDITMANAGER_API_TOKEN`, `AUDITMANAGER_SESSION_STORE=<scratch>/register.json`.
- The seeded account and default password were read from `db/migrations/versions/
  20260922_0006_app_user.py` (`SEED_LOGIN="admin"`, `SEED_PASSWORD="password"`), not the diff.
- I did **not** touch the owner's stand (`auditmanager-w19a-*`, `127.0.0.1:31500`).

## 1. Attack phase — what I tried, and what happened (written before reading the diff)

Every line below is a reproduction against my lane (`API=http://127.0.0.1:8000`,
`WEB=http://127.0.0.1:3100`).

### 1.1 The API, fail-closed
- `curl -s $API/openapi.json` → `authentication_required`. Even the schema is behind the seam.
- Enumerated the surface from `contracts/api/v1/openapi.json`: `POST /auth/token` (open),
  `POST /auth/password` (bearer), 18 other operations (bearer). 20 total, matches serve.py.

### 1.2 The default credential can sign in, but cannot act
- `POST /auth/token {"login":"admin","password":"password"}` → **200**, body
  `{"token":"am2...","expires_in":3600,"is_default_credential":true}`. The token payload
  (base64) is `{exp,iat,login:admin,name:admin,sub:usr_...,ver:1}` — no capability claim.
- That token against **every one of the 18 protected operations** → **403 permission_denied**,
  `details:{"required_capability":"password_changed"}`. Reproduction: loop over all 18 method/
  path pairs with `Authorization: Bearer <token>`; all 403.
- The refusal fires **before resource resolution**: `GET /findings/fnd_x`,
  `GET /runs/run_x`, `GET /versions/ver_x` (non-existent ids) all return 403, not 404/422.
  So the default-credential gate is not reachable around by addressing a real resource.

### 1.3 Forced-change lifecycle, epoch, replay
- `POST /auth/password` with the default token: `new==current` → 422 `validation_failed`
  ("the new password must differ from the current one"); `new_password` 7 chars → 422
  ("a password must be at least 8 characters"); wrong `current_password` → 401
  `authentication_required`.
- A successful change (`current=password`, `new=Password`) → 200. Afterwards:
  - DB: `is_default_credential=f`, `token_epoch` incremented, `password_updated_at>created_at`.
  - The **token minted before the change** (`ver=1`) → **401 at once** on `GET /dashboard`
    (`authentication_required`) — not at the next restart.
  - `POST /auth/token` with the old default password → 401.
  - `POST /auth/token` with the new password → 200, `is_default_credential:false`, `ver=2`;
    that token now acts: `GET /projects` → 200. Forced-change lifts only after the change.

### 1.4 Bypasses attempted that did NOT work
- Path normalisation/casing: `/dashboard/`→307, `/Dashboard`,`/DASHBOARD`,`//dashboard`,
  `/api/v1/dashboard`→404, `/./dashboard`→401. No unauthenticated route to a protected op.
- Token tampering: flipping `ver` in the payload and re-encoding → 401 (signature). No bearer
  → 401.
- **The deployment token as a bearer**: `Authorization: Bearer <AUDITMANAGER_API_TOKEN>` on
  `GET /projects`,`GET /dashboard` → **401**. Raw (no "Bearer") → 401. `X-API-Key` → 401.
  The signing key cannot act; it only signs. (Runbook's wave-34 warning holds.)

### 1.5 The BFF / screens / cookie / session register
- Login is `POST /bff/v1/session` (form `login`/`password`); direct `POST /bff/v1/auth/token`
  is refused ("недоступен из браузера. Вход выполняется через /bff/v1/session").
- Default login → **303 → `/account/password`** (the change screen). Cookie:
  `am_session=<32-byte hex>; Path=/; HttpOnly; SameSite=Strict; Max-Age=3600`. The JWT is
  **not** in the cookie.
- With the default session cookie: every BFF data route
  (`/bff/v1/projects|dashboard|decisions|runs/*`, GET and POST) → **403**
  `required_capability:password_changed`. Every screen (`/projects`,`/dashboard`,`/logs`,
  `/workers`,`/knowledge-base`,`/optimisation`,`/blocks`) → **307 → `/account/password`**;
  only `/account/password` renders 200. No screen other than the change screen is reachable.
- `register.json` is mode **0600**, holds the JWT as `credential` with `isDefaultCredential`;
  the file is **not servable** over the web (traversal attempts → 404). The JWT does **not**
  appear in any served HTML or bundle (`grep` for the credential and for `am2.` → 0).
- Change via `POST /bff/v1/session/password` (`current_password`/`new_password`/
  `confirm_new_password`): 7 chars or `new==current` → 303 `?outcome=unchanged` (refused);
  a valid change → 303 `?outcome=changed`. On change the BFF **rotates the session id** in the
  register **and** sends a fresh `Set-Cookie` — the pre-change cookie is removed and → 401,
  the new cookie → 200. No silent logout, and the old session id is dead (rotation, not reuse).
- **Persistence**: after killing and restarting the `next dev` process, the post-change cookie
  still → 200 on `/bff/v1/projects`. Sessions outlive the process (file-backed register).
- **Revocation**: `python -m auditmanager.access.revoke --login admin` bumps `token_epoch`;
  the surviving session's next request → **401 at once**, and the stored JWT presented directly
  to the API → 401. Revocation is immediate wherever the token is kept.

### 1.6 Attack-phase verdict
From the attacker's side I could **not** reach anything a default credential should not reach.
The default credential signs in and is then confined to the change screen and the change
operation; the API refuses it on all 18 protected operations before resource resolution; the
BFF mirrors that with a screen-lock and 403 data routes; tokens die at once on change and on
revoke; the signing key cannot act; the browser never sees the JWT. Open question carried into
section 2: the min-length-8 policy is enforced by the server, and I must check the frozen
contract text still describes the shape truthfully.

## 2. Verification phase — the diff, read only now

Read after section 1 was committed (`ba68c85`). The wave's security work is `R-50` (the
forced-change lock and `is_default_credential`) and `R-51` (the persistent session register),
spanning `a53d4a1..44937fe`. Core seam: `src/auditmanager/api/security.py`.

### 2.1 Was the check bypassed, or the fixtures repaired?
- No test-only branch, environment flag, `skip`/`xfail`, or fixture that skips the refusal in
  the enforcement path. `grep` for `getenv|environ|NODE_ENV|skip|xfail|bypass|disable` across
  `security.py`, `auth.py`, `repository.py`, `screen-lock.ts`, `store.ts`, `route.ts` finds
  only references to test *names* in comments and legitimate `SESSION_ID_PATTERN.test()` regex
  calls. `store.ts`'s one test-only helper (`clear`, l.387-403) empties the register; it is not
  a refusal bypass.
- The seam (`security.py:655-717`) decides `is_default_credential` from the **account row**
  (`AccountStandings.standing_of`, l.693/703), not from the credential payload — a forged or
  stale token cannot assert it. Confirmed against the payload in §1.2 (no such claim in it).
- The epoch check (401, l.694-695) runs **before** the default check (403, l.703-709), so a
  revoked default credential is refused as revoked, not enumerable. See M3.

### 2.2 Each new guard fails when the thing it guards is broken (my own mutations)
Every mutation below was applied to the committed tree, the named tests run, then
`git checkout --` reverted the file (`git diff --quiet` confirmed clean each time). Lane DB
`56430`. Baseline: the four API tests and the two frontend guard files pass unmutated.

| my mutation | file:line | result | matches doc |
|---|---|---|---|
| M1 — `if False and standing.is_default_credential` (403 disabled) | `api/security.py:703` | **3 failed / 1 passed** (`…reaches_exactly_the_register`, `…once_the_flag_is_off`, `…lifts_the_refusal…`; the revoked-default test still passes, correctly) | yes |
| M3 — default 403 check moved **before** the epoch 401 check | `api/security.py:693-695` | **1 failed** (`test_a_revoked_default_credential_is_refused_as_revoked_and_not_as_default`), 3 passed | yes |
| W2 — `requireAChangedPassword` made a no-op (`return;` first) | `web/src/app/bff/session/screen-lock.ts:48` | **2 failed / 7 passed** (`default-credential-screens.guard`) | yes |
| R1 — `persist()` returns before it writes | `web/src/app/bff/session/store.ts:222` | **3 failed / 5 passed** (`session-durability.guard`) | yes |

All four guards are non-vacuous. I did **not** independently run M2, M4, M5 or R2 (the same
files' remaining mutations); M1/M3 exercise the same seam and W2/R1 the same two modules, and
the doc's table is internally consistent with what I did reproduce.

### 2.3 The contract reseal holds together
`is_default_credential` on `IssueTokenResponse`, `required` and `boolean`, in all four places,
with the same description:
- the document `contracts/api/v1/openapi.json`;
- the mirror `web/openapi/openapi.json` — **byte-identical** to the document;
- the generated client `web/src/shared/api/generated/types.gen.ts`;
- the lock `web/FRONTEND_LOCK.json`.

`sha256(contracts/api/v1/openapi.json) == sha256(web/openapi/openapi.json) ==
FRONTEND_LOCK.json.openapi.sha256 == ffcf3c0c59807d735bbc03be4c811f5f590920b36a133f038edffec49b369359`,
`content_commit a53d4a1`. `node scripts/generate-api-client.mjs --check` (from `web/`) →
`OK - 20 operations, contract sha256 ffcf3c0c…`. The reseal is coherent.

### 2.4 Where the stream did the right thing
- The default-credential fact is read from the row on every guarded request and refused to be
  carried in the credential payload (`security.py` module note; verified: the `am2` payload has
  no such field). This is the correct dual-write avoidance.
- The signing key is `HMAC(AUDITMANAGER_API_TOKEN, context)`, so the raw deployment secret is
  not a usable credential — verified in §1.4 (401). The runbook's wave-34 warning holds in code.
- Session id is rotated on password change on both server and browser; persistence and
  immediate revocation both hold (§1.5).

## 3. Findings

### F1 (narrow / low) — the changePassword contract text contradicts the enforced R-48 policy
- **File/line.** `contracts/api/v1/openapi.json`, `ChangePasswordRequest.new_password.description`
  (and its byte-identical mirror `web/openapi/openapi.json`, and `types.gen.ts:398`... the
  changePassword request schema): *"The bounds are mechanical, not a policy: this surface
  declares no minimum length, no complexity rule, no history and no expiry."*
- **What is false.** The surface **does** enforce a policy on this operation: `R-48`
  (`src/auditmanager/access/policy.py`) imposes minimum length 8 and a contextual blocklist
  (login, product name, current password), applied on the `POST /auth/password` path.
- **Reproduction.** `curl -s -X POST http://127.0.0.1:8000/auth/password -H 'authorization:
  Bearer <default token>' -H 'content-type: application/json' -d
  '{"current_password":"password","new_password":"1234567"}'` → **422 validation_failed**,
  message *"a password must be at least 8 characters"* — while the contract says the surface
  declares no minimum length.
- **Counter-argument, stated honestly.** This is defensible by design and is documented: the
  commit is titled *"R-48's policy as a policy"*, and `policy.py` argues the policy belongs to
  the access boundary, not the transport contract, so a deployment can change it without
  renegotiating the contract. The word *"declares"* is defensible for a document whose schema
  `minLength` is 1. So this is a **documentation-clarity** issue, not a security bypass: the
  refusal works. It is reported because the sentence, read by an API client, states the
  opposite of the operation's behaviour — the same drift-shape (`document vs code`) this
  codebase's own reviewers flag. Severity low; it admits nothing.

### F2 (informational, already recorded) — D-101: the shipped default value is a legal new password
- `policy.py` names `D-101`: `"password"` (8 chars, not a login, not the product name) is a
  legal **new** password everywhere except as the *current* password, and the one-line repair
  (adding the shipped default to the blocklist) is **owner-deferred**, recorded as a passing
  assertion `test_the_d101_gap_is_still_open`.
- **Reproduction (confirmed in §1.3).** From default `password`, `new_password:"Password"`
  (capital P) → **200 changed**. The policy permits weak dictionary-adjacent passwords.
- This is **not a new finding**: it is a known, documented, owner-ruled gap. Named here because
  an attacker who forces a change is not thereby forced to a strong password.

## 4. Questions I could not close
- **The full docker deploy stack** (`compose.server.yml`, the real `<instance>-web-sessions`
  volume, the nginx proxy at one origin) I did **not** bring up — I attacked the API and BFF
  directly in my lane (`next dev`, a file-backed register), which is the same enforcement code
  but not the deployed topology. The volume-mount permissions, the proxy path rewriting
  (`/api/v1`), and TLS were not exercised by me. `W47-JUDGE-Y` (operator entry) covers the
  runbook/deploy path.
- **M2, M4, M5, R2 mutations** I did not independently run (see §2.2).
- **Concurrency**: I did not test two simultaneous sign-ins racing the file-backed register
  (temp-file + rename is used; I read it but did not stress it).

## 5. The gate, run literally, and the counts reconciled by test id

**Method.** `make gate` in `/root/w47j` (lane `gate-w47j`), on my branch at `11b276a` —
`44937fe` plus my two report commits, which add one documentation file and nothing a test
reads. Run alone on the host: I checked `free -g` and for any other `make gate`/battery
process first, and the integrator's earlier battery had finished. Not an exit code — the line:

```
GATE OK: battery, foundation, frontend and whitespace all pass
```

| suite | measured here | `W47-DISPATCH.md` baseline I was given | delta |
|---|---|---|---|
| battery | **2581 passed / 5 skipped** (169 subtests, 748.92 s) | 2567 passed / 5 skipped | **+14** |
| foundation | **35 passed** (24.99 s) | 35 | **0** |
| frontend | **1156 passed in 82 files** (149.12 s) | 1139 in 81 files | **+17 tests, +1 file** |

These are identical to the counts `W47-LOCK.md` §12 records, independently re-measured.
(My battery wall-clock 748.92 s vs the doc's 519.63 s is host load, not scope.)

**The +14, verified by test id.** All fourteen named in `W47-LOCK.md` §12 exist in the tree
now and **none of them existed at the wave's base** — checked with
`git grep -l "def <id>" a53d4a1^ -- tests` (empty for all fourteen) against `grep -rl` now:
3 in `tests/integration/auth/test_the_exchange_over_real_users.py`, 6 in
`tests/integration/api/test_authorization.py`, 5 (the whole new file) in
`tests/integration/composition/test_session_register_volume.py`. 3+6+5 = 14. The skipped
count is **unchanged at 5**, and `git diff a53d4a1^ 44937fe -- tests web/tests | grep '^+.*skip'`
adds no `skip`/`xfail` marker (its only hits are prose asserting no such flag exists).

**The +17 and the +1 file, verified per file.** Under the doc's own stated method (`it(`
counts, excluding `it.each`), base `a53d4a1^` → now:

| file | base | now | delta |
|---|---|---|---|
| `web/tests/guards/default-credential-screens.guard.test.ts` (new, the 82nd file) | 0 | 9 | +9 |
| `web/tests/guards/session-durability.guard.test.ts` | 3 | 8 | +5 |
| `web/tests/unit/session/bff-session.test.ts` | 16 | 18 | +2 |
| `web/tests/unit/screens/forms-and-pages.test.ts` | 15 | 16 | +1 |

9+5+2+1 = **17**, and 81+1 = **82**. **A caution on method, not a finding:** a looser count
(`^\s*it[.(]`, which also catches `it.each`) gives 16→17 for the last file, and the file runs
**20** tests at runtime because one `it.each` expands. The doc's table is right under the
method it states; anyone re-checking it with a different regex will disagree with it and be
wrong. Runtime, static-strict and static-loose are three different numbers here.

## 6. Verdict

The wave does what it claims where I could reach it. A default credential signs in, is told so
in the same answer, and reaches the exchange and the change and nothing else — at the API on
all 18 protected operations before resource resolution, and at the screens through a
server-side lock. Credentials die at once on change and on revoke. The browser never holds the
API credential. Sessions survive the process. The four guards I mutated myself all fail when
broken. The reseal is coherent across four documents by digest. `GATE OK` with every count
accounted by test id.

One low finding (`F1`, a contract sentence that contradicts the policy the same operation
enforces), one recorded known gap (`F2`/`D-101`), and the deployed-topology questions in §4
left open and named rather than guessed.
