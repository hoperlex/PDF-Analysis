# S05 — Expert decisions and knowledge

**Target checkpoint:** `CP-05 / v0.5.0-expert`

## Goal

Сделать human review first-class: immutable decision ledger, discussions, KB projection, evidence verifier and AI suggestions that never overwrite expert history.

## Preconditions

- CP-04 accepted.
- Stable finding identity proven.

## Contract gate

Decision event/reason codes, current-verdict projection, discussions, KB rebuild, verifier/re-review recommendation contracts.

Production implementation tasks consuming these boundaries start only after the wave contract owner records a frozen contract set.

## Wave plan

### W5.1 — decision contract

Freeze append-only semantics and authorization.

### W5.2 — parallel ledger/projection/verifier/UI

DEC/AI/WEB/QA implement isolated consumers.

### W5.3 — rebuild/identity acceptance

Rebuild KB/current verdict and rerun audit to prove history carryover.

## Agent-ready task map

| Task | Lane | Deliverable | Depends on | Primary ownership | Non-goal / guardrail |
|---|---|---|---|---|---|
| W5-C-01 | DEC | Freeze decision/KB contracts | CP-04 | domain/events/api | Human event immutable. |
| W5-DEC-01 | DEC | Decision ledger + current projection | W5-C-01 | decisions/** | New verdict = new event. |
| W5-DEC-02 | DEC | Discussion/comment events | W5-C-01 | decisions | Actor/auth required. |
| W5-DEC-03 | DEC | KB projection + rebuild | W5-C-01 | knowledge | Projection disposable. |
| W5-AI-01 | AI | Evidence verifier recommendation | W5-C-01 | review port | Does not mutate decision. |
| W5-AI-02 | AI | Rejected-finding re-review recommendation | W5-C-01 | review port | Recommendation provenance. |
| W5-WEB-01 | WEB | Review/reason/discussion/KB UI | W5-C-01 | web | Permission/error states. |
| W5-QA-01 | QA | Ledger/rebuild/rerun/AuthZ tests | W5-C-01 | tests/** | AI cannot change human verdict. |
| W5-INT-01 | INT | Expert checkpoint | all | evidence | Manual review route. |

## Automated exit evidence

- [ ] Verdict update appends event and preserves previous row.
- [ ] Projection rebuild yields same semantic current verdict/KB.
- [ ] Rerun links decisions only via stable identity.
- [ ] Unauthorized review denied server-side.
- [ ] AI recommendation failure does not alter verdict.

## Manual local acceptance

Full script: `../manual-tests/CP-05_expert.md`.

- [ ] Accept then reject a finding with reason and inspect history.
- [ ] Rebuild KB projection and compare current UI.
- [ ] Rerun audit and inspect stable-finding history.
- [ ] Run verifier/re-review; confirm recommendation-only UI.
- [ ] Attempt unauthorized review and confirm fail-closed.

## Checkpoint exit criterion

Expert knowledge is durable/auditable and independent of transient run numbering or AI suggestions.

## Integration report must record

- frozen contract versions and commit;
- migration head and dependency lock hashes;
- merged task IDs;
- automated commands/results;
- manual report reference;
- known limitations/risks;
- rollback/recovery note;
- next stage unlocked tasks.
