# `W12-WEB` dispatch prompt — the frontend has never been swept

Base `0c3f464` on `planning/prototype-roadmap`, published as `origin/dev`.

One of three parallel streams in wave 12's stage A. You write **tests only**, so you do not
disturb the certification that follows, and you do not coordinate with the other streams.

---

You are session `W12-WEB`. Repository: /root/projects/PDF-Analysis.
Branch `agent/w12-web`, worktree `/root/w12web`.

## What you are for

Wave 10 swept `src/auditmanager` — about 300 rules across five trees — and found **157 that
could not be told from a deleted rule**. It did not touch `web/`.

`web/src` is **7 604 lines**, with 47 declared constants and 17 files that refuse something,
and 289 tests that have never been asked whether they can fail. It is a delivered part of
PC-01: criteria 3, 5, 6 and 7 are exercised through this UI in the manual runbook.

**PC-01 has been certified three times. Every pass established that each criterion can fail.
None established that each frontend rule can.**

## You own exactly these paths

- `web/tests/**`
- `docs/program/reviews/W12-WEB.md`

Nothing under `web/src`, nothing under `src/`, `db/`, `contracts/`.

## The harness is yours to work out, and to report

The Python streams use `make mutation-copy`. **There is no equivalent for vitest and you
should not pretend there is.** Work out how to mutate `web/src` without editing a tracked
file — a copied tree with a vitest config pointed at it, a path alias, whatever holds — and
**state the mechanism in your report, with the evidence that the mutated tree is the one the
tests imported.** That evidence is the whole basis of every row in your table; the Python
harness proves it by printing `auditmanager.__file__`, and yours needs its own equivalent.

If you cannot establish it, say so and report the sweep as unverified rather than presenting
it as solid.

## Where to look first — a starting point, not a specification

- **`run-presentation.ts`** maps run state to what a user sees. Wave 3 changed what
  `terminal_reason` carries and wave 11 added `cost_basis`; the UI renders `terminal_reason`
  raw. Which state mappings can be changed with 289 still green?
- **`csv-columns.ts`** — the frontend's own copy of the seventeen-column order. Wave 10 found
  the *Python* contract test could not detect a column swap, because it compared the header
  against the same list it was built from. Ask the same question here, and ask whether
  anything notices if the two copies disagree.
- **The upload envelope** — `web/src` refuses some inputs before the API does. Every one of
  those refusals is a rule; wave 9 found three like them in the Python envelope that nothing
  could redden, all on criterion 10's surface.
- **The evidence viewer and the decision panel** — criterion 6 requires a finding to open at
  its exact quotation and a verdict to be recorded with visible history.

Sweep the whole surface. If this list is wrong about something, say so.

## Provisioning

```
cd /root/projects/PDF-Analysis && git fetch origin
git worktree add /root/w12web -b agent/w12-web origin/dev
cd /root/w12web && git log --oneline -1
```

Base `0c3f464` or later. **Not under `/tmp`** — docker is snap-confined. Report your `HEAD` on
arrival. **Commit as you go**; wave 10's first attempt lost four sessions to a restart and
only committed work survived. Open `docs/program/reviews/W12-WEB.md` before your first edit.
Logs in `/root/w12web-logs/` — the five wave-10 streams shared one directory and one read
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

Instance `gate-w12c`, `POSTGRES_PORT=55670`, `S3_API_PORT=59270`, `S3_CONSOLE_PORT=59271`,
`POSTGRES_DB=audit_w12c`, bucket `auditmanager-gate-w12c`. Bootstrap with
`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`; copy `.env.example` to `.env` and set
exactly your instance.

## Report

`docs/program/reviews/W12-WEB.md`, committed incrementally: `HEAD` on arrival; **a table of
every rule you mutated and what reddened**, including the ones that reddened properly — that
table is the deliverable even when it is entirely green; each guard with its red and green
and the literal you pinned; every rule unreddenable by construction with its argument; every
product defect left unrepaired; anything false in this brief; elapsed wall-clock.
