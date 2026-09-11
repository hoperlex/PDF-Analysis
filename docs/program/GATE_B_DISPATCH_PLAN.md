# Gate B and C — the dispatch series

> **Status: ready to dispatch `B-0` on the owner's rulings.** Base: `planning/prototype-roadmap`
> at the Gate A closure. Structure: `PROTOTYPE_WAVE_PLAN.md` §4–§5. Specification content: the
> `P2-*` and `P3-*` task files. Measured Gate A throughput: `GATE_A_CLOSURE.md` §5.

## 1. What is already frozen, and what still gates dispatch

Gate A left every seam a Gate B session consumes already frozen and verified:
the PC-01 schema as one migration head, `docs/program/P02_SEAMS.md`,
`contracts/api/v1/openapi.json` (10 paths, 43 schemas, repaired and re-verified), the
BlobStore port, the local service stack, the AR corpus with its expected-issues manifest,
the web toolchain with a deterministically generated typed client, and a cross-provider
foundation suite whose seventeen guards were each shown red under mutation.

`A1` also closed six owner decisions inside the seam register by taking the defaults the
execution plan had recorded — `OD-04` crop policy, `OD-10` interrupted-run vocabulary,
`OD-11` the CSV contract in full, `OD-12` `author_label` as a column, `OD-14`, and `OD-24`.
`OD-12` is the one worth noticing: deciding it later would have been a schema change.

**Five decisions remain open, and four of them block a named session.** Each has a default
recorded in `PROTOTYPE_EXECUTION_PLAN.md` §7; the owner may accept the defaults in one
sitting or rule otherwise, but the series cannot start on silence.

| Decision | Question | Blocks | Recorded default |
|---|---|---|---|
| `OD-01` | PDF text-extraction library | `B-0` pin, then `B2` | a permissively licensed extractor giving per-character boxes |
| `OD-02` | model provider and model id | `B-0` pin, then `B3` | Anthropic first-party API, `claude-opus-5` |
| `OD-03` | live-run cost ceiling, payer, halt behaviour | `B3` | a per-run ceiling raising `cost_budget_exceeded` |
| `OD-05` | language of finding and recommendation prose | `B3` | Russian prose, machine fields and identities ASCII |
| `OD-13` | is a live provider call part of automated acceptance | `C3` | automated suites recorded-only; the live run is manual |

`OD-01` and `OD-02` are not merely preferences: both add a root dependency, and the root
lock is a single-writer hotspot. That is why `B-0` exists as its own serial step.

## 2. The series

```text
B-0   pins and env          1 session,  serial     ← root lock is single-writer
  |
B-I   the six independents  6 sessions, parallel   ← consume only frozen seams
  |
B-II  the two wirers        2 sessions, parallel   ← consume B-I's real interfaces
  |
B-III journey convergence   1 session,  serial     ← independent QA, authored by none of them
  |
C     composition, e2e,     3 sessions             ← C1 integrator-only, then C2 ‖ C3
      acceptance
```

Sub-waves are not ceremony. `B-I`'s six touch no tree another writes and need nothing from
each other. `B-II`'s two wire `B-I`'s modules together and want their real ports, not their
declared shapes. Splitting them also keeps peak convergence at six rather than eight, which
is the plan's own risk 3 — every session lands on one integrator.

## 3. `B-0` — P02 pins and the additive environment contract

Serial. Nothing else runs while it holds the lock.

| Owns | Delivers |
|---|---|
| root `pyproject.toml`, `uv.lock`, `.env.example` (additive only), `docs/program/P02_LOCK.json` | the PDF extractor pinned per `OD-01`; the provider SDK pinned per `OD-02`; new `.env` names for provider credentials, cost ceiling and provider mode; `P02_LOCK.json` recording pins, paths and invocations |

Forbidden: the `Makefile` and its nine frozen targets, every provider tree, `contracts/**`.
Gate: `make bootstrap` twice, exit `0` and no tracked change on the second; `make foundation`
still exit `0` on the widened lock; `git diff --check` exit `0`.

## 4. `B-I` — six in parallel

Dispatched together from the `B-0` merge. Paths verified disjoint: no session writes a tree
another writes, and none writes a Gate A seam.

| Session | Owns | Delivers | Live services |
|---|---|---|---|
| `B1` ingest | `documents/**`, `ingest/**`, and `storage/**` for the blob-metadata repository only | single-PDF upload, immutable DocumentVersion and input manifest, blob metadata, DB/S3 reconciliation, explicit envelope rejection using `A4`'s negative fixtures | PG + MinIO |
| `B2` stages | `analysis/{engine,ports,stages}/**` | the stage runner and the three deterministic stages: page inventory and text layer with stable character offsets, block index with page/bbox/span anchors, document graph; fail-closed status mapping | PG + MinIO |
| `B3` text AI | `analysis/text/**`, `fixtures/recorded/text_analysis/**` | the AR prompt and profile — internal contradictions and literal placeholders only, never external norms; live adapter; recorded adapter; provenance; the `OD-03` ceiling | provider (live, once) |
| `B4` findings | `findings/**`, `decisions/**` | **the grounding gate** — a published quotation must resolve at its declared anchor or the item is diagnostic only; fresh `finding_uid` allocation; the append-only decision ledger and its verdict projection | PG |
| `B7` web project | `_pages/{projects,run}/**`, `widgets/{project-list,upload-panel}/**`, `features/{create-project,upload-document}/**`, `entities/{project,document-version}/**` | project list and create, upload, run progress by polling, the five explicit states, live-vs-recorded visible | none |
| `B8` web review | `_pages/review/**`, `widgets/{finding-list,evidence-viewer,decision-panel,decision-history,export-panel}/**`, `features/{open-evidence,record-verdict,append-comment,export-run}/**`, `entities/{finding,finding-observation,expert-decision}/**` | finding list, PDF page opened from a finding with its exact quotation beside it, accept/reject with comment and visible history, CSV download | none |

`B4` is the session to read most carefully at convergence. The grounding gate is what makes
PC-01 an audit tool rather than a demo: it is the difference between a finding and a
plausible sentence. `A4`'s manifest is its fixture, and the integrator has already verified
all twelve quotations resolve with an independent extractor.

## 5. `B-II` — the two wirers

| Session | Owns | Delivers |
|---|---|---|
| `B5` run and export | `runs/**`, `exports/**` | one local executor with persisted run and stage state, idempotency keys, stale-`running` reconciliation per `OD-10`, and the UTF-8 CSV bound to the exact project, version and run per the `OD-11` contract already frozen in `P02_SEAMS.md` §6 |
| `B6` API | `api/routers/**`, `api/schemas/**` | the endpoints the frozen OpenAPI already declares — 10 paths, 12 operations. The contract is read-only; a defect in it is reported, not repaired |

## 6. `B-III` — journey convergence

One session, owning `tests/e2e/p02/**` and `tests/integration/p02_journey/**` only. It
authored none of the modules it certifies and may not repair them: a defect goes back as a
report. It proves the backend journey end to end against real services on the recorded
adapter — upload, four stages, grounded findings, decisions, CSV — plus restart and
duplicate-request idempotency, and it must fail if a recorded run is presented as live.

## 7. Gate C

| Session | Owns | Notes |
|---|---|---|
| `C1` composition | `bootstrap/**`, `api/app.py`, `api/composition.py` | **integrator only.** Every accepted module constructed from configuration; a missing dependency fails at construction, not at first use |
| `C2` e2e | `tests/e2e/pc01/**` | the ten `PROTOTYPE_PROFILE.md` §8 criteria as executable tests on the recorded adapter |
| `C3` acceptance | `docs/manual-tests/PC-01_prototype.md`, `artifacts/checkpoints/PC-01/**`, the PC-01 registry rows | the clean-clone runbook and **the live-provider run**: at least two seeded issues found, every published quotation verified present on its declared page |

`C2` and `C3` run in parallel after `C1`. PC-01 passes when a reviewer who authored none of
the slices completes the runbook from a clean clone on a dedicated instance.

## 8. The dispatch template, corrected by Gate A

Every brief carries these. Each earned its place:

1. **The literal base SHA, never a branch name.** One Gate A worktree arrived checked out at
   a W0.2-era commit; the session noticed, verified the briefed base, and branched correctly.
   A session that trusts its worktree builds on the wrong tree.
2. **Commit after every meaningful step.** The first Gate A dispatch was killed by a session
   restart and lost all four sessions entirely, because each held its work uncommitted.
3. **Unique `FOUNDATION_INSTANCE`, ports, database and bucket.** Acceptance runs serially on
   a dedicated instance no authoring session used.
4. **Report defects, never repair outside your tree.** This is what made the `FindingDetail`
   repair trustworthy: three different hands found, fixed and verified it.
5. **Prove each guard can fire.** Mutate what it protects, confirm red, revert, report both.
   Gate A produced twenty-one such demonstrations and two of them found tests that passed
   against broken code.
6. **Never add a root dependency.** If you need one, stop and report it. `A4` wrote a PDF
   writer, a font subsetter and an extractor from the specs rather than take the lock.
7. **The historical suites are not your gate.** `tests/contract` and `tests/checkpoint` are
   CP-00 evidence and are red before you start.
8. **Report elapsed wall-clock from start to last commit.** This is how the forecast stops
   being an extrapolation.
9. **Keep your worktree and your scratch tree out of `/tmp`.** Docker here is a snap package
   and cannot see it; `B-III` lost its first pass to a `make up` failure naming
   `/var/lib/snapd/void/...`, which reads like a broken compose file and is not one.
   `/root/<something>-scratch` works.
10. **A mutation is not evidence until you have proved the mutated copy was imported.** This
    is rule 5's trap: `pyproject.toml` pins `pythonpath = ["src"]` and overrides an exported
    `PYTHONPATH`, so pytest loads the original tree and reports green while the guard looks
    dead. Run `pytest -o pythonpath=<copy>/src`, print the loaded module's `__file__` first,
    symlink `contracts/` and `docs/` beside the copied `src/` or it will not import at all,
    and name the scratch tree for your session. `B6` and the integrator each believed an
    unproven run, the integrator twice; `B1` and `B8` each had a shared-name scratch tree
    overwritten mid-run by a peer.
11. **Run only your own integration suite.** They share one database and some assert global
    state, so a cross-suite failure is a known open item and not a defect to report.

The exact commands behind 9–11, and two setup constraints every session meets before it
writes anything, are in `dispatch/OPERATING_CONSTRAINTS.md`. Link it from every brief.

## 9. Forecast, and what it rests on

Measured, from `GATE_A_CLOSURE.md` §5: seven sessions, **zero returned**, 16–56 minutes each,
Gate A elapsed about four hours against a planned one to two days.

| Wave | Sessions | Bound by | Estimate |
|---|---:|---|---|
| `B-0` | 1 | one serial session plus merge | 0.5 h |
| `B-I` | 6 | the longest of six, plus convergence | 1.5–2 h |
| `B-II` | 2 | the longer of two, plus convergence | 1–1.5 h |
| `B-III` | 1 | one session plus remediation of what it finds | 1–1.5 h |
| Gate C | 3 | `C1` serial, then `C2` ‖ `C3`, then the live runbook | 1.5–2 h |
| **to PC-01** | 13 | | **5.5–7.5 h** |

**This is not Gate A's ratio applied to more sessions, and it must not be read as one.**
Four differences of kind, restated from the closure so nobody drops them:

1. Gate A's sessions were nearly independent. `B-II` consumes `B-I`'s real interfaces, and
   `B-III` consumes everything. Convergence, not authoring, is where this gate can go wrong.
2. Gate A called no model. `B3` carries a live API, a cost ceiling, and output that differs
   between runs on the same input.
3. Peak parallelism rises from four to six on one integrator.
4. Gate A only bootstrapped the frontend. `B7` and `B8` are the first sessions to build a
   product screen in it.

The row that will move first is `B-III`, because it is the first to judge whether six
independently authored modules actually compose. If Gate B costs materially more than this,
the cause will be there and not in authoring — and that is the measurement worth taking.
