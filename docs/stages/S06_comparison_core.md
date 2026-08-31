# S06 — Deterministic comparison core

**Target checkpoint:** `CP-06 / v0.6.0-comparison-core`

## Goal

Построить сравнение версий/стадий поверх зрелых Version/Storage primitives: sheet matching suggestions, approved links, deterministic exclusions/text diff and efficient viewer.

## Preconditions

- CP-03 minimum; CP-04 accepted for integration.
- Two versions with page representations available.

## Contract gate

Comparison identity/revision, sheet descriptor, suggestion set, approved SheetLink, exclusion artifact, raw text diff, preview/tile read contract.

Production implementation tasks consuming these boundaries start only after the wave contract owner records a frozen contract set.

## Wave plan

### W6.1 — comparison contract

Freeze authoritative vs rebuildable state before algorithms.

### W6.2 — parallel matcher/diff/viewer/storage

CMP/STO/WEB/QA consume frozen contracts.

### W6.3 — ownership acceptance

Recompute repeatedly and prove approved link/raw evidence invariants.

## Agent-ready task map

| Task | Lane | Deliverable | Depends on | Primary ownership | Non-goal / guardrail |
|---|---|---|---|---|---|
| W6-C-01 | CMP | Freeze comparison/sheet/evidence contracts | CP-04 | contracts/comparison/api | Approved link is not suggestion. |
| W6-CMP-01 | CMP | Sheet descriptors + suggestion projection | W6-C-01 | comparison matcher | Rebuildable. |
| W6-CMP-02 | CMP | Approved link/unlinked state + revision/audit | W6-C-01 | comparison state | Recompute cannot overwrite. |
| W6-CMP-03 | CMP | Deterministic exclusion + raw text diff | W6-C-01 | comparison deterministic stages | Source signatures/checksums. |
| W6-STO-01 | STO | Page preview/tile/range representations | W6-C-01 | storage read adapter | No internal S3 key in client. |
| W6-WEB-01 | WEB | Pair/mapping/diff viewer | W6-C-01 | web comparison | Manual mapping/empty/error. |
| W6-QA-01 | QA | Ownership/determinism/viewer tests | W6-C-01 | tests/** | Same inputs → same raw checksum. |
| W6-INT-01 | INT | Comparison core checkpoint | all | evidence | Golden pair. |

## Automated exit evidence

- [ ] Suggestion recompute does not change approved SheetLink.
- [ ] Same source/config produces same exclusion/raw diff checksum.
- [ ] Changed source invalidates/rebuilds derived artifact explicitly.
- [ ] Viewer API does not leak internal object key.

## Manual local acceptance

Full script: `../manual-tests/CP-06_comparison_core.md`.

- [ ] Create comparison pair and inspect suggestions.
- [ ] Approve/alter one sheet link; recompute and confirm it remains.
- [ ] Mark one sheet unlinked; recompute and verify ownership.
- [ ] Run deterministic text diff twice and compare checksum.
- [ ] Open previews/diff without bucket URL.

## Checkpoint exit criterion

Comparison has a trustworthy deterministic core and explicit user-owned mapping state.

## Integration report must record

- frozen contract versions and commit;
- migration head and dependency lock hashes;
- merged task IDs;
- automated commands/results;
- manual report reference;
- known limitations/risks;
- rollback/recovery note;
- next stage unlocked tasks.
