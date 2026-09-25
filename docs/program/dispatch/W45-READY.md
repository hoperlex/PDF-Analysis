# W45-READY — the deploy stops being a hope

**task_id:** `W45-READY` · **wave:** 45, sub-stage A · **lane:** `gate-w45b`
**worktree:** `/root/w45rdy` · **branch:** `agent/w45-ready`

`R-1`'s host has not arrived. **Your work is what makes the day it does short and certain.**
Read `docs/program/dispatch/WAVE_PLAN_45_48.md` §W45 first, then rows `D-80` and `D-79` in
`docs/program/DEBT_REGISTER.md` — both carry their measurements.

Do the three in order. **Each is finished when a command shows it, not when it looks right.**

## R1 — `D-80`: a `.dockerignore`, verified by a real build

**Measured, and re-measure it yourself before changing anything:**

- there is **no `.dockerignore`** anywhere in the repository;
- both services build with `context: ../..` (`infra/deploy/compose.server.yml:112,127,174`), so
  every build ships the whole working tree: **6.1 GB here, 5.3 GB of it `.local/`**;
- `infra/deploy/Dockerfile.web:23-26` runs `npm ci` against the lockfile and **then**
  `COPY web/ ./`, which overlays the build host's `web/node_modules` (**576 MB**) on top of it.
  `COPY` merges, so the image's dependency tree is the clean install **overlaid by whatever the
  host had**. `package-lock.json`, `pinned-versions.guard.test.ts` and `web/FRONTEND_LOCK.json`
  all describe a tree the image need not contain.

**Two things already checked, so you do not re-derive them:** no credential reaches an image —
neither Dockerfile has a `COPY . .` and the api one copies named paths only — and
`web/.env.local` cannot change the build, because `@next/env` assigns a parsed key only when it
is absent from the `process.env` snapshot taken before loading, and the Dockerfile sets both
with `ENV` first.

**Write the file, then prove it with a build.** A `.dockerignore` that excludes something a
`COPY` names fails at build time, and changing what `COPY` sees is the whole point of it.
Report: context size before and after, and that both images build.

**Beware the trap this row is about.** `PA-01` criterion 1 is *deploy from a clean clone*, where
none of those directories exist — **the certification passes in exactly the one condition where
the defect cannot appear.** Your repair must therefore be shown to matter in the condition it
does appear in: a build from this working tree.

## R2 — `D-79`: the gate reads `docs/`

`tests/contract/api_v1/test_surface_counts_in_prose.py` reads **three trees** —
`src/auditmanager/api`, `infra/deploy` and `web/src` (lines 47–58). **`docs/` is not among them,
and nothing else reads it.** Every count the gate checks is a count in code.

Extend it to the documents that make load-bearing factual claims — `docs/program/CURRENT_STATE.md`,
`docs/program/ALPHA_ROADMAP.md`, `docs/manual-tests/**` — asserting **the migration head, the
contract surface triple, and the tagged tip** against the tree.

**Wave reports are explicitly out of scope and this is not a detail.** `docs/program/W30-CERT3.md`
naming head `0005` is *correct*, because it records what was true at its wave. **A guard that
cannot tell a record from a claim would force this programme to falsify its own history**, which
is `D-23`'s lesson pointing the other way. Say in your report how yours tells them apart.

**Show it red.** Put a stale surface count into one of those documents and quote the failure.

## R3 — a clean-clone deploy rehearsal, timed

`git clone` this repository to a fresh directory **outside the working tree**, provision it, and
run `infra/deploy/deploy.sh` against **a throwaway instance of your own** — never
`auditmanager-w19a`, which is the owner's stand and read-only to you.

**This does not establish `PA-01` criterion 1** and must not be reported as though it does: this
host has run `deploy.sh` many times, and the criterion is about a host that never has. What it
produces is **a checklist with measured timings** — what the host wave will actually do, in
order, with how long each step took and what each needs in place first.

Write that checklist into your report. **Name every value the deploy needs that is not in the
repository**, since the owner will have to supply each on the day.

## allowed_paths

```
.dockerignore                      (new)
infra/**
tests/contract/api_v1/**
docs/program/W45-READY.md
docs/program/DEPLOYMENT_RUNBOOK.md — only if R3 finds it wrong; say what and why
```

## forbidden_hotspots

`web/**` and `src/auditmanager/**` — **`W45-BLOCKS` owns both**, live in `/root/w45pos` ·
`contracts/**` · `db/migrations/**` · `docs/program/DEBT_REGISTER.md` ·
`docs/program/dispatch/**` · `Makefile` · `package.json` · any container not named `gate-w45b*`
**or your own rehearsal instance, which you name and report** · **the owner's stand
`auditmanager-w19a` is read-only: never restart, redeploy or reconfigure it.**

## Deliverables

1. The three pieces, each committed as you finish it.
2. `docs/program/W45-READY.md`, opened **before** the first measurement.
3. Every new assertion **shown failing** — mutate, red, revert, green, with the failing text
   quoted.
4. R3's checklist, with timings and with the owner-supplied values named.
5. Anything outside the grant: reported, not repaired.

## Verification

Lane `gate-w45b` — PostgreSQL `127.0.0.1:56340`, S3 `59940`/`59941`; `.env` is written.
`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`, then `.venv/bin/python -c "import boto3"`,
then `npm --prefix web ci`. Then `make gate > /root/w45b-gate.log 2>&1` and read the verdict
**from the `GATE OK` line in the log**.

**A harness has reported `exit code 0` over a failed gate four times in four days here.** Read
the log. `alpha-w44` closed at battery **2466**, foundation **35**, frontend **1110 in 78 files**.

## Discipline

Commit each step. Do not tag, push or merge. A judge runs on your branch before it is merged and
two more judge the merged tree before the final gate.
