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
       `-> P0-PLN-01 -> detailed P02-P05 plan + two-task navigation gate approval
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
| P02 AR text-consistency backend | none | bounded PDF → grounded contradiction/placeholder findings | thirteen agent-ready tasks in `PROTOTYPE_EXECUTION_PLAN.md`; not dispatchable until that plan is accepted |
| P03 Expert workflow and prototype acceptance | `PC-01` | page/quote review, append-only decisions, CSV, restart | eight agent-ready tasks; not dispatchable until the plan is accepted and the P02 API is frozen |
| P04 Field validation | `PC-02` | expert evidence on representative documents | four agent-ready tasks; not dispatchable until `PC-01` |
| P05 Deep analysis and next roadmap | `PC-03` | choose next capabilities and production work from measurements | three agent-ready tasks; not dispatchable until `PC-02` |

The old S00–S10 documents remain a long-term capability backlog. Their ordering no
longer grants dispatch authority to prototype tasks.

## Decision-to-code navigation gate

ADR-0019/P-23 introduces a repository navigation layer for human and AI-agent delivery.
It does not delay FF-01 or P01. `P0-PLN-01` must create its agent-ready implementation
tasks — **two** of them: `P1-NAV-01` builds the schema, tooling, index and planned entries
in parallel with P01, and `P1-NAV-02` flips the named foundation entries to `implemented`
after `PF-01` and regenerates the index. Both must be accepted before any P02
implementation fan-out; neither blocks P01.

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

The agent-ready decomposition — thirteen tasks, their allowed-path blocks, the seam
register and the named owners of the migration head, the root locks, the backend
composition root and the server-side CSV export — is in `PROTOTYPE_EXECUTION_PLAN.md`. The
outline below states the scope those tasks implement. PC-01 has no Job, Attempt, lease,
fencing token, retry, resume or outbox: those are deferred, and the plan records the
conformance scope that follows.

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
the session protocol, the PC-02 pass/fail gates and the statement of what a 12–16
measurable document sample can and cannot establish.

Exercise `PC-01` with domain experts on **12–16 measurable** synthetic or anonymized
documents — 5 seeded plus 7–11 controls — together with **2–4 negative-envelope**
documents counted separately and excluded from every finding denominator. Record:

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

## Normative corpus — into PostgreSQL at paragraph granularity, then vectors

**Owner direction, 2026-09-17.** The normative-document corpus is to be carried into
PostgreSQL in later stages, **split to paragraph granularity**, so that vector embeddings can
be laid over it afterwards. It is recorded here rather than in `ALPHA_ROADMAP.md`: nothing in
it belongs to the alpha deployment, and putting it there would make the alpha look like it
waits on this. It does not.

### Where the corpus is today, because git cannot show you

`.local/norms/corpus/`, on this machine, **outside version control** — no diff, grep or clone
of this repository will reveal it, which is why it is named here. `MANIFEST.json` beside it is
the index. Measured 2026-09-17 from that manifest:

| | |
|---|---|
| documents | **674**, none with a missing file |
| kinds | ГОСТ 492, СП 101, Приказ 20, Постановление 18, МДС 7, Решение 6, СНиП 5, and seventeen more |
| pages | **28 251** |
| on disk | 5.1 GB — 712 MB source PDF, 122 MB recognised text (`results.md`), 154 MB HTML, 16 MB block geometry |
| recognition | 28 246 blocks recognised, **3 failed** |

Layout per document: `corpus/<slug>/{document.pdf, blocks.json, stamp_audit.json, results.md,
results.html}`.

### What the corpus is not yet, and it is the whole of the work

**Its granularity today is a page, not a paragraph.** There are 28 249 blocks over 28 251
pages — approximately one per page — and every one is `block_type: text`. Worse for planning
purposes: `blocks.json` carries **geometry and a crop URL and no text at all**
(`block_id`, `ordinal`, `page_index`, `coords_norm`, `polygon_points`, `crop_url`). The
recognised text exists only inside `results.md` and `results.html`, as markdown under a
`### BLOCK #n [TEXT]` heading per page.

Two consequences a later task should not rediscover:

- **paragraph segmentation is work that does not exist yet**, and its input is markdown that
  has to be parsed, not a structured text field that can be read;
- **a paragraph cannot be given a bounding box from what is stored.** Page-level polygons are
  all there is. A paragraph anchored as *page plus character offset in the recognised text* is
  derivable today; a paragraph anchored *visually* requires re-segmenting the page images, and
  those images are `crop_url` values pointing at an external service rather than bytes in the
  corpus. The recognised text is self-contained; the page images are not.

### The stages this implies, and what each one must decide

1. **Custody.** Bring the corpus under the immutable-version model the product already has —
   `DocumentVersion`, `Blob`, `InputManifest` — so a norm has an identity, a digest and a
   version instead of being a directory on one machine. *Decision:* what a version of a norm
   means. The corpus already holds `Изменение` and `Поправка` as separate documents, which is
   the versioning question arriving in disguise.
2. **Segmentation.** Paragraphs with stable identity and an anchor. *Decision:* textual anchor
   or visual one — see above; the first reuses the evidence model unchanged, the second opens
   a new pipeline.
3. **Persistence.** Paragraph rows in PostgreSQL under the same append-only discipline.
   *Decision, and it is new for this system:* 28 251 pages become some hundreds of thousands
   of paragraphs, and that is **the first table here whose row count is not bounded by one
   audit run**. Every query and index assumption in the product predates it.
4. **Vectors.** Embeddings per paragraph. *Decisions:* provider and cost at that volume,
   in-database (`pgvector`) against an external index, and the re-embedding policy when a norm
   gains a new edition.

### Why this is P05+ and not sooner

It is not a storage task. The prototype's analysis checks **internal** contradictions and
literal placeholders and is explicitly forbidden from judging external normative compliance
(P02 outline above). A normative corpus in the database exists to enable exactly that
judgement, so adopting it is a **scope change at ADR level**, not an ingestion job — and it
should be taken on the evidence live use produces about what experts actually need, which is
what P04 and the alpha are for.

The corpus's existence changes none of the alpha's dates and blocks none of its waves.

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

**Forecast, not a commitment. Calibration PENDING until `PF-01`.** Effort and elapsed are
separate quantities and are never added together; the full two-table model, its arithmetic
and its method are in `PROTOTYPE_EXECUTION_PLAN.md` §4.

Effort, in person-days, as the arithmetic sum of the thirty agent-ready task rows:

| Milestone | Basis | P50 effort | P80 effort |
|---|---|---:|---:|
| to PC-01 | navigation + P02 + P03 rows | **31.25** | **62.0** |
| to PC-02 | the above + P04 rows | **40.25** | **79.0** |
| to PC-03 | the above + P05 rows | **46.75** | **91.0** |

Elapsed, in working days, with one integrator, three worker slots and one serial review
slot per acceptance:

| Leg | Bound by | P50 elapsed | P80 elapsed |
|---|---|---:|---:|
| FF-01 approval and P1 dispatch | owner response | 0.5–1 day | 2 days |
| PF-01 accepted foundation after FF-01 | FF-01 §9 wave estimate | **4–7 days** | **11–13 days** |
| PF-01 → PC-01 | effort and slot contention, with the frontend overlapping the P02 tail | **25.75 days** | **51.5 days** |
| FF-01 → PC-01 | the two rows above | **29.75–32.75 days** | **62.5–64.5 days** |
| PC-01 → PC-02 | expert scheduling, not effort | **11–14 days** | **24–27 days** |
| PC-02 → PC-03 | effort plus owner-response cycles | **7.25 days** | **13.5 days** |

P02 and P03 are not fully serial: frontend authoring is unblocked by the frozen
`P2-API-01` contract and runs beside the P02 tail, while `P3-QA-01` waits for the accepted
`P2-INT-02` so end-to-end evidence judges an accepted backend.

These are the first bottom-up forecast, published by `P0-PLN-01` from the agent-ready
graph without waiting for P01. The `FF-01`→`PF-01` row is cited from FF-01 §9 as a
wave-level estimate, not as a sum of task rows, because the six P01 task files carry no
per-task estimate. **Calibration is pending**: no measured implementation throughput exists
for this repository, so no row here may be quoted as a delivery commitment. The integrator
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
