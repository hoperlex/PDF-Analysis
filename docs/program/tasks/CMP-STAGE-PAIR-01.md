# Task CMP-STAGE-PAIR-01 — stage pair catalog and bounded set intake

## Outcome
An expert can upload a plain PDF or ZIP set into a project, review the resulting stage candidates, confirm a П↔Р pair or Р assembly, and open the stage pair catalog. Every saved PDF is validated, every pair names document identities, and the module-off surface still refuses with its sealed 503.

## Depends on
- CMP-SEAL-C3
- CMP-ZIP-FIX-01
- CMP-INGEST-ZIP-01

## Frozen inputs
- API/domain contract: `1.12.0`, 204 paths / 230 operations / 570 schemas; no operation or schema reseal in this task
- migration head: `0041_comparison_stage_core`; the 15 C3 tables and their constraints are frozen
- ZIP reader: `CMP-INGEST-ZIP-01` plus the reviewed `__MACOSX/` Unicode Path repair from `CMP-ZIP-FIX-01`; retain rejection of that prefix
- architecture: ADR-0025 A-9 and decisions 2, 3, 21, 25; `COMPARE-MODULES-PLAN.md` §1.2, §3.2 R3-17 and §4 C3
- base commit: `5761191040539472e4d7170f58b2b70f57eb216f`
- base branch: `agent/cmp-stage-pair-01`, after a local merge of the finished ZIP fix into the completed C3 seal
- product `VERSION`: `0.9.0`; module values `none`, `versions`, `versions,stages`

## Captured premise evidence
- premise: the C3 seal and ZIP policy fix are committed, with no stage-pair implementation yet.

### P-01 — frozen base
- captured_at: 2026-10-29
- command: `git rev-parse HEAD; git status --short; python3 -c 'import json; d=json.load(open("contracts/api/v1/openapi.json")); print(d["info"]["version"],len(d["paths"]),sum(k in {"get","post","put","patch","delete"} for p in d["paths"].values() for k in p),len(d["components"]["schemas"]))'`
- captured_output:
  ```text
  5761191040539472e4d7170f58b2b70f57eb216f
  1.12.0 204 230 570
  ```
- interpretation: the branch has the sealed C3 surface and the ZIP policy repair, and begins clean.

### P-02 — first-use security boundary
- captured_at: 2026-10-29
- command: `rg -n '^## Conditions for the first caller|^2\.|^3\.' docs/program/compare/CMP-ZIP-SECURITY-REVIEW.md | cut -d: -f1`
- captured_output: `27`, `30`, `31`
- interpretation: these are caller obligations, not properties of the reusable ZIP reader.

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `docs/program/tasks/CMP-STAGE-PAIR-01.md`
- `docs/program/CMP-STAGE-PAIR-01.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/DEBT_REGISTER.md`
- `src/auditmanager/comparison/stage/**`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `src/auditmanager/api/app.py`
- `src/auditmanager/api/routers/comparison_stage_uploads.py`
- `src/auditmanager/api/routers/comparison_stage_pairs.py`
- `src/auditmanager/comparison/public.py`
- `scripts/recovery/product_purge.py`
- `tests/unit/comparison/stage/**`
- `tests/integration/comparison/stage/**`
- `tests/integration/api/test_stage_pair_upload.py`
- `tests/integration/composition/test_comparison_stage_stub_operations.py`
- `tests/integration/composition/test_router_answers.py`
- `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`
- `tests/integration/composition/test_every_port_implementation_is_whole.py`
- `tests/integration/composition/test_comparison_core_stub_operations.py`
- `web/src/_pages/stage-compare/**`
- `web/src/app/stage-comparison/**`
- `web/src/widgets/stage-pair-catalog/**`
- `web/src/entities/stage-pair/**`
- `web/src/shared/config/screen-registry.ts`
- `web/src/shared/lib/routes.ts`
- `web/src/_pages/version-compare/ui/version-compare-page.tsx`
- `web/tests/unit/stage-compare/**`
- `web/tests/unit/screens/stage-compare.test.ts`
- `web/tests/unit/screens/route-screens.ts`
- `web/tests/guards/screen-registry.guard.test.ts`
- `tests/e2e/pc01/journey/manifest.json`
- `.venv`
- `web/node_modules`

## Forbidden hotspots
- `contracts/**`, migration files/head, root dependency/lock files, global styles, C2 runtime and jobs, other C3 lanes' module directories, remote refs and server deployment composition
- direct SQL, blob access or ZIP extraction in a router or React component

## Non-goals
- no sheet-map, text-difference, AI, run executor or review implementation; no live model calls
- no product-version, API contract or database schema change; no `origin/dev` or `origin/main` publication
- no claim of a first-use ZIP pass until the caller-level raw-byte, disk, validation and cleanup tests are green

## Deliverables
1. Bounded durable upload commands for the ten sealed stage-upload operations. Raw compressed bytes and staged part count are checked before extraction; admission and disk headroom are bounded; every PDF passes the production comparison envelope before its bytes are stored as a published member. Replays are keyed and safe across restart; cancellation/abort has reconciliation for external blobs.
2. Deterministic, nonbinding pair suggestions by section/designation; expert confirmation of one П document to one Р document or an assembly; append-only assembly membership and explicit completeness; document IDs are canonical and names only display hints.
3. Stage pair catalog/workbench tab 1 with project selection, upload candidate confirmation and module-aware entry. The UI consumes the generated `1.12.0` client without changing generated files.
4. Unit, API, DB and composition evidence for refusal, replay, cross-project scope, module off/on, rollback and ZIP adversarial cases, plus a handoff report and scope proof.

## Required tests
- `git diff --check`; targeted unit tests for deterministic suggestion, pair/assembly state and ZIP admission
- on an isolated stack at `0041`: stage upload/pair API and composition tests, reader caller-level malicious/padded ZIP and PDF refusal tests, project erase and Blob reference checks
- web lint, typecheck and focused stage catalog tests; `npm --prefix web run api:verify`
- integration acceptance runs the relevant whole directories and later full `make gate` on the exact integrated candidate

## Integration contract
The integrator merges this branch only after C2 publication and C3 seal integration, keeping API `1.12.0` and head `0041` byte-for-byte. Pair and upload ports become served only when `AUDITMANAGER_COMPARISON_MODULES=versions,stages`; the module-off refusal stays typed. `CMP-STAGE-LINK-01` reads confirmed pair and assembly identities from this lane and owns no pair mutation. This lane has no remote publication authority.

## Failure/idempotency/security cases
- enforce raw ZIP byte and extraction/admission/disk bounds before first use; reject `__MACOSX/` in raw and Unicode Path names; reject nested violations and leave no published partial set
- validate every member PDF before publication; failures keep retriable durable state and reconcile staged blobs
- one idempotency key with different payload refuses; repeated key returns the same decision; stale or cross-project document IDs refuse
- a suggestion never binds documents; a human expert's keyed confirmation is the canonical act

## Rollback / feature flag
`AUDITMANAGER_COMPARISON_MODULES=none` or `versions` keeps all stage operations unavailable and the stage menu hidden. If this lane cannot complete, leave its adapters as typed stubs; do not downgrade a populated `0041` database.

## Handoff
- changed files: pending implementation
- commands/results: pending
- contracts: none; frozen API `1.12.0` and migration `0041`
- known limits: pending
- integration notes: merge only after the C3 seal; preserve the ZIP fix and its `__MACOSX/` decision
