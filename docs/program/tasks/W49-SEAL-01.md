# Task W49-SEAL-01 — contract, registers, routers and pins in one slot (01a, 01b, 01c)

## Outcome

The resealed contract, the three access registers plus `OPERATION_ROLES`, and the `me`, `registrations` and `users` routers land together with every surface pin, so the gate is green at the slot's final SHA.

## Depends on

- `W49-ACCESS-01` merged
- `W49-DECISIONS-01` merged

## Frozen inputs

- domain contract: revision 8, 27 opaque identities (moves only in `W49-SEAL-01`)
- API contract: 17 / 20 / 61 (moves only in `W49-SEAL-01`)
- error catalog: 22 codes (moves only in `W49-SEAL-01`: `rate_limited`)
- migration head: `0014_durable_analysis_effects` (moves only in `W49-ACCESS-01`)
- code base: `23e0579`, the W48 closure published to `origin/dev`
- controlling plan: `docs/program/dispatch/W49-PLAN.md` at the freeze commit

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json`; `contracts/domain/v1/error-codes.json`; `contracts/domain/v1/identifiers.json`; `contracts/domain/v1/state-machines.json`
- enumerator_owner: `W49-SEAL-01`
- totality_query: the served application's operation set equals the document's (`tests/integration/api/test_operation_surface.py`)

## Captured premise evidence

- premise: the surface is 17 paths, 20 operations, 61 schemas

### P-01 — base measurement

- captured_at: 2026-10-05
- command: `python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print(len(d['paths']), sum(len([m for m in v if m in ('get','post','put','patch','delete')]) for v in d['paths'].values()), len(d['components']['schemas']))"`
- captured_output:
  ```text
  17 20 61
  ```
- interpretation: measured on the code base before dispatch; the lane re-measures it first.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/dispatch/W49-PLAN.md`
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `contracts/api/v1/openapi.json`, `contracts/api/v1/README.md`
- `contracts/domain/v1/identifiers.json`, `contracts/domain/v1/error-codes.json`, `contracts/domain/v1/error-envelope.schema.json`, `contracts/domain/v1/state-machines.json`, `contracts/domain/v1/README.md`
- `src/auditmanager/shared/identity/ids.py` — the `usr` and `reg` registry types only
- `web/openapi/openapi.json`, `web/src/shared/api/generated/**` (via `npm --prefix web run api:generate`), `web/FRONTEND_LOCK.json`
- `web/src/shared/api/catalog-message.ts` — the `rate_limited` sentence only
- `web/src/app/bff/v1/[...path]/route.ts` and `web/src/shared/api/authorization.ts` — the one count comment in each
- `tests/contract/**` except `tests/contract/test_proxy_rate_limits.py`; `web/tests/contract/**`
- `src/auditmanager/api/**`, `src/auditmanager/bootstrap/adapters.py`, `src/auditmanager/bootstrap/composition.py`
- `tests/integration/api/**`, `tests/integration/auth/**`, `tests/integration/composition/**`
- `tests/e2e/pc01/test_acceptance.py` — the route-count assertion only
- `docs/program/CONTRACT_PIN_REGISTRY.md` — all rows but the migration head's
- `docs/program/CURRENT_STATE.md` and `docs/program/ALPHA_ROADMAP.md` — the live surface-triple sentence in each
- `docs/program/W49-SEAL-01a.md`, `docs/program/W49-SEAL-01b.md`, `docs/program/W49-SEAL-01c.md`

## Forbidden hotspots

- every path not listed above; `contracts/**` outside `W49-SEAL-01`; root locks; refs, tags, deployment and secrets; `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md` except an exact sentence named here; `src/auditmanager/access/**` (call it through its public module), migrations, `web/src/**` beyond the lines named

## Non-goals

- no change to an existing operation's shape; no error code but `rate_limited`; no free-text detail key; no business rule in a router

## Deliverables

- 01a: `W49-PLAN.md` §3.4 operations and schemas; `conflict_reason`; `rate_limited` in all four places; identifiers `usr`, `reg`; the two state machines; the superseded denials with the sweep `rg -n -i -e role -e 'rate limit' contracts/api/v1/openapi.json`; regenerated client, mirror and lock; every surface pin; measured triple and SHA-256
- 01b: the three registers and `OPERATION_ROLES` (any-of), `AccountStanding` widened, the evaluation order of §3.2, sweep tests over operation × role set × profile × credential
- 01c: routers `me.py`, `registrations.py`, `users.py`; the decisions router passes the subject's `user_uid`; suite logins become e-mails with complete profiles

## Required tests

- 01a: `.venv/bin/python -m pytest tests/contract -q`; `npm --prefix web run api:verify`; `npm --prefix web test -- --run tests/contract`
- 01b: `.venv/bin/python -m pytest tests/integration/api/test_authorization.py tests/integration/auth -q`
- 01c and the slot: `make gate` with literal `GATE OK` at the final SHA

## Integration contract

The generated client exposes every operation of §3.4; the registers in `security.py` equal the served application; `W49-BFF-01` consumes `getMe`, `submitRegistration`, `readRegistrationStatus`.

## Failure/idempotency/security cases

- unique lane ports taken with `ss -ltn` and recorded; owned disposable services only; never kill a process by pattern; no credential in evidence
- one gate at the final SHA; intermediate commits need not be green (`W49-PLAN.md` §4)

## Rollback / feature flag

Revert the slot's commits together; the reseal is atomic.

## Handoff

- changed files: listed in `docs/program/W49-SEAL-01.md` with `git diff --name-only <base>..<sha>`
- commands/results: verbatim with exit status; every mutation with its red output
- known limits: listed, never decided silently
- integration notes: hand back branch `agent/w49-seal-01` at a recorded SHA
