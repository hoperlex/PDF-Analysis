# The path to GO — the owner's ten steps, measured against the tree

**The owner's list, 2026-09-25.** Each step below is marked by **what is actually in the tree
today**, not by what the plan supposed. Three are already done, four cannot be waved at all, and
three are buildable now.

| | step | state |
|---|---|---|
| 1 | merge, `CURRENT_STATE.md`, fix the release SHA | **done** — `alpha-w44` at `d6ebe3a`, all refs equal; wave 45 closing on top |
| 2 | `.dockerignore`, rebuild, full `make gate` | **done in wave 45** — proven by a real build, not by inspection |
| 3 | deploy that SHA from a clean clone to the target VPS | **the owner's** — there is no VPS. Rehearsed in wave 45 with timings |
| 4 | DNS, trusted TLS, close plain HTTP | **the owner's** for the certificate and the name. `compose.tls.yml`, `enable-tls.sh` and `tls-server.conf` exist and are inert until one appears |
| 5 | change the start password before publication; require `access-check` clean | **buildable** — the check exists (`access-check DEFAULT CREDENTIAL`); **the gate does not** |
| 6 | a minimum password policy and a confirmation field | **buildable** — `api/routers/auth.py:145` says its bounds *"are not a password policy"*, deliberately |
| 7 | connect a real provider and drive a manual run | **the owner's** — `D-70` |
| 8 | off-host backup, rollback, certificate renewal | **mixed** — `reset.sh` restores and `deploy.sh` rolls back; the off-host destination is the owner's; renewal needs a certificate |
| 9 | `PA-01` on the target server | **the owner's** (the host). The journey walks **15/15** since wave 44, and restore is rehearsable here |
| 10 | name the pilot-data owner and the exact deletion event | **ruled** — `R-41` and `R-42`. What remains is writing it into the runbook |

## What this wave must not pretend to do

**Steps 3, 4, 7 and 9 are not work this programme can do.** They need a machine, a domain, a
certificate and an API key. **Every wave that treats them as work produces a rehearsal and calls
it readiness**, and `PA-01` criteria 1 and 2 have read *cannot be established* through four
certifications for exactly that reason.

## What is worth adding, and why each earns its place

- **A publication-readiness command.** Steps 4, 5, 7 and 8 are a checklist somebody has to
  remember. One command that answers *"is this deployment safe to publish?"* — default credential,
  TLS on, plain HTTP closed, provider mode, cost ceiling, backup configured — **turns a
  remembered list into a measured precondition.** That is the difference between a runbook and a
  gate.
- **The durable session register.** `D-65`'s one remaining live item: the BFF holds sessions in
  the Node process's memory, so **a web-container restart signs every reviewer out — and that
  happens on every deploy, not on a rare crash.** With three to five experts in a pilot that is a
  support incident per deployment.
- **The runbook as one artifact.** Wave 45's rehearsal produced measured timings and a list of
  every owner-supplied value. Those belong in one executable document with `R-41` and `R-42`
  written into it, not spread across three reports.

## What stays with the owner by ruling, not by omission

`R-41` — the pilot ends **by his explicit instruction**, with no date and no observable event.
`R-42` — he performs the wipe **personally** and decides the dump's fate. Writing those as a role
would invent the vocabulary `T-6` forbids and the ruling avoided.
