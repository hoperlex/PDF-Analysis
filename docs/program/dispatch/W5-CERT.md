# `W5-CERT` dispatch prompt — PC-01 re-certification

Base `3412fb2cb1bcf3fc4ad926c82dae8c7f5c640b65` on `planning/prototype-roadmap`, published as
`origin/dev`. Gate at that commit: 793 passed / 5 skipped / 116 subtests, `make foundation`
35 passed, `git diff --check` clean.

**This dispatch needs the owner's go-ahead before it is started.** Whether to re-certify is
the owner's decision, not the integrator's. Everything below is ready for when that decision
is taken.

---

You are session `W5-CERT`. Repository: /root/projects/PDF-Analysis.

BASE COMMIT: `3412fb2cb1bcf3fc4ad926c82dae8c7f5c640b65`. Branch `agent/w5-cert`.

## What you are for

PC-01 was accepted on 2026-09-14 at `6d3c0f3`: ten criteria of `PROTOTYPE_PROFILE.md` §8,
a live run that found 3 of 3 seeded issues and flagged 0 of 6 controls.

**Since that acceptance, waves 2 and 3 changed behaviour PC-01 certified** — 915 lines
across `src/` and `db/`, including two new migrations, a new retry module and a rewritten
terminal-selection path. The accepted report describes a system that no longer exists in
those places. Your job is to establish whether the ten criteria still hold.

**You must have authored none of it, and you may repair none of it.** The integrator led
waves 2 through 4 and therefore cannot certify them; that is the entire reason this is a
separate session rather than another integrator wave. A defect goes back as a precise
report naming the tree that owns it. A session that repairs the tree it is measuring cannot
be cited for the measurement — `P4_CLOSURE.md` opens with that rule and it is why every
finding in this programme has held up.

## Provisioning — read this first, it will fire

The harness seeds an agent worktree from `origin/main`. **`origin/main` is deliberately
still at `6d3c0f3` — the commit PC-01 already certified.** It has not moved, because moving
it is what re-certification decides.

So unless you check, you will certify the old code and conclude, correctly and uselessly,
that nothing changed.

Your first action is `git rev-parse HEAD`. If it is not
`3412fb2cb1bcf3fc4ad926c82dae8c7f5c640b65`, fetch and check out the base before anything
else, and **say in your report what your `HEAD` was on arrival.** The same applies to a
clean clone: `git clone` gives you `main`, which is the wrong commit for this work. Clone
and then `git checkout` the base SHA explicitly.

## What changed, and which criteria it touches

Derived from `git diff 6d3c0f3..3412fb2 -- src/ db/`. This is a map for planning your
attention, **not a list of what to test** — you test all ten criteria. Treat the mapping
itself as a claim to check, not as given.

| Criterion | What moved underneath it |
|---|---|
| 2 `migration_from_empty` | two new migrations — `0004_cost_basis`, `0005_truncated_call_status`. The path from an empty database is not the one that was certified |
| 4 `deterministic_path_and_text_analysis` | `analysis/text/stage.py`, `provenance.py`, `lock.py`; provider output-token figures now reach the metrics and the ledger |
| 5 `seeded_issues_and_quotation_grounding` | `findings/queries.py` — the published-findings listing order changed to match the CSV's key family |
| 6 `evidence_decisions_and_history` | `api/routers/ports.py` — the query surface (`limit`, `cursor`, `category`, `verdict`) |
| 7 `csv_resolving_to_exact_aggregates` | the CSV itself is **unchanged**; what changed is that the listing now agrees with it. Verify the CSV bytes still resolve to the exact project/version/run |
| 9 `idempotency_creates_no_duplicates` | `runs/executor.py` (+236 lines) and the new `runs/retry.py`. **Look hardest here.** A retry that reuses a key must not duplicate, and a retry that suffixes one must not orphan |
| 10 `explicit_failures` | `findings/terminal.py` and `runs/retry.py`. An unavailable provider now retries in-process before failing, and the run row names `dependency_unavailable` rather than the generic `analysis_failed` PC-01 recorded |

Criterion 10 is where the certified artifact is most visibly stale, and it is the one to
approach with the most suspicion in **both** directions: the new behaviour is arguably
better conformance to §8's "shown explicitly with no fallback", and a retry that silently
converts a hard failure into a success would be a straight violation of it. Establish which
it is from the run, not from the closure documents.

## You own exactly these paths

- `artifacts/checkpoints/PC-01/**`
- the PC-01 rows of `docs/program/CHECKPOINT_REGISTRY.md`
- `docs/manual-tests/PC-01_prototype.md`
- `docs/program/reviews/W5-CERT.md` — your report

Nothing under `src/`, `db/`, `tests/`, `contracts/` or `web/`. If a criterion cannot be
demonstrated because the code does not permit it, **that is a finding**, not a licence to
change the code.

Do not overwrite the accepted report. `report.json` records an acceptance that really
happened at a named commit; write the new certification beside it so the two can be
compared, and let the registry row say which is current.

## The gate you run

- `.venv/bin/pytest tests --ignore=tests/contract --ignore=tests/checkpoint` — the canonical
  battery. Expect 793 passed / 5 skipped / 116 subtests.
- `make foundation` — expect 35 passed.
- `git diff --check` — expect exit `0`.
- The ten criteria of `PROTOTYPE_PROFILE.md` §8, by the runbook in
  `docs/manual-tests/PC-01_prototype.md`, from a clean clone on your own instance.
- **One live `text_analysis`.** Criterion 4 requires it and a recorded adapter does not
  satisfy it. `OD-03`'s ceiling is machine-readable as `AUDITMANAGER_RUN_COST_CEILING_USD`,
  default USD 1.00, and it now binds across retry attempts rather than per call — confirm
  that is true rather than assuming it.

`tests/contract` and `tests/checkpoint` are CP-00 historical evidence, red before you start,
quarantined by `PROTOTYPE_PROFILE.md` §6.3. Not your gate.

## The two accepted limits — re-examine, do not inherit

The accepted report records two criterion-10 failures as not inducible through the twelve
operations:

- **`checksum_mismatch`** — proved at the storage layer; the journey offers no way to hand
  the store bytes disagreeing with their declared digest.
- **`ungrounded_model_item`** — unreachable by design; the stage drops unresolvable
  quotations before the grounding gate sees them. Owner-accepted 2026-09-11.

Both were true at `6d3c0f3`. **Neither is a fact you may inherit.** `stage.py` and
`provenance.py` both moved, and the second limit is a claim about exactly that code. Check
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

Instance `gate-w5`, `POSTGRES_PORT=55560`, `S3_API_PORT=59160`, `S3_CONSOLE_PORT=59161`,
`POSTGRES_DB=audit_w5`, bucket `auditmanager-gate-w5`. All three ports were confirmed free
on 2026-09-15.

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
4. Do not measure while another session runs against the same services; your ports are
   yours alone. `OPERATING_CONSTRAINTS.md` §9 is worth reading first — §6 covers residue,
   not accumulated population, and telling the two apart means running your suite alone
   against the same database.
5. **Do not create a tag, and do not push or merge to `main`.** Whether `main` advances to
   carry a new PC-01 acceptance is the owner's decision, informed by your report.
6. **Check every premise in this brief against the tree before building on it.** Two of the
   integrator's three wave-2 briefs carried stale premises, both taken from closure records
   rather than from the code — `W2_CLOSURE.md` §2. The table above was built from a diff,
   which is better, but it is still a claim. If something here is wrong, say so in the
   report; that is a useful finding, not an inconvenience.

## Report

`docs/program/reviews/W5-CERT.md`, and in it:

- Your `HEAD` on arrival, and whether it matched the base.
- Every command with its exit code.
- Each of the ten criteria: the evidence, and what would have made it fail.
- The two accepted limits, re-examined, with the verdict on each stated as your own.
- The live run: model, cost against the ceiling, seeded issues found, controls flagged —
  as absolute numbers, comparable to PC-01's 3 of 3 and 0 of 6.
- Every defect found, described precisely, **left unrepaired**, naming the tree that owns
  it.
- A plain verdict: does PC-01 still hold at `3412fb2`, hold with named exceptions, or not
  hold. If you cannot reach one, say what would let you.
- Elapsed wall-clock.
