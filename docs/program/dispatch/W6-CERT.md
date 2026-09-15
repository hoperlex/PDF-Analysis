# `W6-CERT` dispatch prompt — PC-01 re-certification

Base `c0d7dafab33a47e62050ba7c1c6916fae96ff98a` on `planning/prototype-roadmap`, published as
`origin/dev`. If your `HEAD` is one or two commits *ahead* of this and
`git diff ef5b8bf..HEAD --stat` touches only `docs/program/dispatch/**`, that is this brief
being committed — harmless, carry on. Anything else is the provisioning defect below. Gate at that commit: 803 passed / 5 skipped / 116 subtests, `make foundation`
35 passed, `git diff --check` clean.

You are the only session in this wave. Nothing runs beside you.

**The owner authorised this on 2026-09-15.** Start.

---

You are session `W6-CERT`. Repository: /root/projects/PDF-Analysis.

BASE COMMIT: `c0d7dafab33a47e62050ba7c1c6916fae96ff98a`. Branch `agent/w6-cert`.

## What you are for

PC-01 was re-certified on 2026-09-15 at `beaa7f7` by `W5-CERT`: all ten criteria of
`PROTOTYPE_PROFILE.md` §8, each shown able to fail, and a live run that found 3 of 3 seeded
issues and flagged 0 of 6 controls. `origin/main` carries that certification.

**Wave 6 has since changed behaviour again** — 87 lines across four files in `src/` and
`db/`. Much smaller than the 915 that prompted the last pass, and small enough that the
temptation is to certify the diff rather than the checkpoint. **Do not.** A checkpoint is
ten criteria or it is nothing, and the last pass earned its value by re-establishing the two
limits it could have inherited.

**You must have authored none of it, and you may repair none of it.** The integrator led
wave 6 and therefore cannot certify it; that is the entire reason this is a separate
session. A defect goes back as a precise
report naming the tree that owns it. A session that repairs the tree it is measuring cannot
be cited for the measurement — `P4_CLOSURE.md` opens with that rule and it is why every
finding in this programme has held up.

## Provisioning — read this first, it will fire

The harness seeds an agent worktree from `origin/main`. **`origin/main` now carries the
`beaa7f7` certification** (it advanced to `8f418e9` on 2026-09-15), so an ordinarily-seeded
worktree lands on recent code rather than on the W0.2-era commit that caught nineteen
sessions. Verify anyway; the fix is one owner decision old.

Your first action is `git rev-parse HEAD`. If it is not
`c0d7dafab33a47e62050ba7c1c6916fae96ff98a`, fetch and check out the base before anything
else, and **say in your report what your `HEAD` was on arrival.** The same applies to a
clean clone: `git clone` gives you `main`, which is the wrong commit for this work. Clone
and then `git checkout` the base SHA explicitly.

## What changed, and which criteria it touches

Derived from `git diff beaa7f7..c0d7daf -- src/ db/` — **87 lines, four files.** This is a
map for planning your attention, **not a list of what to test**: you test all ten criteria.
Treat the mapping itself as a claim to check.

| File | What moved, and what it touches |
|---|---|
| `runs/retry.py` | `AttemptSummary.budget_exhausted` now asks whether the last attempt *failed* instead of comparing counts. **The persisted value of `attempt_budget_exhausted` has changed** for runs that answered on their last allowed attempt: it was `True`, it is now `False`. Criteria 9 and 10 |
| `bootstrap/composition.py` | the environment is resolved once and governs the whole wiring; `_build_provider` no longer reaches for `os.environ`. `Application` gained a `provider_config` field. Criteria 1 and 4 — the cost ceiling a caller sets is now the ceiling the run obeys, which was not true at `beaa7f7` |
| `db/.../0004_cost_basis.py` | `downgrade()` refuses while any row records a measured cost. The **upgrade path is unchanged**, so criterion 2 should be unaffected — verify that rather than assume it |
| `db/.../0005_truncated_call_status.py` | docstring only; its vacuity justification is marked expired. No behaviour |

`git diff beaa7f7..c0d7daf -- src/ db/` is 87 lines and you should read all of it. That is
cheap here and it is the only way the table above becomes something you checked rather than
something you were told.

## One instruction that is new, and it is the most important thing in this brief

Wave 6 found that **`W2-QA`, an independent convergence session, had pinned the defective
value as its expected value.** Two of its seam tests asserted `attempt_budget_exhausted is
True` on runs that answered on their third attempt and published. That is why the defect
survived four waves and three sessions reading that code.

So: **a passing test is not evidence that the behaviour is right.** A test can encode what
the implementation did rather than what the contract requires, and this repository has a
measured instance of exactly that, written by a careful session. Where a criterion rests on
a test, read what the test actually asserts and decide for yourself whether the contract
says so. Where it rests on a number, ask where the number came from.

`docs/program/W6_CLOSURE.md` §3 has the full account.

## What `W5-CERT` got wrong, so you do not repeat it

The previous pass listed six false premises in its own brief. Four are fixed here. Two are
worth carrying:

- **The credential is git-ignored**, so it is absent from a worktree made by these
  instructions. `_provider_file` now finds it by asking `git rev-parse --git-common-dir`
  (that was `W5CERT-DEF-1`, fixed), so it should resolve without copying — **confirm that,
  because it is a fix you are the first to exercise.**
- **A run costs about $0.038**, not the ~$0.20 the old brief quoted from a stale document.

## The two accepted limits — re-examine, do not inherit

The accepted report records two criterion-10 failures as not inducible through the twelve
operations:

- **`checksum_mismatch`** — proved at the storage layer; the journey offers no way to hand
  the store bytes disagreeing with their declared digest.
- **`ungrounded_model_item`** — unreachable by design; the stage drops unresolvable
  quotations before the grounding gate sees them. Owner-accepted 2026-09-11.

Both were true at `6d3c0f3` and re-established at `beaa7f7`. **Neither is a fact you may
inherit**, and the reason is *not* that the code moved — it did not. `W5-CERT` checked and
found `_ground` byte-identical to `6d3c0f3` and `findings/grounding.py` unchanged; the
W5-CERT brief had claimed otherwise and was corrected in its own report. **That correction
was then carried into this brief unaltered, which is how a fixed record un-fixes itself.**

The real reason to re-establish them is that an inherited limit is an unmeasured one. A
claim about unreachability is exactly the kind that stays true until some unrelated change
makes it false, and nothing announces the day it does. Check
whether either is now inducible. If one is, that is a finding of the first importance — it
means a criterion the owner accepted as unreachable has become reachable and was never
scored.

## Anti-vacuity — the central obligation

Nine tests in this programme have passed or failed without exercising what they named, every
time by asserting a property of the fixture rather than of the code.

You are certifying rather than building, so the obligation takes a different shape: **for
each criterion, show that your check could have failed.** A criterion demonstrated by a
command that would print the same thing against a broken system is not demonstrated. Where
you can, break the thing and watch the criterion fail — the PC-02 corpus checker's
`--self-test` is the standard to match: 23 of 24 checks shown both red and green, with the
twenty-fourth named as an environment assertion no mutation could arrange rather than
counted as covered.

If you do write or mutate any guard: never edit a tracked file. Copy `src/` into a
session-unique scratch directory outside the worktree and run
`pytest -o pythonpath=<copy>/src`, because `pyproject.toml` sets `pythonpath = ["src"]` and
overrides an exported `PYTHONPATH`. **Symlink `contracts/`, `docs/` and `fixtures/` into
that copy** — `analysis.text.lock` resolves `docs/program/P02_LOCK.json` from `parents[4]`
of its own module file, so a copy without `docs/` fails before reaching any assertion. Prove
the copy is the one imported by printing `auditmanager.__file__` under the override before
you trust any result.

## Environment

Instance `gate-w6`, `POSTGRES_PORT=55580`, `S3_API_PORT=59180`, `S3_CONSOLE_PORT=59181`,
`POSTGRES_DB=audit_w6`, bucket `auditmanager-gate-w6`.

Bootstrap with `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`; bare `make bootstrap`
is correctly refused under an active virtualenv. Copy `.env.example` to `.env` and set
exactly your instance; it is git-ignored and is never committed.

**Do not put your worktree under `/tmp`.** Docker is snap-confined here and cannot see it —
`make up` fails with `open /var/lib/snapd/void/...`. Use a path under `/root/`.

A venv holds absolute paths: if you move the worktree, re-bootstrap.

## Rules

1. **Commit after every meaningful step.** A dispatch here was once killed mid-run and lost
   four sessions because each held its work uncommitted.
2. **Never add a root dependency.** `docs/program/P02_LOCK.json` is the pinned set.
3. Stay inside your owned paths. You repair nothing.
4. Nothing else runs in this wave, but the ports below are still yours alone.
   `OPERATING_CONSTRAINTS.md` §9 is worth reading first: §6 covers residue, not accumulated
   population, and telling the two apart means running your suite alone against the same
   database.
5. **Do not create a tag, and do not push or merge to `main`.** Whether `main` advances to
   carry a new PC-01 acceptance is the owner's decision, informed by your report.
6. **Check every premise in this brief against the tree before building on it.** Two of the
   integrator's three wave-2 briefs carried stale premises, both taken from closure records
   rather than from the code — `W2_CLOSURE.md` §2. The table above was built from a diff,
   which is better, but it is still a claim. If something here is wrong, say so in the
   report; that is a useful finding, not an inconvenience.

## Report

`docs/program/reviews/W6-CERT.md`, and in it:

- Your `HEAD` on arrival, and whether it matched the base.
- Every command with its exit code.
- Each of the ten criteria: the evidence, and what would have made it fail.
- The two accepted limits, re-examined, with the verdict on each stated as your own.
- The live run: model, cost against the ceiling, seeded issues found, controls flagged —
  as absolute numbers, comparable to PC-01's 3 of 3 and 0 of 6.
- Every defect found, described precisely, **left unrepaired**, naming the tree that owns
  it.
- A plain verdict: does PC-01 still hold at `c0d7daf`, hold with named exceptions, or not
  hold. If you cannot reach one, say what would let you.
- Elapsed wall-clock.
