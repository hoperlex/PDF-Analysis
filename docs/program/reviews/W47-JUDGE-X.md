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
