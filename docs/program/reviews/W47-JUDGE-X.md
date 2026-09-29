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

---

# 7. Cross-examination of `W47-JUDGE-Y` (`310ddef`)

Read at `/root/w47k/docs/program/reviews/W47-JUDGE-Y.md`. Y came from the operator's side and
drove the full docker topology — the ground I listed in §4 as my first unanswered question.
Every verdict below carries **a measurement Y did not take**; restating Y's own reproduction
would not be an answer. Y's report is the better haul, and three of its rows are on ground I
could not reach. One of them, checked from my end, does not hold.

## 7.1 X1 — a finding neither of us had, which Y8's ground made visible

**`reset.sh --restore` rolls back every piece of credential state this wave added.** The wipe's
`pg_dump` is a full-database dump (`infra/deploy/reset.sh:398`, no `--exclude-table`) and the
restore is `pg_restore --clean --if-exists` (`:258`), so `app_user` — with `password_hash`,
`token_epoch` **and** `is_default_credential` — is replaced wholesale by the dumped rows.
Three consequences, each driven in lane `gate-w47j` against the built API:

**(a) A restore un-revokes.** `revoke` says *"every credential held by 'admin' is refused from
now on"*. It is refused until a restore:

```
GET /projects with credential T                      -> 200     (token_epoch 6)
pg_dump -t app_user                                            (dump carries epoch 6)
python -m auditmanager.access.revoke --login admin   -> epoch 7
GET /projects with T                                 -> 401     revocation works
pg_restore/psql < the dump                           -> epoch 6 again
GET /projects with T                                 -> 200     THE REVOKED CREDENTIAL LIVES
```

**(b) A restore re-animates exactly the credentials Y8 found on the volume.** Same shape: T works
(200), the wipe empties `app_user` (401 — Y's result), the restore puts the original `user_uid`
and epoch back, and **the identical token bytes answer 200 again**.

**(c) A restore can reinstate the shipped default credential — this wave's whole subject.**

```
admin on the seeded default            is_default_credential = t, "password" -> 200
dump taken here
the reviewer does R-50's forced change is_default_credential = f, "password" -> 401
restore that dump                      is_default_credential = t
POST /auth/token {"admin","password"}  -> 200, is_default_credential=true
```

(a) and (b) are bounded by `TOKEN_LIFETIME_SECONDS` — a dump older than an hour carries only
expired credentials. **(c) is not bounded by anything**: a password is not a token, so a restore
of any pre-change dump puts the deployment back on the credential `R-50` exists to force off,
silently, through a documented command. `security.py` argues the epoch is trustworthy because
*"it is a column: the same answer after a restart, after a redeploy, and to every replica at
once."* True — and a column is also the thing a database restore rolls back. Nothing reconciles
the register, the epoch or the default flag across a restore.

This is why Y8's sizing is wrong (below): the repair is not one line in §7.

## 7.2 Verdicts on Y's sixteen findings

| # | verdict | the measurement Y did not take |
|---|---|---|
| **Y8** | **upheld, and escalated** | Y's 401 is real but holds **only for a wipe that is never restored**, and it holds because the *row is absent*, not because of anything about the credential. Driven above (7.1b/c): `reset.sh --restore` returns the original `user_uid`, `token_epoch` **and** `is_default_credential`, and the same token bytes answer **200**. Y's sizing — *"the repair is one line in §7 … not a change to `reset.sh`"* — does not survive it: §7 already orders `revoke --everyone` after the wipe, and 7.1(a) shows a later restore undoes that too. |
| **Y-E** | **narrowed — the central claim is falsified** | Y grepped `docs/` and concluded 2567 *"has never been printed by a gate"*. It was. `/root/w47-a-merged-gate.log` (the gate on the merged sub-stage A, 11:24 today): line **125** `2567 passed, 5 skipped, 4 warnings, 169 subtests passed in 650.98s`; lines **230-231** `Test Files 81 passed (81)` / `Tests 1139 passed (1139)`; line **235** `GATE OK`. The pair was measured, by a gate, on the merged tree. **Upheld** is the other half: `W47-LOCK.md:334,336` cites it to `W47-DISPATCH.md`, which carries 2516 / 1135 in 80. The number is sound and *measured*; only its citation is wrong. |
| **Y4** | **narrowed, sharply** | Y measured one corruption shape and called the window *"live credential material"*. I measured four. Only a fault that destroys the value's **opening quote** produces a quoted window at all, and what it quotes is `"edential":@am2.eyJle` — **9 characters of credential, all of them the public prefix** (`am2.` is the documented format tag; `eyJ` is base64 for `{"`, shared by every credential). A fault **inside** the credential, at its **closing** quote, or just **after** it gives a *positional* message with **no `...` window at all** (`Expected ',' or '}' … at position 189`), and an ordinary printable corruption inside the string **parses fine and logs nothing**. The HMAC tag is never quoted in any shape. Reachability: the container log needs host/docker privilege — strictly more than is needed to `cat` the 0600 file and get all three credentials whole, which is Y8. `compose.server.yml` sets no `logging:` driver and `infra/observability/` holds only a README, so nothing ships it. Real, worth the one-line repair as hygiene; not credential exposure. |
| **Y-F** | **upheld on the document, narrowed on impact** | The runbook sentence is false — agreed. What the hop does **not** expose: that token is **refused by the very API it is sent to** (my §1.4: `Authorization: Bearer <AUDITMANAGER_API_TOKEN>` → **401** on protected operations, raw and as `X-API-Key` too), because the seam signs with `HMAC(secret, "auditmanager/api/token-signing/v1")` and the configured value is not itself a credential. And it rides **only the exchange forward**: `route.ts:394` passes `getApiToken()`, while the data forwards at `:541` and `:643` pass `token: held` — `credentialOf(sessionId)`, the *reviewer's* credential. What it **does** expose is exactly what Y named: mint-capable key material in a second container's environment. So: not a usable bearer, not one byte browser-reachable, and not on any forward but sign-in. |
| **Y2** | **upheld, narrowed** | `deploy.sh:751-772` verbatim: the guard probes `/api/v1/openapi.json` and refuses unless the code is **401**, with `200` carrying its own named refusal (*"A 200 here is therefore a REFUSAL"*). So readiness.sh:185 is false. Two things Y did not measure: the sentence's **conclusion survives** its false premise (a proxy `301` is ≠ 401, so it is still refused — the operator is misled about the number, not into a wrong action); and **no test anywhere pins that string** (`grep` over `tests/`, `web/tests/`, `infra/` returns only the source line), so the two-word repair has nothing to update behind it. |
| **Y3** | **upheld** | Same guard reading. Added: the published port is not 200 on the **root** either — on the built web tier `GET /` answers **307** to `/projects` (measured in my §1.5), so *"the published port answering 200"* is wrong on every path a reader might mean, not only on the guard's. |
| **Y5** | **upheld** | 14 guards and 8 before the build — confirmed, and with the trap named: the naive `grep -c '# >>> guard:'` answers **15**, because `deploy.sh:89` *documents the marker syntax using the marker string itself*; `grep -cE '^# >>> guard: '` gives 14. Provenance Y asserted but did not trace: `git log -S'derived-secrets-coherent'` → **`e114519` `repair(W47-GATE): D-103`**, this wave, which is the guard that makes both counts stale. |
| **Y7** | **upheld — latent *and* unpinned** | Callers of `sessionDurability()`, repo-wide: the definition and `session-durability.guard.test.ts`, and nothing else — so latent, as Y says. What Y did not check: **no test asserts durability on a path the process cannot write** (the file asserts `true` for a *writable* configured dir at `:115` and `false` for unset at `:193`). So the wrong answer is **uncovered rather than frozen** — the repair needs a *new* test, not an edited one, which is the cheaper kind of debt. |
| **Y1** | **upheld** | All three `register` hits in the runbook are `R-46`'s readiness *"register row"* (`:539,:547,:551`) — **none** is `R-51`'s session register; `web-sessions` and `--volumes` occur **zero** times. Added: `:124`'s *"both named volumes"* is **the same count error as Y9**, in a second file — so Y1 and Y9 are one repair at two sites, which Y filed as two findings without connecting them. |
| **Y9** | **upheld, one word** | Three named volumes — and I checked the part Y did not: **all three** derive from `ALPHA_INSTANCE` (`name: ${ALPHA_INSTANCE:?…}-postgres-data|-s3-data|-web-sessions`). So the mechanism the sentence describes is correct for every volume and only the word *"BOTH"* is wrong. |
| **Y6** | **upheld** | `alpha.env.example:147` still says *"The browser client presents it as `Authorization: Bearer <token>`."* Added: a repo-wide sweep finds that sentence at **exactly one site** — there is no third copy — so this is a single-line repair and the README/runbook corrections really did land everywhere else. |
| **Y-C** | **upheld** | `:400/:426/:458` are bare `PYTHONPATH=src python -m …` against a host `:43-46` says has *"no `.venv`"*. Added, because it sizes the repair: `Dockerfile.api:69` is `COPY src/ /app/src/` with the venv on `PATH`, so the working form **already exists** — `docker compose exec api python -m auditmanager.access.revoke --everyone`. The repair is a prefix on three lines, not new code. |
| **Y-A** | **upheld** | Read verbatim: `:14-18` still says `R-4`'s halves are *"**not settled**"*; `:369` says *"**Answered by `R-41`**: the pilot ends when the owner says so."* One file, two live answers, 355 lines apart. |
| **Y-B** | **upheld** | Y cited `D-39`'s closure by date; I read the SQL that implements it. `reset.sh:345` totals `sum(n) FILTER (WHERE kind = 'BASE TABLE')` and lists views separately as *"projecting rows already in that number"*. The total therefore **cannot** over-report, and the runbook `:501-505` warning is stale in the code's own terms. |
| **Y10** | **upheld** | Y compared documents to the contract. I have the **process's own count**: the API printed `operations=20` on startup in my lane (`serve.py`'s wired line), and the contract's paths×methods is 20. The runbook says *"nineteen"* twice. |
| **Y-D** | **upheld on Y's evidence; not independently reproduced** | I have no deployed stack with an empty bucket, and I say so rather than borrow Y's run. What I could measure: `reset.sh` issues **only** 0, 2 and 3 deliberately — `exit 1` appears nowhere as an intended status — so any exit 1 is necessarily the `set -euo pipefail` abort Y isolated, and `usage()` documenting 2 and 3 is complete for every *intended* exit. That corroborates the shape without confirming the empty-bucket run. |

## 7.3 Where Y's method shares an assumption with its subject (`OPERATING_CONSTRAINTS.md` §12)

**The consequential one is Y8, and it cost a verdict.** Y asked *"is the credential refused after
the wipe?"* — and a wipe is terminal only if you accept the subject's own framing of what the
wipe is. `reset.sh` is not a wipe script; it is a **dump, wipe and restore** script, and its
third mode undoes the property Y's answer rests on. The query inherited the subject's boundary,
so it could not see the subject being wrong one flag further on. §12's shape exactly: *the query
and its subject shared an assumption.*

**The cleanest one is Y-E**, and it is §12's own worked example. Y ran `grep -rn '2567' docs/`
and `grep -c '2567' W47-DISPATCH.md`, then wrote *"2567 occurs **once in the repository**"* —
which is true — and concluded *"it has never been printed by a gate"* — which is false. The
assumption shared with the subject is **that this programme's measurements live in the
repository**. They do not: gate logs are written to `/root/*.log`, outside git, exactly as the
norms corpus is. Y searched one location and reported the absence as a property of the world.
§12: *search both spellings, or say which one you searched.*

**A third, milder: Y7 takes its expectation from the subject's own docstring.** The finding is
that `sessionDurability()` *"reports the configuration, not the register in force"* — and the
standard it is measured against is the function's own sentence, *"Which of the two registers is
in force"*. That is §12's *never build an expectation out of the thing under test*: had the
docstring said "reports how this deployment is configured", the same code would have passed the
same query. The durable warrant is the one I took instead — **who calls it, and does any test
hold it to the stronger reading** (nobody, and none).

**And one Y avoided that I nearly walked into**, worth recording because it is the same family:
counting `deploy.sh`'s guards by their marker string returns 15, not 14, because the file
documents the marker using the marker. Y got 14 and did not say how; the method matters more
than the number.

## 7.4 The two places our reports touch

**The `+17` caution is the same observation, on the same file and the same expansion —
independently.** Y: *"`forms-and-pages.test.ts` also holds one `it.each`, so a grep for `it(`
**or** `it.each` answers 17 and not 16."* Mine (§5), reached from the gate's side before I read
Y: strict 15→16, loose 16→17, runtime **20**. Same file, same single `it.each`, same arithmetic.
So the agreement is real and not two coincidences. Y adds the reason the *delta* is unaffected —
that `it.each` **was already in the base**. I add the number neither static count shows: the file
runs **20** cases, so that one `it.each` expands to **4**. Three methods, three numbers
(16 / 17 / 20), one correct delta.

**The baseline's provenance, corrected in both directions.** Y is right that the figure is not in
`W47-DISPATCH.md` and that `W47-LOCK.md:334,336` cites it there wrongly — my §5 repeated that
citation from my brief and inherited the error. Y is wrong that it was never measured: it is
line **125** of `/root/w47-a-merged-gate.log`, a gate that printed `GATE OK`. **The record should
carry `/root/w47-a-merged-gate.log` as the source of 2567 / 1139-in-81**, not `W47-DISPATCH.md`
and not "the arithmetic of two branch gates". My reconciliation in §5 is unaffected: the same
numbers, now with a provenance.
