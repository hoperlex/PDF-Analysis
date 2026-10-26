# Task EXEC-PAR-START-01 — start a run on an explicitly chosen executor

task_id: EXEC-PAR-START-01

## Outcome

`startRun` accepts an optional `executor_connection_id`. Absent: the run is started exactly as
today (global route, standby rule). Present: the run freezes **that connection's current
revision** if it passes the same usability test as a routed primary (served by this release,
probed `ok` on its current key, not archived). If not, the start is refused and no run exists.
An explicit choice never falls back to the standby or to any other connection. The run's status
tells which executor it is on, so the web can show it. «Повторить прогон» keeps the original
run's executor.

## Depends on

- `EXEC-HTTP-01`, `EXEC-PULL-01`, `EXEC-SSH-01` — completed (the connection kinds).
- `EXEC-PAR-DECISION-01` — the decision record.

## Frozen inputs

- base commit: `f6ee66ee73d0bfb7e87cc6a057d010be8d1df4e5` (`origin/main`); this lane starts from
  branch `plan/exec-parallel-runs`, which adds documents only;
- shared contract `1.5.0`, API 92 paths / 104 operations / 300 schemas, 27 error codes, migration
  head `0032_ar_v3_run_group`;
- `docs/program/dispatch/EXEC-PARALLEL-RUNS-PLAN.md`, `docs/program/EXEC-PAR-DECISION-01.md`;
- the recipe of the last additive API change: `docs/program/tasks/AR-V3-BETA-PACK-STATUS-API-01.md`
  and `docs/program/AR-V3-BETA-PACK-STATUS-API-01.md` (what a contract change touches).

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: contracts/api/v1/openapi.json
- enumerator_owner: EXEC-PAR-START-01
- totality_query: `python3 -c "import json; d=json.load(open('contracts/api/v1/openapi.json')); print(len(d['paths']), sum(len([m for m in v if m in ('get','put','post','delete','patch')]) for v in d['paths'].values()), len(d['components']['schemas']))"` — the counts must be recomputed and every prose count that names them updated (the prose-count guards list them).

## Captured premise evidence

- premise: `StartRunRequest` has no executor field
- captured_at: 2026-10-26
- command: `python3 -c "import json; d=json.load(open('contracts/api/v1/openapi.json')); s=d['components']['schemas']['StartRunRequest']; print(sorted(s['properties']), s.get('required'))"`
- captured_output:
  ```text
  ['provider_mode', 'version_uid'] ['version_uid']
  ```
- interpretation: the optional field is additive; nothing existing is renamed.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

The lane commits to its own branch only. It does not merge, push or tag.

## Allowed paths

Start from the recipe's list and **derive the exact set from the tree**: run the seal and prose
guards (`tests/contract`), list what they name, and record every path beyond the core below with
its reason in the report, as the recipe's report did.

- `contracts/**` (this lane owns the contract slot)
- `src/auditmanager/executors/resolver.py`, `src/auditmanager/executors/queries.py`,
  `src/auditmanager/executors/runtime.py`, `src/auditmanager/executors/public.py`
- `src/auditmanager/runs/commands.py` and the run-start files it needs under `src/auditmanager/runs/`
- `src/auditmanager/api/routers/runs.py`, `src/auditmanager/api/**` files that map `StartRunRequest`
  and `RunStatus`
- `src/auditmanager/bootstrap/providers.py` (the `freeze` seam only)
- `scripts/recovery/product_purge.py` and the event registry, if a new event type is journalled
- `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json`, `web/tests/**` files that pin counts or the
  contract version (exact paths, with reasons)
- `infra/deploy/proxy/nginx.conf`, `infra/deploy/proxy/tls-server.conf`, `infra/deploy/README.md`,
  `infra/deploy/serve.py` — only the version literals and surface counts the seal test names
- `tests/unit/executors/**`, `tests/unit/runs/**`, `tests/integration/runs/**`,
  `tests/integration/api/**`, `tests/contract/**`
- `docs/program/tasks/EXEC-PAR-START-01.md`, `docs/program/EXEC-PAR-START-01.md`

### Derived additions (found by the lane, each with its measured reason)

The exact set came from the tree: the seal and prose guards were run, every path that had to
move was listed, and a path was kept only if reverting it turned a guard red (or the code could
not work without it). Full reasons and the red guard per path are in
[`../EXEC-PAR-START-01.md`](../EXEC-PAR-START-01.md).

- `src/auditmanager/bootstrap/adapters.py` — the one place that joins runs and executors:
  `RunAdapter.start_run` passes the choice, `_run_status_view` fills `executor`. Not
  `composition.py`.
- `src/auditmanager/runs/provider.py`, `src/auditmanager/runs/repository.py` — the freeze seam's
  types (`FrozenRoute.chosen_connection_id`, `RouteFreezer`) and the reader of the run's choice
  event (`RunRepository.chosen_executor_connection`); run-start files under `runs/`.
- `src/auditmanager/api/routers/ports.py`, `src/auditmanager/api/schemas/models.py`,
  `src/auditmanager/api/schemas/runs.py` — the port, the request/response models and the status
  view (the `api/**` files that map `StartRunRequest` and `RunStatus`).
- `src/auditmanager/api/routers/__init__.py`, `src/auditmanager/analysis/engine/result.py`,
  `src/auditmanager/api/schemas/models.py` (`ErrorEnvelope`) — the `CONTRACT_VERSION` constants
  `test_contract_seal` equates with the sealed version.
- `src/auditmanager/api/app.py`, `src/auditmanager/api/routers/declarations.py`,
  `docs/program/ALPHA_ROADMAP.md` — the schema count in prose, read by
  `test_surface_counts_in_prose` and `test_doc_prose_facts`.
- `web/src/shared/api/credentialed-forward.ts` — the edge forwarder's own error body carries the
  version literal `test_contract_seal` reads.
- `tests/support/expected_facts.json` — the independent surface and version facts.
- `tests/integration/executors/test_explicit_executor.py` (new, database-backed),
  `tests/integration/runs/test_w55a_pin_offline.py` (its fake run row gains the
  `connection_revision_id` a real `RunRow` always has).
- `web/tests/**` — the 44 files whose error-envelope fixtures say `contract_version: '1.5.0'`
  (typed against the generated `ErrorEnvelope`, and asserted by the two forwarder tests).

## Forbidden hotspots

- `src/auditmanager/jobs/**`, `src/auditmanager/workers/**`, `src/auditmanager/bootstrap/composition.py`
  (owned by `EXEC-PAR-QUEUE-01`);
- `db/migrations/**` (no migration is expected: `audit_run.connection_revision_id` exists — if the
  work seems to need one, stop and report);
- `web/src/features/**`, `web/src/widgets/**`, `web/src/entities/**`, `web/src/app/**` (owned by
  `EXEC-PAR-WEB-01`);
- root dependency and lock files, global styles, `docs/program/CURRENT_STATE.md`, refs, tags, the stand.

## Non-goals

No new error code (use `dependency_unavailable` with `dependency` and a reason, and
`validation_failed` with `field: executor_connection_id` for a malformed or unknown id). No new
operation and no change to the routes or to who may administer connections. No parallelism and no
queue change. No UI.

## Work

1. **Contract.** Add optional `executor_connection_id` to `StartRunRequest`; add a nullable
   read-only `executor` to the run status (and to the run list item if it has its own schema):
   `connection_id`, `display_name`, `pin_id` — and nothing secret. Seal the version the way the
   recipe does; recompute the counts and fix every prose count.
2. **Freezing.** Give `freeze_connection` an optional `connection_id`. With it, resolve that
   connection's current revision, apply `_why_unusable`, and raise the typed refusal on failure;
   never read the route or the standby. Without it, behaviour is byte-for-byte today's.
3. **Run start.** Pass the choice through the start command and the `freeze` seam. The idempotency
   fingerprint (`start_run_fingerprint`) **must include the choice**: the same key with another
   executor is a conflict, not a replay. Journal the explicit choice as an event, as
   `audit_run.standby_used` is, and classify the event for the product purge and the event registry.
4. **Repeat.** `reauditRun` freezes the original run's connection (not the route) when the original
   was explicit, and is refused when that connection is no longer usable.
5. **Read.** Fill `executor` from the frozen revision for runs that have one; `null` otherwise.
6. **Client.** Regenerate the web client and fix only the files the contract seal and the count
   guards force; do not write UI.

## Deliverables

The contract change, the freezing and start code, the tests, the regenerated client, and the
report `docs/program/EXEC-PAR-START-01.md` (what was changed with reasons for each path beyond the
core list, commands and results, mutation table, known limits, integration note).

## Required tests

- command: `/root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/executors tests/unit/runs`; expected: pass.
- command: the gate's own contract invocation — `.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py`; expected: pass (baseline 1155).
- command: `node web/scripts/generate-api-client.mjs --check`; expected: OK with the new operation/schema counts.
- the integration tests that need a database: run them only if a database is already provided to you; otherwise list them as not run. Do not start docker for this lane.
- command: `git diff --check`; expected: exit 0.

## Integration contract

An absent choice is today's behaviour. A present choice either freezes the named connection's
current revision or refuses before any run row exists. The refusal reuses `dependency_unavailable`
(`dependency: executor_connection`, a reason word) and `validation_failed`. The run status gains
`executor` (nullable). Nothing about a key, an address or a token is exposed.

## Failure/idempotency/security cases

- unknown, archived, unserved, unprobed or probe-failed connection: refused, no run, no event;
- a connection whose key is not readable for its address: refused at start as today's route would;
- the same idempotency key with a different `executor_connection_id`: a conflict, not a replay;
- a repeat of an explicit run whose connection became unusable: refused, never redirected;
- any role that may start a run may choose among connections it can already read (reads are open to
  every role); the choice grants no write access to connections.

## Rollback / feature flag

Omit the field: behaviour is unchanged. Revert the lane's commits to remove the field; there is no
data migration.

## Handoff

changed files with reasons; commands and results; the mutation table (each guard shown red once);
the contract version and counts; risks; the instruction to the integrator; proof the forbidden
hotspots are untouched (`git diff --stat` of those paths).
