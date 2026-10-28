# Task CMP-SEAL-C0 — the seal of wave C0: contract 1.9.0, migration 0038, dependencies, module flag

## Outcome
On `integration/compare-modules` the contract is `1.9.0` with every C0 operation sealed as a stub (`503
dependency_unavailable`, listed in the stub enumerators), migration `0038` creates the C0 tables, the lock carries
`numpy`, `opencv-python-headless` and `reportlab`, the module flag is readable through the contract, and every pin
that these facts move is updated, so that the C0 lanes (WORK, SPEND, STORAGE-PARTS, EXEC-IMAGES, INGEST-ZIP,
INGEST-01, INGEST-02, PROFILE, VERSION-MARK) can start on a green tree and each implement its own operations.

## Depends on
- CMP-ADR-01 (ADR-0025), CMP-FIXTURES-01, CMP-ORIGINAL-READ-01 (merged); `origin/dev` `10432537` merged (`c86ae7b0`)

## Frozen inputs
- domain contract: `contracts/domain/v1/**` at `c86ae7b0` (identifiers catalogue gets the new prefixes)
- API contract: `contracts/api/v1/openapi.json` `1.8.0`, 98 paths / 111 operations / 321 schemas at `c86ae7b0`
- analysis/comparison/event contract: ADR-0025 decisions 2, 4, 5, 9, 10, 11, 18, 23, 24, 25
- migration head: `0037_analysis_presets` (this seal takes `0038`; revision id ≤ 32 characters)
- base commit: `c86ae7b0` on `integration/compare-modules`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json`
- enumerator_owner: CMP-SEAL-C0
- totality_query: `python3 tools/plan/pin_sweep.py reseal` and `python3 tools/plan/pin_sweep.py contract-version` and `python3 tools/plan/pin_sweep.py table` and `python3 tools/plan/pin_sweep.py migration-head` (whichever modes exist; list `python3 tools/plan/pin_sweep.py --help` first)

## Captured premise evidence
- premise: base facts read by the integrator at `c86ae7b0`: contract `1.8.0`, 98/111/321, head `0037_analysis_presets`,
  VERSION `0.9.0`; the lane re-reads and prints them before any edit and STOPs if they differ

### P-01 — the base facts the lane re-read before any edit
- captured_at: 2026-10-27
- command: `git show 03f73103:contracts/api/v1/openapi.json | python3 -c "import json,sys;d=json.load(sys.stdin);print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas',len(d['components']['schemas']['ErrorCode']['enum']),'error codes')"; git show 03f73103:VERSION; git grep -n "^revision: str" 03f73103 -- db/migrations/versions/20261027_0037_analysis_presets.py | cut -d: -f3-`
- captured_output:
  ```text
  contract 1.8.0 98 paths 111 operations 321 schemas 27 error codes
  0.9.0
  revision: str = "0037_analysis_presets"
  ```
- interpretation: equal to the premise (contract `1.8.0`, 98 / 111 / 321, head `0037_analysis_presets`, `VERSION` `0.9.0`), so the lane did not STOP; the report is `docs/program/CMP-SEAL-C0.md`

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `contracts/api/v1/**`
- `contracts/domain/v1/**`
- `web/openapi/openapi.json`
- `web/src/shared/api/**`
- `web/FRONTEND_LOCK.json`
- `web/src/app/bff/v1/[...path]/route.ts`
- `db/migrations/versions/**`
- `src/auditmanager/api/**`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `src/auditmanager/shared/**`
- `src/auditmanager/comparison/**`
- `src/auditmanager/documents/models.py`
- `src/auditmanager/executors/model.py`
- `src/auditmanager/access/references.py`
- `scripts/recovery/**`
- `infra/deploy/apply-grants.sh`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/proxy/tls-server.conf`
- `infra/deploy/serve.py`
- `infra/deploy/README.md`
- `pyproject.toml`
- `uv.lock`
- `docs/program/P02_LOCK.json`
- `docs/program/CURRENT_STATE.md`
- `docs/program/ALPHA_ROADMAP.md`
- `docs/program/CMP-SEAL-C0.md`
- `docs/program/tasks/CMP-SEAL-C0.md`
- `tests/**`
- `web/tests/**`

Any further file the probe proves pins a fact this seal moves may be edited; list each with the reason in the report
(the integrator grants by message if asked). Product logic is NOT in scope even inside the allowed directories.

## Lane resources
- foundation_instance: `auditmanager-cmp-seal-c0`
- postgres_port: `57710`
- s3_api_port: `61710`
- s3_console_port: `61711`
- postgres_db: `auditmanager_cmp_seal_c0`
- s3_bucket: `auditmanager-cmp-seal-c0`

## Forbidden hotspots
- `web/src/**` outside `web/src/shared/api/**` and the BFF route; global styles; screens
- `src/auditmanager/jobs/**` (PROD-20), `infra/deploy/compose.server.yml` (PROD-05b) — the flag is a contract field,
  not a compose env (ADR-0025 decision 23)
- any implementation of an operation beyond the stub; any `origin/*` push

## Non-goals
- no service logic, no worker loop, no UI; the C0 lanes implement their operations

## Deliverables
1. **Probe first** (disposable branch or commit you drop): add one stub operation, one table and the version bump,
   run `tests/contract` and the static guards, and list every file that turns red; build the grant list from it.
2. **Contract `1.9.0`** (additive minor): sealed stub operations with request/response schemas, keyed writes with
   `Idempotency-Key`, expert/admin roles per ADR-0025 decision 16, for:
   - plain-PDF comparison upload of one or many document sets (ADR-0025 decisions 10, 11): create an upload with
     declared files (sha256, size, display name as a hint only), upload a part (≤ 16 MiB body, multipart staging),
     complete a file, read the upload and its proposal (grouping by designation/stamp, order, stage and section
     proposal), confirm grouping and order per set, exclude/retry a set, pause after the current set/resume, cancel
     («Отменить пакет»); the limits of decision 9 as typed refusals (reasons under existing codes)
   - comparison version order revisions of a document set: read and append (expert only; decision 16)
   - page profile, preview PNG, thumbnail PNG and tile PNG reads of a version page (decision 9; stubs)
   - `DocumentVersion` gains an upload-kind field (`portal_bundle` | `comparison_pdf`)
   - runner image references (decision 18): `RunnerImage` without a required `portal_block_id`, an opaque crop
     reference, `ClaimedExecutorTask.images` up to 8, the claim request's declared `max_images` (absent = 1)
   - the module set (`none` | `versions` | `versions,stages`) as an additive field of an existing authenticated read
     that the web shell already loads (product version or session subject — choose, state why) (decision 23)
   - no new error code: reasons under existing codes (decision 25), including `comparison_only_version` under
     `analysis_input_invalid` with its Russian sentence in the catalogue
3. **Migration `0038_comparison_foundation`** (or another id ≤ 32 characters): `comparison_upload`,
   `comparison_upload_file`, `comparison_upload_part` (multipart token persisted before the first part),
   `comparison_version_order`, `comparison_page_profile` (per-version rows, ULID id + content-key column),
   `comparison_work`, `comparison_work_attempt`, `comparison_model_call` (`prepared → sent → completed | failed |
   unknown`, decision 5); `document_version.upload_kind` with a CHECK; `executor_task` origin `comparison_call` and a
   nullable `comparison_attempt_id` (widen the CHECK); append-only triggers where rows are events; every new table
   reachable from `project` by foreign keys; the non-terminal states of `comparison_work`/`attempt` added to
   `NON_TERMINAL_STATES` with its derivation test (decision 7); up and down on an isolated database
4. **Dependencies** (decision 24): `numpy`, `opencv-python-headless`, `reportlab` pinned in `pyproject.toml`,
   `uv.lock` regenerated (network), `docs/program/P02_LOCK.json` and the `DIRECT` tuple of
   `tests/contract/test_w55b_direct_pins.py` updated; record each licence (including what the OpenCV wheel bundles)
   and the wheel sizes in the report
5. **Pins**: the contract-version family, the reseal surface family (counts in prose:
   `docs/program/CURRENT_STATE.md`, `docs/program/ALPHA_ROADMAP.md`, `infra/deploy/README.md`, `nginx.conf`,
   `serve.py`, `web/src/app/bff/v1/[...path]/route.ts`, `web/src/shared/api/authorization.ts`), the migration head
   pins, the per-table family (recovery scripts, `apply-grants.sh`, `access/references.py`, table-count tests,
   `P02_TABLES` in `tests/integration/p02_journey/journey.py`), the identifiers catalogue, the stub enumerators
   (`tests/integration/composition/test_router_answers.py`, `test_an_absent_parent_is_not_an_empty_page.py`)
6. Generated client: `npm --prefix web run api:generate` then `api:verify`; `web/FRONTEND_LOCK.json` resealed per
   the repository procedure
7. Report `docs/program/CMP-SEAL-C0.md`: operations table, tables, pins moved with files, probe output, licences,
   commands and results, limits, and for each C0 lane the operations and tables it implements

## Required tests
- provisioning: `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`, `npm --prefix web ci`, the six lane-resource
  values in `.env` on both sides (service and application), `mkdir -p .local/norms && ln -s
  /root/projects/PDF-Analysis/.local/norms/corpus .local/norms/corpus`; `df -h /` before each (stop under 1.5 GiB)
- command: `git diff --check`; `pytest -q tests/contract` (the three `D-220` files may stay red as on the base: show
  them red on the base too); `npm --prefix web run lint -- --quiet`, `typecheck`, `test -- --run`, `api:verify`; on
  the lane's own containers `pytest -q tests/integration/db tests/integration/recovery tests/integration/composition
  tests/integration/p02_journey tests/integration/foundation`; migration up/down round trip; the journey conformance
  test `tests/e2e/test_pc01_journey_conformance.py`
- expected: green apart from failures shown identical on the base; run with
  `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent` while `/root/projects/PDF-proverka` is absent

## Integration contract
After merge every C0 operation answers `503 dependency_unavailable` until its lane wires it (ADR-0025 decision 25,
plan §4.0 rule 1); the C0 lanes rely on the tables and schemas exactly as sealed and STOP to the wave's FIX slot if a
field is missing.

## Failure/idempotency/security cases
- uploads: limits refused before the first part; declared sha256/size checked at completion; names never identity
- spend journal: the `prepared` row exists before any provider call (schema allows nothing else)
- erase: a project with non-terminal comparison work is refused by the erase tools (decision 7)

## Rollback / feature flag
The module set defaults to `none`: with the flag off no comparison menu entry exists and every comparison operation
answers `dependency_unavailable`.

## Handoff
- changed files: `docs/program/CMP-SEAL-C0.md` section 6 lists every pinned file moved and section 2 the three files outside `allowed_paths` with their reasons; the new files are the migration `db/migrations/versions/20261028_0038_comparison_foundation.py`, three router files (`comparison_uploads.py`, `comparison_version_orders.py`, `version_pages.py`), `src/auditmanager/comparison/modules.py` and five test files
- commands/results: report section 8 (contract battery, web, the five integration directories, the journey conformance test, the migration round trip) and section 9 (eighteen mutation proofs)
- known limits: report section 10 (every operation is a stub; the flag gates nothing yet; `max_images` is accepted and ignored; `upload_kind` is not yet read from the database; the nine tables are empty and unwritten; the ninth table `comparison_upload_set` is this seal's addition)
- integration notes: report section 12 (merge without squashing, because `web/FRONTEND_LOCK.json` names `21058a2f`; image grows by about 230 MB; the compose line for the flag is PROD-05b's; per-lane operations and tables in section 11)
