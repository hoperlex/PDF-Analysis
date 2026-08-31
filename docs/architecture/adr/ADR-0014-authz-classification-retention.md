# ADR-0014: Object authorization and classification/retention policy

- Status: proposed

## Decision direction
Authorization is server-side per object and fail-closed. Data/artifacts are classified; retention/erasure/legal-hold operations are explicit state transitions/jobs with audit evidence.

## Unresolved owner decisions
Exact TTL/legal retention, tenant model, identity provider and legal-hold authority are not supported by supplied sources and must be approved before CP-09 production gate. No arbitrary TTL is baked into code before that decision.
