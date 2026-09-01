# S00 — Architecture and behavior freeze

**Target checkpoint:** `CP-00 / v0.0.0-architecture`

## Goal

Превратить working legacy и архитектурные идеи в утверждённый greenfield product/domain contract, не начиная production implementation.

## Preconditions

- Доступен только для чтения канонический legacy snapshot, зафиксированный в `docs/SOURCE_TRACEABILITY.md`.
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
| W0-QA-00 | QA | Fail-closed bootstrap validator + focused tests | — | scripts/validator, focused contract test | Не меняет contracts/dependencies. |
| W0-DEP-01 | BUILD | Hash-locked validation dependency set | W0-QA-00 | validation-only requirements lock | Не выбирает application package manager. |
| W0-EVD-01 | BHV | Exact immutable evidence anchors | W0-BHV-01 | accepted inventory locators | Не меняет capability semantics. |
| W0-QA-02 | QA | Git-aware validator + real-schema regressions | W0-QA-00,W0-DEP-01 | validator/test paths | Не меняет machine contracts. |
| W0-INT-00 | INT | Clear W0.2 preflight blockers | W0-BHV-01,W0-DEP-01,W0-EVD-01,W0-QA-02 | W0.2 task/wave program docs | No machine contract/checkpoint change. |
| W0-BHV-02 | BHV | Golden journeys + edge-case matrix | W0-BHV-01,W0-DEP-01,W0-EVD-01,W0-QA-02 | fixtures/golden plan | Synthetic/anonymized only. |
| W0-ARC-01 | ARC | Ratify/adapt Bible and extensible ADR set | W0-BHV-01,W0-DEP-01,W0-EVD-01,W0-QA-02 | docs/architecture/** | No hidden Strangler dependency. |
| W0-DOM-01 | DOM | Freeze schema-backed IDs/state/errors v1 draft | W0-BHV-01,W0-DEP-01,W0-QA-02 | contracts/domain/v1/** | Finding/observation and Run/Job/Attempt separate. |
| W0-ANA-01 | ENG | Inventory stage I/O and package draft | W0-BHV-01,W0-DEP-01,W0-EVD-01,W0-QA-02 | contracts/analysis/v1/** | Single stage registry concept. |
| W0-QA-01 | QA | Contract examples/schema checks + golden test plan | W0-BHV-02,W0-ARC-01,W0-DOM-01,W0-ANA-01 | tests docs | Independent consumer view. |
| W0-INT-01 | INT | CP-00 integration/decision report/tag | all required W0 tasks | checkpoint evidence | No production domain implementation. |

### Backlog drafts — not executable until their dependencies are integrated

`AGENTS.md` §2 allows `depends_on` to name completed task IDs only. Each row below
carries a `backlog draft` banner and a `<pending integration commit>` placeholder; it
becomes executable when its dependency is integrated at a recorded commit, not before.

| Task | Lane | Result | Depends on | Blocked because |
|---|---|---|---|---|
| W0-ARC-02 | ARC | Architecture lint rule specification (`U-03`) | W0-ARC-01 | W0-ARC-01 accepted as candidate, not integrated. |
| W0-QA-03 | QA | Validator reads `contract_version` (`ID-01`) | W0-QA-02, W0-ARC-01 | `ID-01` exists only in uncommitted architecture artifacts. |
| W0-DOM-02 | DOM | Remove deprecated domain `version` mirror (`ID-01`) | W0-QA-03, W0-DOM-01 | Validator still hard-requires the bare key. |
| W0-EVT-01 | EVT | Event envelope on `contract_version` (`ID-01`) | W0-DOM-02, W0-QA-03, W0-DOM-01, W0-ANA-01 | Last in the `ID-01` chain; its sweep cannot pass earlier. |

`ID-01` completes only in that order: `W0-QA-03` → `W0-DOM-02` → `W0-EVT-01`.

### Planned outside W0

| Task | Lane | Result | Scheduled | Note |
|---|---|---|---|---|
| W5-OPT-01 | OPT | Project Optimization bounded context, `contracts/optimization/v1/**` | After core audit and decision-contract freeze | Owner decision on `U-06`. Separate OPT contract owner, not ANA or DOM. The capability is disabled until this task is accepted, and CP-00 explicitly excludes its runtime semantics. |

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
