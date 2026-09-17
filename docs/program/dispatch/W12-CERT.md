# `W12-CERT` dispatch prompt — re-certify PC-01 after waves 11 and 12

**Stage A has landed.** Base `2be71b9` on `planning/prototype-roadmap`, published as
`origin/dev`. Gate there: **1505 passed / 5 skipped / 167 subtests**, frontend **440 passed**,
foundation 35, `GATE OK`.

Three stage-A streams merged: one changed `src/` (`W12-RCN`, reconciliation) and two wrote
tests only (`W12-WEB` on the frontend, `W12-DEC` on the decision ledger). Read all three
reviews in `docs/program/reviews/` before you read their code.

---

You are session `W12-CERT`. Repository: /root/projects/PDF-Analysis.
Branch `agent/w12-cert`, worktree `/root/w12cert`.

## What you are for

PC-01 was re-certified at `beaa7f7` by `W5-CERT` and again at `c0d7daf` by `W6-CERT`.
**`src/` has since moved and `W6-CERT`'s certification no longer describes this tree.**

Certify the checkpoint, not the diff: **all ten criteria of `PROTOTYPE_PROFILE.md` §8, each
shown able to fail.** The diff is small; the temptation to certify only what moved is the
thing to resist, and the last two passes earned their value by re-establishing limits they
could have inherited.

**You authored none of it and you may repair none of it.** The integrator led wave 11's
governance stream and merged every branch in both waves, and therefore cannot certify them.

## You own exactly these paths

- `artifacts/checkpoints/PC-01/**` — write the new record **beside** `report.json`,
  `recertification-beaa7f7.json` and `recertification-c0d7daf.json`; touch none of them
- the PC-01 rows of `docs/program/CHECKPOINT_REGISTRY.md`
- `docs/manual-tests/PC-01_prototype.md`
- `docs/program/reviews/W12-CERT.md`

Nothing under `src/`, `db/`, `tests/`, `contracts/` or `web/`.

## What moved, and what did not

From `git diff c0d7daf..<base> -- src/ db/`. **A map for your attention, not a list of what
to test** — and a claim to check, not a given.

| File | Carries |
|---|---|
| `exports/service.py` | `CsvExport.filename` and `_FILENAME_TEMPLATE` removed. **A public attribute on an exported class — the one source-compatible break.** Criterion 7 |
| `ingest/service.py` | `read_source_bytes` hashes returned bytes against the manifest digest. Criteria 3, 10 |
| `storage/s3.py` | `read(verify=True)` refuses an object with no recorded digest. Criteria 3, 10 |
| `analysis/text/stage.py` | `cost_basis` added to the success path's metrics. Criterion 4 |
| `ingest/reconciliation.py` | `verify_version` now **hashes the bytes** and compares them to the manifest digest, after a cheaper declaration check that runs first; an object recording no digest is refused as `validation_failed` before either. `W12-RCN` measured the cost on live MinIO: 2.08 → 4.11 ms on the AR baseline, 2.23 → 50.10 ms on a 25 MiB object. **Nothing in `src/` calls this method**, so no in-tree path pays that cost today. Criteria 3, 10 |
| `shared/errors/envelope.py` | docstring only; six shapes named |
| `multipart.py`, `projects.py`, `executor.py` | comments only, zero code lines |

## The two accepted limits — re-establish, never inherit

`checksum_mismatch` not inducible through the twelve operations, and `ungrounded_model_item`
unreachable by design. Both held at `c0d7daf`.

**`checksum_mismatch` is the one to look hardest at.** Waves 11 and 12 changed precisely the
code that decides when bytes and their declarations disagree. `W11-RD` reported it found no
way to induce either of its new faults through the twelve operations — **that is an
observation by the session that wrote the code, not a certification, and it said so.** It is
yours to establish.

## One instruction the earlier certifications did not carry

**A passing test is not evidence the behaviour is right.** Wave 6 found `W2-QA` had pinned a
*defective* value as its expected value. Wave 10 found 157 rules that could not be told from
a deleted rule. Wave 11 found the gate had not been running 212 contract tests that existed
all along — so a rule can be covered, findable by grep, and still unguarded by the gate.

Where a criterion rests on a test, read what the test asserts and decide for yourself whether
the contract requires it. Where it rests on a number, ask where the number came from.

## Provisioning

```
cd /root/projects/PDF-Analysis && git fetch origin
git worktree add /root/w12cert -b agent/w12-cert origin/dev
cd /root/w12cert && git log --oneline -1
```

Base `<the wave-12 stage A convergence commit>` or later. **Not under `/tmp`** — docker is snap-confined and cannot see it.
Report what your `HEAD` was on arrival.

**Commit as you go.** Wave 10's first attempt lost four sessions to a restart and only
committed work survived. Open `docs/program/reviews/W12-CERT.md` before your first edit.

**Use a session-unique scratch directory for logs** (`/root/w12cert-logs/`). The five wave-10
streams shared one; one of them read another lane's gate failures as its own.

## The method

```
make mutation-copy MUT=/root/w12cert-mut
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

Expect **1505 passed / 5 skipped / 167 subtests** and frontend **440 passed**. The frontend rose from 289 in stage A: `W12-WEB` added 151 tests and found that **18% of `web/src` — 34 of 110 modules — is reached by no test at all**, including the only place `terminal_reason` is rendered. That is reported, not repaired, and it is not yours to repair either. That count rose by 212 in wave 11 without
a single new test: `PROTOTYPE_PROFILE.md` §6.3's quarantine had been implemented as a
directory exclusion and was narrowed to the three CP-00 files it actually means. A linked
worktree has no `web/node_modules`; run `npm --prefix web ci` once.

## Environment

Instance `gate-w12b`, `POSTGRES_PORT=55660`, `S3_API_PORT=59260`, `S3_CONSOLE_PORT=59261`,
`POSTGRES_DB=audit_w12b`, bucket `auditmanager-gate-w12b`. Bootstrap with
`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`; copy `.env.example` to `.env` and set
exactly your instance.

## The provider path

Criterion 4 needs a model to answer. **The mode is `proxy`, not `live`** (`OD-02` revised
2026-09-14). Credentials are on disk in `.env.provider`; `_provider_file` locates it through
`git rev-parse --git-common-dir`, and you must never print one. Follow
`docs/manual-tests/PC-01_prototype.md`, **not** `LIVE_RUN_INSTRUCTIONS.md`, which is
superseded. Check the wiring before spending: `PYTHONPATH=src .venv/bin/python -m
auditmanager.api.app` prints `wired, provider_mode=proxy` and `operations=12` and makes no
call. A run costs about **$0.038** against the USD 1.00 `OD-03` ceiling.

## Report

`docs/program/reviews/W12-CERT.md`: `HEAD` on arrival; every command with its exit code; each
of the ten criteria with its evidence and **what would have made it fail**; both accepted
limits re-examined with your own verdict; the live run as absolute numbers comparable to
3 of 3 seeded and 0 of 6 controls; every defect found and **left unrepaired**; anything false
in this brief; a plain verdict — holds, holds with named exceptions, or does not hold; elapsed
wall-clock.

**No tag. Do not push or merge to `main`.** Whether `main` advances is the owner's decision,
and `DEBT_REGISTER.md` §3 records that it is waiting on exactly this certification.
