# Domain model v1 — conceptual

Это conceptual model для CP-00. SQL model появляется отдельными contract/migration tasks; здесь намеренно нет ORM.

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

Rerun may create new Run. Retry normally creates new Attempt for same Job according to retry policy. A stale Attempt cannot publish after fencing token changed.

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
