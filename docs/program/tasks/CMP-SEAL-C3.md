# Task CMP-SEAL-C3 — freeze the deterministic stage-comparison contract

## Outcome
The API contract is `1.12.0` with C3 stage-upload, stage-pair, assembly, sheet-link, text-difference and chain-run operations sealed as typed `503 dependency_unavailable` stubs. Migration `0041_comparison_stage_core` creates the durable C3 tables and their project reachability. Generated clients, permissions and all version/table/head pins agree with the seal, so `CMP-STAGE-PAIR-01`, `CMP-STAGE-LINK-01` and `CMP-STAGE-TEXT-01` can implement against one frozen shape.

## Depends on
- CMP-SEAL-C2
- CMP-C2-FIX-01

## Frozen inputs
- domain contract: ADR-0025 decisions 5, 9, 12, 15, 16, 21, 23 and 25; plan §1.2 and §4 C3; `CMP-INGEST-ZIP-01`
- API contract: `1.11.0`, 176 paths / 198 operations / 517 schemas
- analysis/comparison/event contract: as sealed by `CMP-SEAL-C2`; deterministic raw evidence remains immutable to AI
- migration head: `0040_comparison_ai_reports`; this seal takes `0041_comparison_stage_core`
- base commit: `06c312a3f8d35b569019066fff9e47d38e69501c` on `integration/compare-modules`
- product `VERSION`: `0.9.0`; module enum already includes `none`, `versions`, `versions,stages`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json`
- enumerator_owner: CMP-SEAL-C3
- totality_query: `python3 tools/plan/pin_sweep.py --help`, then the applicable `reseal`, `contract-version`, `table` and `migration-head` sweeps; every grant outside the paths below must be added to this task before edit

## Captured premise evidence
- premise: P-01 and P-02 fix the C2 contract/head and the C3 wave boundary before any C3 source edit.

### P-01 — clean C2 base
- captured_at: 2026-10-29
- command: `git rev-parse HEAD; git status --short; python3 -c 'import json;d=json.load(open("contracts/api/v1/openapi.json"));print(d["info"]["version"],len(d["paths"]),sum(k in {"get","post","put","patch","delete","head","options","trace"} for p in d["paths"].values() for k in p),len(d["components"]["schemas"]))'; ls db/migrations/versions | tail -n 1; cat VERSION`
- captured_output:
  ```text
  06c312a3f8d35b569019066fff9e47d38e69501c
  1.11.0 176 198 517
  20261029_0040_comparison_ai_reports.py
  0.9.0
  ```
- interpretation: this separate C3 worktree starts from a clean C2 repair commit with the planned frozen inputs.

### P-02 — C3 scope and existing module flag
- captured_at: 2026-10-29
- command: `rg -n '^    (NONE|VERSIONS|VERSIONS_STAGES) = ' src/auditmanager/api/schemas/models.py | head -n 3; sed -n '576p' docs/program/dispatch/COMPARE-MODULES-PLAN.md`
- captured_output:
  ```text
  1127:    NONE = "none"
  1128:    VERSIONS = "versions"
  1129:    VERSIONS_STAGES = "versions,stages"
  | CMP-SEAL-C3 | contract `1.12.0`/migration: stage pairs, assemblies, link revisions, hints, fragments, exclusions, differences, chain runs | L | seal |
  ```
- interpretation: the module flag is already contracted; the seal adds the C3 surface and storage without implementing the three lanes.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `contracts/api/v1/**`, `contracts/domain/v1/**`
- `contracts/analysis/**`, `contracts/events/**` (shared `contract_version` pins only; added after the disposable probe and literal `1.11.0` inventory)
- `src/auditmanager/analysis/engine/result.py` (served analysis contract-version constant only)
- `db/migrations/versions/20261029_0041_comparison_stage_core.py`
- `src/auditmanager/api/routers/comparison_stage_uploads.py` (new), `src/auditmanager/api/routers/comparison_stage_pairs.py` (new), `src/auditmanager/api/routers/comparison_stage_links.py` (new), `src/auditmanager/api/routers/comparison_stage_text.py` (new), `src/auditmanager/api/routers/comparison_stage_runs.py` (new), `src/auditmanager/api/routers/__init__.py`, `src/auditmanager/api/routers/ports.py` (the five new stage-router protocols), `src/auditmanager/api/app.py`, `src/auditmanager/api/README.md`, `src/auditmanager/api/schemas/models.py`, `src/auditmanager/api/security.py`
- `src/auditmanager/bootstrap/adapters.py`, `src/auditmanager/bootstrap/composition.py`
- `src/auditmanager/shared/identity/**`, `src/auditmanager/comparison/public.py`
- `scripts/recovery/grant_classification.py`, `scripts/recovery/product_purge.py`, `scripts/recovery/project_erase.py`, `scripts/recovery/schema_coverage.py`, `infra/deploy/apply-grants.sh`
- `infra/deploy/proxy/nginx.conf`, `infra/deploy/proxy/tls-server.conf` (edge error-envelope version and current surface comments only)
- `web/openapi/openapi.json`, `web/src/shared/api/**`, `web/FRONTEND_LOCK.json`, `web/src/app/bff/v1/[...path]/route.ts`
- `tests/contract/api_v1/**`, `tests/contract/domain_p02/**`, `tests/integration/api/**`, `tests/integration/composition/**`, `tests/integration/db/**`, `tests/integration/recovery/**`, `tests/integration/p02_journey/journey.py`, `tests/e2e/test_pc01_journey_conformance.py`
- `tests/support/expected_facts.json` (current contract version, surface and migration-head facts only)
- `web/tests/contract/**`, `web/tests/guards/rendered-language.guard.test.ts`
- `web/tests/**` (existing expected `1.11.0` error-envelope literals only; no behavior changes outside C3-specific tests)
- `docs/program/tasks/CMP-SEAL-C3.md`, `docs/program/CMP-SEAL-C3.md`, `docs/program/P02_SEAMS.md`
- `docs/program/CURRENT_STATE.md`, `docs/program/ALPHA_ROADMAP.md`, `docs/program/CONTRACT_PIN_REGISTRY.md`, `docs/manual-tests/PC-01_prototype.md`, `docs/manual-tests/README.md` (the probe exposed live API/head claims)
- ignored local setup: `.venv`, `web/node_modules`, `.local/norms/**`

## Forbidden hotspots
- root dependency and lock files, global styles, stage UI, C2 runtime logic, `src/auditmanager/jobs/**`, `infra/deploy/compose.server.yml`, remote refs
- any unlisted pin discovered by the probe until this task is amended with its reason

## Non-goals
- no stage-pair suggestion, upload or ZIP-set use; no sheet-link algorithm, text exclusion/diff engine, AI reviewer, run executor or screen
- no live model call, production deployment, `origin/dev` or `origin/main` publication
- no change to the C2 deterministic evidence or existing C2 operation behavior

## Deliverables
1. A disposable contract/table/version probe that enumerates affected pins before the full seal; record its red checks and any scope amendment in `docs/program/CMP-SEAL-C3.md`.
2. Additive API `1.12.0`: opaque-identity stage-pair catalog/workbench and assembly commands; chunked stage upload and candidate confirmation separate from the C0 PDF-only completion path; sheet-passport/suggestion/link-revision reads and expert edits; text-fragment/exclusion/difference/hint reads and commands; chain-run start/read/cancel and step state. Every write requires an idempotency key and expert role; reads follow the existing authenticated role policy. New operations answer typed `503` under `comparison_modules` when stages are off and their lane dependency while on.
3. Migration `0041`: project-reachable stage-upload candidate, stage-pair, assembly, sheet-link revision, fragment/exclusion/difference and chain-run storage. Immutable evidence and append-only expert/link history have schema guards; migration up/down and project erase are tested.
4. Identifier prefixes, domain constraint notes, generated web client, API mirror and frontend lock; update every contract-version, operation-surface, table-count, migration-head, role and stub enumerator pinned by the probe.
5. A seal report with exact operations/tables per C3 lane, migration/rollback evidence, test results, forbidden-hotspot proof and known limits.

## Required tests
- `git diff --check`; contract suite and `npm --prefix web run api:verify`, lint, typecheck and Vitest under the same local-process permissions as the integration gate
- on an isolated C3 stack, migration up/down and `tests/integration/db`, `tests/integration/recovery`, `tests/integration/composition`, `tests/integration/api`, `tests/integration/p02_journey`, and journey conformance
- focused tests proving every C3 operation is a module-gated stub until its lane wires it, every write has the expert/key policy, and the migration's tables are reachable from project
- the integration task, not this seal, owns the later exact-candidate `make gate` and `origin/dev` publication

## Integration contract
The C3 lanes consume the sealed `1.12.0` schema and `0041` tables. They do not change contracts or migration head; if an essential field is missing they stop for a separately scoped contract repair. `CMP-STAGE-PAIR-01` cannot first use ZIP sets until D-262's code-review blocker is fixed and its caller satisfies the raw-upload, disk and PDF-validation conditions. The module flag defaults to `none`.

## Failure/idempotency/security cases
- no ZIP-set use is claimed by the seal; an upload caller must enforce its own raw-byte/admission bound and never store an unvalidated PDF
- no path, filename or display number is identity; every command uses an opaque ID and idempotency key
- append-only revisions preserve expert changes; a stale revision is a typed refusal; a project erase can reach every new table
- a missing pin, non-fast-forward remote or unmet prerequisite stops this task before any publication

## Rollback / feature flag
`AUDITMANAGER_COMPARISON_MODULES=none` keeps C3 unavailable. The migration's downgrade is exercised on isolated empty C3 tables; no production rollback is claimed. Stubs have no external side effects.

## Handoff
- changed files: pending
- commands/results: pending
- contracts: planned `1.12.0` / `0041`, not yet built
- known limits: pending
- integration notes: pending
