# `W2-QA` dispatch prompt — convergence QA for wave 2

Base `4182b440308dcd7e54b83523badde89c787be3e7` — the convergence commit, all three wave-2 sessions merged and the full gate green: 754 passed / 5 skipped / 116 subtests, `make foundation` 35 passed, frontend 289 passed, `git diff --check` clean.
The integrator fills the SHA in at dispatch and must not leave a placeholder here.

---

You are session `W2-QA`. Repository: /root/projects/PDF-Analysis.

BASE COMMIT: `4182b440308dcd7e54b83523badde89c787be3e7` on `planning/prototype-roadmap`.
Branch `agent/w2-qa`.

## What you are for

Three sessions changed three disjoint path sets in parallel, each verified its own segment,
each passed. **Nobody has proved they compose.** That is the whole reason you exist, and it
is the role that found the two blockers in this programme's last convergence pass: a
manifest role that made the real upload path unrunnable, and a `provider_mode` a caller
could simply declare.

You authored none of it and you may repair none of it. A defect goes back as a precise
report naming the tree that owns it.

## You own exactly these paths

- `tests/e2e/p02/**`
- `tests/integration/p02_journey/**`

These already exist and carry the previous convergence pass. Extend them; do not rewrite
what is there without saying why.

## What to attack

1. **The retry and the ledger together.** `W2-RUN` retries `dependency_unavailable`;
   `W2-PROV` changed what `model_call` can record. Does a retried run's provenance still let
   a reader count attempts and tell a first-try success from a third-try one? Does the
   `OD-03` ceiling still bind across attempts once both changes are in?
2. **`truncated` end to end.** It must survive from the provider's stop reason, through
   persistence, into the ledger, and — if it is visible at all — into the API and the CSV
   without being flattened back to `failed`.
3. **The query surface against the real corpus.** Page and filter over a run with real
   findings, not a fixture of three rows. Assert that a cursor is stable across an insert
   and that a filter actually narrows. A test that passes against a surface ignoring the
   parameter is vacuous.
4. **Everything the last pass pinned is still true.** The journey figures, the grounding
   gate, idempotency across all sixteen tables, the extractor-divergence anchors. If a wave-2
   change moved one of them, that is the finding.

## Gate

- `.venv/bin/pytest tests/e2e/p02` and `tests/integration/p02_journey` each exit `0`
- the full backend battery and the frontend suite exit `0`
- `make foundation` exits `0`; `git diff --check` exits `0`
- report the journey figures again, measured, not quoted

Instance: `FOUNDATION_INSTANCE=gate-w2qa`, `POSTGRES_PORT=55530`, `S3_API_PORT=59130`,
`S3_CONSOLE_PORT=59131`, `POSTGRES_DB=audit_w2qa`, `S3_BUCKET=audit-w2qa`.
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

Changed paths. Every command with its exit code. The journey figures, reproduced
independently. Each guard mutated, red and green. Every defect found, described precisely,
**left unrepaired**, naming the tree that owns it. Whether your `HEAD` matched the base on
arrival. Elapsed wall-clock.
