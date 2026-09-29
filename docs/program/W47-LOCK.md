# `W47-LOCK` — `R-50` and `R-51`, one stream

Brief: `docs/program/dispatch/W47-A2-DISPATCH.md`. Base `45d784f`, branch `agent/w47-lock`,
worktree `/root/w47pass`, lane `gate-w47b`.

This page is written as the work lands, not after it, so a restart loses nothing but the
step in progress.

## 1. `R-50`, the field — the Python half

`IssueTokenResponse` gains `is_default_credential`, required. The value is the account's
own column, read in the statement that authenticated the password and passed through
unchanged:

- `api/security.py`: `IssuedCredential` gains the field, with **no default** — the same
  rule `Subject.token_epoch` and `Subject.display_label` are held to, and for the same
  reason: the value a caller would assume is the permissive one. `TokenSigner.issue` takes
  it as a required keyword and puts it on the returned record and **not into the payload**.
- `bootstrap/adapters.py`: both mint sites read `record.is_default_credential` — the record
  `authenticate` returned, and the record the `change_password` UPDATE returned (which
  clears the column in the same statement, so `false` there is the write's doing).
- `api/routers/auth.py`: both operations answer the port's value.

**Why not in the credential's payload**, which would have been the other shape: the seam
decides the refusal (§2) from the account's row on every guarded request, so a copy in the
payload would be a second and older answer to the question that decides whether a request is
refused. It would also have forced `am2` → `am3` (see `_FORMAT`'s own note), signing every
holder out, and it would have left a pre-deploy credential on a default password claiming
not to be on one.

Tests: `tests/integration/auth/test_the_exchange_over_real_users.py` — a flagged account
reads `true`, a created account reads `false` (the control that makes the first mean
something), and a password change turns it off in the same answer, confirmed by the next
exchange so that the answer is the row and not a constant.

## 2. `R-50`, the reseal — four documents, one commit

`contracts/api/v1/openapi.json`, the regenerated client, `web/openapi/openapi.json` and
`web/FRONTEND_LOCK.json`, in one commit, because a lock that trails its contract by a commit
is a window in which the frontend reads a digest the backend does not serve (`D-18`).

- contract sha256 `78eccd9e…` → `ffcf3c0c…`; mirror verified equal to it before the gate ran.
- **The counts do not move: 17 / 20 / 61, catalog 22.** A property on an existing schema adds
  no schema. `tests/contract/api_v1/test_surface_counts_in_prose.py` reads the reseal's own
  paragraph against the live document and agrees.
- `contracts/domain/v1/**` untouched; `db/migrations/**` untouched, head still
  `0011_document_section`.

## 3. `R-50`, the refusal — the lock at the seam

Every operation except `issueToken` and `changePassword` answers **403 `permission_denied`**
with `required_capability: password_changed` while the authenticated account is on the
password the deployment seeded it with.

**Where the fact comes from, and the one design decision in this half.** The seam already
read the account's row on every guarded request (`token_epoch`, for revocation). It now
reads two columns of that row in the same statement instead of one:

- `access/models.py` gains `CredentialStanding(token_epoch, is_default_credential)`;
  `access/ports.py` and `access/repository.py` replace `token_epoch(...)` with
  `credential_standing(...)`; `_SELECT_TOKEN_EPOCH` becomes `_SELECT_CREDENTIAL_STANDING`.
- `api/security.py` gains its own `AccountStanding`, and `CredentialEpochs.epoch_of` becomes
  `AccountStandings.standing_of`. `bootstrap/adapters.py` translates between the two
  vocabularies, as it already does for `Subject`.

*Not* two lookups, and *not* the credential's payload. Two lookups would be two reads of one
row inside one decision, which this package already argues against for the lockout column;
the payload would be an older second answer to the question that decides the refusal, and a
required payload field means `am2` → `am3`, which signs every holder out on deploy.

The exempt set is a **register**, `OPERATIONS_A_DEFAULT_CREDENTIAL_REACHES`, not a rule about
paths — `issueToken` (already open) and `changePassword` (the act the refusal demands;
refusing it would bar the only way out). `PASSWORD_CHANGED_CAPABILITY = "password_changed"`
is the integrator's value and names the act, not the credential.

**Order:** a revoked credential on a default password is refused `401`, not `403` — a `403`
would tell a caller holding a credential the deployment has already stopped accepting that
the account behind it is real.

Guards, all in `tests/integration/api/test_authorization.py`:
`test_a_default_credential_reaches_exactly_the_register` (a **set** sweep: refused set ==
`router.operation_ids - register`, envelope asserted down to `details`),
`test_the_password_change_is_the_one_operation_that_still_answers`,
`test_the_exchange_still_answers_and_says_which_state_the_account_is_in`,
`test_the_same_surface_serves_the_same_credential_once_the_flag_is_off` (anti-vacuity),
`test_changing_the_password_lifts_the_refusal_on_the_very_next_request`,
`test_a_revoked_default_credential_is_refused_as_revoked_and_not_as_default`.

## 4. `R-50`, the signpost — the screens

- `app/bff/session/store.ts`: the register row and `SessionSubject` carry
  `isDefaultCredential`, and `openSession` takes it as a **required** argument. The value is
  the API's answer, recorded; this tier never decides it.
- `app/bff/v1/[...path]/route.ts`: `is_default_credential` is validated as a boolean exactly
  as `token` and `expires_in` are — a body missing it is `upstream`, **not** a `false`. A
  sign-in on a default credential lands on `/account/password`; every other sign-in lands
  where it always did.
- `app/bff/session/screen-lock.ts` (new): `requireAChangedPassword()`. Every `page.tsx` but
  three awaits it. A layout cannot do this (a server component is not told its address, so it
  would redirect the change screen to itself) and middleware cannot (its runtime has no
  access to the register), which is why the call is in the route files.
- `/account/password` says why the reviewer is there, rather than being a silent redirect.

Guards:
- `web/tests/guards/default-credential-screens.guard.test.ts` (new, 9 tests). The subject is
  **derived** from `web/src/app` by `routeAddresses()`; each address either calls the lock or
  is in `OPEN_TO_A_DEFAULT_CREDENTIAL` with a written reason, and never both. It reads the
  route's *code*, with comments stripped — the first run reported `/account/password` as both,
  because its docstring explains that it does not call the lock.
- `web/tests/unit/session/bff-session.test.ts`: where each sign-in lands, and that the
  register recorded what the API said; plus two more unusable-answer shapes (the field
  missing, and the field not a boolean).

## 5. The bar (`app-frame.tsx:116`)

`AppFrame` gains a **required** `session` prop — no default, so every renderer of the frame
says which state it is rendering, and the defect cannot come back by omission. `app/layout.tsx`
(the framework adapter, and the only part of the chrome allowed to know there is a request)
reads the cookie and passes it down; `AppFrame` stays a pure server component every instrument
can render synchronously. Signed in: the login and a `Выйти` POST to `/bff/v1/session/end`.
Signed out: the `Вход` link, as before. One global-stylesheet rule gained four declarations
(`background`, `border`, `padding`, `font-family`, `cursor`) so the `<button>` looks like the
`<a>`; no new selector and no new colour, so the contrast census has nothing new to reach —
and it renders both states now anyway.

## 6. `R-51` — the register on a volume

- `infra/deploy/compose.server.yml`: a named volume `${ALPHA_INSTANCE}-web-sessions`,
  mounted at `/var/lib/auditmanager/sessions` **by the `web` service and by nothing else**,
  and `AUDITMANAGER_SESSION_STORE` set to `register.json` inside it (a literal, not a
  substitution: an operator who could point it elsewhere could get a register that silently
  stops surviving deploys).
- `infra/deploy/Dockerfile.web`: the mount point is created and `chown`ed to `node` **before**
  `USER node`. Docker seeds a fresh named volume from the image's directory, ownership
  included, so a missing or root-owned directory would give a volume the process cannot write
  to — and the register would report a write failure on every sign-in while appearing to work.
- `web/src/app/bff/session/store.ts`: whole-file writes, atomic (temp + `rename`), mode `0600`;
  hydrated once per process on the first read, dropping what expired while nothing was running;
  a file it cannot read is **reported** and treated as empty (refusing to serve because of one
  corrupt line turns a lost session into a lost deployment); a write failure is reported and
  does not refuse the request (the session is live in memory either way).
- `web/src/shared/config/session-store.ts` (new): the env read, because `shared/config` is the
  only place in `web/` that reads `process.env`. Deliberately not in the barrel, for
  `server-env.ts`'s reason. Not imported by `server-env.ts` and not importing it, so
  `server-credential.guard.test.ts`'s "imported by exactly the BFF route handler" stays true.
- **No new dependency in `web/package-lock.json`** (`node:fs` and `node:path` only) and no reseal.
- The cost `R-51` states is in `infra/deploy/README.md` where an operator meets it, with the two
  things that are unchanged by it (never in the browser; `token_epoch` still revokes at once)
  and the two operational consequences (`down --volumes` signs everyone out; a write failure
  names itself in the log).

Guards:
- `web/tests/guards/session-durability.guard.test.ts`: the wave-47 block that characterized the
  gap — and said in its own comment that it *"is expected to go red the day a genuine durable
  mechanism lands ... the assertions above invert"* — is replaced by that inversion, driven
  against a real file in a temp directory: a session opened before `dropTheInMemoryRegister()`
  is found after it, with `isDefaultCredential` intact; a closed one and an expired one are not;
  a corrupt register is reported and recovered from; the file is not world-readable and the
  cookie still carries none of the credential. The memory-only deployment is kept as its own
  named case, because it is a configuration that really exists (`next dev`, this suite).
- `tests/integration/composition/test_session_register_volume.py` (new, 5 tests): the volume is
  declared and instance-scoped; **exactly one service mounts it and that service is `web`** (a
  set comparison — "web mounts it" would pass on a stack where the API mounted it too); the
  mount point and the configured file agree; no other service is even told where the register
  is; and the image owns the directory before it drops privileges.

## 7. The fixtures — repaired, not bypassed

Nothing was given a way past the refusal. There is no test-only branch, no environment flag
and no fixture that skips the check; what changed is **which credentials the fixtures use**.

- `tests/integration/api/driver.py`: `SuiteCredentialAdapter` holds
  `is_default_credential` as a **field** (default `False` — this suite's account is an
  account that has changed its password, like every account a deployment is meant to have),
  and `change_password` clears it in the same step it raises the epoch, because the real
  repository does it in one UPDATE and a suite adapter that did not would let a test pass
  that the deployment fails. The field is what lets the sweep drive the refusal against the
  real seam.
- `tests/integration/api/test_decision_authorship.py`: its two-account adapter answers
  `standing_of` with `is_default_credential=False` — that module is about *whose* decision a
  row records, and a default credential would refuse every operation it drives.
- `tests/integration/auth/test_the_exchange_over_real_users.py`: a new `seeded_user`
  fixture creates a **real row with the flag set**, rather than using the seeded `admin`
  (whose password a suite must not change out from under the rest of the tree). The chain to
  the real deployment is not broken by that: `tests/integration/db/test_app_user_migration.py`
  already pins that migration `0006` leaves `admin` with `is_default_credential = true`, and
  the sweep pins that such an account reaches two operations.
- `web/tests/unit/session/bff-session.test.ts` and `change-password.test.ts`: the fake
  upstream answers the contract's body — all three properties — and `is_default_credential`
  is a **parameter** of the fixture so both states are drivable. Two new unusable-answer
  shapes were added rather than removed: the field missing, and the field not a boolean.
- The live journey: `tests/e2e/pc01/journey/README.md` states the precondition — the account
  must be one whose password has been changed, which is what every deployment must do anyway
  — and says explicitly that there is no flag that skips the refusal and that a harness able
  to put itself past it would stop proving it is there. `session.mjs` names the state in its
  failure when a run lands on `/account/password`: the sign-in was *accepted*, and R-50 sent
  that account to the one screen it may open.

## 8. Guards, and each one shown able to fail

Every mutation below was applied to the committed tree, measured, and reverted with
`git checkout --`; nothing was left in the tree and the suites were green before and after.

| # | mutation | what went red |
|---|---|---|
| M1 | the seam's refusal block replaced by `pass` | `test_a_default_credential_reaches_exactly_the_register`, `…_once_the_flag_is_off`, `…_lifts_the_refusal_on_the_very_next_request` (3 failed / 33 passed) |
| M2 | `listProjects` written into `OPERATIONS_A_DEFAULT_CREDENTIAL_REACHES` | the same three (3 failed / 33 passed) — the sweep is a set comparison, so a third entry is reported |
| M3 | the default-credential check moved **before** the epoch check | `test_a_revoked_default_credential_is_refused_as_revoked_and_not_as_default` (1 failed / 35 passed) |
| M4 | `issueToken`'s body writes the constant `True` instead of the port's value | `test_the_exchange_reports_a_changed_credential_as_not_default`, `test_changing_a_default_password_turns_the_field_off_in_the_same_answer` (2 failed / 12 passed) |
| M5 | the capability renamed to `non_default_credential` (the declined alternative) | `test_a_default_credential_reaches_exactly_the_register` (1 failed / 35 passed) |
| W1 | `await requireAChangedPassword()` deleted from `/dashboard`'s route | `default-credential-screens.guard.test.ts` — *"/dashboard (web/src/app/dashboard/page.tsx)"*, by address, plus the comment-strip case |
| W2 | `requireAChangedPassword` made a no-op | the two driven cases in the same file (2 failed / 7 passed) |
| W3 | the BFF lands every sign-in on `/projects` | `lands a changed password on the application and a seeded one on the change screen` |
| W4 | the BFF reads a missing `is_default_credential` as `false` | `refuses an answer it does not understand rather than inventing a session` |
| W5 | the bar returned to the unconditional `Вход` link | `offers the way in when there is no session, and the way out when there is` |

| R1 | `persist()` returns before it writes | `finds the session again in a process that has never seen it`, `keeps the credential in a file only this process reads`, `reports a register it cannot read…` (3 failed / 5 passed) |
| R2 | `hydrate()` returns before it reads the file back | the first and the last of those (2 failed / 6 passed) |
| V1 | the `api` service mounts the volume too | `test_exactly_one_service_mounts_it_and_that_service_is_web` |
| V2 | the register configured one directory **outside** the mount | `test_the_web_service_is_told_where_the_register_goes` |
| V3 | the `chown` dropped from `Dockerfile.web` | `test_the_image_owns_the_mount_point_so_the_process_can_write_to_it` |

The durability guard is also shown able to fail by construction, which is the stronger of the
two demonstrations: the block it replaces **was** the failing state. `session-durability`'s
wave-47 text asserted that a restart loses every session and said in its own comment that it
would go red the day a durable mechanism landed; the file now asserts the opposite of that on
the same event, so the tree before this wave fails the file after it.

## 9. Live evidence, on a running stand

The refusal, driven with `curl` against the API served from this worktree (lane `gate-w47b`,
`127.0.0.1:56421`, `operations=20` at startup) on an account seeded with the flag:

```
POST /auth/token   -> 200 {"token":"<redacted>","expires_in":3600,"is_default_credential":true}
GET  /projects     -> 403 {"error_code":"permission_denied", …,
                           "details":{"required_capability":"password_changed"}}
GET  /dashboard    -> 403
POST /auth/password-> 200 {"token":"<redacted>","expires_in":3600,"is_default_credential":false}
GET  /projects     -> 200   (with the replacement)
GET  /projects     -> 401   (with the credential the change revoked)
```

`R-51`, on the same stand: Next was started with
`AUDITMANAGER_SESSION_STORE=/root/w47lock-sessions/register.json`, and after the journey's
sign-in that file existed with mode `-rw-------`, `{"version":1,"sessions":[…]}`, one row
carrying `login: "admin"`, `isDefaultCredential: false` and the credential — on the disk, as
`R-51` says it will be, and nowhere the browser can reach.

## 10. The screens and the register, driven on the stand

With the API and Next served from this worktree (`127.0.0.1:56421` / `:56423`, the web tier
started with `AUDITMANAGER_SESSION_STORE` set), on an account seeded with the flag:

```
POST /bff/v1/session     -> 303  location: /account/password   (+ the HttpOnly cookie)
GET  /projects           -> 307  -> /account/password
GET  /dashboard          -> 307  -> /account/password
GET  /knowledge-base     -> 307  -> /account/password
GET  /blocks             -> 307  -> /account/password
GET  /logs               -> 307  -> /account/password
GET  /account/password   -> 200  and carries data-change-password-required="true"
```

`R-51`, driven as a restart rather than simulated: the session the journey's own browser
opened was read back after the Next process was **killed by PID and started again**, with
the same opaque cookie —

```
GET /bff/v1/projects -> 200     (before the restart)
kill <pid>; npx next start …    (a new process, empty memory, same volume)
GET /bff/v1/projects -> 200     (after it)
GET /projects        -> 200
```

Before this wave both of those would have been a redirect to the sign-in screen, which is
what `D-65` says every deploy did to every reviewer.
