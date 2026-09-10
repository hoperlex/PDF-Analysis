# Gate A — closure and the first measured throughput

> **Status: the Python foundation is accepted. `A5` (web toolchain and generated client)
> is in flight.** Accepted on `planning/prototype-roadmap` at the merge of `agent/gate-a6-qa`.

## 1. What was accepted

Six sessions, five landed. Every one stayed inside its ownership block — verified for each
by `git diff --name-only <base> <branch>` filtered against its allowed paths, not by the
lane's own claim.

| Session | Owns | Commits |
|---|---|---:|
| `A1` seams | `db/migrations`, `shared/{db,identity}`, `contracts/api/v1`, `P02_SEAMS.md` | 8 |
| `A2` services | `infra/local` | 3 |
| `A3` storage | `src/auditmanager/storage` | 6 |
| `A4` corpus | `fixtures/synthetic/ar`, `tools/fixtures` | 10 |
| `A6-QA` convergence | `tests/integration/foundation` | 7 |
| `A5` web | `web/**` shell, shared and generated client | in flight |

## 2. The closing checks, run by the integrator

On the dedicated `gate-a-conv` instance (PG `55440`, S3 `59040`/`59041`, db `audit_conv`,
bucket `audit-conv`), which no authoring session used. `A6-QA` authored against its own
`gate-a-qa` instance and its suite was run here afterwards, not by its author.

| Check | Result |
|---|---|
| `make bootstrap` ×2, tracked state compared between runs | `0`, `0`, unchanged |
| `make foundation` from clean state | `0` — 35 foundation tests in 28.8 s |
| `make down`, `up`, `check-services`, `check-db`, `check-storage` | `0`, `0`, `0`, `0`, `0` |
| `scripts/validate_bootstrap.py` | `0`, `PASS` |
| `git diff --check` | `0` |
| success sentinels observed across the run | 6 |

Substantive criteria, checked as evidence rather than as exit codes:

- **Privacy** — anonymous list, read and write each `403 AccessDenied` over bare HTTP,
  read attempted against a key that existed, write confirmed to have created nothing.
- **Publication integrity** — `corrupt upload: refused, nothing canonical`.
- **The corpus oracle** — 12 of 12 quotations, 5 seeded and 7 control, found at their
  declared page by `pdftotext`, which shares no code with the extractor `A4` wrote, so a
  matching writer/reader bug cannot cancel out. Command and tree recorded in §5.
- **Seams** — `contracts/api/v1/openapi.json` is OpenAPI 3.1.0, 10 paths, 43 schemas;
  `docs/program/P02_SEAMS.md` frozen at `9924d32`.

## 3. Two defects only convergence could find

Both in the frozen `Makefile`, both integrator-owned, neither an FF-01 freeze-break: the
nine target names and their invocations are unchanged.

1. **Three of nine targets could not run** (`e0ba71f`). `check-services`, `check-db` and
   `check-storage` passed `scrubbed_run …` as argv to `run_checked`, which already wraps
   argv in `scrubbed_run`; the inner `exec` cannot run a shell function, so all three
   exited 127 before reaching a checker. Found independently by `A2` and `A3`. The repair
   also rejects a non-assignment before `--` instead of exporting it as a bare variable
   name — that permissiveness is why the defect read as a provider problem for a full
   session cycle.
2. **`make bootstrap` could not run on this checkout** (`68dd437`). uv refuses a project
   environment directory that exists without an interpreter. FF-01 §3 nests
   `.venv/bootstrap` inside `.venv`, and the governance environment has existed since W0,
   so `.venv` held only `bootstrap/`. **A fresh clone never shows this**, which is exactly
   why all four lanes passed and only convergence hit it — and why every developer
   carrying a W0-era governance environment has the same break.

A third correction was to this plan, not to the code: `P1-QA-00` was listed as subsumed by
Gate A but no brief was written for it, so `make test-foundation` failed closed with no
owner. `A6-QA` was dispatched to fill it, deliberately not written by the integrator who
had merged the four lanes it certifies.

## 4. Guards proven able to fail

Twenty-one demonstrations across two sessions, each mutating the thing a guard protects and
reverting it. `A3` ran four; `A6-QA` ran seventeen, as throwaway pytest plugins outside the
repository so the lanes it certifies stayed byte-identical.

Two sessions independently discovered the same trap by different methods: **MinIO records
`LastModified` to one-second resolution**, so a timestamp comparison certifies a store that
rewrites bytes on every republication. `A3` found it when a mutation exposed a passing
immutability test and replaced the assertion with an out-of-band witness; `A6-QA` found it
by counting `copy_object` calls and watching both `LastModified` and `ETag` agree while the
copy had run twice. Agreement from two methods is why this is recorded as a fact rather
than as one lane's opinion.

## 5. Measured throughput — the figure that did not exist

**Method.** Per-session wall-clock is the orchestration runtime for each dispatched
session, measured from dispatch to completion. Rounds-to-accept counts how many times a
session's result was returned to it for remediation. The tree is
`planning/prototype-roadmap` at the `agent/gate-a6-qa` merge. The corpus check is
`pdftotext -f N -l N fixtures/synthetic/ar/ar_baseline.pdf -` per declared page, compared
against `fixtures/synthetic/ar/expected_issues.json` on whitespace-normalised text.

| Session | Wall-clock | Tool calls | Rounds to accept |
|---|---:|---:|---:|
| `A1` seams | 56.0 min | 181 | **0** |
| `A2` services | 18.9 min | 72 | **0** |
| `A3` storage | 24.8 min | 111 | **0** |
| `A4` corpus | 39.5 min | 117 | **0** |
| `A6-QA` convergence | 48.2 min | 186 | **0** |

**Rounds-to-accept is zero across five implementation sessions.** That is the number the
programme had never measured and on which the whole forecast rested. `PROTOTYPE_WAVE_PLAN.md`
§8 assumed one to two rounds per gate, extrapolated from authoring times alone;
`PROTOTYPE_EXECUTION_PLAN.md` §4 priced a review slot per acceptance; the W0 record was
three to twelve rounds per task.

**Zero rounds does not mean zero rework.** No session was sent back, but the integrator
made three repairs the sessions could not: two `Makefile` defects and one gap in this plan.
The honest reading is that rework moved from the session loop into the integration slot,
where it is cheaper, because the gates are executable. A prose gate cannot tell an
integrator that `exec` will not run a shell function; `exit 127` can.

**Elapsed for Gate A: about 2.5 hours.** Four authoring sessions in parallel bounded by
`A1` at 56 minutes, then integrator merges and the first `Makefile` repair, then `A6-QA`
serially at 48 minutes, then the merge and the closing run above. Against
`PROTOTYPE_WAVE_PLAN.md` §8's estimate of **1–2 days**.

## 6. What this does and does not license

It licenses replacing the Gate A row with measurement. It does **not** license scaling the
same ratio onto Gates B and C, for four reasons that are differences in kind, not degree:

1. Gate A's sessions were largely independent. Gate B's eight all consume `A1`'s seams and
   each other's shapes, so convergence risk is qualitatively higher.
2. Gate A called no model provider. Gate B carries `text_analysis`, a live API, a cost
   ceiling and nondeterminism.
3. Gate B doubles the session count converging on one integrator — the plan's own risk 3.
4. Gate B's frontend sessions work in a stack Gate A only bootstrapped, and `A5` has not
   yet reported.

The next measurement that matters is Gate B's convergence, not its authoring.
