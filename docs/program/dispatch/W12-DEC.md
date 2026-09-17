# `W12-DEC` dispatch prompt — the decision ledger, swept only by reading

Base `0c3f464` on `planning/prototype-roadmap`, published as `origin/dev`.

One of three parallel streams in wave 12's stage A. You write **tests only**, so you do not
disturb the certification that follows, and you do not coordinate with the other streams.

---

You are session `W12-DEC`. Repository: /root/projects/PDF-Analysis.
Branch `agent/w12-dec`, worktree `/root/w12dec`.

## What you are for, and the mistake that created the gap

Wave 10 gave `W10-FND` `src/auditmanager/decisions/**` to read and named the append-only
ledger as a first place to look — **but did not give it `tests/integration/decisions/**` to
write in.** A guard for the ledger had nowhere to go, so that session swept the tree *by
reading* and reported the gap rather than widening its own scope, which was the right call.

That gap is mine and this stream closes it. `tests/integration/decisions/` exists and holds
`test_decision_ledger.py` and `test_keyed_append.py`; you own it now.

## You own exactly these paths

- `tests/integration/decisions/**`, `tests/integration/findings/**`
- `docs/program/reviews/W12-DEC.md`

You **read** `src/auditmanager/decisions/**` and the decision-facing parts of
`src/auditmanager/findings/**`. You write neither.

## What is already established, so you do not re-prove it

`W10-FND` swept `findings/` and reported, from reading rather than from mutation:

- the projection's agreement with the raw stream **is** asserted — `test_decision_ledger.py`
  folds the stream against the PostgreSQL view at lines 157 and 304;
- `finding_uid` freshness is caught by the `finding` primary key plus 25 tests.

**Both are claims from a session that could not test them. Check them by mutation.** If they
hold, say so — a confirmed claim is a result. If one does not, that is the finding.

## Where to look first

- **`expert_decision_event` is immutable by trigger.** Wave 10 found three trigger *arms*
  with no write attempt anywhere in the repository — the SQLSTATEs are well guarded, but
  per-table per-arm reachability was not, and `test_schema_shape.py` structurally cannot see
  it: it reads `pg_trigger` for the function name and never asks what the trigger fires on.
  Does the decision ledger's own trigger have both arms exercised?
- **`finding_current_verdict` is a projection over the stream.** Criterion 6 requires one
  finding accepted, one rejected, and a comment appended *later* and visible. What in that
  ordering can be changed without reddening anything?
- **The keyed append** — `append_decision_under_key` claims through
  `ingest.CommandRepository`, the same primitive `start_run` uses. Wave 8 found criterion 9's
  safety lives in a `UNIQUE` constraint and the recovery after it collides, **not** in the
  pre-read that looks like the guard. Ask whether the same is true here.
- **The verdict vocabulary** — what refuses a value outside it, and is the refusal asserted
  by *its own rule* rather than by "something raised"?

Sweep the whole surface. If this list is wrong about something, say so.

## Provisioning

```
cd /root/projects/PDF-Analysis && git fetch origin
git worktree add /root/w12dec -b agent/w12-dec origin/dev
cd /root/w12dec && git log --oneline -1
```

Base `0c3f464` or later. **Not under `/tmp`** — docker is snap-confined. Report your `HEAD` on
arrival. **Commit as you go**; wave 10's first attempt lost four sessions to a restart and
only committed work survived. Open `docs/program/reviews/W12-DEC.md` before your first edit.
Logs in `/root/w12dec-logs/` — the five wave-10 streams shared one directory and one read
another lane's failures as its own.

## Three outcomes, all of them results

- **Unreddenable and reachable** → write the guard. This is the yield.
- **Unreddenable by construction** → report it with the argument, and **do not fake a test**.
- **Reddened by something** → say what. Wave 9 spent two minutes ruling out a rule this way
  and saved a wave spent guarding something already guarded.

**A sweep that finds nothing is a successful sweep.** Report the empty result plainly. A
manufactured finding costs more than a quiet wave, because the next session builds on it.

**Assert which rule refused, not merely that something did.** Wave 9 found a test asserting
only the *field* of a refusal, which passed whichever of three rules fired — that is how a
deleted check survived a sweep.

## What makes a green meaningless — all four already made here

1. **Importing the constant you are testing** and building the expected value from it: both
   sides move together under mutation. **Pin literals.**
2. **Deriving your test's *input* from that constant**: wave 10 raised a limit and the test
   allocated 13 GiB and was killed — recorded as a red, and it was not one.
3. **A mutation that does not mutate.** `frozenset() or frozenset({...})` evaluates to the
   real set; `26 * 1024 * 1024` is a substring of `26 * 1024 * 1024 * 1024`. **Read the
   mutated line back for meaning, not text.**
4. **Reading source text from your own file's location.** Under a mutation copy that reads
   the *pristine* tree, so the guard is green against a tree that still has the defect.
   Reading an **authority** — a contract, a migration, a lock file — from the test file's
   location is the opposite case and is correct.

## Rules

1. **You write tests, never product code.** A defect goes back as a precise report,
   unrepaired, naming the owning tree. A session that repairs what it measures cannot be
   cited for the measurement.
2. Stay inside your owned paths. If a surface does not let you reach a rule, that is a
   finding, not a licence to reach elsewhere.
3. No root dependency. No bytes added to `fixtures/synthetic/ar/**` or
   `fixtures/validation/PC-02/**` — frozen evidence; build what you need inside the test.
4. No tag, no push, no merge to `main`.
5. **Check every premise here against the tree.** Ten stale premises are on record, most in
   briefs by the integrator who wrote this one — last wave, a class name that exists nowhere.
   Say so in your report if one is wrong.

## Your gate

```
make gate
```

Expect **1492 passed / 5 skipped / 163 subtests**, and frontend **289 passed**. That battery
count rose by 212 in wave 11 **without a single new test**: a quarantine written as a
directory exclusion had been hiding live contract tests from the gate. A linked worktree has
no `web/node_modules`; run `npm --prefix web ci` once.

Instance `gate-w12d`, `POSTGRES_PORT=55680`, `S3_API_PORT=59280`, `S3_CONSOLE_PORT=59281`,
`POSTGRES_DB=audit_w12d`, bucket `auditmanager-gate-w12d`. Bootstrap with
`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`; copy `.env.example` to `.env` and set
exactly your instance.

## Report

`docs/program/reviews/W12-DEC.md`, committed incrementally: `HEAD` on arrival; **a table of
every rule you mutated and what reddened**, including the ones that reddened properly — that
table is the deliverable even when it is entirely green; each guard with its red and green
and the literal you pinned; every rule unreddenable by construction with its argument; every
product defect left unrepaired; anything false in this brief; elapsed wall-clock.
