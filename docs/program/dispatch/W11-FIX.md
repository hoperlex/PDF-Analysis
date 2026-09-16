# `W11-FIX` dispatch prompt — four small defects, three of them documentation that lies

Base `30d129c` on `planning/prototype-roadmap`, published as `origin/dev`. Gate at that
commit: **1264 passed / 5 skipped / 116 subtests**, `make gate` → `GATE OK`.

One of three parallel streams repairing what wave 10's sweep found. The others work on
disjoint trees; you do not coordinate with them.

---

You are session `W11-FIX`. Repository: /root/projects/PDF-Analysis.
Branch `agent/w11-fix`, worktree `/root/w11fix`.

## You own exactly these paths

- `src/auditmanager/api/routers/multipart.py`, `src/auditmanager/api/schemas/projects.py`, `src/auditmanager/shared/errors/envelope.py`, `src/auditmanager/analysis/text/stage.py`, `src/auditmanager/exports/service.py`
- `tests/integration/api/**`, `tests/integration/analysis/**`, `tests/integration/exports/**`
- `docs/program/reviews/W11-FIX.md`

## Four defects, verified against the tree before this brief was written

### 1. Two comments that are false in the dangerous direction

`api/routers/multipart.py:96` and `api/schemas/projects.py:53` both state that `details`
values "are not screened the way `message` is". **They are**, and have been since the `B6`
fix: `shared/errors/envelope.py` runs detail values through the same `_FORBIDDEN` tuple and
raises `UnsafeDetailValue`.

A comment that says a safety check is absent when it is present invites a later reader to add
one, or to route around it. Correct the statement; the refusals themselves are right.

### 2. A docstring that undercounts the screen

`shared/errors/envelope.py`'s docstring lists **five** forbidden shapes. There are **six** —
it omits the S3-style object key. Count them in the `_FORBIDDEN` tuple yourself; my own
wave-10 brief said "seven" twice and was wrong, which is exactly why you count rather than
believe.

### 3. `cost_basis` is on the wrong path

`analysis/text/stage.py`: the budget-overrun branch puts `cost_basis` in its metrics
(line ~278); **the success branch does not** (metrics built around line ~338). A consumer
reading `metrics["cost_basis"]` gets a value when the run overran its budget and a `KeyError`
when it succeeded — backwards from useful.

The `model_call` row itself is fine: `_record(..., cost_basis=...)` sets it on both paths, so
the ledger is correct and only the stage metrics are asymmetric. The comment at lines 299–302
records that a first attempt put it on a dict the executor never reads, so **this is the
unfinished half of a repair already in progress**, not a fresh decision.

Note `contracts/analysis/v1/stage-result.schema.json` admits only scalars in `metrics`.

### 4. A filename property with no consumer

`exports/service.py` defines `_FILENAME_TEMPLATE = "audit_run_{run_id}.csv"` and an
`ExportResult.filename` property. **Nothing reads it.** The live header comes from
`api/routers/export.py:_disposition` → `{run_id}.csv`, and the frontend's `csvFileName` →
`{runId}-findings.csv`.

**Check the contract before you touch this.** `openapi.json`'s `Content-Disposition` response
header says the name is "presentation only and is never an identity" and pins no value — so
the UI and the header differing is **permitted**, not a defect, and is not yours to
reconcile. The defect is the dead property that reads as the source of truth.

Removing it is a public-surface change; if you judge it should stay, say what would read it
and make that argument instead. Either way the outcome must be that a reader can tell which
name the system actually serves.

## The shape of this wave's work

Three of these four are text. That is the point: wave 10 found that a stale comment on a
security surface survives longer than a stale test, because nothing executes it. Where you
can make the claim executable instead of merely correcting it, do — a test asserting that the
screen has six shapes and that each is reachable is worth more than a corrected sentence.

## Provisioning

```
cd /root/projects/PDF-Analysis && git fetch origin
git worktree add /root/w11fix -b agent/w11-fix origin/dev
cd /root/w11fix && git log --oneline -1
```

Base `30d129c` or later. **Not under `/tmp`** — docker is snap-confined. Say in your report
what your `HEAD` was on arrival.

**Commit as you go.** Wave 10's first attempt lost four sessions to a restart and only
committed work survived. Open `docs/program/reviews/W11-FIX.md` early and append to it.

**Use a session-unique scratch directory for logs.** The five wave-10 streams shared one and
overwrote each other's gate output; one of them read another lane's failures as its own.

## What is different about this wave

Wave 10 swept and wrote tests. **You write product code.** That changes three things:

1. **Every repair needs a guard that reddens without it.** Not "a test that passes after" —
   a test you have mutated back to the defect and watched fail. A repair with a green test
   either way is a repair nobody can defend later.
2. **You may not certify your own repair.** Say what you changed and what you proved; a
   later session re-certifies PC-01 against it. Do not write a sentence claiming a criterion
   still holds.
3. **Behaviour changes carry re-certification debt.** Keep the change minimal and say what
   an operator or a stored row would observe differently.

## The method

```
make mutation-copy MUT=/root/w11fix-mut
```

New in wave 10 and it replaces the prose recipe every brief carried since wave 3 — which was
**wrong**, and not in a harmless way: it omitted `db/` and `tools/`, and a copy without
`tools/` fails four `p02_journey` tests **unmutated**. It manufactured reds. The target links
all five directories and proves the copy is the tree that will be imported.

`FULL=1` copies them instead of symlinking, which is how you mutate a contract or a fixture.
**No copy makes a migration mutable** — `tests/integration/db/conftest.py` derives the
repository root from its own file.

**Baseline the unmutated copy against your suites before trusting any red.** That instruction
matters more than the directory list: no list is safe against the next path someone resolves
from the root, and a baseline is.

**Pin expected values as literals.** Wave 9 lost five tests to importing the module's own
constants and building the expectation from them — both sides move together under mutation.
Wave 10 found the same failure in a third form: where a test derives its *input* from the
constant it tests, raising the constant is not a red test, it is an out-of-memory kill.

**Read your mutated line back for meaning**, not just for text. Four wave-10 streams wrote
mutations that did not mutate; `frozenset() or frozenset({...})` evaluates to the real set,
and `26 * 1024 * 1024` is a substring of `26 * 1024 * 1024 * 1024`.

## Rules

1. Stay inside your owned paths. A defect in another tree goes back as a report, unrepaired.
2. Never add a root dependency; `docs/program/P02_LOCK.json` is the pinned set.
3. Never add bytes to `fixtures/synthetic/ar/**` or `fixtures/validation/PC-02/**` — frozen
   evidence. Build the bytes your test needs inside the test.
4. No tag, no push, no merge to `main`.
5. **Check every premise in this brief against the tree.** Nine stale premises are on record
   in this programme, most of them in briefs written by the integrator who wrote this one —
   including, last wave, a count of forbidden shapes that was simply wrong. If something here
   is false, say so in your report.

## Your gate

```
make gate
```

Expect **1264 passed / 5 skipped / 116 subtests** before you change anything. A linked
worktree has no `web/node_modules`; run `npm --prefix web ci` once.

`tests/contract` and `tests/checkpoint` are quarantined by `PROTOTYPE_PROFILE.md` §6.3 and
are **not** your gate. Wave 10 found they cover rules the gate does not, which is why
grepping them for coverage misleads; the integrator is handling that separately.

## Environment

Instance `gate-w11b`, `POSTGRES_PORT=55640`, `S3_API_PORT=59240`, `S3_CONSOLE_PORT=59241`,
`POSTGRES_DB=audit_w11b`, bucket `auditmanager-gate-w11b`. Bootstrap with
`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`; copy `.env.example` to `.env` and set
exactly your instance. No live provider needed.

## Report

`docs/program/reviews/W11-FIX.md`: your `HEAD` on arrival; every repair with the guard that
reddens without it, shown red and green; what an operator or a stored row observes
differently; anything you decided not to repair and why; anything false in this brief;
elapsed wall-clock.
