# Documentation index

## Product
- [Product synopsis](PRODUCT_SYNOPSIS.md)
- [Legacy behavior baseline](LEGACY_BEHAVIOR_BASELINE.md)
- [Legacy technical inventory](LEGACY_TECHNICAL_INVENTORY.md)
- [Source traceability](SOURCE_TRACEABILITY.md)

## Architecture
- [Architecture Bible](architecture/ARCHITECTURE_BIBLE.md)
- [System architecture](architecture/SYSTEM_ARCHITECTURE.md)
- [Repository layout](architecture/REPOSITORY_LAYOUT.md)
- [Technology baseline](architecture/TECHNOLOGY_BASELINE.md)
- [Domain glossary](architecture/GLOSSARY.md)
- [Domain model](architecture/DOMAIN_MODEL.md)
- [Contract catalog](architecture/CONTRACT_CATALOG.md)
- [ADR index](architecture/ADR_INDEX.md)
- [ADR-0019 decision-to-code navigation](architecture/adr/ADR-0019-decision-code-navigation.md) — proposed prototype extension

## Program
- [Roadmap](program/ROADMAP.md)
- [Prototype profile](program/PROTOTYPE_PROFILE.md) — scope, reuse and gate policy
- [FF-01 PostgreSQL/S3 Foundation Freeze](program/PROTOTYPE_FOUNDATION_FREEZE.md) — accepted 2026-09-09
- [Task P0-FND-00](program/tasks/P0-FND-00.md) — accepted and complete
- [Task P0-PLN-01](program/tasks/P0-PLN-01.md) — dispatchable detailed plan, parallel with P01
- [Task P0-NAV-00](program/tasks/P0-NAV-00.md) — AI-agent decision-to-code navigation architecture
- [Prototype execution plan P02–P05](program/PROTOTYPE_EXECUTION_PLAN.md) — candidate graph, ownership, estimates and owner decisions
- [Task P1-NAV-01](program/tasks/P1-NAV-01.md) — navigation layer implementation, pre-P02 gate
- [Task P2-INT-00](program/tasks/P2-INT-00.md) — P02 pins, composition root and wave ownership
- [Task P2-DOM-01](program/tasks/P2-DOM-01.md) — P02 migration head and domain primitives
- [Task P2-BHV-01](program/tasks/P2-BHV-01.md) — synthetic AR corpus and seeded-issue oracle
- [Task P2-META-01](program/tasks/P2-META-01.md) — ingest, immutable version and blob registration
- [Task P2-JOB-01](program/tasks/P2-JOB-01.md) — run, job, attempt and the local orchestrator
- [Task P2-ENG-01](program/tasks/P2-ENG-01.md) — stage engine and deterministic preparation stages
- [Task P2-AI-01](program/tasks/P2-AI-01.md) — text_analysis, prompt bundle and provider adapters
- [Task P2-FND-01](program/tasks/P2-FND-01.md) — evidence gate, findings and decision ledger
- [Task P2-API-01](program/tasks/P2-API-01.md) — frozen OpenAPI v1 surface
- [Task P2-QA-01](program/tasks/P2-QA-01.md) — independent P02 journey and restart evidence
- [Task P3-WEB-00](program/tasks/P3-WEB-00.md) — frontend toolchain, composition root and UI seam
- [Task P3-API-01](program/tasks/P3-API-01.md) — generated OpenAPI client and transport seam
- [Task P3-WEB-01](program/tasks/P3-WEB-01.md) — project, upload and run-progress slice
- [Task P3-WEB-02](program/tasks/P3-WEB-02.md) — finding list and page-beside-quotation review
- [Task P3-WEB-03](program/tasks/P3-WEB-03.md) — append-only expert decision UI
- [Task P3-WEB-04](program/tasks/P3-WEB-04.md) — CSV export and column verification
- [Task P3-QA-01](program/tasks/P3-QA-01.md) — automated PC-01 journey and restart evidence
- [Task P3-INT-01](program/tasks/P3-INT-01.md) — PC-01 acceptance runbook and checkpoint
- [Task P4-QA-01](program/tasks/P4-QA-01.md) — PC-02 validation corpus and session protocol
- [Task P4-OPS-01](program/tasks/P4-OPS-01.md) — PC-02 measurement ledger
- [Task P4-BHV-01](program/tasks/P4-BHV-01.md) — moderated expert validation sessions
- [Task P4-INT-01](program/tasks/P4-INT-01.md) — PC-02 validation report and acceptance
- [Task P5-ARC-01](program/tasks/P5-ARC-01.md) — evidence-to-candidate architecture disposition
- [Task P5-META-01](program/tasks/P5-META-01.md) — beta/v1 roadmap and recalibrated forecast
- [Task P5-INT-01](program/tasks/P5-INT-01.md) — PC-03 acceptance and backlog disposition
- [Task P1-INT-00](program/tasks/P1-INT-00.md) — dispatchable toolchain and command pins
- [Task P1-INF-01](program/tasks/P1-INF-01.md) — local PostgreSQL and MinIO
- [Task P1-DB-01](program/tasks/P1-DB-01.md) — migration/session foundation
- [Task P1-STO-01](program/tasks/P1-STO-01.md) — checksum-verified BlobStore
- [Task P1-QA-00](program/tasks/P1-QA-00.md) — convergence foundation QA
- [Task P1-INT-01](program/tasks/P1-INT-01.md) — PF-01 acceptance
- [Wave execution guide](program/WAVE_EXECUTION_GUIDE.md)
- [Accepted wave W0.1](program/waves/W0.1_behavioral_inventory.md)
- [Accepted wave W0.2](program/waves/W0.2_architecture_domain_contract.md)
- [Active wave W0.3](program/waves/W0.3_ratification_integration.md)
- [Task W0-BHV-01](program/tasks/W0-BHV-01.md)
- [Task W0-QA-00](program/tasks/W0-QA-00.md)
- [Task W0-DEP-01](program/tasks/W0-DEP-01.md)
- [Task W0-EVD-01](program/tasks/W0-EVD-01.md)
- [Task W0-QA-02](program/tasks/W0-QA-02.md)
- [Task W0-INT-00](program/tasks/W0-INT-00.md)
- [Task W0-BHV-02](program/tasks/W0-BHV-02.md)
- [Task W0-ARC-01](program/tasks/W0-ARC-01.md)
- [Task W0-DOM-01](program/tasks/W0-DOM-01.md)
- [Task W0-ANA-01](program/tasks/W0-ANA-01.md)
- [Task W0-ARC-02](program/tasks/W0-ARC-02.md) — accepted and integrated
- [Task W0-QA-03](program/tasks/W0-QA-03.md) — accepted and integrated
- [Task W0-DOM-02](program/tasks/W0-DOM-02.md) — accepted and integrated
- [Task W0-EVT-01](program/tasks/W0-EVT-01.md) — accepted and integrated
- [Task W0-CLN-01](program/tasks/W0-CLN-01.md) — accepted and integrated
- [Task W0-QA-01](program/tasks/W0-QA-01.md) — accepted and integrated
- [Task W0-INT-01](program/tasks/W0-INT-01.md) — accepted and integrated; CP-00 ratified and tagged `v0.0.0-architecture`, and superseded by the recovery: acceptance round eleven is owed and `W0-INT-03` cuts `v0.0.1-architecture`
- [Task W0-QA-04](program/tasks/W0-QA-04.md) — accepted and integrated; the CP-00 final-state contour
- [Task W0-INT-02](program/tasks/W0-INT-02.md) — CP-00 state reconciliation and evidence erratum
- [Task W0-INT-03](program/tasks/W0-INT-03.md) — superseding ratification and `v0.0.1-architecture`
- [CP-00 recovery execution plan](program/EXECUTION_PLAN.md)
- [Checkpoint registry](program/CHECKPOINT_REGISTRY.md)
- [Version/freeze policy](program/VERSIONING_AND_FREEZE_POLICY.md)
- [Integration policy](program/INTEGRATION_POLICY.md)
- [Current state](program/CURRENT_STATE.md)

## Stage plans
See [stage plan index](stages/README.md) — S00 through S10.

## Checkpoint evidence
See `artifacts/checkpoints/` — one directory per checkpoint; CP-00 holds its manifest and acceptance records. Read `artifacts/checkpoints/CP-00/erratum.md` beside them: it carries every claim in the CP-00 bundle that was found false or unsupported, with the quote, the location, what is true and how it was measured.

## Manual acceptance
See `docs/manual-tests/` — one runbook per checkpoint.

## Templates
See `docs/templates/`.
