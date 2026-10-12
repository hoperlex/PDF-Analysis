# W54-SEAL-01 — hand-back report

- Task: `docs/program/tasks/W54-SEAL-01.md`; grant: `dispatch/W54-PLAN.md` §4 Stage A `W54-SEAL-01`,
  plus every path `tools/plan/pin_sweep.py reseal-surface migration table route` prints, plus this file.
- Branch `agent/w54-seal-01`, worktree `.local/worktrees/w54-seal`, base `7ebf162` (`origin/dev`,
  the `W54-FREEZE-01` commit). Implementation commit `6f4a2da`; this report is the next commit.
- Checks follow `R-102` (light acceptance). **No container was started**: every database-backed
  step is listed in §5 for the owner's window (`W54-FREEZE-01`).

## 1. Changed files

70 paths in `6f4a2da`, plus this report (the full list is `git diff --name-only 7ebf162..HEAD`).

- **Migrations (new):** `db/migrations/versions/20261012_0018_norm_custody.py`,
  `db/migrations/versions/20261012_0019_execution_workers.py`.
- **Contracts:** `contracts/api/v1/openapi.json`; `contracts/domain/v1/{identifiers,error-codes,state-machines}.json`,
  their three `*.schema.json` (`candidate_revision` const), `contracts/domain/v1/README.md`.
- **Four-document reseal** (the `W49-SEAL-01a` set): the contract, `web/openapi/openapi.json`,
  `web/src/shared/api/generated/**` (regenerated, never hand-edited), `web/FRONTEND_LOCK.json`.
- **API and composition:** `api/routers/{execution,ports,__init__,declarations,errors}.py`,
  `api/schemas/models.py`, `api/security.py`, `api/{app,health}.py` (count prose only; the lifespan
  is untouched), `api/README.md`, `bootstrap/adapters.py` (stub bodies). `bootstrap/composition.py`
  needed no change: the stubs live on the existing `ExecutionAdapter`.
- **Identity and scope:** `shared/identity/{ids,__init__}.py`; `runs/scope.py`.
- **Tests:** new `tests/integration/db/test_norm_custody_migration.py` and
  `test_execution_workers_migration.py`; resealed pins in `tests/contract/**`,
  `tests/integration/{api,db}/**`, three composition files, two `runs` files,
  `p02_journey/journey.py`, `e2e/pc01/test_acceptance.py`, `tests/support/expected_facts.json`,
  `web/tests/contract/seam-operations.contract.test.ts`.
- **Prose pins:** `web/src/app/bff/v1/[...path]/route.ts`, `web/src/shared/api/authorization.ts`,
  `infra/deploy/{README.md,serve.py,proxy/nginx.conf}`.
- **Documents:** `NORM_CORPUS_CUSTODY.md` (two-phase sequence, roles section, the re-recognition
  order rewritten), `NORM_CORPUS_DECISION_BACKLOG.md` (NORM-Q05), `P02_SEAMS.md`,
  `CONTRACT_PIN_REGISTRY.md` (sealed-stub convention), `CURRENT_STATE.md` and `ALPHA_ROADMAP.md`
  (sweep edits only), `docs/manual-tests/PC-01_prototype.md`, the ADR addenda
  `ADR-0020` (R-104) and `ADR-0002` (R-105).

## 2. Checks run, with commands and results

All on the committed tree `6f4a2da` unless stated otherwise.

| Command | Result |
| --- | --- |
| `git diff --check 7ebf162..HEAD` | clean |
| `.venv/bin/python -m compileall -q` over every changed module, both migrations and the changed test packages | exit 0 |
| `.venv/bin/python -m pytest -q tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py` | **554 passed**, 50 subtests (`test_alpha_acceptance_command.py` needs a clean checkout and failed only while the tree was dirty) |
| `.venv/bin/python -m pytest -q tests/integration/composition/test_every_port_implementation_is_whole.py` (container-free) | 16 passed |
| `npm --prefix web run api:verify` | OK, 45 operations, contract SHA-256 `0dbfbee4…` |
| `npm --prefix web run lint` | exit 0 |
| `npm --prefix web run typecheck` | exit 0 |
| `cd web && npx vitest run` | **123 files, 1852 tests passed**. This was the second run: the first (before the commit) caught generated files left behind a later contract edit (5 drift failures); the client and lock were regenerated and resealed, then rerun once. |
| `.venv/bin/python tools/plan/pin_sweep.py reseal-surface migration table route` | 89 paths before and after the work, identical; every changed path is inside the grant (checked by script against the sweep output and the §4 list) |
| Migration SQL, container-free: every `op.execute` of both migrations' `upgrade()` and `downgrade()` rendered without a database and parsed with `pglast` 8.5 (libpg_query) in a scratch virtualenv, PL/pgSQL bodies included | 0018 up 35 / down 21 statements, 0019 up 9 / down 6, four PL/pgSQL functions parse. A deliberately broken body raises `ParseError`, so the check can fail. This proves syntax only, not column names or semantics. |

Not run (heavy, window only): every database-backed test, listed in §5.

## 3. Contracts

**API surface:** 36 paths / 43 operations / 91 schemas → **38 / 45 / 96**. OpenAPI SHA-256
`008a7932…` → `0dbfbee44843c198c533d7a580df0fd8b768db010351c323b9518febfd8ecbfb`.

| Operation | Method and path | Roles | Refusals |
| --- | --- | --- | --- |
| `listWorkers` | `GET /execution/workers?cursor=&limit=` | any role, `role:admin\|expert` (R-80) | 401, 403, 422, 500, 503 |
| `setWorkerIntake` | `PUT /execution/workers/{worker_id}/intake`, `Idempotency-Key`, body `{enabled}` | `admin` | 401, 403, 404, 409, 422, 500, 503 |

New schemas: `WorkerId`, `WorkerState` (`online | stale | offline`), `ExecutionWorker`
(`worker_id`, `state`, `intake_enabled`, `slots ≥ 1`, `version`, `started_at`, `heartbeat_at`,
`current_run_ids`), `ExecutionWorkerPage`, `SetWorkerIntakeRequest`; one component parameter
`WorkerId`. Both operations are sealed stubs on `ExecutionAdapter` that raise
`dependency_unavailable` with `dependency: worker_registry`. **No error code was added** (catalog
23, stored vocabulary 22); `contract_version` stays `1.0.0-draft.1`. The `Role` schema
description and the security-scheme prose were corrected to R-80 (they still said product reads
need no role).

**Domain family:** candidate revision 9 → **10**. Identities `norm_custody_admission_id` (`nad`),
`norm_custody_binding_id` (`nbd`), `norm_repair_call_id` (`nrc`) with entities
`NormCustodyAdmission`, `NormCustodyBinding`, `NormRepairCall` and two distinct-identity rules
(`custody_identity`, `repair_call_identity`); `worker_id` (`wrk`) was already declared and is
unchanged. 29 → 32 identities. No machine, state or code changed.

**Migration head:** `0017_execution_queue` → `0018_norm_custody` → **`0019_execution_workers`**.

- `0018`: `norm_custody_admission` (intent and outbox in one row; `pending → confirmed | poisoned
  | rejected`, `poisoned → pending | rejected`; five tries; one live admission per slot; never
  deleted), `norm_custody_binding` (insert guard re-checks invariants 1–4; composite FK to the
  admission's tuple; immutable, never deleted), `ck_norm_custody_role_shape` on both
  (`norm_source → norm_document`, anchor `pdf | crop`), `norm_repair_call` (`prepared →
  response_received → completed`, `prepared → not_processed | outcome_unknown`; scope = own id;
  `not_processed` charges 0; `outcome_unknown` carries its charged bound; never deleted),
  `norm_paragraph.text_reliability`, `norms_snapshot.unreliable_count`, the replaced
  `ck_norms_snapshot_raw_key` (`repair_count = 0 AND unreliable_count = 0 ⇔ base = content key`),
  `analysis_artifact_publication.abandoned` with `abandoned_at` (D-142, `prepared → abandoned`
  only), and both effect-table state guards `BEFORE INSERT OR UPDATE` with insert ⇒ `prepared`
  (D-148). Downgrade refuses with any custody, repair, abandoned or unreliable row.
- `0019`: `worker` (only `heartbeat_at` and `intake_enabled` change; `slots ≥ 1`) and
  `lease.worker_id` (nullable, FK, joins `trg_lease_frozen_guard`). Downgrade refuses with any
  worker row or any lease naming one.

### Readings where the plan was silent (conservative choices)

1. *Four-document reseal* is `W49-SEAL-01a`'s set: the contract, the web mirror, the generated
   client and `FRONTEND_LOCK.json`. The domain family moves to revision 10 beside it.
2. `listWorkers` pages (`cursor`, `limit`, `{items, page}`), so it obeys D-67's collection rule
   and joins the page-shape sweep when WORKER removes the stub mark. `setWorkerIntake` takes an
   `Idempotency-Key` like the other execution controls (`setJobPriority`, `setExecutionPaused`).
3. Worker state is derived from `heartbeat_at` on read and never stored.
4. The custody outbox is the admission row (R-76 "intent plus outbox"); no `outbox` table exists,
   and `outbox` stays a forbidden table name in `test_migration_lifecycle.py`.
5. The repair checkpoint's **bytes are not a database column**: `test_schema_shape.py` bans
   `response_body` (a model payload) from every table. The row pins `response_sha256`; REPAIR
   keeps the bytes beside the fsynced local journal. `attempt_number` is only `≥ 1` in the
   database; R-79's three-try limit stays in REPAIR's code so an owner-approved rerun is possible.
6. `unreliable_count` counts repair-ledger blocks that did not end `REPAIRED` (the `m` of `+<m>u`).
7. Admission and repair-call deletes are refused inside their own state guards, not with
   `am_immutable_row`, because their state moves; only the binding is registered immutable.
8. `nad`, `nbd`, `nrc` are not added to `UNALLOCATED_IN_PC01`: their Stage-B owners allocate them
   in this wave. `worker_id` stays listed until WORKER allocates it.
9. `runs/scope.py` drops `worker` and `outbox` from `AGGREGATES_NOT_INSTANTIATED`; the
   remote-execution note is WORKER's line and is unchanged.

## 4. Risks and known limitations

- **No database ran.** Both migrations and their 29 new collected tests are unexecuted; the SQL is
  syntax-checked only. A wrong column name in a trigger body would surface first in the window.
- `tests/integration/db/test_schema_invariant_inventory.py` is **expected red** until resealed in
  the window. The reviewed per-family delta is written above `EXPECTED_INVENTORY`.
- `W54-WORKER-01` will need to remove `worker_id` from `UNALLOCATED_IN_PC01` and P02 §9.1 when it
  allocates the identity, but its grant does not name `shared/identity/ids.py` or `P02_SEAMS.md`.
- W57a must replace `ck_norm_custody_role_shape` on **both** tables and the binding guard's
  target arm (`am_guard_norm_custody_binding`).
- `pin_sweep.py` does not scan the top-level `tasks/` directory: three W53 task records state
  36 / 43 / 91. They are registered as history in `test_surface_counts_in_prose.py`
  (`KNOWN_HISTORICAL_SURFACE_CLAIMS`) rather than rewritten.
- `listWorkers` and `setWorkerIntake` answer 503 until `W54-WORKER-01`; the «Исполнители»
  screen is unchanged and calls neither.

## 5. Integrator instructions

1. Read the diff and this report; merge `agent/w54-seal-01` first in Stage A (plan §5).
2. **Heavy step, owner window only** (`W54-FREEZE-01`: `free` ≥ 6 GiB available and `df` ≥ the
   increment + 3 GiB, measured just before): bring up this lane's private stack on PostgreSQL
   `57110` and S3 `60710/60711` with a lane `.env`, then, from the worktree:

   ```sh
   set -a; . ./.env; set +a
   .venv/bin/python -m pytest -q tests/integration/db/test_norm_custody_migration.py \
       tests/integration/db/test_execution_workers_migration.py
   .venv/bin/python -m pytest -q tests/integration/db tests/integration/api \
       tests/integration/runs/test_idempotency_and_topology.py \
       tests/integration/runs/test_w53c_exec_closure.py \
       tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py \
       tests/integration/composition/test_router_answers.py \
       tests/integration/composition/test_composition_root.py \
       tests/integration/composition/test_api_token_channel.py \
       tests/integration/p02_journey
   ```

   Expect exactly one red: `test_schema_invariant_inventory.py`. Compare its printed inventory with
   the delta written above `EXPECTED_INVENTORY`; if it agrees, reseal the eleven tuples from the
   printed values (an integrator-owned edit) and rerun that file.
3. Stop the lane stack by its own compose project; kill nothing by pattern.
4. Stage B owners inherit: the stub mark (`SEALED_STUB_COLLECTIONS`, `SEALED_STUB_GETS`) for
   WORKER to empty; the custody and repair schema for CUSTODY and REPAIR; reading 5 for REPAIR.

## 6. Containment

- `git diff --name-only 7ebf162..HEAD`: the 70 paths of §1 plus this report. A script checked each
  against the 89 sweep paths and the §4 grant: none outside.
- Not touched: `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, root dependency and
  lock files, existing migrations, refs, tags, the stand, `.local/norms/**`, other worktrees.
- No container, no push, no merge, no tag. `git status --porcelain -uall` is empty after this
  commit.
