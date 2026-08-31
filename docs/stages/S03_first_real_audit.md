# S03 — First real audit vertical slice

**Target checkpoint:** `CP-03 / v0.3.0-audit-alpha`

## Goal

Заменить fake engine минимальным реальным analysis path, создающим evidence-backed finding с воспроизводимой AI provenance.

## Preconditions

- CP-02 accepted.
- Synthetic input bundle and recorded provider response available.

## Contract gate

Normalized ingest manifest, stage registry subset, AnalysisProfile/PromptBundle/NormsSnapshot/ModelCallRecord, evidence coordinates, finding identity policy v1.

Production implementation tasks consuming these boundaries start only after the wave contract owner records a frozen contract set.

## Wave plan

### W3.1 — analysis contract freeze

Define preparation/text stage I/O and model ledger before runner code.

### W3.2 — parallel engine/AI/identity/UI/QA

ENG, AI, FND and WEB build against frozen packages.

### W3.3 — live/replay integration

Recorded replay mandatory; live provider smoke never sole proof.

## Agent-ready task map

| Task | Lane | Deliverable | Depends on | Primary ownership | Non-goal / guardrail |
|---|---|---|---|---|---|
| W3-C-01 | ENG | Freeze ingest/analysis/model/evidence contracts | CP-02 | contracts/analysis + API | One stage registry. |
| W3-ING-01 | META | Normalize direct/ZIP inputs to InputManifest | W3-C-01 | ingest/** | Transport is not identity. |
| W3-ENG-01 | ENG | Preparation + one real text-analysis stage | W3-C-01 | analysis/** | No direct PG write. |
| W3-AI-01 | AI | Profile/Prompt/ModelCall ledger + replay adapter | W3-C-01 | analysis AI adapters | Provider payload protected; cost recorded. |
| W3-FND-01 | FND | Stable finding matcher + evidence publication | W3-C-01 | findings/** | Uncertain match creates new identity. |
| W3-API-01 | API | Run/evidence/provenance queries | W3-C-01 | api/** | Safe payload only. |
| W3-WEB-01 | WEB | PDF/evidence/finding alpha view | W3-C-01 | web slices | No object key exposure. |
| W3-QA-01 | QA | Replay/timeout/identity rerun tests | W3-C-01 | tests/** | No live text-equality assertion. |
| W3-INT-01 | INT | Alpha checkpoint | all | evidence | Provider outage explicit. |

## Automated exit evidence

- [ ] Recorded provider replay is deterministic downstream.
- [ ] Run records input/stage/profile/prompt/norm/model-call provenance.
- [ ] Provider timeout follows retry policy without duplicate run.
- [ ] Finding UID persists only when matcher policy permits.

## Manual local acceptance

Full script: `../manual-tests/CP-03_audit_alpha.md`.

- [ ] Run synthetic real bundle.
- [ ] Open finding and verify page/evidence/provenance.
- [ ] Inspect run ledger/checksums/stage/profile/model call.
- [ ] Force provider timeout and verify explicit state/retry UI.
- [ ] Rerun via replay and inspect stable finding identity.

## Checkpoint exit criterion

One genuine audit result is explainable from input through model call to evidence and stable identity.

## Integration report must record

- frozen contract versions and commit;
- migration head and dependency lock hashes;
- merged task IDs;
- automated commands/results;
- manual report reference;
- known limitations/risks;
- rollback/recovery note;
- next stage unlocked tasks.
