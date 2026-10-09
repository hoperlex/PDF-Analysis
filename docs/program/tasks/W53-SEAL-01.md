# Task W53-SEAL-01 — seal execution API, migration and custody design

task_id: W53-SEAL-01

## Outcome

The six W53 execution operations and optional `RunStatus.reaudit_of_run_id` are declared, role-gated and wired to explicit port stubs; migration `0017_execution_queue` and the current pin set agree. Custody design documents reflect R-76 without implementing custody.

## Depends on

- `W53-FREEZE-01`, completed at `3c527d363ee5a196fbd44bf2f5b187d544615dd6`.

## Frozen inputs

- Base `3c527d363ee5a196fbd44bf2f5b187d544615dd6`; `dispatch/W53-PLAN.md` §3.1–§3.2, §3.5, §4 SEAL and the 2026-10-09 execution amendment.
- API 30 paths / 37 operations / 83 schemas, OpenAPI SHA-256 `dc8f18754d22ef85820c124e086df7f9d9ca769c188554decd8a373b1b460304`; domain revision 9 / 29 identities, 23 API error codes; head `0016_release_notes`; contract version `1.0.0-draft.1`.
- R-75…R-79 and W52 D-137–D-140 exact-candidate validation debt. W53 backup and live MinIO upgrade have no grant.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json`; `contracts/domain/v1/state-machines.json`; `db/migrations/versions/20261009_0017_execution_queue.py`
- enumerator_owner: `W53-SEAL-01` alone
- totality_query: `python3 tools/plan/pin_sweep.py reseal-surface migration route --check docs/program/tasks/W53-SEAL-01.md`; served operation set must equal OpenAPI and Alembic must report only `0017_execution_queue` as head.

## Captured premise evidence

- premise: W52 closed development at 30/37/83 with migration 0016; the current route stubs are `/logs` and `/queue`.

### P-01 — base and surface

- captured_at: 2026-10-09
- command: `git rev-parse 3c527d363ee5a196fbd44bf2f5b187d544615dd6`
- captured_output:
  ```text
  3c527d363ee5a196fbd44bf2f5b187d544615dd6
  ```
- interpretation: this pins the dispatch code tree; the agent must remeasure the contract before writing.

## Historical evidence

- correction_mode: addendum
- source_record: `docs/program/tasks/NORM-CUSTODY-01.md`
- addendum_path: `docs/program/NORM-CUSTODY-W53-ADDENDUM.md`

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `contracts/**` — only the exact W53 API/state-machine seal; no new error code, detail key or identifier; all existing files outside the changed declarations are review-only.
- `db/migrations/versions/**` — only new `20261009_0017_execution_queue.py` may be edited; every existing migration is review-only.
- `src/auditmanager/api/**` — skeleton/router/role declarations and directly affected head/surface prose; `app.py` only count/surface pins, not lifespan execution.
- `src/auditmanager/bootstrap/{adapters,composition}.py` — port-stub wiring only.
- `src/auditmanager/documents/refusals.py`, `src/auditmanager/storage/check.py`, `src/auditmanager/shared/db/{__init__,check,errors,migrations,schema}.py`, `src/auditmanager/shared/statemachine/topology.py` — head comments/constants only.
- `web/openapi/openapi.json`, `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json` — generated mirror/client and lock.
- `tests/contract/**`, `web/tests/contract/**`, `web/tests/guards/**` — W53 surface/state/role/pin assertions only; no unrelated guard weakening.
- `tests/integration/{api,auth,db}/**`, `tests/integration/composition/{test_api_token_channel,test_composition_root,test_execution_seal}.py` — W53 seal/role/migration checks only; no MinIO, backup/reset/readiness or Stage-B execution behavior.
- `tests/integration/foundation/test_cross_provider_publication.py`, `tests/integration/p02_journey/journey.py`, `tests/support/expected_facts.json`, `tests/support/expected_facts.py`, `tests/e2e/pc01/test_acceptance.py`, `tests/e2e/pc01/journey/manifest.json` — exact new pins only.
- `web/src/app/bff/v1/[...path]/route.ts`, `web/src/shared/api/{credentialed-forward,authorization}.ts`, `web/src/shared/config/screen-registry.ts`, `web/src/shared/lib/routes.ts`, `web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx`, `web/tests/unit/**` — W53 generated/capability/surface references only, no execution UI.
- `web/src/_app/navigation.ts`, `web/src/shared/config/index.ts`, `web/src/widgets/home-tiles/model/registrations-screen.ts` — route-pin review only; edit solely an affected W53 enumerator if its current content proves it necessary.
- `docs/program/{CONTRACT_PIN_REGISTRY,P02_SEAMS,CURRENT_STATE,ALPHA_ROADMAP,NORM_CORPUS_CUSTODY,NORM_CORPUS_DECISION_BACKLOG}.md`, `docs/program/NORM-CUSTODY-W53-ADDENDUM.md`, `docs/architecture/adr/ADR-0020-normative-corpus-alpha-runtime.md` — direct reseal/custody-design corrections; preserve the completed `NORM-CUSTODY-01.md` task and write the new addendum instead; ADR addendum only.
- `docs/manual-tests/{PC-01_prototype,README}.md`, `infra/deploy/{README.md,serve.py}`, `infra/deploy/proxy/nginx.conf`, `src/auditmanager/api/README.md` — exact head/surface prose, not deployment behavior.
- `docs/program/W53-SEAL-01.md` — six-item hand-back.

## Forbidden hotspots

Every path outside this list; the completed historical `docs/program/tasks/NORM-CUSTODY-01.md`; root dependency/lock files; global styles; existing migration files; error-catalog and identifier semantic changes; MinIO image/compose/foundation-lock paths; backup scripts/reset/readiness/runbook behavior; `VERSION`, `release-notes/**`; execution behavior in `jobs/**`, `runs/**`, `analysis/text/**`, `api/app.py` lifespan; refs, tags and the working stand. A pin-sweep hit is a review obligation, not permission to change unrelated behavior.

## Non-goals

No dispatcher, retry/heartbeat implementation, UI, custody implementation, backup, release notes or deployment. No attempt to close D-137–D-140.

## Deliverables

Six-operation OpenAPI and generated client, role register and stub port boundary, migration 0017 with backfill/refused downgrade, state-machine notes, current facts/pins, custody-design addenda and report.

## Required tests

- `python3 tools/plan/pin_sweep.py reseal-surface migration route --check docs/program/tasks/W53-SEAL-01.md` before hand-back; classify `table` hits separately, requesting a narrow repair grant for a needed edit outside this task.
- Contract/API role and generated-client verification; a fresh migration, a populated 0016→0017 upgrade with an unreleased lease and queued run without Job, refused downgrade with retained data; frontend lint/typecheck for touched files; `git diff --check`.
- Full `make gate` and independent QA are reserved for the integrator's exact candidate and D-139/D-140; report focused checks actually run.

## Integration contract

Use branch `agent/w53-seal-01` in an isolated worktree from the exact dispatch SHA supplied by the integrator. No refs published. Reserve only `gate-w53seal` PostgreSQL 56830 and S3 60430/60431 if needed; recheck before use. Preserve the `RunCarrier`/`RunAdapter` and direct `execute_run` signatures for Stage B. The integrator merges this branch first.

## Failure/idempotency/security cases

The six skeleton routes must fail explicitly through port stubs, not return fabricated empty results. Enforce roles for each operation, optional absence of `reaudit_of_run_id`, transaction-local migration backfill and downgrade refusal. Do not emit secrets or raw provider content in the journal declaration.

## Rollback / feature flag

Revert this atomic seal before Stage B. Migration 0017 has a guarded downgrade policy; there is no production feature flag or stand write.

## Handoff

Provide branch and exact SHA; changed files; commands/results; contract and migration delta; risks; integrator instructions; forbidden-hotspot and allowed-path audit. No checkpoint/tag/push.
