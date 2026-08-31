# ADR-0016: Testing is an evidence model, not a test pyramid quota

- Status: accepted for bootstrap; ratify at CP-00

## Decision
Use characterization/golden, domain, contract, integration with real PostgreSQL/S3, migration, E2E, replay/live-quality, restore/rollback and manual checkpoint evidence. No layer has an arbitrary coverage percentage as sole release proof.
