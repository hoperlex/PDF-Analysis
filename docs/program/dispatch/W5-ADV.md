# `W5-ADV` dispatch prompt — adversarial QA of what waves 2 and 3 changed

Base `ef5b8bf6cbef240fe6b63043455545fb4bdf12b8` on `planning/prototype-roadmap`, published as
`origin/dev`. If your `HEAD` is one or two commits *ahead* of this and
`git diff ef5b8bf..HEAD --stat` touches only `docs/program/dispatch/**`, that is this brief
being committed — harmless, carry on. Anything else is the provisioning defect below. Gate at that commit: 793 passed / 5 skipped / 116 subtests, `make foundation`
35 passed, `git diff --check` clean.

Runs **in parallel** with `W5-CERT` (`docs/program/dispatch/W5-CERT.md`), on a different
instance. You do not coordinate with it and you do not read its output; §"How your report
combines" says how the two results meet.

---

You are session `W5-ADV`. Repository: /root/projects/PDF-Analysis.

BASE COMMIT: `ef5b8bf6cbef240fe6b63043455545fb4bdf12b8`. Branch `agent/w5-adv`.

## What you are for

Wave 2 ran three sessions in parallel and an independent convergence QA checked that they
composed. **Wave 3 got no such pass.** The integrator authored it, mutation-proved it, and
merged it. That is one pair of eyes on code that changes what a failed run tells an
operator, and the integrator is not able to be the second pair.

You authored none of it and **you may repair none of it.** A defect goes back as a precise
report naming the tree that owns it. A session that repairs the tree it is measuring cannot
be cited for the measurement.

## The seam to attack first, and why it is the sharpest

Wave 2 built the retry loop. Wave 3 rewrote terminal selection. **Neither session saw the
other's code, and they meet on one path.**

- `tests/integration/runs/test_retry_policy.py:303`,
  `test_the_budget_is_finite_and_its_exhaustion_reaches_a_terminal`, asserts that when the
  attempt budget is exhausted the **stage** row carries `dependency_unavailable` — "an
  operator reading `analysis_failed` has no reason to retry".
- Wave 3 made the **run** row carry the cause too, via `select_terminal(..., stage_errors=)`.
- **Nothing asserts `audit_run.terminal_reason` on the exhausted path.** The wave-3 guard
  `test_terminal_reason_names_the_cause.py` reaches the unreachable-provider case by a
  different route.

So the run row's reason after an exhausted budget is unasserted, and the two halves were
written by sessions that never read each other. Establish what it actually says. If it is
right, say so and say what now holds it right — an unasserted correct behaviour is a
coverage hole, and per this programme's rule that is worth a new test rather than a shrug.

Do not stop there. That is the seam I can see; you are here for the ones I cannot.

## What changed, and where to look

`git diff 6d3c0f3..ef5b8bf -- src/ db/` — 915 lines. Read the diff, not the closures.

| Area | What to doubt |
|---|---|
| `runs/retry.py` (new, 260 lines) | `ATTEMPT_BUDGET = 3`, `BACKOFF_SECONDS = (2.0, 8.0)`. Which failures are retried and which are not; whether a retried call can launder a bad answer into a good one; whether the cost ceiling really binds **across** attempts rather than per attempt |
| `runs/executor.py` (+236) | idempotency under retry. A retry that reuses a key must not duplicate; one that suffixes a key must not orphan. `P4_CLOSURE.md` §1 accepted a retry judgement on the grounds that the input was provably identical — check that property still holds in code |
| `findings/terminal.py` | the single-distinct-code rule and the frozen-catalog validation. `audit_run.terminal_reason` is CHECK-constrained to the 20-member catalog; a code that escapes validation turns a failed run into a database error |
| `findings/queries.py` | listing order now claims to match the CSV's key family. The integrator reported two mutations that stayed **green** — dropping the tiebreaker, and dropping `COLLATE "C"`. Both are recorded in `W3_CLOSURE.md` §1 as unreddenable. **Decide for yourself whether that is true** |
| `db/migrations` `0004`, `0005` | forward and backward, against a database with rows in it, not only an empty one |
| `analysis/text/provenance.py`, `stage.py` | `truncated` as a first-class status. `GATE_B2_CLOSURE.md` §5.3 records that it was previously mapped onto `succeeded` — truncated answers were filed as clean successes. Check nothing downstream still treats it as success |

## You own exactly these paths

- `tests/integration/runs/**`
- `tests/integration/findings/**`
- `tests/integration/exports/**`
- `docs/program/reviews/W5-ADV.md` — your report

Nothing under `src/`, `db/`, `contracts/` or `web/`. If a module's public surface does not
let you demonstrate something, **that is a finding**, not a licence to reach inside.

You are extending suites that already exist and that carry the integrator's wave-3 guards.
Do not rewrite what is there without saying why in the report. If you believe one of those
guards is vacuous, **prove it** — show it green against a mutation that should have
reddened it — and report it rather than deleting it.

## Anti-vacuity — the central obligation

Nine tests in this programme have passed or failed without exercising what they named, every
time by asserting a property of the fixture rather than of the code. **Every guard you write
must be shown to fail.** Mutate the thing it protects, confirm red, revert, confirm green,
report both. A mutation producing a collection error, an import error, or a `DomainError`
from unrelated machinery rather than a guard failure proves nothing and must be redone.

A mutation that reddens nothing is itself a result: either the guard is vacuous or the
behaviour is unspecified rather than wrong. Say which, as the integrator did for M2 and M3
in `W3_CLOSURE.md` §1 — and check whether that reasoning survives your reading of it.

Never edit a tracked file to mutate. Copy `src/` into a session-unique scratch directory
outside the worktree and run `pytest -o pythonpath=<copy>/src`, because `pyproject.toml`
sets `pythonpath = ["src"]` and overrides an exported `PYTHONPATH`. **Symlink `contracts/`,
`docs/` and `fixtures/` into that copy** — `analysis.text.lock` resolves
`docs/program/P02_LOCK.json` from `parents[4]` of its own module file, so a copy without
`docs/` fails before reaching any assertion. Prove the copy is the one imported by printing
`auditmanager.__file__` under the override before you trust any mutation result.

## Provisioning — read this first, it will fire

The harness seeds an agent worktree from `origin/main`. **`origin/main` is deliberately
still at `6d3c0f3`** — the PC-01 acceptance, ~before everything you are here to attack. It
has not moved because moving it is what re-certification decides.

So unless you check, you will attack the old code and find nothing, correctly and uselessly.

Your first action is `git rev-parse HEAD`. If it is not
`ef5b8bf6cbef240fe6b63043455545fb4bdf12b8`, fetch and check out the base before anything
else, and **say in your report what your `HEAD` was on arrival.**

## The gate you run

- `.venv/bin/pytest tests --ignore=tests/contract --ignore=tests/checkpoint` — expect 793
  passed / 5 skipped / 116 subtests before you start, and green again when you finish, with
  your additions on top.
- `make foundation` — expect 35 passed.
- `git diff --check` — expect exit `0`.

`tests/contract` and `tests/checkpoint` are CP-00 historical evidence, red before you start,
quarantined by `PROTOTYPE_PROFILE.md` §6.3. Not your gate.

Freeze the tree before the battery: `OPERATING_CONSTRAINTS.md` §8. And read §9 before you
conclude that another session interfered — §6 covers residue, not accumulated population,
and telling the two apart means running your suite alone against the same database. A
wave-2 session lost time to exactly that confusion: a paging test that walked at most 400
rows against a 495-row population and blamed interference.

## Environment

Instance `gate-w5a`, `POSTGRES_PORT=55570`, `S3_API_PORT=59170`, `S3_CONSOLE_PORT=59171`,
`POSTGRES_DB=audit_w5a`, bucket `auditmanager-gate-w5a`. All three ports were confirmed free
on 2026-09-15. **`W5-CERT` is on `gate-w5` / 55560 / 59160 / 59161 — never touch those.**

Bootstrap with `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`; bare `make bootstrap`
is correctly refused under an active virtualenv. Copy `.env.example` to `.env` and set
exactly your instance; it is git-ignored and is never committed.

**Do not put your worktree under `/tmp`.** Docker is snap-confined here and cannot see it —
`make up` fails with `open /var/lib/snapd/void/...`. Use a path under `/root/`.

A venv holds absolute paths: if you move the worktree, re-bootstrap.

You need no live provider. Everything in your scope is reachable with recorded and scripted
adapters, and a live call would only add cost and variance.

## Rules

1. **Commit after every meaningful step.** A dispatch here was once killed mid-run and lost
   four sessions because each held its work uncommitted.
2. **Never add a root dependency.** `docs/program/P02_LOCK.json` is the pinned set.
3. Stay inside your owned paths. You repair nothing.
4. Do not measure while `W5-CERT` runs against its services; your ports are yours alone.
5. **Do not create a tag, and do not push or merge to `main`.**
6. **Check every premise in this brief against the tree before building on it.** Two of the
   integrator's three wave-2 briefs carried stale premises, both taken from closure records
   rather than from the code — `W2_CLOSURE.md` §2. The table above was built from a diff and
   the seam in §"The seam to attack first" from reading the tests, which is better, but both
   are still claims. If something here is wrong, **say so in the report** — that is a useful
   finding, not an inconvenience, and it is the finding this programme has most often
   missed.

## How your report combines with `W5-CERT`

`W5-CERT` asks whether the ten §8 criteria still hold at the journey level. You ask whether
the new code is correct and whether its guards are real. Different failure modes, deliberately.

If you find a defect that is visible through the twelve journey operations, `W5-CERT` should
have found it too; if it did not, **that gap is itself a finding about the certification**,
and worth saying. If you find one that is not journey-visible, `W5-CERT`'s verdict stands
and the defect is repaired separately.

Neither session's verdict is subordinate to the other's. Both go to the integrator.

## Report

`docs/program/reviews/W5-ADV.md`, and in it:

- Your `HEAD` on arrival, and whether it matched the base.
- Every command with its exit code.
- The exhausted-budget `terminal_reason` question, answered with evidence either way.
- Each guard you wrote, mutated, red and green — and each mutation that reddened nothing,
  with your judgement on which of the two reasons it was.
- Your verdict on the integrator's two green mutations (M2, M3 in `W3_CLOSURE.md` §1):
  agree, or show one of them reddenable.
- Every defect found, described precisely, **left unrepaired**, naming the tree that owns it.
- Anything in this brief that turned out to be false.
- Elapsed wall-clock.
