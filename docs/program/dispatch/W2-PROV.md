# `W2-PROV` dispatch prompt — the provenance the ledger cannot currently record

Base `c509950c86abd39cb89d98ecdb312d8b47e5d7c2`. One session, parallel with `W2-RUN` and `W2-API`. **Sole migration writer this wave.**

---

You are session `W2-PROV`. Repository: /root/projects/PDF-Analysis.

BASE COMMIT: `c509950c86abd39cb89d98ecdb312d8b47e5d7c2` on `planning/prototype-roadmap`. Branch `agent/w2-prov`.

## What you are for

Two facts the measurement cannot express, both recorded and both left unrepaired.

**1. `model_call.status` admits only `succeeded|failed`; `B3`'s provenance emits a third
value, `truncated`.** `GATE_B2_CLOSURE.md` carries this. The executor maps the third value
onto `failed` for persistence and keeps the provider's own stop reason in `parameters` —
a deliberate lossless workaround, not a fix. The consequence lands in PC-02: the ledger
that report will cite files a truncated answer as a failure, and truncation is a different
product fact from the provider being unreachable or the model answering badly.

**2. Nothing records how much the model actually said.** `P4_CLOSURE.md` §6: "`PC02-C01`
and `PC02-C07` returned after 10 output tokens; `PC02-C09` reasoned for 530 and still
published nothing. If a later checkpoint wants to know whether a clean document was
actually *read*, output-token count is a cheap proxy worth recording beside the finding
count." Precision evidence is already **saturated** on this corpus — zero findings across
nine controls — so the next question is not "how many findings" but "was the document
read at all", and nothing in the tree can answer it.

## You own exactly these paths

- `db/migrations/**` — **you are the sole migration writer this wave**; no other session
  may touch the head
- `src/auditmanager/analysis/text/provenance.py` and the stage-metric emission beside it
- `src/auditmanager/runs/executor.py` **only** where it persists `model_call` rows
- `tools/validation/ledger_report.py`
- `tests/integration/analysis_text/**`, `tests/integration/runs/**` only for tests you add

`W2-RUN` owns the rest of `src/auditmanager/runs/**` and is working in parallel. Touch the
persistence of `model_call` and nothing else there; if you need more, that is a finding and
a conversation with the integrator, not an edit.

## The work

- Widen `model_call.status` to admit `truncated` as a first-class value, through a
  migration, and stop the executor mapping it onto `failed`. The existing rows are real
  evidence: say in your handoff what happens to them and why that is safe.
- Record the provider's output-token count where the ledger can read it, beside the finding
  count, per call and rolled up per run.
- Teach `ledger_report.py` to report both, and to keep reporting correctly on rows written
  before your migration.

Two things that are **not** yours, and saying so is part of the job:

- The **21st error code**. `GATE_B1_CLOSURE.md` §4 item 6 is open: the catalog has no code
  for "usable output over a strict subset of the input", `B3` borrowed
  `partial_result_not_publishable`, and adding a member to a frozen twenty-member enum
  propagates to `shared/errors`, the API schema, the generated client and every consumer.
  **That is an owner decision.** `truncated` as a *call status* is not the same object as an
  *error code*; if your work starts to need the 21st code, stop and report that it does.
- Re-certifying PC-01. The PC-01 record is bound to `6d3c0f3`; this wave does not amend it.

## Guards this session must show failing

At minimum: a truncated call persists as `truncated` and not as `failed`; the ledger
distinguishes the three statuses; the output-token count is the provider's figure and not a
recomputation; a row written before the migration still reports correctly.

## Gate

- `.venv/bin/pytest tests/integration/analysis_text tests/integration/runs` exits `0`
- `.venv/bin/python tools/validation/ledger_report.py --self-check` exits `0`
- the full backend battery exits `0`
- `make migrate` from an empty database, then again, both exit `0`
- `make foundation` exits `0`; `git diff --check` exits `0`

Instance: `FOUNDATION_INSTANCE=gate-w2prov`, `POSTGRES_PORT=55510`, `S3_API_PORT=59110`,
`S3_CONSOLE_PORT=59111`, `POSTGRES_DB=audit_w2prov`, `S3_BUCKET=audit-w2prov`.
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

Changed paths and the new migration head. Every command with its exit code. Each guard
mutated, red and green. What happens to `model_call` rows written before the migration.
Whether anything you did pushed toward the 21st code. Whether your `HEAD` matched the base
on arrival. Elapsed wall-clock.
