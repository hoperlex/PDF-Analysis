# ADR-0004: Repository layout and module boundaries

- Status: accepted for bootstrap; ratify at CP-00

## Decision
Use `src/auditmanager/<bounded-context>` for backend, `web/src/{app,_app,_pages,widgets,features,entities,shared}` for frontend, top-level `contracts/`, `db/`, `infra/`, `tests/`, `fixtures/`, `docs/`. Architecture lint/test must prevent deep cross-context imports and FSD upward/cross-slice imports.

Empty folders are not architecture: sublayers appear only when a real use case needs them.
