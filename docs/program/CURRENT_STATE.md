# Current state

**Program state:** CP-00 discovery wave W0.1 accepted; W0.2 evidence/contract tasks opened. Production implementation remains locked.

## Active checkpoint

Target: `CP-00 / v0.0.0-architecture`.

## Active wave

`W0.2 — golden baseline and architecture/domain contracts`.

Completed inputs:

- `W0-QA-00` — fail-closed bootstrap validator, commit
  `c25ff4a5393595260384aaffea1fddc2382189e8`;
- `W0-BHV-01` — accepted legacy capability inventory, commit
  `667fb00fe3e45d1ce0bce7860725c1654b4cdeba`;
- canonical behavioral oracle — `32b9d903792b30506048a1d42b0e6b2d07aee403`;
- refactoring architecture source — `0b937dc0e24d38fb98485a920152b83d2f19c982`.

Open task contracts:

- `W0-BHV-02` — golden journeys and edge-case matrix;
- `W0-ARC-01` — architecture/ADR reconciliation and owner decisions;
- `W0-DOM-01` — domain identifiers/states/errors draft.1;
- `W0-ANA-01` — target stage registry and analysis packages draft.1.

See `docs/program/waves/W0.2_architecture_domain_contract.md`.

## Allowed work before CP-00

- read-only legacy inventory;
- domain glossary/capability inventory;
- synthetic/anonymized fixture extraction;
- contract drafts/examples;
- Architecture Bible/ADR review;
- spikes that do not create irreversible production dependency.

## Prohibited before CP-00

- domain production implementation based on unresolved identity/state contracts;
- importing legacy services as new architecture;
- selecting irreversible vendor/retention/security policy without owner decision.

## Next integration tasks

Execute the four open W0.2 task contracts against the accepted `W0-BHV-01` base.
Do not record a contract freeze until architecture reconciliation, explicit owner
decisions and independent consumer checks agree.
