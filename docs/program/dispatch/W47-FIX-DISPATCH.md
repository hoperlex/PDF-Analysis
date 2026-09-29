# Wave 47, repair — `W47-FIX`

**One stream, because the findings interlock.** `R-52` changes what `reset.sh` does and the
runbook must describe what it now does; the port that answers `401` is stated wrongly in four
places at once; and the contract sentence and the policy it misdescribes are two ends of one
fact. Split across streams these would be reconciled by correspondence.

## Base

- **Base:** `audit-auth` at the merge of `W47-LOCK` plus the integrator's ruling and debt
  commits. Cut `agent/w47-fix` from `audit-auth`'s tip.
- **Worktree:** `/root/w47pass`, lane `gate-w47b`, already provisioned.
- **Baseline, and note its source — the wave's own briefs got this wrong:**
  `GATE OK`, battery **2581 passed / 5 skipped**, foundation **35**, frontend **1156 in 82
  files**, from `/root/w47-a2-merge-gate.log` line 258. The earlier figure `2567 / 1139 in 81`
  was measured at line 125 of `/root/w47-a-merged-gate.log` and was **misattributed to
  `W47-DISPATCH.md`** in two briefs and in `W47-LOCK.md:334,336`. **Do not re-take a baseline.**

## Frozen inputs

`R-52` (`9bdd464`) and the owner's two answers of 2026-09-29: **close `D-101` now**, and **fix
`Y-G` in this repair**. Both judges' reports are evidence, not instructions:
`docs/program/reviews/W47-JUDGE-X.md` (`950cbc3`) and `W47-JUDGE-Y.md` (`a2c1553`).

---

## 1. `R-52` — the restore, and the volume, in one change

`reset.sh` dumps the whole database and restores with `pg_restore --clean --if-exists`, so
`app_user` returns entire. **Restoring any dump taken before the forced password change brings
back the shipped `admin`/`password`.**

- **After a restore, raise `token_epoch` on every row.** Every restored credential is dead.
- **Name, by login, any account that came back on its default password**, and say what to do.
- **It reports; it does not refuse.** `R-46`'s line, taken with `D-72` in hand. A restore that
  refuses blocks the legitimate one at the moment it is needed most.
- **The wipe clears the session register volume** in the same movement as the database and the
  bucket (`Y8`). Today `register.json` survives byte-identical with live credentials in it.

`Y-D`: `reset.sh --yes-destroy-everything` dies silently with **exit 1** on an empty bucket —
`mc --json stat --recursive` exits 1 on empty and line 406 runs it under `set -e`. The script
intends only 0, 2 and 3. `--dry-run` handles the same case correctly.

## 2. `D-101` — closed, by the owner's answer

Add the **shipped default credential value** to the contextual blocklist in
`src/auditmanager/access/policy.py`. It is context about this deployment, not a stored corpus:
no file, no dependency, no licence. `test_the_d101_gap_is_still_open` states the gap as a passing
test — **it must become the test that proves the gap is closed, not be deleted.**

## 3. `Y-G` — the published origin's redirect

Any `/api/v1/…` with a trailing slash redirects to a `Location` that has lost **both** the prefix
and the port: `/api/v1/dashboard/` → `http://127.0.0.1/dashboard`. Two causes in
`infra/deploy/proxy/nginx.conf` (`4f6d9a4`, not this wave): `proxy_set_header Host $host` drops
the port, and `proxy_pass http://api:8000/` strips the prefix with nothing restoring it. **Over
the owner's tunnel that Location is port 80 of the operator's own machine**, and the API path
lands on the web screen of the same name. Data does not leak — the screen is empty and the data
calls `401`. It is a correctness defect on the one origin `T-2` promises.

## 4. The contract sentence — one reseal, and the wording is fixed

`ChangePasswordRequest.new_password.description` says *"this surface declares no minimum length,
no complexity rule, no history and no expiry"*. `R-48`'s `policy.py` enforces a minimum of 8 and
a contextual blocklist on that exact operation.

**X argued this was defensible because `minLength` is 1 and policy belongs at the access
boundary. Y falsified that from the same description**: its next sentence declares a rule in
prose (*"A value equal to `current_password` is `validation_failed`"*), so "declares" already
includes prose in this document's own vocabulary. And `change-password-form.tsx` carries
`minLength={8}` **twice** — the only client in the tree already knows a minimum the contract
calls undeclared, and did not learn it from the contract.

**Use this wording, and do not restate the policy:**

> The bounds are mechanical. The deployment enforces a password policy on this operation — a
> refusal is `validation_failed` and names the rule in `message` — and that policy is not
> declared here, because it is the deployment's and may differ between them. No history and no
> expiry are enforced.

Writing "minimum 8" into the contract would give the transport a second authority over
`policy.py` and make every policy change a reseal, killing the property `R-48` bought by putting
policy at the access boundary. **Only "no minimum length, no complexity rule" are false; "no
history and no expiry" are true and stay.**

**One reseal, one movement**: contract, mirror, generated client, `FRONTEND_LOCK.json`. The
sentence lives in no `.md` — checked. Counts do not move.

## 5. The documents, each with its finding

| finding | what is false |
|---|---|
| `Y-A` | `DEPLOYMENT_RUNBOOK.md:14-18` still says `R-4` has **two halves open** and is **not settled**, twenty lines above §7 saying `R-41` answered it. **This one is the integrator's own defect**, left by a diff that began at line 336 |
| `Y1` | the runbook says **nothing** about the session register: `grep -c -i session` → `0`, `down --volumes` → `0`. §1 says "**both** named volumes" and there are three. The cost `R-51` states is in `README.md`, and commit `a134f9a` claims it is in the runbook |
| `Y-C` | §7's `PYTHONPATH=src python -m auditmanager.access.revoke|unlock|check` cannot run on the host §1 describes — §1 promises **no `.venv`**, and the command gives `ModuleNotFoundError: sqlalchemy`. `readiness.sh` already uses the working idiom. `R-42` makes this worse, not softer: the owner is now at the keyboard |
| `Y-F` | §2 says the signing key "goes into no request header". It does: `compose.server.yml:208` gives it to `web`, and the exchange forward sends `authorization: Bearer <token>`. **X measured that this authorizes nothing an outsider can reach** — so correct the absolute sentence, do not overstate the consequence |
| `Y2` | `readiness.sh:185` tells the operator `deploy.sh`'s proxy guard requires **200**; it requires **401** and refuses on 200. This wave's file (`26cd836`). No test pins the string |
| `Y3`, `Y6`, `Y9`, `Y10` | §3, §6 and `README:308` say the port answers 200 (it answers 401); `alpha.env.example:147` still teaches *"The browser client presents it as `Authorization: Bearer <token>`"*, corrected only in `README`; `alpha.env.example:48` says "both volumes" of three; "nineteen"/"fifteen operations" against **20** in the contract |
| `Y5` | guards are **14**, not 13, and **8** before docker, not 7 — moved by `e114519`, this wave. A naive `grep -c` gives 15 because `deploy.sh:89` documents the marker with the marker |
| provenance | `W47-LOCK.md:334,336` cites `W47-DISPATCH.md` for `2567 / 1139 in 81`. The source is `/root/w47-a-merged-gate.log` line 125 |

## 6. Two more, small and named

- **`Y7`** — `sessionDurability()` answers `durable: true` for a volume it cannot write to.
  **X checked and no test pins this at all**, so the repair needs a **new** test, not an edited
  one.
- **`D-118`, third error** — `web/src/app/bff/session/store.ts:157` uses `console.info` where the
  rule allows only `warn` and `error`. **This is a decision, not formatting**: the unset case is
  correctly a `warn`; the configured case states where API credentials live. Escalating a correct
  configuration to a warning cries wolf; deleting the line drops what `R-51` asked to be said out
  loud. Choose, and say why in your report. **Do not wire `lint` into `make gate` in this
  repair** — that is `D-118`'s structural half and it will redden other files.

## allowed_paths

`infra/deploy/**`, `src/auditmanager/access/policy.py`, `contracts/api/v1/openapi.json`,
`web/openapi/**`, `web/FRONTEND_LOCK.json`, `web/src/shared/api/generated/**`,
`web/src/app/bff/session/store.ts`, `docs/program/DEPLOYMENT_RUNBOOK.md`,
`docs/program/W47-LOCK.md`, `tests/**`, `web/tests/**`, `docs/program/W47-FIX.md` (your report).

## forbidden_hotspots

`contracts/domain/v1/**` (22 codes, frozen), `db/migrations/**`, `docs/program/DEBT_REGISTER.md`,
`docs/program/OWNER_RULINGS_2026-09-17.md`, `docs/program/CURRENT_STATE.md`,
`docs/program/reviews/**` (the judges' reports are evidence and are not edited), `Makefile`,
any tag, any push.

## non-goals

User management, roles, registration, rate-limit or lockout changes, `D-118`'s structural half,
anything about `R-1` or `D-70`, and any contract change beyond the one description in §4.

## Stop and report rather than guess

If any repair needs an error code, a migration, or a contract change beyond that description,
stop with the options and their cost.

## Discipline

Unchanged from `W47-DISPATCH.md`. In particular: **kill only by PID and only your own
descendants** (`readlink /proc/<pid>/cwd`) — a pattern kill has reached other sessions twice on
this host and once killed the caller's own shell; **one full gate at a time**, `free -g` first,
**exit 137 is the OOM killer, not a result**; never assert on an exit code, read the `GATE OK`
line; commit after each step; **any screen change drives the live journey** and you quote its
summary.

## Deliverables

1. The branch `agent/w47-fix` and the sha to merge at.
2. `docs/program/W47-FIX.md`: every finding above, what you did, and **for each one the command
   that now shows it repaired**. Every new guard shown able to fail.
3. Your final `GATE OK` line and counts, accounted against the baseline **by test id**, and the
   live-journey summary.
4. Anything you stopped on.
