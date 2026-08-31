# ADR index

| ADR | Status | Decision |
|---|---|---|
| [ADR-0001-greenfield-behavioral-oracle](adr/ADR-0001-greenfield-behavioral-oracle.md) | accepted bootstrap | Greenfield product; legacy is a behavioral oracle |
| [ADR-0002-modular-monolith-control-plane](adr/ADR-0002-modular-monolith-control-plane.md) | accepted bootstrap | Modular monolith control plane |
| [ADR-0003-contract-first-and-data-ownership](adr/ADR-0003-contract-first-and-data-ownership.md) | accepted bootstrap | Contract-first boundaries and single data owner |
| [ADR-0004-repository-layout-and-module-boundaries](adr/ADR-0004-repository-layout-and-module-boundaries.md) | accepted bootstrap | Repository layout and module boundaries |
| [ADR-0005-postgresql-metadata-and-durable-state](adr/ADR-0005-postgresql-metadata-and-durable-state.md) | accepted bootstrap | PostgreSQL owns metadata and durable workflow state |
| [ADR-0006-private-s3-artifact-storage](adr/ADR-0006-private-s3-artifact-storage.md) | accepted bootstrap | Private S3-compatible artifact storage |
| [ADR-0007-postgres-jobs-outbox-and-attempt-fencing](adr/ADR-0007-postgres-jobs-outbox-and-attempt-fencing.md) | accepted bootstrap | PostgreSQL jobs/outbox; Attempt fencing |
| [ADR-0008-execution-engine-package-contract](adr/ADR-0008-execution-engine-package-contract.md) | accepted bootstrap | Execution engine is a package-contract boundary |
| [ADR-0009-nextjs-react-typescript-fsd](adr/ADR-0009-nextjs-react-typescript-fsd.md) | accepted bootstrap | Next.js/React/TypeScript strict with FSD vertical slices |
| [ADR-0010-stable-finding-identity](adr/ADR-0010-stable-finding-identity.md) | accepted bootstrap | Stable Finding identity is separate from run observation |
| [ADR-0011-llm-reproducibility-and-cost](adr/ADR-0011-llm-reproducibility-and-cost.md) | accepted bootstrap | LLM reproducibility and cost ledger |
| [ADR-0012-expert-decision-ledger-and-kb-projection](adr/ADR-0012-expert-decision-ledger-and-kb-projection.md) | accepted bootstrap | Expert decisions are append-only; KB is a projection |
| [ADR-0013-comparison-evidence-layers](adr/ADR-0013-comparison-evidence-layers.md) | accepted bootstrap | Comparison separates approved state, raw evidence and AI synthesis |
| [ADR-0014-authz-classification-retention](adr/ADR-0014-authz-classification-retention.md) | proposed | Object authorization and classification/retention policy |
| [ADR-0015-observability-audit-and-redaction](adr/ADR-0015-observability-audit-and-redaction.md) | accepted bootstrap | Diagnostic logs, durable audit and metrics are separate |
| [ADR-0016-testing-evidence-model](adr/ADR-0016-testing-evidence-model.md) | accepted bootstrap | Testing is an evidence model, not a test pyramid quota |
| [ADR-0017-contract-waves-and-worktree-ownership](adr/ADR-0017-contract-waves-and-worktree-ownership.md) | accepted bootstrap | Contract waves and worktree-per-task ownership |
| [ADR-0018-checkpoint-versioning](adr/ADR-0018-checkpoint-versioning.md) | accepted bootstrap | Checkpoint version = tag + frozen contracts + automated + manual evidence |

## Status semantics

`accepted bootstrap` means this package selects the decision as its baseline, but the program still requires the explicit CP-00 ratification task so a coding agent cannot silently treat a supplied/refactoring proposal as owner-approved production policy.
