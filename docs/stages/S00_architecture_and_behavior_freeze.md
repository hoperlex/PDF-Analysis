# S00 — Architecture and behavior freeze

**Target checkpoint:** `CP-00 / v0.0.0-architecture`

## Goal

Превратить working legacy и архитектурные идеи в утверждённый greenfield product/domain contract, не начиная production implementation.

## Preconditions

- Доступны legacy source/docs только для чтения.
- Доступны исходные refactoring ADR/Bible.
- Назначен program integrator/architecture owner.

## Contract gate

Domain glossary, identifier catalog, state-machine catalog, error envelope, Analysis package draft v1, capability/golden baseline.

Production implementation tasks consuming these boundaries start only after the wave contract owner records a frozen contract set.

## Wave plan

### W0.1 — behavioral inventory

Параллельно BHV/QA анализируют user journeys, input/output artifacts, failure cases; ARC не меняет contracts до сводного inventory.

### W0.2 — architecture/domain contract

Один DOM/ARC owner формирует machine contract drafts и decision list; QA пишет consumer-style schema tests/examples.

### W0.3 — ratification/integration

Integrator reconciles Bible/ADR/domain contracts, records unresolved owner decisions and executes CP-00 manual review.

## Agent-ready task map

| Task | Lane | Deliverable | Depends on | Primary ownership | Non-goal / guardrail |
|---|---|---|---|---|---|
| W0-BHV-01 | BHV | Capability inventory legacy | — | docs/PRODUCT_SYNOPSIS.md, legacy notes | Только behavior/evidence. |
| W0-BHV-02 | BHV | Golden journeys + edge-case matrix | W0-BHV-01 | fixtures/golden plan | Synthetic/anonymized only. |
| W0-ARC-01 | ARC | Ratify/adapt Bible and ADR set | W0-BHV-01 | docs/architecture/** | No hidden Strangler dependency. |
| W0-DOM-01 | DOM | Freeze IDs/state/errors v1 draft | W0-BHV-01 | contracts/domain/v1/** | Finding/observation and Run/Job/Attempt separate. |
| W0-ANA-01 | ENG | Inventory stage I/O and package draft | W0-BHV-01 | contracts/analysis/v1/** | Single stage registry concept. |
| W0-QA-01 | QA | Contract examples/schema checks + golden test plan | W0-DOM-01,W0-ANA-01 | tests docs | Independent consumer view. |
| W0-INT-01 | INT | CP-00 integration/decision report/tag | all W0 tasks | checkpoint evidence | No production domain implementation. |

## Automated exit evidence

- [ ] All JSON schemas/examples parse.
- [ ] Internal documentation links resolve.
- [ ] Domain prefixes/states/errors have no duplicate meaning.
- [ ] Architecture lint rules are specified even if implementation waits for CP-01.

## Manual local acceptance

Full script: `../manual-tests/CP-00_architecture.md`.

- [ ] Review 3–5 golden journeys against legacy with domain owner.
- [ ] Walk one legacy finding through rerun identity and expert-decision mapping.
- [ ] Walk one comparison pair and prove approved link/raw evidence ownership rules.
- [ ] Review unresolved decisions; none may be silently defaulted if legal/security/product-owned.

## Checkpoint exit criterion

Architecture, vocabulary and first machine contracts are sufficiently frozen to let independent agents start without inventing identities/state semantics.

## Integration report must record

- frozen contract versions and commit;
- migration head and dependency lock hashes;
- merged task IDs;
- automated commands/results;
- manual report reference;
- known limitations/risks;
- rollback/recovery note;
- next stage unlocked tasks.
