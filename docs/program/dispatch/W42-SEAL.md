# W42-SEAL — one reseal, one migration, and the door the owner asked to close

**task_id:** `W42-SEAL` · **wave:** 42 (the fix wave) · **lane:** `gate-w42a`
**worktree:** `/root/w42seal` · **branch:** `agent/w42-seal`

**You own the reseal.** One stream carries it because wave 34 proved a reseal splits badly, and
`R-11` reverted an entire wave over one discovered at the end rather than planned at the start.
Everything below was ruled by the owner on 2026-09-23 — read
`docs/program/OWNER_RULINGS_2026-09-17.md` §3.13 before you start.

## A reseal is four documents in one change

`contracts/api/v1/openapi.json` · the regenerated client in `web/src/shared/api/generated/` ·
the mirror `web/openapi/openapi.json` · the contract sha in `web/FRONTEND_LOCK.json`, **written
by hand**. `D-18` named that coupling. Surface today: **15 paths / 18 operations / 51 schemas**.

**The error catalog `contracts/domain/v1/error-codes.json` is 22 codes and stays frozen.**
Nothing below needs a new one. If you conclude something does, **stop and report** — that is a
second reseal and the owner's.

## S1 — `R-37`: a decision shows a display name, not a login

Wave 41 made `author_label` the authenticated reviewer's **login** (`D-78`). It reaches every
other reviewer through `listDecisionHistory`, `listDecisions` and two screens. The owner ruled
for a **display name**.

- `app_user` gains a display name. Migration head is `0008_sign_in_throttle`; yours is `0009`.
- The ledger writes it. **The rule that must survive untouched:** it is never taken from a
  request body — server-derived or nothing.
- **Decide and argue the empty case.** An account with no display name set must not write an
  empty label (`author_label` is `min_length=1`) and must not silently fall back to something
  the reviewer did not choose without saying so. Falling back to the login is defensible;
  **inventing one is not**, and a blank is a `500` waiting to happen.
- `W12-DEC`'s mutation `M21` and wave 41's `test_decision_authorship.py` are your acceptance.
  Pinning the label to a constant must stay **red**.

## S2 — `D-86`: the sealed contract's description of `author_label` is false

It reads *"OD-12: one configured local reviewer label… **a label, not a subject identity**"*.
It is a subject identity now. Correct it to describe what the field carries after `S1`.

**The schema does not move** — same type, same `1..128`. This is a description change, and it
is a full reseal anyway, which is the whole reason `W41-AUTHOR` refused to do it quietly.

Two copies outside the seal are **already corrected and already name `D-86`** —
`docs/program/P02_SEAMS.md:508` and `web/src/widgets/decision-history/ui/decision-history.tsx:13`.
Read them; make the sealed copy agree; **the widget is `W42-LOOK`'s file, do not touch it.**

## S3 — `D-46`: a failed run cannot say *which* dependency

**The integrator picks the shape under `R-29`, and it is the row's own cheaper option:**
`RunStatus` gains an optional `terminal_detail`, **restricted to the reported code's own
`safe_detail_keys`**. Not a new catalog code — that was the row's option 2 and it is a second
reseal.

The true sentence this makes sayable, from `W29-SAY`: *your document is fine, the provider is
fine, this deployment has no recording for it.* **That sentence matters this week**, because
`R-30` just put the stand in `recorded` mode and a document with no recording is now the
ordinary case rather than a hypothetical.

`terminal_reason` is `oneOf [ErrorCode, null]` today — read it before designing beside it.
Restriction to `safe_detail_keys` is the point, not decoration: an unrestricted detail object is
how internals leak into a client.

## S4 — `R-31` / `D-73`: four routes answer `200` with no credential

`/openapi.json`, `/docs`, `/redoc`, `/docs/oauth2-redirect`. The authorization dependency is
attached with `app.include_router(router, dependencies=[...])`, so it covers the router's
eighteen routes and **not the four the application itself carries**. Measured on the live stand
by the integrator: all four `200`, every real operation `401`, and `/openapi.json` hands out the
full 15-path / 51-schema description including the shape of `/auth/token`.

Move the seam so it covers the served application. **Two things must not break**, and both need
a test: `POST /auth/token` stays reachable without a credential (a door with a handle on the
inside), and the four routes serve normally **to a caller who has one**.

**The anti-vacuity case is specific here:** write a guard that fails if the dependency is ever
attached to the router again instead of the application. A test that only drives the four routes
passes the day somebody adds a fifth.

## allowed_paths

```
contracts/**
db/migrations/**
src/auditmanager/**
tests/**                       (NOT web/tests/**)
web/src/shared/api/generated/**
web/openapi/**
web/FRONTEND_LOCK.json
docs/program/W42-SEAL.md
```

## forbidden_hotspots

`web/src/**` except `shared/api/generated/**` — **all of it is `W42-LOOK`'s**, live right now in
`/root/w42look` · `web/tests/**` · `contracts/domain/v1/error-codes.json` · `Makefile` ·
`pyproject.toml` · `uv.lock` · `package.json` · `package-lock.json` ·
`docs/program/DEBT_REGISTER.md` (the integrator's) · `docs/program/dispatch/**` ·
any container not named `gate-w42a*`.

## Deliverables

1. The four pieces, each committed as you finish it. **The reseal is one commit** — four
   documents moving together is the property `D-18` exists to protect.
2. `docs/program/W42-SEAL.md`, opened **before** the first measurement.
3. Every guard **shown to fail**: mutate → red → revert → green, with the mutation and the
   failing assertion quoted. **A mutation that comes back green is a finding, not an obstacle** —
   that sentence stopped being automatically true only last wave, and only for three of seven
   cases.
4. Anything outside the grant: reported, not repaired.

## Verification

```
cd /root/w42seal
make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12
.venv/bin/python -c "import boto3"
npm --prefix web ci
make migrate                      # your migration is 0009; prove it applies and rolls back
make gate > /root/w42a-gate.log 2>&1; echo "exit=$?"
grep -c 'GATE OK' /root/w42a-gate.log
```

Read the verdict from the **`GATE OK` line in the log**, never a status a harness hands you.
Report battery / foundation / frontend **with the commit each was taken at**. Wave 41 closed at
**2361 / 35 / 1022 in 72 files**. `PYTHONDONTWRITEBYTECODE=1` for every mutation run.

## Integration contract

You are the only stream touching `contracts/**`, `db/migrations/**` and `FRONTEND_LOCK.json`
this wave. `W42-LOOK` owns `web/src/**` and `web/tests/**` and will be editing them while you
work — **your regenerated client is the one file of theirs you write, and you write only that.**

## Rollback

The migration must roll back. Everything else is `git revert`.

## Discipline

**Commit each step as you finish it.** Wave 41's lanes were killed mid-flight by a host restart;
the one that had committed lost nothing and the one that had not nearly lost 278 lines. Do not
tag, do not push, do not merge.
