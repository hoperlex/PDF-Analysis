# Roadmap — prototype first, deeper architecture from evidence

> **Planning status, 2026-09-09:** the PostgreSQL/S3 Foundation Freeze `FF-01` is
> accepted and `P0-FND-00` is complete. `P1-INT-00` and `P0-PLN-01` are dispatchable
> from the acceptance commit. P02–P05 below remain a scope-and-order outline until the
> detailed plan receives separate approval. Existing CP-00 contracts, fixtures, stage
> files and evidence are preserved and are not rewritten by this roadmap.

## Program objective

Deliver a durable working audit prototype as soon as possible, put it in front of domain
experts, and use measured behavior to decide which production architecture and product
capabilities deserve further investment.

The first useful result is not a repository skeleton or a fake pipeline. It is this
complete journey:

```text
PDF upload
  -> immutable version in PostgreSQL + private S3
  -> one real analysis stage
  -> finding beside page evidence
  -> expert accept/reject/comment
  -> export tied to the exact version and Run
```

## Two approvals, not one long planning barrier

```text
P0-FND-00
  -> FF-01 ACCEPTED
       |-> P1-INT-00 -> PostgreSQL/S3 implementation lanes -> PF-01
       |
       `-> P0-PLN-01 -> detailed P02-P05 plan + navigation task approval
                              |
                    PF-01 + accepted plan + navigation gate
                    + forecast recalibrated from P01 evidence
                              `-> P02 implementation
```

`FF-01` approves only the foundation direction and its P01 tasks. This intentionally
allows infrastructure development before the complete prototype plan is ratified.
`P0-PLN-01` runs in parallel and cannot edit the accepted Foundation Freeze.

## Stage map

| Stage | Approval/checkpoint | Goal | Current authority |
|---|---|---|---|
| P00 Direction and early freeze | `FF-01` | fix prototype rules and PostgreSQL/S3 boundaries | **accepted 2026-09-09**; `P0-FND-00` complete |
| P01 PostgreSQL/S3 foundation | `PF-01` | reproducible DB/object-storage providers and tests | `P1-INT-00` dispatchable; providers wait for its acceptance |
| P02 AR text-consistency backend | none | bounded PDF → grounded contradiction/placeholder findings | ten agent-ready tasks in `PROTOTYPE_EXECUTION_PLAN.md`; not dispatchable until that plan is accepted |
| P03 Expert workflow and prototype acceptance | `PC-01` | page/quote review, append-only decisions, CSV, restart | eight agent-ready tasks; not dispatchable until the plan is accepted and the P02 API is frozen |
| P04 Field validation | `PC-02` | expert evidence on representative documents | four agent-ready tasks; not dispatchable until `PC-01` |
| P05 Deep analysis and next roadmap | `PC-03` | choose next capabilities and production work from measurements | three agent-ready tasks; not dispatchable until `PC-02` |

The old S00–S10 documents remain a long-term capability backlog. Their ordering no
longer grants dispatch authority to prototype tasks.

## Decision-to-code navigation gate

ADR-0019/P-23 introduces a repository navigation layer for human and AI-agent delivery.
It does not delay FF-01 or P01. `P0-PLN-01` must create its agent-ready implementation
task, which may prepare the schema and tooling in parallel with P01 but must be accepted
before any P02 implementation fan-out.

The layer uses task/context-owned machine-readable fragments and a generated aggregate
index. It maps active decisions and contracts to owning tasks, implementation paths/public
symbols, runtime entrypoints and proving tests, and supports reverse lookup from a code
path/context. Canonical authority remains in the linked ADR, contract, task, code or test;
the navigation index is rebuildable and never silently resolves ambiguity.

## P00 — direction and early Foundation Freeze

### Outcome

- The prototype profile separates blocking, advisory and historical gates.
- PostgreSQL and private S3-compatible storage are fixed from the skeleton.
- Runtime code is included by explicit use case and composition, not by presence in
  legacy or in the repository.
- Non-working and obsolete legacy scripts are not ported or repaired speculatively.
- P01 can start before P02–P05 planning is complete.

### Exit

The repository owner issued the exact `FF-01 ACCEPTED` record in
`PROTOTYPE_FOUNDATION_FREEZE.md` on 2026-09-09. `P0-FND-00` is complete. This approval
does not extend to P02–P05.

## P01 — PostgreSQL/S3 foundation

### Goal

Build only the durable provider skeleton that every plausible prototype path needs:

- reproducible Python lock and nine root commands, including separate service-health and
  migration-state checks;
- local PostgreSQL and MinIO/S3 with health checks and persistent volumes;
- private, idempotently initialized bucket;
- migration runner, baseline head and typed transaction/session factory;
- BlobStore port and S3 adapter implementing `temporary -> verify -> publish`;
- real-service tests for privacy, checksum failure, restart and idempotency.

No Project, Run or Finding schema is created in P01. That prevents the early foundation
approval from silently approving the full domain design.

### Task graph

```text
P1-INT-00
  |-> P1-INF-01 --|
  |-> P1-DB-01 ---|-> P1-QA-00 -> P1-INT-01 / PF-01
  `-> P1-STO-01 --|
```

Provider code may be authored in parallel after `P1-INT-00`. Acceptance against the
real services is ordered: integrate INF, rebase/review DB and STO on that provider, then
run convergence QA. Parallel authoring uses unique instance names, ports, volumes,
databases and buckets; convergence/acceptance is serial on a dedicated integration
instance.

### Exit evidence

- `make foundation` passes from a clean checkout;
- repeated bootstrap changes no lock or tracked file;
- migration succeeds from empty state and is safe at current head;
- anonymous S3 access is denied;
- correct bytes publish and corrupt bytes do not;
- restart preserves migrated state and a published test object;
- public storage values expose `blob_id` and metadata, not bucket/key;
- a concise PF-01 report records exact commits, locks, image digests and migration head.

### Explicit exclusions

No API/UI, product tables, audit engine, job framework, outbox, retry/fencing, cloud
deployment, production IAM, retention or backup work.

## P02 — AR text-consistency audit backend — outline

The agent-ready decomposition — ten tasks, their disjoint allowed paths, the seam register
and the named owners of the migration head, the root locks and the backend composition
root — is in `PROTOTYPE_EXECUTION_PLAN.md`. The outline below states the scope those tasks
implement.

This stage is not dispatchable until `P0-PLN-01` is accepted. It implements one fixed
product slice, not a generic audit platform: a local expert uploads one Russian-language
AR PDF with an embedded text layer and receives evidence-backed observations of internal
cross-page contradictions and explicit placeholders.

Accepted input is one unencrypted PDF up to 25 MiB/30 pages. Scanned PDFs, OCR, ZIP,
companions and other disciplines are explicit non-goals. The acceptance fixture is a
small synthetic AR PDF with two seeded contradictions, one placeholder and clean control
statements.

P02 includes:

- minimal Project, DocumentVersion, Blob, AuditRun, StageResult, Finding,
  FindingObservation and ExpertDecision-event persistence;
- direct PDF upload, immutable version/InputManifest and explicit DB/S3 reconciliation;
- one local execution process with persisted run/stage states;
- deterministic `source_preparation`, `page_geometry_extraction` and
  `document_context_build`, followed by the sole visible AI stage `text_analysis`;
- a fixed AR prompt/profile that checks only internal contradictions and literal
  placeholders, never external normative compliance; it is a new narrow prompt, not a
  wholesale port of the legacy AR prompt tree;
- live model adapter plus recorded response for deterministic tests;
- publication validation that exact evidence quotations exist at their declared
  page/text/block anchors;
- one-to-one fresh Finding allocation for new observations, with no cross-run matcher;
- explicit live/recorded/partial/failed outcomes;
- minimal typed API consumed by the UI.

An ungrounded model item is diagnostic only and never published as a finding. Expert
decisions target `finding_uid`; the model never writes the verdict. Deferred from P02:
all other disciplines/stages, OCR, automatic retry, Job/Attempt, cross-run matching and
distributed execution.

## P03 — expert loop and PC-01 acceptance — outline

The agent-ready decomposition is eight tasks in `PROTOTYPE_EXECUTION_PLAN.md`, which also
carries the numbered PC-01 acceptance runbook and names the single owner of the frontend
composition root and global styles.

Intended scope:

- minimal project/upload, run-progress and PDF/finding-review views;
- clicking a finding opens its PDF page and shows the exact extracted quotation beside
  it; a graphical bounding-box overlay is not required for PC-01;
- polling-based progress and explicit failure state;
- append-only accept/reject/comment over `finding_uid` with visible history;
- one UTF-8 CSV export containing the exact project/version/run/finding/observation
  identities, category, finding text, evidence page/quote, current expert verdict,
  comment and decision timestamp;
- duplicate-request and application/execution-process restart tests;
- a clean local runbook using the seeded synthetic AR PDF and one live provider call.

`PC-01` passes only when the live run finds at least two seeded issues, every published
item is grounded in an exact source quotation, an expert accepts one and rejects another,
the CSV resolves back to the same version/run, and restart preserves all canonical state.
Recorded replay proves deterministic application behavior; no automated test requires
identical live-model wording. `PC-01` is the first product checkpoint. No earlier stage
may claim a working prototype.

## P04 — field validation — outline

The agent-ready decomposition is four tasks in `PROTOTYPE_EXECUTION_PLAN.md`, which carries
the session protocol, the PC-02 pass/fail gates and the statement of what a 12–16 document
sample can and cannot establish.

Exercise `PC-01` with domain experts on 10–20 synthetic or anonymized representative
documents. Record:

- useful/incorrect/unclear findings;
- evidence-location correctness;
- review time and navigation friction;
- provider latency, cost and failures;
- missing capability that most prevents real use;
- preference for deeper audit stages versus document comparison;
- actual need for retry, rerun carryover or remote execution.

P04 changes no foundational architecture merely to explain disappointing results. It
produces measurements and product decisions.

## P05 — deep analysis and next roadmap — outline

The agent-ready decomposition is three tasks in `PROTOTYPE_EXECUTION_PLAN.md`, which
carries the next-investment decision rule and the per-candidate evidence that makes each
one win or lose.

Use P04 evidence to choose, reject or simplify the old backlog. Candidate work includes:

- additional deterministic/AI stages;
- Run/Job/Attempt, retry, outbox and fencing if observed failures justify them;
- stable finding identity and decision carryover if rerun workflows require them;
- knowledge projection if expert decisions prove reusable;
- deterministic comparison if users rank it above deeper audit;
- remote workers only if measured execution constraints require distribution;
- multi-tenant AuthZ, retention, backup/restore, SLO and load gates before external
  production use.

The output is a new beta/v1 roadmap with estimates based on actual P01–P04 throughput.

## Existing work retained

| Existing material | Role in the prototype programme |
|---|---|
| CP-00 domain/analysis/event contracts | read-only source of identities, states, package semantics and evidence rules |
| five golden journeys | GJ-01 and selected GJ-02/GJ-03 assertions feed prototype tests; comparison/distributed journeys remain backlog |
| Architecture Bible and ADRs | advisory corpus plus the small subset repeated in the accepted Foundation Freeze |
| CP-00 contract/checkpoint tests | historical verification, run only in a disposable clone until hermetic |
| checkpoint reports and manifests | immutable audit history, never a prototype dispatch barrier |
| S01–S10 stage documents | long-term capability inventory; no bulk rewrite |
| prepared `prep/W1` documents | source of useful commands and ownership ideas, not a wholesale merge candidate |

## Prototype gate policy

Blocking gates protect the complete user journey, migration/startup, PostgreSQL/S3
canonical ownership, checksums/publication, evidence correctness, human-decision history,
explicit failure state and secret/key boundaries.

Architecture checks unrelated to the implemented route, complete legacy parity, future
stage aliases, comparison/distributed failures and production SLOs are advisory or
historical. A test is blocking only when a dispatched task names the literal command and
expected result.

## Estimates

Assumptions: one program integrator plus three worker slots, near-continuous orchestration,
same-day owner/reviewer responses and no production/customer data.

| Milestone/work | Estimate basis | P50 elapsed | P80 elapsed |
|---|---|---:|---:|
| FF-01 approval and P1 dispatch | owner-response assumption | 0.5–1 day | 2 days |
| `P0-PLN-01` detailed P02–P05 plan | task estimate; parallel with P01 | 1–2 days | 3–4 days |
| first PostgreSQL/MinIO infrastructure commit | P1 task decomposition | 1–2 days | 3 days |
| PF-01 accepted foundation after FF-01 | arithmetic sum of P1 rows | **4–7 days** | **11–13 days** |
| PF-01 from the current unaccepted candidate | approval latency plus P1 rows | **4.5–8 days** | **13–15 days** |
| PC-01 working real-stage prototype | bottom-up sum of the 19 agent-ready task rows | **30.75–31.75 work-days** | **61.5 work-days** |
| PC-02 field-validation evidence | bottom-up sum of the P04 task rows | **+9–14 work-days** | **+22–25 work-days** |
| PC-03 next-roadmap decision | bottom-up sum of the P05 task rows | **+5–8 work-days** | **+12 work-days** |

The PC-01 rows above are the first bottom-up forecast, published by `P0-PLN-01` from the
agent-ready graph in `PROTOTYPE_EXECUTION_PLAN.md` without waiting for P01. They are sums
of task rows in **work-days of effort**, not elapsed calendar time, and every total is the
arithmetic sum of its rows; the per-stage rows and the critical-path figures are in that
plan. **Calibration is pending**: no measured implementation throughput exists for this
repository, so no row here may be quoted as a delivery commitment. The integrator
recalibrates every row after `PF-01` is accepted and before P02 is dispatched, replacing
each assumption with a measured P01 figure and the command and tree that produced it.
Internal alpha,
pilot readiness and the former CP-10 scope are deliberately unestimated until P04 shows
which capabilities users need; P04 may remove large parts of that scope. The repository's
pre-pivot activity measures planning/review throughput, not runtime delivery, so it is not
used as an implementation velocity baseline.

## Operating rules

1. One writer owns the integration branch. Agents work in isolated branches/clones.
2. No test may commit, switch, reset or stage paths in a shared checkout.
3. Root locks, migration head, contracts, composition root and global styles have one
   writer per active batch.
4. Task specifications stay concise and identify observable results, not an exhaustive
   narration of the agent's procedure.
5. After two rejections of the same defect shape, the owner decides whether the issue is
   product-blocking, advisory or a plan error.
6. Every implementation batch ends in a runnable integrated result.
7. New scope is disabled until a task and acceptance criterion enable it.
8. P02+ implementation changes update their owned decision-to-code navigation fragment;
   only the integration owner regenerates the shared index.
