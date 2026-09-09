# Prototype profile — working audit before platform completion

> **Status: foundation section accepted under `FF-01` on 2026-09-09.** `P0-FND-00` is
> complete and section 3 is frozen for P01. The remaining prototype scope guides
> `P0-PLN-01` but does not approve P02–P05 implementation by itself. This profile does
> not rewrite or invalidate CP-00 architecture, contracts, fixtures or historical
> evidence.

## 1. Objective

Deliver the smallest durable application through which a domain expert can complete
the full first-value journey:

```text
upload one PDF
  -> publish an immutable document version
  -> run one real analysis stage
  -> inspect a finding beside its evidence
  -> accept or reject the finding with a comment
  -> export the reviewed result
```

The prototype exists to measure product value and expose implementation facts. It is
not a reduced claim of production readiness.

## 2. Working assumptions

- The prototype is single-tenant and operated in a trusted local/internal environment.
- PostgreSQL owns canonical metadata and durable workflow state from the first build.
- Private S3-compatible storage owns PDF bytes and generated artifacts from the first
  build; MinIO is the default local implementation.
- FastAPI remains the backend/control-plane direction and Next.js/React remains the UI
  direction, but framework architecture is implemented only where the journey needs it.
- One local execution process is sufficient. Run and stage state are persisted before
  execution, but distributed-worker semantics are deferred.
- Automated tests use a recorded provider response. A live provider or an isolated
  characterized legacy adapter supplies the real demonstration path.
- No customer or production payload is committed to Git.

External pilot deployment, multiple tenants or untrusted users require a later security
gate and are outside these assumptions.

## 3. Foundation invariants

These are the only architecture decisions frozen before the full prototype plan is
complete:

1. PostgreSQL is canonical for Project, DocumentVersion, Blob metadata, AuditRun,
   StageResult, FindingObservation and ExpertDecision.
2. S3-compatible object storage is canonical for source bytes and large artifacts.
3. Business identity is opaque; path, object key, filename and display ordinal are not
   identifiers.
4. A published document version and its input manifest are immutable.
5. Every published blob records role, media type, size and SHA-256.
6. Blob publication follows `temporary -> verify -> publish`; a failed checksum cannot
   become canonical.
7. Buckets are private. Internal object keys never appear as API or UI identity.
8. Schema change has one migration-head owner; root locks and composition root also
   have one owner at a time.
9. Credentials are local disposable values or injected secrets and are never committed.
10. Foundation ports may gain capabilities later, but later work may not bypass them by
    issuing direct SQL or S3 operations from routers, React components or analysis code.

The Foundation Freeze deliberately does **not** freeze cloud vendor, retention, legal
hold, backup topology, high availability, lifecycle policy or distributed execution.

## 4. Runtime inclusion policy

Existing material is preserved, but existence in the repository is not authorization to
execute it.

A code path belongs to the prototype runtime only when all four conditions hold:

1. a prototype task names the use case;
2. the composition root imports or registers it deliberately;
3. the owning lane supplies a passing test for the used behavior;
4. its dependencies are present in the reproducible lock and startup path.

Consequences:

- do not port obsolete scripts or endpoints for parity alone;
- do not import the legacy application as the new control plane;
- a useful legacy algorithm may be called behind a narrow adapter or subprocess after
  its input/output is characterized;
- dead, incomplete or unreferenced code is excluded rather than repaired speculatively;
- no silent fallback from a failed real stage to a fake successful result;
- the fake/recorded adapter is explicit in Run provenance and UI state.

## 5. Reuse without rewriting

| Existing family | Prototype use | Treatment |
|---|---|---|
| `contracts/domain/v1/**` | identifiers, state/error vocabulary | read-only source; select only the surface a provider and consumer actually use |
| `contracts/analysis/v1/**` | stage/result/package semantics and provenance | read-only source; full-schema conformance is claimed only for objects actually published as those contracts |
| `contracts/events/v1/**` | versioned event-envelope vocabulary | read-only; runtime event bus is not required |
| `fixtures/golden/GJ-01/**` | ingest and version-isolation cases | direct prototype evidence |
| relevant parts of `GJ-02` and `GJ-03` | restart/export and expert-decision cases | select by assertion ID in task specifications |
| remaining golden journeys | comparison/distributed backlog | preserved, not blocking |
| `docs/architecture/**` | long-term constraints and rationale | advisory unless repeated in Foundation invariants or a dispatched task |
| `tests/contract/**`, `tests/checkpoint/**` | CP-00 historical verification | preserved; not a shared-checkout prototype gate |
| `artifacts/checkpoints/CP-00/**` | immutable audit trail | preserved; not dispatch authority for prototype work |
| `docs/stages/S00`–`S10` | capability backlog | preserved; no automatic dependency on their old order |

No existing family is mass-reformatted, copied into a new document or deleted as part
of the prototype pivot.

## 6. Gate classes

### 6.1 Prototype-blocking

A failure blocks integration when it can cause any of the following:

- the primary user journey does not complete;
- migration or startup fails from a clean environment;
- metadata or bytes are lost, duplicated incorrectly or published before validation;
- PostgreSQL or S3 is bypassed as canonical storage;
- evidence points at the wrong document version or page;
- a human decision is overwritten rather than appended;
- a failed/partial/recorded run is represented as a live success;
- a secret, internal path or object key crosses a forbidden boundary;
- an owned interface is changed incompatibly without its consumer test.

### 6.2 Advisory

Architecture lint not exercised by the prototype, complete legacy parity, optional
contract fields, future stage aliases, distributed failure modes, cross-version finding
matching and production SLO checks are recorded but do not block the prototype.

### 6.3 Historical

CP-00 ratification mechanics, round reports and their exact digest/accounting model are
historical evidence. They do not gate prototype code. Until their sandbox is hermetic,
they run only in a disposable clone and never in a shared integration checkout.

Every task lists its blocking commands. No ambient suite becomes blocking merely because
it exists.

## 7. Prototype scope

### 7.1 Concrete PC-01 slice: AR text-consistency review

The first working product is one deliberately narrow audit use case:

> A local expert creates a project, uploads one Russian-language Architectural
> Solutions (`AR`) PDF with an embedded text layer, runs a text-only internal-consistency
> review, opens each finding beside its source quotations, records an accept/reject
> decision with a comment, and downloads a CSV for that exact document version and run.

The accepted input envelope is one unencrypted PDF, at most 25 MiB and 30 pages. Every
page must have extractable embedded text. Scanned/image-only,
password-protected, mixed-file, ZIP and companion-file inputs fail explicitly as
unsupported; OCR is not silently substituted.

The only product question answered by PC-01 is:

> Does the text state conflicting values or claims about the same project attribute in
> different places, or leave an explicit placeholder/incomplete field that requires
> expert attention?

Examples include two different fire-resistance classes or evacuation-exit counts stated
on different pages, and literal placeholders such as `TBD`/`уточнить`. The stage does
not decide compliance with external norms, infer facts from drawings or claim that a
missing statement was legally required.

One visible AI stage, canonical `text_analysis`, is supported by three deterministic
preparation stages required for evidence: `source_preparation`,
`page_geometry_extraction` and `document_context_build`. Geometry is used only to bind
text spans to pages/blocks; PC-01 implements no visual finding detection.

Every emitted observation contains:

- a fresh `finding_uid` plus immutable `finding_observation_id` and `run_id`;
- category `internal_contradiction` or `explicit_placeholder`;
- concise finding and recommendation text;
- one or more evidence references with page, exact extracted quotation and text/block
  anchor;
- stage, prompt/profile and live-or-recorded model-call provenance.

The publication gate verifies that every quotation exists at its declared anchor. An
ungrounded model item is rejected from the finding list and retained only as diagnostic
evidence. A new run may allocate new findings; cross-run matching and decision carryover
are not part of PC-01. Expert decisions target `finding_uid`, reference the reviewed
observation and are append-only. Model output never becomes an expert verdict.

The deterministic acceptance fixture is a small synthetic AR PDF containing two seeded
cross-page contradictions, one explicit placeholder and clean control statements. The
recorded-response adapter drives automated tests. A live-provider manual run must find
at least two seeded issues, but no test asserts byte-equality of generated wording.

### 7.2 Included implementation surface

Included:

- one local reviewer with no authentication or tenant administration;
- create/list one or more Projects and direct single-PDF upload;
- one immutable DocumentVersion per accepted upload;
- private S3 publication with checksum verification;
- persisted Blob metadata, AuditRun and per-stage status plus a narrow reconciliation
  path for interrupted DB/S3 publication;
- the four-stage preparation/text path above with live and recorded-response adapters;
- Finding plus FindingObservation with validated text/page evidence and provenance;
- project/upload, run-progress and PDF/finding-review views;
- polling and explicit unsupported/failed/partial states;
- append-only accept/reject/comment;
- one UTF-8 CSV export tied to the exact Project, DocumentVersion and AuditRun;
- restart and duplicate-request tests needed by the journey.

Deferred:

- OCR, ZIP and every legacy companion format;
- disciplines other than the single AR validation profile;
- visual finding detection, block-analysis, finding merge, grounding-review,
  correction, normative verification and every optimization pipeline;
- automatic retry/skip/resume policy, Job/Attempt lease, heartbeat, fencing and outbox;
- stable finding identity and decision carryover across reruns;
- knowledge-base projection and AI re-review;
- comparison, repair/undo and graphic/vector evidence;
- remote/distributed workers;
- multi-tenant AuthZ, retention, legal hold, HA, DR, load and cost budgets;
- production deployment and production data.

## 8. Evidence of a working prototype

The prototype checkpoint passes only when a reviewer can, from a clean local start:

1. start the app, PostgreSQL and private S3-compatible storage with documented commands;
2. migrate an empty database;
3. create a project and upload the bounded synthetic AR PDF, observing an immutable
   version plus verified private S3 object;
4. execute the deterministic preparation path and one live `text_analysis`, while the
   UI distinguishes the contract run states `queued`, `running`, `validating`,
   `published`, `partial` and `failed`, and the live or recorded provider mode. The
   success terminal of an `AuditRun` is `published`; `succeeded` is a `StageResult`
   status on a different aggregate and is never used as a run state;
5. observe at least two seeded issues in the live run and verify that every published
   finding quotation exists on the declared PDF page;
6. open the page from a finding, view its exact quotation, accept one finding, reject
   another and append a later comment without overwriting history;
7. export a UTF-8 CSV whose rows resolve to the exact project, version, run, finding,
   observation and current expert verdict;
8. restart application and execution process without losing canonical state;
9. repeat the same upload/run commands under the same idempotency keys without creating
   duplicate versions, runs, observations or decisions;
10. show explicit unsupported input, checksum, unavailable-provider and ungrounded-model
    failures without filesystem fallback or fake success.

## 9. Learning gate after delivery

The prototype is exercised with domain experts on 12–16 measurable synthetic or anonymized
documents — 5 seeded plus 7–11 controls — together with 2–4 negative-envelope documents
counted separately and excluded from every finding denominator. The validation report
measures:

- percentage of findings marked useful, incorrect and unclear;
- evidence-location correctness;
- expert review time and navigation friction;
- provider latency, cost and failure distribution;
- which missing stage or capability prevents real use;
- whether audit depth or document comparison is the next highest-value investment;
- which failures actually require retry, Attempt fencing or remote execution;
- agent navigation friction: the search and rework incidents tasks recorded, reported as
  absent rather than as zero when no task recorded one.

P05 architecture work starts from this report. It does not defend an earlier solution
merely because that solution appears in the long-term backlog.
