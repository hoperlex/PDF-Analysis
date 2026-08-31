# S07 — Advanced comparison: AI + graphic evidence

**Target checkpoint:** `CP-07 / v0.7.0-comparison-advanced`

## Goal

Добавить AI synthesis, high-level project changes, repair and graphic/vector evidence как derived layers поверх immutable core.

## Preconditions

- CP-06 accepted.
- Raw comparison evidence contracts stable.

## Contract gate

AI review artifact, project summary, repair proof/action/undo, graphic evidence/overlay coordinate contract.

Production implementation tasks consuming these boundaries start only after the wave contract owner records a frozen contract set.

## Wave plan

### W7.1 — derived contracts

Freeze source-checksum references and failure behavior.

### W7.2 — parallel AI/repair/graphic/UI

Independent lanes read CP-06 raw evidence.

### W7.3 — immutability/undo

Fault injection proves invalid AI cannot damage raw/user-owned state.

## Agent-ready task map

| Task | Lane | Deliverable | Depends on | Primary ownership | Non-goal / guardrail |
|---|---|---|---|---|---|
| W7-C-01 | CMP | Freeze derived comparison contracts | CP-06 | contracts/comparison | Derived artifacts reference raw checksum. |
| W7-AI-01 | AI | Text comparison reviewer/synthesis | W7-C-01 | comparison AI | Invalid response leaves raw usable. |
| W7-AI-02 | AI | Project change summary | W7-C-01 | comparison summary | Provenance to sheet/raw. |
| W7-CMP-01 | CMP | Repair proposal + proof/audit/undo | W7-C-01 | comparison repair | No silent overwrite. |
| W7-CMP-02 | CMP | Graphic/vector raw evidence G1 | W7-C-01 | comparison graphic | Deterministic recipe where possible. |
| W7-WEB-01 | WEB | AI/overlay/repair UI | W7-C-01 | web comparison | Raw vs AI clearly distinct. |
| W7-QA-01 | QA | Immutability/failure/undo/overlay tests | W7-C-01 | tests/** | AI failure cannot mutate source. |
| W7-INT-01 | INT | Advanced comparison checkpoint | all | evidence | Golden graphic pair. |

## Automated exit evidence

- [ ] AI artifact records source raw checksum and model provenance.
- [ ] Malformed/timeout AI leaves raw evidence unchanged/viewable.
- [ ] Repair has proof/event and undo restores prior state.
- [ ] Graphic overlay coordinates round-trip to page reference.

## Manual local acceptance

Full script: `../manual-tests/CP-07_comparison_advanced.md`.

- [ ] Generate AI review and inspect linked raw evidence.
- [ ] Force malformed output and verify raw diff remains.
- [ ] Accept repair and undo; inspect audit.
- [ ] Verify graphic overlay alignment on golden pair.
- [ ] Regenerate with changed profile: new derived revision, not overwrite.

## Checkpoint exit criterion

Advanced intelligence improves comparison without becoming authority for raw evidence or approved mappings.

## Integration report must record

- frozen contract versions and commit;
- migration head and dependency lock hashes;
- merged task IDs;
- automated commands/results;
- manual report reference;
- known limitations/risks;
- rollback/recovery note;
- next stage unlocked tasks.
