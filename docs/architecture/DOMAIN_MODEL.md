# Domain model v1 — conceptual

Это conceptual model для CP-00. SQL model появляется отдельными contract/migration tasks; здесь намеренно нет ORM.

**Owner decisions recorded 2026-09-01.** Two semantics below were prepared in round 1
and are now decided in [CP00_OWNER_DECISIONS.md](CP00_OWNER_DECISIONS.md); the
dispositions and evidence are in
[CP00_ARCHITECTURE_REVIEW.md](CP00_ARCHITECTURE_REVIEW.md).

- `PD-01` — **approved with modification**: the `ExpertDecision` ledger is
  append-only; a correction and a revocation each create a new `decision_id`; a
  revocation moves the current verdict projection to `pending` and does **not**
  automatically restore the superseded verdict; history is preserved.
- `PD-03` — **approved with modification**: `AuditRun`, `Job` and `Attempt` are
  distinct. A new `AuditRun` is created when a top-level audit/re-audit command is
  accepted for a frozen set of inputs and configurations; the same idempotency key
  and payload return the existing Run; changed inputs, an explicit re-audit or a
  repeat of a terminal Run create a new Run; retry, resume, restart and worker
  failover create a new `Attempt` of the same `Job`, never a new Run; a terminal Run
  is never reopened. The attempt-authority capability is named `execution_token`
  (opaque, equality-only, refreshed per `Attempt`, verified in the publishing
  transaction).
  - **Precedence clarification, recorded inside `PD-03` on 2026-09-01** (owner; not a
    new decision): where the two rules above overlap — a repeat of a Run that is
    already terminal, under the same idempotency key and the same payload — identical
    idempotency key and payload **always** return the original Run. A repeat of a
    terminal Run creates a new Run **only** under a new idempotency key. Neither rule
    is changed and the terminal Run is reopened on neither branch.

A contract lane carries these modifications with the decision. Nothing here is
ratified until the CP-00 integration task records acceptance, and nothing that
depends on the still-open `U-04` (tenant model, IdP, retention TTL, legal hold) may
be encoded at all.

## Aggregate ownership

| Context | Authoritative aggregates/entities | Notes |
|---|---|---|
| Access | User, Session, Role/Grant | object-level authorization |
| Documents | Object, Discipline, Project, Document | display/business metadata |
| Ingest | DocumentVersion, Import | immutable version after publish |
| Storage | Blob, BlobPublication | physical S3 layout hidden |
| Jobs | AuditRun, Job, Attempt | three identities; durable states |
| Analysis | AnalysisProfile, PromptBundle, NormsSnapshot, ModelCallRecord | run reproducibility |
| Findings | Finding, FindingObservation, ReviewState | stable identity vs run evidence |
| Decisions | ExpertDecision, DecisionReason, Discussion | append-only decisions |
| Knowledge | KBProjection, SimilarityIndex | rebuildable projection |
| Comparison | Comparison, SheetLink, SuggestionSet, ComparisonRevision | approved link ≠ suggestion |
| Export | ExportRequest, ExportArtifact | derived artifact |
| Workers | Worker, WorkerCapability, Lease | remote execution control |
| Operations | AuditEvent | append-only security/business audit |

## Critical identities

### Finding vs FindingObservation

`Finding` represents durable semantic issue identity across reruns when identity policy can match it.

`FindingObservation` represents evidence emitted by one `AuditRun`:

```text
Finding 1 ─── * FindingObservation * ─── 1 AuditRun
                     │
                     ├── page/geometry/source artifacts
                     ├── stage/version
                     └── confidence/quality metadata
```

Display ordinal such as `F-014` belongs to a run/read model and **never** serves as FK.

### Run / Job / Attempt

```text
AuditRun       business request/result history
  └── Job      schedulable durable work item
       └── Attempt  one concrete execution lease/token
```

Rerun may create new Run. Retry normally creates new Attempt for same Job according to retry policy. A stale Attempt cannot publish after fencing token changed. The exact creation rule is the decided `PD-03` semantics above, including its precedence clarification: the same idempotency key with the same payload always returns the original Run, and a repeat of a terminal Run creates a new Run only under a new idempotency key.

### DocumentVersion

Version becomes immutable after publication. New source files or corrected companions create a new version; `current_version_uid` is explicit mutable pointer owned by Documents/Ingest transition.

## Decision ledger

```text
Finding
  └── ExpertDecision(event 1: accepted)
  └── ExpertDecision(event 2: rejected, reason=...)
  └── ExpertDecision(event 3: accepted, comment=...)

CurrentVerdict = projection(last valid event according to rules)
KnowledgeBase = projection(events + selected evidence)
```

Deleting/rewriting an old decision event is not normal edit semantics.

## Comparison ownership

```text
Comparison
  ├── source Version A
  ├── target Version B
  ├── SuggestionSet(rebuildable)
  ├── SheetLink(user-approved state/revision)
  └── ComparisonRevision
       ├── deterministic exclusions
       ├── raw text diff
       ├── raw graphic evidence
       └── derived AI synthesis
```

Recompute suggestions cannot mutate approved SheetLink.

## Analysis provenance

Published `AuditRun` references immutable:

- `analysis_profile_id`;
- `prompt_bundle_id`(s);
- `norms_snapshot_id`;
- input manifest checksum/version;
- stage contract versions;
- model call records;
- result package checksum.

This is the minimum evidence needed to explain why two runs differ.
