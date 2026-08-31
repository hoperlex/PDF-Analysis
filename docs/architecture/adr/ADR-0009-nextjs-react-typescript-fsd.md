# ADR-0009: Next.js/React/TypeScript strict with FSD vertical slices

- Status: accepted for bootstrap; ratify at CP-00

## Decision
Use Next.js App Router; thin `app/`; domain UI organized under `_pages`, widgets, features, entities, shared. API transport is generated from OpenAPI. Server state and UI state remain separate; no global domain mega-store. PDF viewer/live progress are bounded client islands.
