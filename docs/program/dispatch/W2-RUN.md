# `W2-RUN` dispatch prompt — a retry policy where it belongs

Base `8e0288ce5ee7bb5c1a019586856af06ffaa7f7db`. One session, parallel with `W2-PROV` and `W2-API`. Dispatch text below, verbatim.

---

You are session `W2-RUN`. Repository: /root/projects/PDF-Analysis.

BASE COMMIT: `8e0288ce5ee7bb5c1a019586856af06ffaa7f7db` on `planning/prototype-roadmap`. Branch `agent/w2-run`.

## What you are for

`P4-RUN-01` ran the PC-02 corpus live and lost three of seventeen attempts to
`dependency_unavailable` at roughly 133 seconds each — an 18% attempt-failure rate. It
retried by hand inside its own harness, and `P4_CLOSURE.md` §1 accepted that retry on the
grounds that the failure is **transport, not judgement**: the provider was unreachable, the
model never answered, so no model output is being discarded and a retry cannot launder a
bad answer into a good one.

`P4_CLOSURE.md` §6 then records what must not happen next: "A retry policy for
`dependency_unavailable` belongs in the run executor, not in each caller… Ruling 1 accepts a
retry performed by hand; that is not a licence for every caller to invent its own."

Build it in the executor. `P4-BHV-01` will put experts in front of this stack, and a
133-second silent failure in front of a paid expert is the worst possible place to discover
that every caller rolls its own.

## You own exactly these paths

- `src/auditmanager/runs/**`
- `tests/integration/runs/**`

Nothing else. Not `db/migrations/**` — `W2-PROV` is the sole migration writer this wave.
Not `contracts/**`, not `web/**`, not the `Makefile`, not root locks.

## The work

A bounded, in-process retry for **`dependency_unavailable` only**, inside `execute_run`.

Constraints that are not yours to relax, each already recorded:

- PC-01 has **no Job, no Attempt, no lease, no execution token and no outbox**
  (`PROTOTYPE_EXECUTION_PLAN.md` §1). This is one process retrying one call, not durable
  execution. If your design needs any of those, stop and report it.
- Retry **only** `dependency_unavailable`. `analysis_failed` is the model answering badly
  and must never be retried. Make that distinction structural, not a comment.
- The run's idempotency key must not change. `P4-RUN-01`'s harness suffixed the *run*
  command key per attempt; inside the executor there is no second command to key.
- Every attempt must stay visible. `P4_CLOSURE.md` §1 cites "three attempt records are
  committed and the ledger carries `model_call_rows: 0` for each" as the reason the
  alternative headline stays computable. Whatever you record, a later reader must still be
  able to count attempts and distinguish a first-try success from a third-try success.
- The attempt budget and the backoff are **pins, not literals scattered in code**. Put them
  where `P02_LOCK.json`-style facts live for `runs`, and say in your handoff where.
- `OD-03`'s USD 1.00 per-run ceiling is enforced by `B3`'s guard. Retries spend real money;
  show that the ceiling still binds across attempts, not per attempt.

## Guards this session must show failing

At minimum: a retry happens on `dependency_unavailable`; a retry does **not** happen on
`analysis_failed`; the budget is finite and the run reaches an explicit terminal when it is
exhausted; the cost ceiling binds across attempts; attempt provenance survives.

## Gate

- `.venv/bin/pytest tests/integration/runs` exits `0`
- the full backend battery exits `0` — one command, order-independent
- `make foundation` exits `0`
- `git diff --check` exits `0`

Instance: `FOUNDATION_INSTANCE=gate-w2run`, `POSTGRES_PORT=55500`, `S3_API_PORT=59100`,
`S3_CONSOLE_PORT=59101`, `POSTGRES_DB=audit_w2run`, `S3_BUCKET=audit-w2run`.

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

Changed paths. Every command with its exit code. Each guard mutated, what went red, what
went green on revert. Where you put the attempt budget and backoff, and why there. What a
later reader must do to recompute the 12/14-vs-14/14 headline. Whether your `HEAD` matched
the base on arrival. Your elapsed wall-clock from start to last commit.
