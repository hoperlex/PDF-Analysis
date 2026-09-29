# Wave 47, sub-stage A2 — `W47-LOCK`

**One stream, because the two rulings share a shape.** `R-50`'s client half needs the
session record to carry the default-credential flag, and `R-51` decides where that record
lives. Split between two streams, they would agree on that shape by correspondence; given
to one, there is one shape and nothing to reconcile.

## Base and baseline

- **Base:** `audit-auth` @ `45d784f` — sub-stage A merged (`W47-GATE` at `9a9f8c5`,
  `W47-PASS` at `45d784f`).
- **Baseline:** `BASELINE_PLACEHOLDER`
- **Surface now:** 17 paths / 20 operations / 61 schemas, 22 error codes, migration head
  `0011_document_section`.
- **Worktree:** `/root/w47pass`, lane `gate-w47b` (PostgreSQL `56420`, S3 `60020/60021`,
  API `56421`, Next `56423`) — already provisioned, `.env` and venv paths rewritten.
  **Cut a new branch `agent/w47-lock` from `45d784f`.** `agent/w47-pass` is merged; do not
  build on it.

## Frozen inputs — read, do not re-derive

`R-50` and `R-51` in `docs/program/OWNER_RULINGS_2026-09-17.md` (`253a0bf`). The owner chose
the expensive option in both. The options and their costs are in `docs/program/W47-PASS.md`
§1 and §3; they are history now, not a menu.

## Three things the integrator measured so you do not spend the wave on them

1. **`app_user.is_default_credential` already exists** (migration `0006`), and
   `src/auditmanager/access/repository.py` already reads it and clears it in the same
   `UPDATE` that stores a new digest. **No migration is needed.** What is missing is that
   the value never reaches the API layer — that is your work, not a schema change.
2. **The error catalog needs no change, and you must not touch it.**
   `permission_denied.safe_detail_keys` already contains `required_capability`
   (`contracts/domain/v1/error-codes.json`). The catalog stays **22 codes and frozen**.
3. **The register is `web/src/app/bff/session/store.ts`**, held in the Node process's
   memory. That is the file `R-51` moves onto a volume.

## What you build

### 1. The reseal — one movement

`IssueTokenResponse` gains `is_default_credential`, boolean, required. In one commit:
`contracts/api/v1/openapi.json`, the regenerated client, the `web/openapi/openapi.json`
mirror and the `web/FRONTEND_LOCK.json` digests. A reseal that lands in two commits is a
tree in which the frontend reads a contract the backend does not serve.

**The counts do not move** — a property on an existing schema adds no schema, so it stays
17 / 20 / 61. Add the reseal's own paragraph to the document description in the house
pattern; `tests/contract/api_v1/test_surface_counts_in_prose.py` reads what you claim there
against the live document.

### 2. The refusal — the lock

Every operation except `issueToken` and `changePassword` answers **403 `permission_denied`**
with detail **`required_capability: password_changed`** when the authenticated subject is
still on its default password.

**The value `password_changed` is the integrator's, and it is not open.** `non_default_credential`
was the alternative and was declined: the client already reads `is_default_credential`, so
naming the capability after the credential would give one fact two names, while naming it
after the act tells the caller what to do.

### 3. The signpost — the screens

The session register carries the flag. A sign-in on a default credential lands on
`/account/password` and **no other screen opens** until the password is changed. The client
never guesses this state: it reads the field, and the server refuses independently. That
is why the owner bought both.

### 4. `R-51` — the register on a volume

A named docker volume **mounted only by the web container**; the register persists to a file
on it and survives the container being recreated. `infra/deploy/**` and the register only:
**no reseal and no new dependency in `web/package-lock.json`.**

Write the cost `R-51` states into the runbook rather than leaving it in the ruling: until
each credential expires, API credentials sit on that volume. They still never reach the
browser, and `token_epoch` still stops a revoked one on the next request.

### 5. The fixtures — and the trap in them

Tests and the live journey sign in as the seeded `admin`/`password`
(`E2E_PC01_LOGIN`, `E2E_PC01_PASSWORD`; about eleven Python files mention it). Under the
refusal they all break, and that is the feature working.

**Give them non-default credentials. Do not give them a way past the check.** A fixture that
changes the password, or seeds an account with `is_default_credential = false`, is correct.
A fixture that skips the refusal, or a test-only branch that disables it, is the failure
mode this programme keeps finding — it satisfies the gate while removing the thing the gate
exists to prove. **Every guard you add must be shown able to fail.**

### 6. The bar, because it is the same flow

`web/src/_app/app-frame.tsx:116` renders `Вход` as a plain `<Link href="/login">` with no
session condition and no sign-out beside it, so a signed-in reviewer sees `Вход` on every
screen — measured in a browser, on the dashboard, whose data only loads with a session.
`R-50` sends a signed-in reviewer to a change screen; a bar that invites them to sign in
while they are signed in is the same defect in the same journey. Make the bar reflect the
session.

## allowed_paths

`contracts/api/v1/openapi.json`, `src/auditmanager/**`, `web/**`, `infra/deploy/**`,
`tests/**`, `docs/program/W47-LOCK.md` (your report).

## forbidden_hotspots

`contracts/domain/v1/**` (frozen; see measurement 2), `db/migrations/**` (see measurement 1
— if you believe you need one, **stop and report**), `docs/program/DEBT_REGISTER.md`,
`docs/program/CURRENT_STATE.md`, any tag, any push.

## non-goals

User management, roles, registration, password reset, changes to the rate limit or lockout,
anything about `R-1` or `D-70`, and any second contract change beyond the one field.

## Stop and report rather than guess

If the honest mechanism needs an error code, a migration, or a contract change beyond
`is_default_credential`, **stop with the options and their cost.** `W47-PASS` did exactly
that on these two forks and it is why the owner could rule them. A stream that guesses a
contract costs the wave a reseal; a stream that stops costs it a message.

## Discipline (unchanged from `W47-DISPATCH.md`, each lesson paid for)

- **Kill only by PID**, and only processes confirmed to be your own descendants
  (`readlink /proc/<pid>/cwd`). Never `pkill -f`, never `killall`.
- **One full gate on the host at a time.** Check `free -g` and that no other `make gate`
  under `/root/w4*` is running. The host has 11 GB. **Exit 137 is the OOM killer, not a
  result.**
- **Commit after each step.** A restart kills you; only committed work survives.
- **Any screen change drives the live journey**, `npm --prefix web run e2e:pc01 -- --phase all`,
  and quotes its summary. `make gate` does not run it.
- **A new mutation hook under `features/**` must be added to the dashboard-invalidation
  guard's map** (`web/tests/guards/dashboard-invalidation.guard.test.ts`), or it reddens.
  That is the guard working.
- **When you hand back, stop.** No re-runs, no further commits. The integrator merges at the
  sha you report.

## Deliverables

1. The branch `agent/w47-lock`, and the sha to merge at.
2. `docs/program/W47-LOCK.md`: what you built, the two rulings' implementation, every guard
   shown failing, the forks you stopped on if any.
3. **Your final gate line and counts**, accounted against the baseline by test id, and the
   live-journey summary. Three wave-46 reports omitted this; it is `D-117`.
