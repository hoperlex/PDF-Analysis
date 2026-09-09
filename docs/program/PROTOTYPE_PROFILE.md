# Prototype profile — working audit before platform completion

> **Status: candidate for repository-owner acceptance.** `FF-01 ACCEPTED` completes
> `P0-FND-00` and freezes section 3 for P01. The remaining prototype scope guides
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

Included:

- direct PDF upload;
- one Project and multiple immutable DocumentVersions;
- private S3 publication with checksum verification;
- persisted AuditRun and per-stage status;
- one real text-analysis stage plus a recorded-response adapter;
- FindingObservation with page/evidence reference and provenance;
- PDF/evidence view, progress polling and explicit error state;
- append-only accept/reject/comment;
- one simple CSV/XLSX or JSON export tied to the exact Run;
- restart and duplicate-request tests needed by the journey.

Deferred:

- ZIP and every legacy companion format;
- all nine analysis stages, visual/block/norm/critic/corrector pipelines;
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
3. upload a synthetic PDF and observe an immutable version plus verified S3 object;
4. execute one real stage and distinguish live, recorded, partial and failed outcomes;
5. open a finding on the correct PDF page/evidence location;
6. append an expert decision and see its history;
7. export reviewed results tied to the exact version and Run;
8. restart application and execution process without losing canonical state;
9. repeat upload/run requests without uncontrolled duplication;
10. show that corrupt bytes, wrong checksum and provider failure remain explicit and
    unpublished where publication would be unsafe.

## 9. Learning gate after delivery

The prototype is exercised on 10–20 synthetic or anonymized representative documents
with domain experts. The validation report measures:

- percentage of findings marked useful, incorrect and unclear;
- evidence-location correctness;
- expert review time and navigation friction;
- provider latency, cost and failure distribution;
- which missing stage or capability prevents real use;
- whether audit depth or document comparison is the next highest-value investment;
- which failures actually require retry, Attempt fencing or remote execution.

P05 architecture work starts from this report. It does not defend an earlier solution
merely because that solution appears in the long-term backlog.
