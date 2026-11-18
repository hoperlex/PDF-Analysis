# ADR-0014: Object authorization and classification/retention policy

- Status: proposed
- Date: 2026-08-31; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: CP-00 (W0-ARC-01) disposition: defer (`docs/architecture/CP00_ARCHITECTURE_REVIEW.md` §5; input `U-04` open by explicit owner disposition); partially accepted by `R-146` (2026-10-26; `R-146c`, `R-146d`; `docs/program/OWNER_RULINGS_2026-09-17.md` §3.46; recorded by `PRODUCTION-ADR-PACK-01`); legal-hold authority settled by `R-146aj` and classification labels left open by `R-146ak` (same section)
- Amends: — · Amended by: `ADR-0022`, `ADR-0023` (the parts `R-146` decided)

## Context
The source ADR is `proposed` with a retention matrix whose values are all unfilled; the legacy evidence does not exercise an exact runtime policy (`WS-01`), has an explicit insecure-admin mode (`DW-01`) and establishes no retention/immutability guarantee (`LO-01`) (CP-00 review §5). CP-00 kept `U-04` open with deadlines: tenant/IdP boundary before `W2-C-01`, TTL/legal hold before `W9-C-01`.

## Decision
**Direction.** Authorization is server-side per object and fail-closed. Data/artifacts are classified; retention/erasure/legal-hold operations are explicit state transitions/jobs with audit evidence.

**Required inputs.** Exact TTL/legal retention, tenant model, identity provider and legal-hold authority are not supported by supplied sources and must be approved before the CP-09 production gate. No arbitrary TTL is baked into code before that decision; this rule is unchanged by `R-146`.

**Accepted by `R-146` (2026-10-26).** All four inputs are decided for 1.0, the first three by `R-146` and the legal-hold authority by `R-146aj`:
- **Tenant model = single organisation** (`R-146d`). Every active expert sees every project; there is no tenant or organisation column and none is added for 1.0. Multi-tenancy is excluded, with the reopen conditions in `ADR-0023`.
- **Identity provider = none; local accounts** with administrator approval (`R-146d`). MFA and an external identity provider are excluded from 1.0. `ADR-0023` states the audited access changes and the default-credential rule (`R-146i`).
- **Retention TTL = none; operator erase** (`R-146c`). No automatic retention limit is declared for client data; an operator erases one project through a journalled operation. `ADR-0022` defines the operation, what it removes and keeps, and its interaction with the append-only ledgers.
- **Legal-hold authority = none in the product; a rule of procedure** (`R-146aj`, a later round of the same poll). The product has no legal-hold mechanism in 1.0: the owner's word is the only ground on which the operator erases a project on which a hold is claimed, and a project erase is never run without the owner's permission (`ADR-0022` decisions 2 and 3). `R-146aj` closes the legal-hold half of this ADR's open items.

**Open:** data classification labels. They were not asked in `R-146`; `R-146ak` introduces none and fixes none in 1.0 and leaves the question open after the release. `U-04` is settled for 1.0 (the legal-hold authority by `R-146aj`); `OPEN-RETENTION` in `contracts/domain/v1/identifiers.json` is not edited. The CP-09 requirement is met for the four named inputs (TTL, tenant model, identity provider, legal-hold authority); whether the open classification labels are a precondition of the production gate is not decided by `R-146` or `R-146ak`.

## Consequences
- Positive: tenant model, identity provider, retention TTL and the legal-hold authority are decided for 1.0 (no automatic retention limit; no product hold mechanism).
- Cost: the classification labels stay open (`R-146ak`).

## Revisit trigger
None recorded beyond closing the open point (the classification labels) by an owner decision; the multi-tenancy reopen conditions are in `ADR-0023`; a hold mechanism in the product reopens `R-146aj` (`ADR-0022` revisit trigger).

## History
- 2026-08-31 — bootstrap baseline, status `proposed`.
- 2026-09-01 — CP-00 disposition recorded: defer (W0-ARC-01); `U-04` open, status unchanged.
- 2026-10-26 — addendum `R-146` (`R-146c`, `R-146d`; `PRODUCTION-ADR-PACK-01`): partially accepted, folded into Decision; the addendum changed no runtime behaviour.
- 2026-11-18 — unified to the template (`ADR-OPTIMISE-01`); addendum folded in; meaning unchanged.
- 2026-11-18 — status statements updated to dev fb6c2203e: the legal-hold authority is settled by `R-146aj` as a rule of procedure (no product mechanism in 1.0); the classification labels stay open by `R-146ak`.
