# ADR-0014: Object authorization and classification/retention policy

- Status: proposed
- Date: 2026-08-31; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: CP-00 (W0-ARC-01) disposition: defer (`docs/architecture/CP00_ARCHITECTURE_REVIEW.md` §5; input `U-04` open by explicit owner disposition); partially accepted by `R-146` (2026-10-26; `R-146c`, `R-146d`; `docs/program/OWNER_RULINGS_2026-09-17.md` §3.46; recorded by `PRODUCTION-ADR-PACK-01`)
- Amends: — · Amended by: — (the accepted parts are detailed in `ADR-0022` and `ADR-0023`)

## Context
The source ADR is `proposed` with a retention matrix whose values are all unfilled; the legacy evidence does not exercise an exact runtime policy (`WS-01`), has an explicit insecure-admin mode (`DW-01`) and establishes no retention/immutability guarantee (`LO-01`) (CP-00 review §5). CP-00 kept `U-04` open with deadlines: tenant/IdP boundary before `W2-C-01`, TTL/legal hold before `W9-C-01`.

## Decision
**Direction.** Authorization is server-side per object and fail-closed. Data/artifacts are classified; retention/erasure/legal-hold operations are explicit state transitions/jobs with audit evidence.

**Required inputs.** Exact TTL/legal retention, tenant model, identity provider and legal-hold authority are not supported by supplied sources and must be approved before the CP-09 production gate. No arbitrary TTL is baked into code before that decision; this rule is unchanged by `R-146`.

**Accepted by `R-146` (2026-10-26).** Three of the four inputs are decided for 1.0:
- **Tenant model = single organisation** (`R-146d`). Every active expert sees every project; there is no tenant or organisation column and none is added for 1.0. Multi-tenancy is excluded, with the reopen conditions in `ADR-0023`.
- **Identity provider = none; local accounts** with administrator approval (`R-146d`). MFA and an external identity provider are excluded from 1.0. `ADR-0023` states the audited access changes and the default-credential rule (`R-146i`).
- **Retention TTL = none; operator erase** (`R-146c`). No automatic retention limit is declared for client data; an operator erases one project through a journalled operation. `ADR-0022` defines the operation, what it removes and keeps, and its interaction with the append-only ledgers.

**Open:** legal-hold authority and data classification labels. They were not asked in `R-146` and remain unresolved. `U-04` is therefore settled for 1.0 except the legal-hold authority (`R-146d`); `OPEN-RETENTION` in `contracts/domain/v1/identifiers.json` is not edited. The CP-09 requirement is met for three of the four named inputs (TTL, tenant model, identity provider); whether the open legal-hold authority is a precondition of the production gate is not decided by `R-146`.

## Consequences
- Positive: tenant model, identity provider and retention TTL are decided for 1.0 and no automatic retention limit is declared.
- Cost: the legal-hold authority and the classification labels stay open.

## Revisit trigger
None recorded beyond closing the open points by an owner decision; the multi-tenancy reopen conditions are in `ADR-0023`.

## History
- 2026-08-31 — bootstrap baseline, status `proposed`.
- 2026-09-01 — CP-00 disposition recorded: defer (W0-ARC-01); `U-04` open, status unchanged.
- 2026-10-26 — addendum `R-146` (`R-146c`, `R-146d`; `PRODUCTION-ADR-PACK-01`): partially accepted, folded into Decision; the addendum changed no runtime behaviour.
- 2026-11-18 — unified to the template (`ADR-OPTIMISE-01`); addendum folded in; meaning unchanged.
