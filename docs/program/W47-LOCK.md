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
