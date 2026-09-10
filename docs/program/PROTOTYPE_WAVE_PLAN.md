# Prototype wave plan — three gates to PC-01

> **Status: proposal, 2026-09-10.** This replaces the *dispatch graph* of
> `PROTOTYPE_EXECUTION_PLAN.md` §2 (19 serial acceptances) with three gates. It does not
> replace the 29 task files: their `Deliverables`, `Required tests` and
> `Failure/idempotency/security cases` sections remain the specification content each
> session is briefed from. Nothing in `PROTOTYPE_FOUNDATION_FREEZE.md` (FF-01) changes.

## 1. Why the graph collapses

Every dependency block in the P02/P03 task files reads *"not dispatchable until each is
**accepted and integrated**"*. That is a dependency on a review queue, not on code. What
each task physically needs from its predecessor is a **frozen shape**:

| Task | Stated dependency | Physically needs |
|---|---|---|
| `P2-ENG-01` | `P2-DOM-01` accepted | migration head and identifier types |
| `P2-AI-01` | `P2-ENG-01` accepted | the text-layer artifact shape |
| `P2-FND-01` | `P2-AI-01` accepted | the observations shape + a recorded fixture |
| `P2-API-01` | four tasks accepted | use-case signatures |
| `P3-WEB-*` | `P2-API-01` accepted | the OpenAPI document |

Shapes can all be frozen in one pass on day one. This is what
`WAVE_EXECUTION_GUIDE.md` §B and §D already prescribe — consumers build against a frozen
contract with disjoint `allowed_paths` — and what the CP-00 contract families
(`contracts/domain|analysis/events/v1/**`, frozen 2026-09-01) already supply.

The 19 acceptances were not architecture. They were one integrator reviewing serially,
which is the plan's own risk 3.

**What genuinely cannot be parallelised**, and how each is handled here:

1. **Migration head** — one writer. Handled by writing the whole PC-01 schema in a single
   pass in Gate A, not growing it across eight tasks.
2. **Composition root** — one file, wired once, in Gate C, by the integrator.
3. **The grounding gate against a live model** — built against the recorded fixture, which
   the profile mandates anyway; the live run is a Gate C acceptance step.

## 2. Before dispatch — integrator, not a gate

Serial, one writer, ~1 hour:

1. Merge `agent/p1-int-00` (toolchain, nine `make` targets, `FOUNDATION_LOCK.json`).
2. Merge `agent/p0-pln-01` (29 task files, seam register, owner-decision register).
3. Add the P02 runtime pins to the root lock in the same pass — PDF extractor (`OD-01`),
   provider SDK (`OD-02`). Root locks are a single hotspot; no session may add a
   dependency later.
4. Obtain owner rulings on the critical-path decisions in one sitting: `OD-01`, `OD-02`,
   `OD-03`, `OD-04`, `OD-11`, `OD-12`, `OD-13`, `OD-14`. Serialised individually these
   cost more calendar time than the build.
5. Snapshot the tip and record the SHA in every session brief. Uncommitted deliverables
   are reverted by writers you did not dispatch.

`OD-14` is the one that can move everything: it rules whether P02 sits behind CP-00
acceptance round eleven and `W0-INT-03`. This plan assumes it does not.

## 3. Gate A — seams frozen, foundation running

`A1` is dispatched first because `A5` consumes its OpenAPI document. `A2`, `A3` and `A4`
need nothing from it and start at the same moment as `A1`.

| Session | Owns | Delivers |
|---|---|---|
| `A1` **seams** | `db/migrations/**`, `src/auditmanager/shared/**`, `contracts/api/v1/**`, `docs/program/P02_SEAMS.md` | the complete PC-01 schema as **one** migration head; identifier types; session/transaction factory; every stage-artifact shape; the OpenAPI document; the CSV column contract |
| `A2` **infra** | `infra/local/**` | Compose Postgres + MinIO, pinned digests, health checks, volumes derived from `FOUNDATION_INSTANCE`, idempotent private-bucket init, `check_services.py` |
| `A3` **storage** | `src/auditmanager/storage/**` | BlobStore port, S3 adapter with `temporary -> verify -> publish`, opaque `blob_id`, typed errors, `check.py` |
| `A4` **corpus** | `fixtures/synthetic/ar/**`, `tools/fixtures/**` | synthetic AR PDF — two cross-page contradictions, one explicit placeholder, clean controls — plus its expected-issues manifest and the negative fixtures (encrypted, image-only, oversize, 31-page) |
| `A5` **web shell** | `web/` toolchain, `web/src/app/**`, `web/src/shared/**` | pinned Node/npm, lockfile, app shell, generated typed API client from `A1`'s OpenAPI |

`A1` is the one session that must not be hurried. Every later session is a consumer of it,
and a seam error found in Gate B is the expensive failure mode of this whole structure.

**Gate A closes when**, on one clean integration instance:

- `make foundation` exits `0` — `up`, `check-services`, `migrate`, `check-db`,
  `check-storage`, `test-foundation`;
- `make bootstrap` twice changes no lock or tracked file;
- anonymous bucket list/read/write is denied; a wrong checksum publishes nothing;
- `make down && make up` preserves the migrated state and a published test object;
- `docs/program/P02_SEAMS.md` is frozen at a named commit and the OpenAPI document
  validates;
- the synthetic AR PDF's seeded quotations are recoverable from its extracted text layer;
- `npm --prefix web ci && npm --prefix web run build` exits `0`.

This subsumes `P1-INF-01`, `P1-DB-01`, `P1-STO-01`, `P1-QA-00`, `P1-INT-01` (PF-01),
`P2-INT-00`, `P2-DOM-01`, `P2-BHV-01`, `P3-WEB-00` and `P3-API-01`.

## 4. Gate B — the journey implemented

Eight sessions, all dispatched at once against the Gate A commit. No session waits on
another; each consumes frozen seams and its own recorded fixtures.

| Session | Owns | Delivers |
|---|---|---|
| `B1` **ingest** | `src/auditmanager/documents/**`, `src/auditmanager/ingest/**`, and `src/auditmanager/storage/**` **for the blob-metadata repository only**, taken over from `A3` at the Gate A boundary | direct single-PDF upload, immutable DocumentVersion + input manifest, blob metadata persistence, DB/S3 reconciliation, explicit envelope rejection |
| `B2` **stages** | `src/auditmanager/analysis/engine/**`, `ports/**`, `stages/**` | stage runner; `source_preparation` with stable character offsets; `page_geometry_extraction` with block index and span anchors; `document_context_build`; fail-closed status mapping |
| `B3` **text AI** | `src/auditmanager/analysis/text/**`, `fixtures/recorded/text_analysis/**` | the AR prompt/profile — internal contradictions and literal placeholders only; live adapter; recorded adapter; provenance; cost ceiling per `OD-03` |
| `B4` **findings** | `src/auditmanager/findings/**`, `src/auditmanager/decisions/**` | the grounding gate — every published quotation resolves at its declared anchor, ungrounded items retained as diagnostics only; fresh `finding_uid` allocation; append-only decision ledger |
| `B5` **run + export** | `src/auditmanager/runs/**`, `src/auditmanager/exports/**` | one local executor with persisted run/stage state; idempotency keys; interrupted-run reconciliation per `OD-10`; UTF-8 CSV bound to exact project/version/run per `OD-11` |
| `B6` **API** | `src/auditmanager/api/routers/**`, `schemas/**` | the typed endpoints the frozen OpenAPI already declares |
| `B7` **web project** | `web/src/_pages/projects/**`, `_pages/run/**`, `widgets/project-list|upload-panel/**`, `features/create-project|upload-document/**`, `entities/project|document-version/**` | project list/create, upload, run progress by polling, explicit queued/running/succeeded/partial/failed and live/recorded state |
| `B8` **web review** | `web/src/_pages/review/**`, `widgets/finding-list|evidence-viewer|decision-panel|decision-history|export-panel/**`, `features/open-evidence|record-verdict|append-comment|export-run/**`, `entities/finding|finding-observation|expert-decision/**` | finding list, PDF page open from a finding with its exact quotation, accept/reject with comment and visible history, CSV download |

`B1` is the only Gate B session that writes a Gate A tree, and only the blob-metadata
repository inside it; the BlobStore port and the S3 adapter stay frozen as `A3` left them.

Each session owns its own tests under its own path — `tests/integration/<area>/**`,
`web/tests/unit/<area>/**`. No session writes `src/auditmanager/bootstrap/**`,
`db/migrations/**`, root locks, `contracts/**`, the `Makefile`, or another session's tree.

**Gate B closes when** every session's own suite passes against real PostgreSQL and MinIO
on its own instance, no session has written outside its block, and the Gate A seams are
byte-identical.

This subsumes `P2-META-01`, `P2-ENG-01`, `P2-AI-01`, `P2-FND-01`, `P2-RUN-01`,
`P2-EXP-01`, `P2-API-01`, `P3-WEB-01`, `P3-WEB-02`, `P3-WEB-03`, `P3-WEB-04`.

## 5. Gate C — wired, proven, accepted

| Session | Owns | Delivers |
|---|---|---|
| `C1` **composition** — integrator only | `src/auditmanager/bootstrap/**`, `api/app.py`, `api/composition.py` | every accepted module constructed from configuration; a missing dependency fails at construction, not at first use |
| `C2` **journey tests** | `tests/e2e/pc01/**`, `tests/integration/p02_journey/**` | the ten §8 criteria as executable tests on the recorded adapter; restart and duplicate-request cases; anti-vacuity checks proving real services |
| `C3` **acceptance** | `docs/manual-tests/PC-01_prototype.md`, `artifacts/checkpoints/PC-01/**`, PC-01 rows in `CHECKPOINT_REGISTRY.md`, `CURRENT_STATE.md`, `docs/INDEX.md` | the clean-clone runbook, the live-provider run record, the PC-01 report |

**Gate C closes — and PC-01 passes — when** a reviewer who authored none of the slices, from
a clean clone on a dedicated instance, completes all ten criteria of
`PROTOTYPE_PROFILE.md` §8: services up, empty DB migrated, project created, AR PDF
uploaded to an immutable version and a verified private object, the deterministic path and
one **live** `text_analysis` executed, **at least two seeded issues found**, every published
quotation verified present on its declared page, one finding accepted and one rejected with
a later appended comment, a CSV exported that resolves to the exact version and run, both
processes restarted without state loss, the same commands repeated under the same
idempotency keys without duplicates, and unsupported-input, checksum, unavailable-provider
and ungrounded-model failures shown explicitly with no fallback.

This subsumes `P2-INT-01`, `P2-QA-01`, `P2-INT-02`, `P3-QA-01`, `P3-INT-01`.

## 6. Deferred out of PC-01

- **The navigation layer** — `P1-NAV-01`, `P1-NAV-02`, `docs/navigation/entries/**`,
  `docs/navigation/incidents/*.jsonl` and the six-owner regeneration sequence. ADR-0019
  stays `proposed`. It is a delivery aid for a codebase that does not exist yet; it
  becomes worth building once PC-01 shows which seams people actually navigate.
- **Three separate P02 integration tasks** — collapsed into `C1`.
- **`W0-INT-03` / CP-00 round eleven** — an independent obligation of the CP-00 line,
  quarantined from the prototype path by `PROTOTYPE_PROFILE.md` §6.3. Subject to `OD-14`.

## 7. Operating rules for the fan-out

1. Disjoint `allowed_paths` per session, taken from the tables above; a session that needs
   another's path stops and hands it to the integrator.
2. Unique `FOUNDATION_INSTANCE`, `POSTGRES_PORT`, `S3_API_PORT`, `S3_CONSOLE_PORT`,
   `POSTGRES_DB` and `S3_BUCKET` per session (FF-01 §5). Acceptance runs serially on one
   dedicated instance.
3. Snapshot the tip before dispatch; every session brief carries that literal SHA.
4. No measurement during a fan-out — the suites copy the working tree and will report
   another session's state.
5. Review is the executable gate, not a prose round. A defect is a failing command.
6. A defect shape rejected twice goes to the owner as a plan error, not a third round.

## 8. Estimate

Measured inputs: authoring 2.5–3h per session including self-remediation, from
`P1-INT-00` (2h31m, 3 rounds) and `P0-PLN-01` (2h58m, 4 rounds) on 2026-09-09;
orchestration span 5–11h/day over eight active days, ~3 commits/hour sustained.

| Gate | Sessions | Serial cost | Elapsed |
|---|---:|---|---|
| pre-dispatch | integrator | merge, pins, owner rulings | 0.5 day |
| A | 5 | `A1` then the widest of `A2`–`A5`, then convergence | 1–2 days |
| B | 8 | widest session, then convergence | 2–3 days |
| C | 3 | `C1` serial, then `C2`/`C3`, then the live runbook | 1–1.5 days |
| **FF-01 → PC-01** | | | **5–6 days P50** |

P80 is 9–11 days. The two drivers are both named and both unmeasured: first contact with
real Docker services in Gate A, and seam divergence surfacing at the Gate B convergence.
**Rounds-to-accept for an implementation task has never been measured in this repository** —
after Gate A there will be five samples, and this table is replaced with arithmetic.

## 9. What this trades away

The 19-gate graph buys per-task independent review, a navigation index, and a per-task
evidence trail. This buys none of those. It is the right trade for an instrument whose
purpose is to measure product value with experts and which the programme is explicitly
willing to discard: `PROTOTYPE_PROFILE.md` §1 states the prototype "is not a reduced claim
of production readiness", and risk 1 of the execution plan names *grounded but
professionally useless findings* as a real outcome. Spending three weeks of governance to
reach that answer costs more than the answer is worth.

If PC-01 survives P04 and the code becomes a production line, the per-task apparatus is
worth reinstating — from evidence about which seams broke, rather than from CP-00's
history.
