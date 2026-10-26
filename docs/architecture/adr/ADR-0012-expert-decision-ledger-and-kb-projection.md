# ADR-0012: Expert decisions are append-only; KB is a projection

- Status: accepted for bootstrap; ratify at CP-00

## Decision
Expert verdict change creates a new immutable decision event. Current verdict, reason aggregates, similar-case index and knowledge-base views are rebuildable projections. AI/reverification may create recommendations but cannot rewrite a human event.

## Addendum — amended by R-146o for the operator project erase only (2026-10-26)

Recorded by `PRODUCTION-ADR-PACK-01` under owner ruling `R-146o` (`OWNER_RULINGS_2026-09-17.md` section 3.46). The text above
stays as written and stays true for every path of the product: a verdict change creates a new immutable event, and no API
operation, screen or job deletes or rewrites an expert decision event.

- **The exception.** The operator project erase (`ADR-0022` section 3, item `PROD-07` of `PRODUCTION-READINESS-PLAN-01.md`)
  removes every row of one project, among them its `expert_decision_event` rows, its findings, its evidence quotes and its comments. It is a deliberate
  exception, granted by `R-146o` for that one operation. It is not an API operation and not a verdict change; it runs only as the
  table owner through a script that switches the append-only trigger off inside one transaction and on again before it commits.
  What stays is the record of the erasure (the `erasure.requested` and `erasure.completed` events and a manifest of the erased
  Blobs), not the decisions.
- **The frozen domain contract.** `contracts/domain/v1/state-machines.json` (line 167) says that erasing a Blob's bytes never deletes decision, finding
  or audit history. That sentence is named here as the exception's counterpart and is not edited: it stays true of the Blob `erased`
  transition, which the project erase does not use. A clarifying edit of the frozen text is a contract-owner item (`PROD-22`).
- Nothing exists yet: the tool is not written. This addendum changes no runtime behaviour.
