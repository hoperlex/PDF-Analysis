# `W10-RUN` dispatch prompt — mutation sweep of runs, ingest and the migrations

Base `fb30e96` on `planning/prototype-roadmap`, published as `origin/dev`. Gate at that
commit: **816 passed / 5 skipped / 116 subtests**, `make gate` → `GATE OK`.

One of five parallel streams. The others sweep disjoint trees on their own instances. You do
not coordinate with them and you do not read their output.

---

You are session `W10-RUN`. Repository: /root/projects/PDF-Analysis.
Branch `agent/w10-run`, worktree `/root/w10run`.

## What you are for

Two waves running, a mutation sweep has found guards that do not guard. Wave 8 found three —
a cross-check the twelve operations cannot reach, a recovery carrying criterion 9's safety
with no test, and a tautology standing in for a live measurement. Wave 9 swept one module and
found three more rules no test could redden, all on the criterion-10 surface.

**PC-01 has been certified twice, and both passes established that each *criterion* can fail.
Neither established that each *rule* can.** That is the gap you are sweeping.

You read `src/auditmanager/runs/**`, `src/auditmanager/ingest/**`, `db/migrations/**` — 3502 lines plus five migrations.

## You own exactly these paths

- `tests/integration/runs/**`, `tests/integration/ingest/**`, `tests/integration/db/**`
- `docs/program/reviews/W10-RUN.md`

Nothing under `src/`, `db/`, `contracts/` or `web/`.

## Where to look first

**This tree has had the most integrator hands on it, which is exactly why it is dispatched
rather than swept by me.** Waves 2, 3, 6 and 8 all changed code here, and wave 8's finding was
that a careful independent QA had pinned a defective value as its expected value. **Treat
every existing assertion in your test paths as a claim, not as evidence.**

- **`runs/retry.py`** — `ATTEMPT_BUDGET = 3`, `BACKOFF_SECONDS = (2.0, 8.0)`,
  `RETRYABLE_STAGE_ERRORS`. Which can change without reddening anything? The ladder is
  asserted by value and order in one place; is the policy *refusing a non-retryable code*
  asserted, or only described in its docstring?
- **`runs/executor.py`** — 236 lines added in wave 2. Interrupted-run reconciliation
  (`OD-10`), the stage sequence, the terminal write.
- **`ingest/service.py` and `reconciliation.py`** — `envelope.py` was swept in wave 9 and
  `commands.py`'s race guarded in wave 8; **these two were swept by nobody.** Blob/DB
  reconciliation, and the rejected-blob settlement whose consequence `GATE_B1_CLOSURE` item 2
  records.
- **`db/migrations/**`** — `0004`'s downgrade refusal is guarded as of wave 6. Are `0002`'s
  triggers — `am_append_only` and the immutability triggers — each reachable and each
  asserted by their own SQLSTATE (`AM001`/`AM002`/`AM003`) rather than by "it raised"? Note
  the CP-00 suites cannot run from a linked worktree; that is quarantine material, not yours.

This is a starting point built from the closure records and the tree, **not a
specification**. Sweep your whole surface. If the list is wrong about something, say so.

## Provisioning — check, do not assume

`origin/main` now carries the `beaa7f7` certification, so an ordinarily-seeded worktree
should land on recent code. That is one owner decision old and has never been relied on.

```
git rev-parse HEAD
```

Base is `fb30e96` on `planning/prototype-roadmap`, published as `origin/dev`. If your HEAD is
not on that line:

```
cd /root/projects/PDF-Analysis && git fetch origin
git worktree add /root/w10run -b agent/w10-run origin/dev
cd /root/w10run
```

**Do not put your worktree under `/tmp`** — docker is snap-confined and cannot see it.
Say in your report what your `HEAD` was on arrival.

## The method, and it is not negotiable

For every constant and every refusing branch in the `src/` paths you read, in turn:

1. **Mutate it on a copy.** Never edit a tracked file. Copy `src/` to a session-unique
   directory outside the worktree, **symlink `contracts/`, `docs/` and `fixtures/` into it**
   — `analysis.text.lock` resolves `docs/program/P02_LOCK.json` from `parents[4]` of its own
   module file, so a copy without `docs/` fails before reaching any assertion — and run
   `pytest -o pythonpath=<copy>/src`. **Print `auditmanager.__file__` and confirm it resolves
   under the copy before you trust a single result.**
2. **Run the suites that could plausibly cover it**, not only the one you expect. Wave 9's
   first sweep ran two suites and that is what separated "unguarded" from "guarded
   elsewhere".
3. **Record what reddened.** A mutation that reddens nothing is the finding this wave exists
   for.

### The one mistake that will cost you the whole wave

Wave 9 wrote five green tests over three rules they could not check. They imported the
module's own constants and built the expected value from them, so **both sides of every
comparison moved together under mutation**: raising a limit also lengthened the input the
test sent, the refusal still happened, and the test still passed.

**Pin expected values as literals.** Never import `MAX_BYTES` from the module and then assert
a message built from it. Write the number. Where an independent authority exists — a
migration's CHECK, a frozen contract, `P02_LOCK.json` — pin against that and say so, so a
constant that drifts away from it is a red test rather than a quiet agreement between a
module and itself.

### Three outcomes, and all three are results

- **Unreddenable and reachable** → write the guard. This is the yield.
- **Unreddenable *by construction*** → report it and do not fake a test. Wave 9 found
  `MIN_PAGES` looked unguarded, but a zero-page document is refused earlier by the page
  parser and no document can have fewer than zero pages. Wave 3 found a tiebreaker whose
  removal makes an order *unspecified* rather than wrong. Say which, and give the argument.
- **Reddened by something** → say what reddened it. Wave 9 spent two minutes ruling out
  `PDF_MAGIC` this way and saved a wave spent guarding something already guarded.

**A sweep that finds nothing is a successful sweep.** Report the empty result plainly. Do not
pad it. A manufactured finding costs more than a quiet wave, because the next session builds
on it.

### Field is not reason

Where a guard refuses, assert **which rule** refused, not merely that something did. Wave 9
found a test asserting `details["field"] == "source_filename"`, which passed whichever of
three name rules fired — and that is how a deleted check survived a sweep.

## Rules

1. **Commit after every meaningful step.** A dispatch here was once killed mid-run and lost
   four sessions because each held its work uncommitted.
2. **Stay inside your owned paths.** If a module's public surface does not let you reach a
   guard, **that is a finding**, not a licence to reach into another tree.
3. **You write tests, not product code.** Writing a guard for an unguarded rule is your job.
   Changing the rule is not: a product defect goes back as a precise report, unrepaired,
   naming the tree that owns it. A session that repairs the tree it measures cannot be cited
   for the measurement.
4. **Never add a root dependency.** `docs/program/P02_LOCK.json` is the pinned set.
5. **Never add bytes to a corpus.** `fixtures/synthetic/ar/**` and
   `fixtures/validation/PC-02/**` are frozen evidence; adding to either invalidates a
   measurement already taken. Build the bytes your test needs inside the test — wave 9's
   zero-page PDF is 311 bytes and `pypdf` writes it in three lines.
6. **Do not create a tag, and do not push or merge to `main`.**
7. **Check every premise in this brief against the tree.** Eight stale premises have been
   recorded in this programme, several in dispatch briefs written by the integrator who
   wrote this one. If something here is wrong, **say so in your report** — that is a useful
   finding, not an inconvenience.

## Your gate

```
make gate
```

It runs `make foundation`, the canonical battery, the frontend suite and `git diff --check`,
and fails if any fails. It replaced four things a wave had to remember;
`OPERATING_CONSTRAINTS.md` §7 names the Makefile as the authority. Expect **816 passed / 5
skipped / 116 subtests** before you add anything.

`tests/contract` and `tests/checkpoint` are CP-00 historical evidence, red before you start
and quarantined by `PROTOTYPE_PROFILE.md` §6.3. Not your gate.

A linked worktree has no `web/node_modules` — it is git-ignored. Run `npm --prefix web ci`
once; the gate will not borrow another checkout's modules and says so.

## Environment

Instance `gate-w10d`, `POSTGRES_PORT=55620`, `S3_API_PORT=59220`, `S3_CONSOLE_PORT=59221`,
`POSTGRES_DB=audit_w10d`, bucket `auditmanager-gate-w10d`. Ports confirmed free 2026-09-16.

Bootstrap with `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`; bare `make bootstrap`
is correctly refused under an active virtualenv. Copy `.env.example` to `.env` and set
exactly your instance; it is git-ignored and never committed.

You need **no live provider**. Everything in your scope is reachable with recorded and
scripted adapters; a live call would add cost and variance for nothing.

Read `OPERATING_CONSTRAINTS.md` §9 before concluding another session interfered: §6 covers
residue, not accumulated population, and telling them apart means running your suite alone
against the same database.

## Report

`docs/program/reviews/W10-RUN.md`, and in it:

- Your `HEAD` on arrival, and whether it matched the base.
- **A table of every rule you mutated and what reddened**, including the ones that reddened
  properly. That table is the deliverable even when it is entirely green.
- Each guard you wrote, mutated red and green, with the literal you pinned and the authority
  you pinned it against.
- Every rule unreddenable *by construction*, with the argument.
- Every product defect, precise, **left unrepaired**, naming the owning tree.
- Anything in this brief that turned out to be false.
- Elapsed wall-clock.
