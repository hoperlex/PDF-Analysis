# ADR-0014: Object authorization and classification/retention policy

- Status: proposed; partially accepted by R-146 (2026-10-26): tenant model, identity provider and retention TTL are decided for 1.0; the legal-hold authority and classification labels stay open (see the addendum)

## Decision direction
Authorization is server-side per object and fail-closed. Data/artifacts are classified; retention/erasure/legal-hold operations are explicit state transitions/jobs with audit evidence.

## Unresolved owner decisions
Exact TTL/legal retention, tenant model, identity provider and legal-hold authority are not supported by supplied sources and must be approved before CP-09 production gate. No arbitrary TTL is baked into code before that decision.

## Addendum — partially accepted by R-146 (2026-10-26)

Recorded by `PRODUCTION-ADR-PACK-01` under owner ruling `R-146` (`OWNER_RULINGS_2026-09-17.md` section 3.46,
`R-146c`, `R-146d`). The text above stays as written. This addendum changes no runtime behaviour.

- **Tenant model = single organisation** (`R-146d`). Every active expert sees every project; there is no tenant or
  organisation column and none is added for 1.0. Multi-tenancy is excluded, with the reopen conditions in `ADR-0023`.
- **Identity provider = none; local accounts** with administrator approval (`R-146d`). MFA and an external identity
  provider are excluded from 1.0. `ADR-0023` states the audited access changes and the default-credential rule (`R-146i`).
- **Retention TTL = none; operator erase** (`R-146c`). No automatic retention limit is declared for client data; an
  operator erases one project through a journalled operation. `ADR-0022` defines the operation, what it removes and keeps,
  and its interaction with the append-only ledgers. The "No arbitrary TTL is baked into code" rule above is unchanged.
- **Open: legal-hold authority and data classification labels.** They were not asked in `R-146` and remain unresolved.
  `U-04` is therefore settled for 1.0 except the legal-hold authority (`R-146d`); `OPEN-RETENTION` in
  `contracts/domain/v1/identifiers.json` is not edited by this addendum.
- The sentence "must be approved before CP-09 production gate" is met for three of the four named inputs (TTL, tenant
  model, identity provider). The fourth, the legal-hold authority, was not asked and is open; whether it is a precondition
  of the production gate is not decided by `R-146`.
