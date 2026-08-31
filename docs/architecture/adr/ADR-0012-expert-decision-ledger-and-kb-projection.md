# ADR-0012: Expert decisions are append-only; KB is a projection

- Status: accepted for bootstrap; ratify at CP-00

## Decision
Expert verdict change creates a new immutable decision event. Current verdict, reason aggregates, similar-case index and knowledge-base views are rebuildable projections. AI/reverification may create recommendations but cannot rewrite a human event.
