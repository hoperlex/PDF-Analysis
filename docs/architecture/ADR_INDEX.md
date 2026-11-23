# ADR index

A locator: the ADR text is the authority. Rebuilt on 2026-11-18 by `ADR-OPTIMISE-01` (owner ruling `R-156a`).

## Rules

- **Status** is one of `accepted`, `proposed` or `superseded by ADR-YYYY`. A point still open inside an accepted ADR is an
  "Open:" line in its Decision; partial acceptance is stated in the Basis line.
- **An ADR is amended, never rewritten.** The one exception is `R-156a`: on 2026-11-18 every ADR was brought to
  [the template](ADR_TEMPLATE.md), its addenda folded in and ADR-0020…0029 compressed. The full earlier text of any ADR is
  `git show fb6c2203e:docs/architecture/adr/<file>`.
- **Numbers are permanent.** ADR numbers, decision and section numbers, table rows and `AD-NN` are cited from code, tests and
  documents; a revision may shorten the text but never renumbers, merges or drops one.
- **A new ADR** takes the next free number, follows the template and gets its row here in the same commit
  (`scripts/validate_bootstrap.py` checks files against this index).

## Index

| ADR | Status | Area | Decision | Amends · amended by |
| --- | --- | --- | --- | --- |
| [ADR-0001-greenfield-behavioral-oracle](adr/ADR-0001-greenfield-behavioral-oracle.md) | accepted | foundation | Greenfield product; the legacy application is a behavioural oracle, not a code base | — |
| [ADR-0002-modular-monolith-control-plane](adr/ADR-0002-modular-monolith-control-plane.md) | accepted | foundation | Modular monolith control plane; model work by the worker (`R-105`) and remote executors (`R-143`) | — |
| [ADR-0003-contract-first-and-data-ownership](adr/ADR-0003-contract-first-and-data-ownership.md) | accepted | foundation | Contract-first boundaries; one owner per data set | — |
| [ADR-0004-repository-layout-and-module-boundaries](adr/ADR-0004-repository-layout-and-module-boundaries.md) | accepted (CP-00 qualification) | foundation | Repository layout and module boundaries | — |
| [ADR-0005-postgresql-metadata-and-durable-state](adr/ADR-0005-postgresql-metadata-and-durable-state.md) | accepted | data | PostgreSQL owns metadata and durable workflow state | — |
| [ADR-0006-private-s3-artifact-storage](adr/ADR-0006-private-s3-artifact-storage.md) | accepted | data | Durable bytes in private S3-compatible storage behind opaque `blob_id`; the fork's objects move to a Yandex bucket | — |
| [ADR-0007-postgres-jobs-outbox-and-attempt-fencing](adr/ADR-0007-postgres-jobs-outbox-and-attempt-fencing.md) | accepted (CP-00 qualification) | data | PostgreSQL jobs and outbox; Attempt fencing | — |
| [ADR-0008-execution-engine-package-contract](adr/ADR-0008-execution-engine-package-contract.md) | accepted (CP-00 qualification) | analysis | The execution engine is a package-contract boundary | — |
| [ADR-0009-nextjs-react-typescript-fsd](adr/ADR-0009-nextjs-react-typescript-fsd.md) | accepted | web | Next.js, React and strict TypeScript with FSD vertical slices | — |
| [ADR-0010-stable-finding-identity](adr/ADR-0010-stable-finding-identity.md) | accepted | data | Stable Finding identity is separate from a run's observation | — |
| [ADR-0011-llm-reproducibility-and-cost](adr/ADR-0011-llm-reproducibility-and-cost.md) | accepted | analysis | LLM reproducibility by artifacts and a cost ledger | — |
| [ADR-0012-expert-decision-ledger-and-kb-projection](adr/ADR-0012-expert-decision-ledger-and-kb-projection.md) | accepted (CP-00 qualification) | data | Expert decisions are append-only; the KB is a projection | · ADR-0022 (project erase, `R-146o`), ADR-0027 (case content) |
| [ADR-0013-comparison-evidence-layers](adr/ADR-0013-comparison-evidence-layers.md) | accepted (CP-00 qualification) | comparison | Approved state, raw evidence and AI synthesis are separate layers | · ADR-0025 |
| [ADR-0014-authz-classification-retention](adr/ADR-0014-authz-classification-retention.md) | proposed; accepted in part by `R-146` | data | Object authorization, classification and retention; the parts `R-146` decided live in ADR-0022/0023 | · ADR-0022, ADR-0023 |
| [ADR-0015-observability-audit-and-redaction](adr/ADR-0015-observability-audit-and-redaction.md) | accepted | operations | Diagnostic logs, durable audit and metrics are separate | — |
| [ADR-0016-testing-evidence-model](adr/ADR-0016-testing-evidence-model.md) | accepted | foundation | Testing is an evidence model, not a pyramid quota | — |
| [ADR-0017-contract-waves-and-worktree-ownership](adr/ADR-0017-contract-waves-and-worktree-ownership.md) | accepted (CP-00 qualification) | foundation | Contract waves and worktree-per-task ownership | — |
| [ADR-0018-checkpoint-versioning](adr/ADR-0018-checkpoint-versioning.md) | accepted | foundation | Checkpoint = tag + frozen contracts + automated and manual evidence | — |
| [ADR-0019-decision-code-navigation](adr/ADR-0019-decision-code-navigation.md) | proposed | foundation | Rebuildable decision ↔ code/contracts/tests navigation for people and agents | — |
| [ADR-0020-normative-corpus-alpha-runtime](adr/ADR-0020-normative-corpus-alpha-runtime.md) | accepted | norms | Canonical norms in PostgreSQL with in-database pgvector, source bytes in private S3; on the fork server embeddings on the fly, BGE-M3 F32 for the beta, DB local (decision 7) | — |
| [ADR-0021-production-topology-and-operations](adr/ADR-0021-production-topology-and-operations.md) | accepted (`AD-04` open) | production | One VPS, TLS and ACME in `infra/`, two database roles, manual copies (A-1); the fork's 32 GB server with a local DB and one disk (section 11) | — |
| [ADR-0022-production-data-governance](adr/ADR-0022-production-data-governance.md) | accepted | production | No automatic retention; journalled operator project erase; what leaves the host | ADR-0012, ADR-0014 · ADR-0027 |
| [ADR-0023-production-identity-and-access](adr/ADR-0023-production-identity-and-access.md) | accepted | production | One organisation, local accounts, sliding session; seeded administrator closed by the deploy (`R-146s`); audited access changes | ADR-0014 (accepts it in part) · — |
| [ADR-0024-production-analysis-path-and-ai-execution](adr/ADR-0024-production-analysis-path-and-ai-execution.md) | accepted (`AD-18` open) | analysis | АР runs the standard analysis (`R-154a`); OpenRouter base connection; other sections to full versions first | — |
| [ADR-0025-comparison-modules](adr/ADR-0025-comparison-modules.md) | accepted | comparison | «Сравнение версий» and «Сравнение стадий»: comparison-local queue and spend journal, raw evidence then AI layers, refusal caps | ADR-0013 · — |
| [ADR-0026-executor-capacity-enrollment-groups](adr/ADR-0026-executor-capacity-enrollment-groups.md) | accepted | executors | Capacity per connection, one agent enrollment path, homogeneous executor groups with dispatch-time binding | · ADR-0028 |
| [ADR-0027-decision-memory](adr/ADR-0027-decision-memory.md) | accepted (revisable by the owner) | memory | The case content is a primary record written with the decision and outliving it | ADR-0012, ADR-0022 · ADR-0029 |
| [ADR-0028-hosts-and-stage-models](adr/ADR-0028-hosts-and-stage-models.md) | accepted | executors | Executor hosts with system-managed groups; per-stage models frozen at dispatch | ADR-0026 · — |
| [ADR-0029-precedents](adr/ADR-0029-precedents.md) | accepted | memory | A model-free precedents core for the AI critic and the expert; the night encoder is temporary, on the fork server vectors on the fly | ADR-0027 · — |

## Where the statuses come from

ADR-0001…0018 were the bootstrap baseline. The CP-00 review (`W0-ARC-01`,
[CP00_ARCHITECTURE_REVIEW.md](CP00_ARCHITECTURE_REVIEW.md) and its JSON) recorded a disposition for each — `ratify` for
eleven, `adapt` for ADR-0004, 0007, 0008, 0012, 0013 and 0017, `defer` for ADR-0014 — and the owner decided `PD-01`…`PD-05`
([CP00_OWNER_DECISIONS.md](CP00_OWNER_DECISIONS.md)). CP-00 was ratified on 2026-09-07 on acceptance round ten (commit `39a3a643`, tag `v0.0.0-architecture`, `artifacts/checkpoints/CP-00/acceptance.md`); the review's JSON keeps `ratified: false` for the review artefact itself. Each ADR's Basis line names its disposition and an `adapt` ADR carries its qualification in its Decision. Ratification is not owner approval of a refactoring proposal (`E-05`, open, carried forward at ratification): for an ADR whose refactoring source ADR was `proposed` (CP-00 review §5: ADR-0002, ADR-0004, ADR-0011, ADR-0017), `accepted` means the ratified CP-00 baseline, not owner-approved production policy, except for parts a later owner ruling named in the ADR approves. Later ADRs rest on owner rulings:
ADR-0020 (owner, alpha), ADR-0021…0024 (`R-146`), ADR-0025 (`Q-CMP-1`…`Q-CMP-11`, `R-147`), ADR-0026 (`R-149`),
ADR-0027 (the autonomous window of 2026-11-09, revisable), ADR-0028 (`R-153a`…`R-153f`), ADR-0029 (`R-153q`…`R-153ar`, `R-157l`); the
fork decisions in ADR-0006, 0020, 0021, 0022 and 0029 rest on `R-156b`…`R-156l`, `R-156o`, `R-157i`, `R-157j`, `R-157k`, `R-158f` and `R-158h`.
