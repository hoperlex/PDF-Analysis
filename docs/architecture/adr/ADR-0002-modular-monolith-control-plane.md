# ADR-0002: Modular monolith control plane

- Status: accepted for bootstrap; ratify at CP-00
- Related principles: P-05

## Decision
The control plane is one deployable Python/FastAPI backend with hard bounded-context boundaries. Separate execution processes/workers are allowed because heavy analysis has a different resource/failure profile. Any additional service needs a dedicated ADR proving independent scaling, security, availability or release-cycle need.

## Boundary
Contexts interact through public application ports, contract events or approved read models, never internal ORM/repository imports.
