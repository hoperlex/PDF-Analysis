# `W12-RCN` dispatch prompt — reconciliation proves less than it promises

Base `38a973a` on `planning/prototype-roadmap`, published as `origin/dev`.

**Stage A of wave 12.** `W12-CERT` re-certifies PC-01 *after* you land, so your change is
inside the certification rather than immediately stale against it. You do not coordinate with
that session and it does not start until your branch is merged.

---

You are session `W12-RCN`. Repository: /root/projects/PDF-Analysis.
Branch `agent/w12-rcn`, worktree `/root/w12rcn`.

## You own exactly these paths

- `src/auditmanager/ingest/reconciliation.py`
- `tests/integration/ingest/**`
- `docs/program/reviews/W12-RCN.md`

## The defect — `DEBT_REGISTER.md` D-2, verified by me before this brief

`Reconciler.verify_version` (`reconciliation.py:203`) calls `self._store.inspect(entry.blob_id)`
and compares `published.sha256` against `entry.sha256`.

**`inspect` is a `head_object`.** It returns the object's *recorded metadata*, not its bytes.
So the comparison is between two **declarations**: the metadata says X, the manifest says X,
and nothing has looked at the bytes. A replacement that leaves the metadata and the length
intact is reported **sound**.

`W11-RD` measured this on real MinIO rather than reading it off the source: `inspect().sha256`
equalled the manifest digest, `verify_version` did not fire, and `store.read` raised
`ChecksumMismatchError` over the same object. **The read path and reconciliation now disagree
about one row, with reconciliation the permissive one** — the reverse of how the wave-11 brief
described the system, which is itself worth knowing.

The docstring's second sentence is accurate. The first — *"Prove one published version is
still readable"* — is not: it proves neither readability nor byte integrity.

## This is a design call, and the argument is yours to make

`reconciliation.py`'s own docstring makes **"never lists, never reads bytes"** a deliberate
property. It is a cheap sweep meant to run over many versions. Converting it to a full-body
read changes what it costs, which is a real objection and not a formality.

At least three shapes are defensible:

- **Correct the promise, not the code.** Rename or restate so the method claims what it does
  — that the store's declaration still agrees with the manifest's. Cheapest, honest, and
  leaves a real fault detectable only by reading every object.
- **Add an opt-in deep check.** `verify_version(..., deep=False)`, hashing bytes only when
  asked. Keeps the sweep cheap and gives an operator a way to answer the question at all.
- **Always hash.** Strongest guarantee, and you must then say what it costs on a version with
  many entries and who would be surprised by that.

**Pick one and argue for it in your report.** A repair with no argument is a preference.
Whatever you choose, do not flatten two causes into one code: "the store's declaration
disagrees with the manifest" and "the bytes are not what either says" are different faults,
and wave 3 had to undo exactly that flattening for `analysis_failed`. `W11-RD` reached the
same conclusion independently and used `BlobMetadataInvalidError` for the second of its two
cases rather than inventing a code — **the 21st code is owner-blocked and you may not need
it; say so if you think you do.**

## Also in your tree — `DEBT_REGISTER.md` D-4

Against an unstamped object, `inspect` yields `sha256=""` and `verify_version` puts
`actual_sha256=""` into an operator-facing envelope. Wave 11 narrowed the reachable path by
making such an object unreadable through `read(verify=True)`, but an empty string can still
reach a reader where a digest is expected. Repair it or argue it is unreachable; do not leave
it unmentioned.

## What is different about this wave

**You write product code.** So:

1. **Every repair needs a guard that reddens without it** — mutated back to the defect and
   watched fail, not merely green afterwards. `W11-RD`'s three-mutation table is the standard.
2. **You do not certify your own repair.** `W12-CERT` follows you. Make no claim about
   PC-01 or any criterion.
3. **Say what an operator or a stored row observes differently**, including anything that
   becomes slower.

## Provisioning

```
cd /root/projects/PDF-Analysis && git fetch origin
git worktree add /root/w12rcn -b agent/w12-rcn origin/dev
cd /root/w12rcn && git log --oneline -1
```

Base `38a973a` or later. **Not under `/tmp`** — docker is snap-confined and cannot see it.
Report what your `HEAD` was on arrival.

**Commit as you go.** Wave 10's first attempt lost four sessions to a restart and only
committed work survived. Open `docs/program/reviews/W12-RCN.md` before your first edit.

**Use a session-unique scratch directory for logs** (`/root/w12rcn-logs/`). The five wave-10
streams shared one; one of them read another lane's gate failures as its own.

## The method

```
make mutation-copy MUT=/root/w12rcn-mut
```

It links the five directories a copy needs and proves the copy is the tree that will be
imported. It replaced a prose recipe that was wrong from wave 3 to wave 10 and did not merely
lose coverage — **it manufactured reds**. `FULL=1` copies instead of symlinking, which is how
you mutate a contract or fixture; **no copy makes a migration mutable**.

**Baseline the unmutated copy against your suites before trusting any red.**

**Pin expected values as literals.** Wave 9 lost five tests to importing the module's own
constants and building expectations from them. Wave 10 found a third form: where a test
derives its *input* from the constant it tests, raising the constant is an out-of-memory kill
rather than a red test.

**Read your mutated line back for meaning**, not just text. Four wave-10 streams wrote
mutations that did not mutate.

**A test that scans source text must resolve it from `auditmanager.__file__`, never from
`Path(__file__)`.** `W11-FIX` wrote guards that read the pristine checkout under a mutation
copy and were green against a tree that still had the defect. Reading an *authority* — a
contract, a migration, `P02_LOCK.json` — from the test file's own location is correct and is
the opposite case.

## Rules

1. Stay inside your owned paths. A defect elsewhere goes back as a report, unrepaired.
2. No root dependency; `docs/program/P02_LOCK.json` is the pinned set.
3. No bytes added to `fixtures/synthetic/ar/**` or `fixtures/validation/PC-02/**` — frozen
   evidence. Build what your test needs inside the test.
4. No tag, no push, no merge to `main`.
5. **Check every premise here against the tree.** Ten stale premises are on record in this
   programme, most in briefs written by the integrator who wrote this one — last wave, a
   class name that does not exist anywhere in the tree. Say so in your report if one is wrong.

## Your gate

```
make gate
```

Expect **1492 passed / 5 skipped / 163 subtests**. That count rose by 212 in wave 11 without
a single new test: `PROTOTYPE_PROFILE.md` §6.3's quarantine had been implemented as a
directory exclusion and was narrowed to the three CP-00 files it actually means. A linked
worktree has no `web/node_modules`; run `npm --prefix web ci` once.

## Environment

Instance `gate-w12a`, `POSTGRES_PORT=55650`, `S3_API_PORT=59250`, `S3_CONSOLE_PORT=59251`,
`POSTGRES_DB=audit_w12a`, bucket `auditmanager-gate-w12a`. Bootstrap with
`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`; copy `.env.example` to `.env` and set
exactly your instance.
