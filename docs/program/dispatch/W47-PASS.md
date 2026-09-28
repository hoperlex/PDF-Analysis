# W47-PASS — the password policy, the forced first change, and sessions that survive a deploy

**task_id:** `W47-PASS` · **wave:** 47 (GO), sub-stage A · **lane:** `gate-w47b`
**worktree:** `/root/w47pass` · **branch:** `agent/w47-pass`

Read `docs/program/dispatch/W47-PLAN.md`, then `OWNER_RULINGS` §3.16 — `R-47` and `R-48`, which
the owner settled in detail by a second poll after saying the specifics were his to decide.

## P1 — `R-48`: the policy, exactly as ruled

| | ruled |
|---|---|
| minimum length | **8** |
| blocklist | **contextual only** — the account's login, the product name, the current password. Nothing stored |
| expiry | **none** |
| confirmation | a second entry of the new password in the UI |

`api/routers/auth.py:145` says its `1..1024` bounds *"are not a password policy"* — they bound a
request body. **Build the policy as a policy**, in the access context, not as a transport bound.
A refused password is the catalog's `validation_failed`; **the catalog is frozen at 22 codes.**

**`D-101` is the consequence the integrator named when recording `R-48`:** the literal string
`password` is exactly 8 characters, is not the login and is not the product name, so it is legal —
refused only at the forced first change, where it is the *current* password. **Do not close that
gap unilaterally; the one-line repair is recorded and the owner has been asked.** Do write a test
that states the gap, so it is visible rather than accidental.

## P2 — the forced first change

**`R-48`: the seeded account's sign-in works and leads straight to the change screen, and no other
screen opens until the password is changed.** The default cannot be left in place by forgetting.

**This is the fork most likely to force a reseal, and you must find out before building.** The
flag exists server-side (`is_default_credential`). **The client has no way to learn it today** —
no operation returns it. The mechanisms are a field on the credential exchange, a refusal on every
other operation, or something cheaper you find. **Two of those touch the contract.** Wave 46 has
just closed a reseal, and a second one in two waves is `R-11`'s shape.

**So: if the only honest mechanism needs a contract field or a new error code, stop and report,
naming the options and their cost.** Do not choose it silently, and do not build a client-side
guess — a client that decides an account is on its default password is inventing a security state.

## P3 — `R-47`: sessions that survive a deploy

`web/src/app/bff/session/store.ts:73` holds every session in a `Map` on `globalThis`, so **a
web-container restart signs every reviewer out — on every deploy, not on a rare crash.** With three
to five pilot experts that is a support incident per deployment.

**Constraints that survive the repair**, both measured: the credential the API mints **never
reaches the browser** — the browser holds an opaque `HttpOnly` identifier and the token stays in
the Node process (`W15-AUTH`, and `server-credential.guard.test.ts` is the static half of that
proof). **A durable register must not move the token anywhere the browser can read**, and a
revoked credential (`token_epoch`) must still stop working the moment it is revoked.

## allowed_paths

```
src/auditmanager/access/**   (NOT check.py — W47-GATE's)
src/auditmanager/api/**
db/migrations/**            — only if P3 or P2 genuinely need one; argue it
web/src/**  ·  web/tests/**
tests/**    (NOT tests/e2e/** and NOT tests/integration/composition/**)
docs/program/W47-PASS.md
```

## forbidden_hotspots

`infra/**`, `src/auditmanager/access/check.py`, `tests/integration/composition/**` — **`W47-GATE`
owns them**, live in `/root/w47gate` · `contracts/**` **unless P2 forces it, in which case stop
and report** · `docs/program/DEBT_REGISTER.md` · `docs/program/dispatch/**` · `Makefile` ·
any container not named `gate-w47b*` · **the owner's stand is read-only.**

## Deliverables and verification

The policy, the forced change (or a stop-and-report on P2's fork), the durable register, every
new guard shown failing, and `docs/program/W47-PASS.md` opened before the first measurement.
Lane `gate-w47b` (`56420`, `60020/60021`). **Run the canonical battery literally**; verdict from
the `GATE OK` line. Commit each step. Do not tag, push or merge.
