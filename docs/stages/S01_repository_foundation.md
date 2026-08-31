# S01 — Repository foundation

**Target checkpoint:** `CP-01 / v0.1.0-foundation`

## Goal

Сделать новый репозиторий воспроизводимым: toolchain, local PostgreSQL/S3, backend/frontend skeleton, contract generation and CI-like local command surface.

## Preconditions

- CP-00 accepted.
- Domain/API baseline frozen for foundation.
- No feature code requires legacy runtime.

## Contract gate

Toolchain/dependency lock, health/error envelope, local infra config, generated-client pipeline, import-boundary rules.

Production implementation tasks consuming these boundaries start only after the wave contract owner records a frozen contract set.

## Wave plan

### W1.1 — root/toolchain single-owner

Integrator alone chooses/pins package managers, root locks and stable local commands.

### W1.2 — parallel foundations

OPS, API, WEB, ARC, QA implement isolated foundations against frozen conventions.

### W1.3 — reproducibility integration

Clean clone/bootstrap on second worktree/environment, then CP-01 smoke.

## Agent-ready task map

| Task | Lane | Deliverable | Depends on | Primary ownership | Non-goal / guardrail |
|---|---|---|---|---|---|
| W1-INT-00 | INT | Pin toolchain/root command surface | CP-00 | root manifests/locks | Single hotspot owner. |
| W1-OPS-01 | OPS | Local PostgreSQL + private S3-compatible stack | W1-INT-00 | infra/local/** | No production credentials. |
| W1-ARC-01 | ARC | Backend/FSD architecture lint | W1-INT-00 | architecture checks | Fail on deep cross-context imports. |
| W1-API-01 | API | FastAPI bootstrap/liveness/readiness/errors | W1-INT-00 | api/bootstrap | Liveness no dependency checks. |
| W1-WEB-01 | WEB | Next/FSD shell + API codegen | W1-INT-00 | web/** | No handwritten raw HTTP outside shared transport. |
| W1-QA-01 | QA | Unit/contract/integration/E2E harness | W1-OPS-01,W1-API-01,W1-WEB-01 | tests/** | Integration uses real local PG/S3. |
| W1-OPS-02 | OPS | Logging/correlation/redaction baseline | W1-API-01 | operations | No secrets/raw payloads by default. |
| W1-INT-01 | INT | Fresh-clone bootstrap + checkpoint | all | evidence | Must reproduce without author state. |

## Automated exit evidence

- [ ] Fresh database migration succeeds.
- [ ] S3 private policy/local equivalent checked.
- [ ] Backend lint/type/tests pass.
- [ ] Frontend lint/type/build pass.
- [ ] Architecture check catches a known bad fixture.
- [ ] OpenAPI client generation is reproducible.

## Manual local acceptance

Full script: `../manual-tests/CP-01_foundation.md`.

- [ ] Start local stack from documented commands.
- [ ] Stop PostgreSQL: readiness must fail while liveness stays healthy.
- [ ] Open frontend shell and exercise safe API error/correlation path.
- [ ] Restart all services and repeat without manual data repair.

## Checkpoint exit criterion

A new agent can clone, bootstrap, test and run the product shell without tribal knowledge.

## Integration report must record

- frozen contract versions and commit;
- migration head and dependency lock hashes;
- merged task IDs;
- automated commands/results;
- manual report reference;
- known limitations/risks;
- rollback/recovery note;
- next stage unlocked tasks.
