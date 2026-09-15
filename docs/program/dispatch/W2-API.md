# `W2-API` dispatch prompt — the query surface the contract already promises

Base `8e0288ce5ee7bb5c1a019586856af06ffaa7f7db`. One session, parallel with `W2-RUN` and `W2-PROV`.

---

You are session `W2-API`. Repository: /root/projects/PDF-Analysis.

BASE COMMIT: `8e0288ce5ee7bb5c1a019586856af06ffaa7f7db` on `planning/prototype-roadmap`. Branch `agent/w2-api`.

## What you are for

`GATE_B2_CLOSURE.md` records it plainly: **no query surface accepts the `cursor`, `limit`,
`category` or `verdict` parameters the contract declares.** The contract promises them, the
generated client exposes them, nothing implements them, and a caller that supplies one gets
it silently ignored — which is worse than a refusal, because the caller believes it filtered.

`P4-BHV-01` will put experts in front of fourteen documents' findings. Paging and filtering
is the first thing a reviewer reaches for, and "it accepted my filter and ignored it" is the
kind of defect that discredits a whole session's labels.

## You own exactly these paths

- `contracts/api/v1/**`
- `src/auditmanager/api/**`
- `web/src/shared/api/generated/**` — regeneration only, from the contract you change
- `tests/integration/api/**`, and the frontend tests that cover the generated client

Nothing else. Not `db/migrations/**` — `W2-PROV` is the sole migration writer this wave.
Not `src/auditmanager/runs/**` — `W2-RUN` is in there. Not the query modules another
context owns: if a filter cannot be expressed through a module's public surface, **that is
a finding**, not a licence to reach into its internals or to write SQL in the router.

## The work

Implement the four declared parameters on the surfaces that declare them, or — where a
parameter turns out to be wrong for PC-01 — **remove it from the contract with a reason**.
Both are acceptable outcomes; silently declaring and ignoring is not. Say which you chose
per parameter and why.

Constraints:

- `cursor` must be opaque. `PROTOTYPE_PROFILE.md` foundation invariant 3: path, object key,
  filename and display ordinal are never identity. A cursor that encodes a row offset or a
  primary key in the clear is a leak; a cursor that is stable across an insert is a
  correctness claim you must test.
- `category` and `verdict` take their vocabularies from the frozen contract, not from new
  strings. `verdict` values come from the current-verdict projection; `category` from the
  analysis profile's two.
- The API README tables eight seam mismatches. Close the four that are yours and **leave the
  other four listed**, updated to say what is still true.
- Regenerating the client is part of the work, not a follow-up: `web/FRONTEND_LOCK.json` and
  the generated sources must agree with the contract you ship.

## Guards this session must show failing

At minimum: each implemented parameter actually filters or pages — a test that would pass
against a surface ignoring it is vacuous and will be treated as such; an unstable cursor is
caught; an out-of-vocabulary `category` or `verdict` is refused rather than returning
everything; the generated client and the contract cannot drift apart unnoticed.

Beware the shape that has caught nine tests here: asserting a property of the fixture. Four
projects created in one loop landed in the same millisecond and a descending-order test
stayed green against a reversed `ORDER BY`. If you assert an order, make the data
discriminate.

## Gate

- `.venv/bin/pytest tests/integration/api` exits `0`
- the full backend battery exits `0`; the frontend suite exits `0`
- `make foundation` exits `0`; `git diff --check` exits `0`

Instance: `FOUNDATION_INSTANCE=gate-w2api`, `POSTGRES_PORT=55520`, `S3_API_PORT=59120`,
`S3_CONSOLE_PORT=59121`, `POSTGRES_DB=audit_w2api`, `S3_BUCKET=audit-w2api`.
## Provisioning — verify, then report

Every session before you arrived on `43a84d9`, ~240 commits behind, because the harness
seeds an agent worktree from `origin/main` and `origin/main` had not moved since the W0.2
era. `origin/main` now carries the PC-01 acceptance commit, so this **should** no longer
fire. Check your `HEAD` against the base SHA anyway and **say in your report whether it
matched on arrival** — you are the first session that can confirm the fix.

## Environment

Bootstrap with `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`; bare `make bootstrap`
is correctly refused under an active virtualenv. Copy `.env.example` to `.env` and set
exactly your instance below; it is git-ignored and is never committed.

**Do not put your worktree under `/tmp`.** Docker is snap-confined here and cannot see it —
`make up` fails with `open /var/lib/snapd/void/...`. Use a path under `/root/`.

## Anti-vacuity — the central obligation

Nine tests in this programme have passed or failed without exercising what they named. The
shape was identical every time: the test asserted a property of the fixture rather than of
the code. **Every guard you write must be shown to fail.** Mutate the thing it protects,
confirm red, revert, confirm green, and report both. A mutation that produces a collection
error, an import error or a `DomainError` from unrelated machinery rather than a guard
failure proves nothing and must be redone.

Never edit a tracked file to mutate. Copy `src/` into a session-unique scratch directory
outside the worktree and run `pytest -o pythonpath=<copy>/src`, because `pyproject.toml`
sets `pythonpath = ["src"]` and overrides an exported `PYTHONPATH`. **Symlink `contracts/`,
`docs/` and `fixtures/` into that copy** — `analysis.text.lock` resolves
`docs/program/P02_LOCK.json` from `parents[4]` of its own module file, so a copy without
`docs/` fails before reaching any assertion. Prove the copy is the one imported by printing
`auditmanager.__file__` under the override before you trust any mutation result.

## Rules

1. **Commit after every meaningful step.** A dispatch here was once killed mid-run and lost
   four sessions because each held its work uncommitted.
2. **Never add a root dependency.** `docs/program/P02_LOCK.json` is the pinned set.
3. `tests/contract` and `tests/checkpoint` are CP-00 historical evidence, **red before you
   start** and quarantined by `PROTOTYPE_PROFILE.md` §6.3. Not your gate.
4. Stay inside your owned paths. If a module's public surface does not let you do the work,
   **that is a finding**, not a licence to reach inside another tree.
5. Do not measure while another session runs against the same services; your ports are
   yours alone.

## Report

Changed paths. Every command with its exit code. Per parameter: implemented or removed, and
why. Each guard mutated, red and green. The four seam mismatches you did not own, restated
as they now stand. Whether your `HEAD` matched the base on arrival. Elapsed wall-clock.
