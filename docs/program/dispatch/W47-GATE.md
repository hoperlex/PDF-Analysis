# W47-GATE — the deploy tells you what is unsafe, and stops lying about what it checked

**task_id:** `W47-GATE` · **wave:** 47 (GO), sub-stage A · **lane:** `gate-w47a`
**worktree:** `/root/w47gate` · **branch:** `agent/w47-gate`

Read `docs/program/dispatch/W47-PLAN.md` and `GO_PATH.md` first, then `OWNER_RULINGS` §3.16.

## G1 — the publication-readiness command (`R-46`)

One command that answers *"is this deployment safe to publish?"* — default credential, TLS on,
plain HTTP closed, provider mode, cost ceiling, off-host backup configured.

**`R-46` ruled that it REPORTS and REGISTERS; it does not block a deploy.** That reads backwards
and the owner chose it with the precedent in hand: `D-72`'s repair was correct and fail-closed and
took the stand down for a day, because a configuration that had always been wrong stopped being
survivable the moment the code got strict. **So its output is a corpus of problems, each one
phrased as a register row requiring a ruling** — not a green light.

**Reuse what exists.** `src/auditmanager/access/check.py` already prints stable sentinels
(`access-check OK no default credentials`, `access-check DEFAULT CREDENTIAL`, and two more) and
says in its own comments that they are stable *so a checklist can grep*. **Consume them; do not
re-derive the default-credential question.**

**Each check must be shown able to fail**, on a configuration built to fail it. A readiness
command that is green on every input is the thing seven waves were spent learning about.

## G2 — step 5: the default credential before publication

The owner's step: *change the start password before publication and require `access-check OK no
default credentials`*. The check exists; **what does not exist is it being consulted.** Put it in
the readiness command's output, and say plainly in your report what a deployment with the default
still in place looks like to an operator.

## G3 — `D-103`: the placeholder guard reads four names and the secrets are written seven times

`infra/deploy/deploy.sh:227` checks `POSTGRES_PASSWORD MINIO_ROOT_PASSWORD MINIO_ROOT_USER
AUDITMANAGER_API_TOKEN`. `alpha.env.example` embeds the same secrets **again** inside
`DATABASE_URL`, `S3_ACCESS_KEY_ID` and `S3_SECRET_ACCESS_KEY`. Rotating exactly the four the
checklist and the guard's own error message name **passes the refusal, builds both images, starts
five containers, and fails ~93 seconds later** with an Alembic trace naming none of it.

**The repair is to apply a check that already exists to the file that lacks it.** `FF-01` §3 makes
the lane `.env` prove `DATABASE_URL` carries the same user, password, port and database as the
`POSTGRES_*` names. The deploy file has no equivalent. **And add the warning the file an operator
actually copies does not carry** — `W45-JUDGE-X` found that the *"DATA, NOT CODE"* warning lives in
the root `.env.example`, not in `alpha.env.example`.

**Show it failing on the exact reproduction**: rotate only the four, and the guard must now refuse
**before** a build, naming the three derived values.

## allowed_paths

```
infra/**
src/auditmanager/access/check.py        — only to add stable sentinels the command needs
tests/integration/composition/**
tests/contract/**                        — only if a readiness check needs a contract-side assertion
docs/program/W47-GATE.md
docs/program/DEPLOYMENT_RUNBOOK.md       — the readiness command's place in it
```

## forbidden_hotspots

`src/auditmanager/access/**` except `check.py`, `src/auditmanager/api/**`, `web/**` — **`W47-PASS`
owns them**, live in `/root/w47pass` · `contracts/**` · `db/migrations/**` ·
`docs/program/DEBT_REGISTER.md` · `docs/program/dispatch/**` · `Makefile` · any container not
named `gate-w47a*` · **the owner's stand and its `infra/deploy/env/*.env` files are read-only —
they were destroyed once this week by a lane's teardown and restored from the running stack.**

## Deliverables and verification

The readiness command, `D-103`'s repair, every check shown able to fail, and
`docs/program/W47-GATE.md` opened before the first measurement. Lane `gate-w47a`
(`56410`, `60010/60011`). **Run the canonical battery command literally** and read the verdict
from the `GATE OK` line. Commit each step. Do not tag, push or merge.
