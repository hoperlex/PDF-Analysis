# Task EXEC-SEAL-01 — seal executor connections: contract, migration 0030, sealed secrets

task_id: EXEC-SEAL-01

## Outcome

Through the API, an administrator can do five things:

- create a connection of kind `http_api`, `ssh_command` or `pull`;
- add an immutable revision with its non-secret settings;
- set a **write-only** secret, which the `api` process seals to the stand's public key;
- request a probe, which is recorded as `requested`: the worker that executes probes
  arrives in `EXEC-HTTP-01`;
- set the route for `text_analysis`.

Any role can list connections and read one, and **no response, event or log ever carries
a secret**. Migration `0030` holds the tables. The `api` process loads public keys only;
the worker loader holds the private ring. A run's behaviour does not change: the provider
source stays `environment`. This is the plan's one enabling slice
(`CODE-FIRST-TO-BETA.md` §2.1 rule 2).

## Depends on

- `EXEC-RULE-01` — merged (`R-143`).

## Frozen inputs

- base commit: `origin/dev` at the integrator's freeze (planned on
  `7cb317b0a6fa9ae74c8a5e152419027ec37aca2d`);
- at the planning base: API 73 paths / 83 operations / 242 schemas, 27 error codes,
  migration head `0029_routing_refusal_codes`, contract and catalogue `1.0.0`. This task
  alone takes migration `0030` and the contract slot. The contract version label of the
  additive reseal is the integrator's call;
- plan `docs/program/dispatch/EXECUTOR-CONNECTIONS-PLAN.md` §2 (model, kinds), §3 (call-row
  and run columns), §4 (sealing, key ring, write-only, sentinel test), §5;
- rulings `R-143a`–`R-143c`, `R-133`, `R-29`; the error catalogue's detail-key ban
  (`contracts/domain/v1/error-codes.json:34-60`).

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: tests/support/expected_facts.json
- enumerator_owner: EXEC-SEAL-01 (migration head and API surface, after the integrator hands over both slots)
- totality_query: `python3 -c "import json;d=json.load(open('tests/support/expected_facts.json'));s=d['surface'];print(s['path_count'],len(s['operations']),len(s['schema_names']),d['migration_head'])"`

## Captured premise evidence

- premise: the surface is 73/83/242 at head `0029_routing_refusal_codes`, and `cryptography` is locked only transitively

### P-01 — the surface and migration head at the planning base
- captured_at: 2026-10-22
- command: `python3 -c "import json;d=json.load(open('tests/support/expected_facts.json'));s=d['surface'];print(s['path_count'],len(s['operations']),len(s['schema_names']),d['migration_head'])"`
- captured_output:
  ```text
  73 83 242 0029_routing_refusal_codes
  ```
- interpretation: the facts this task moves. They are re-measured at freeze, and a
  different value is reported, never assumed.

### P-02 — cryptography is locked transitively and is not a direct dependency
- captured_at: 2026-10-22
- command: `grep -n -A1 '^name = "cryptography"' uv.lock; grep -c cryptography pyproject.toml`
- captured_output:
  ```text
  239:name = "cryptography"
  240-version = "50.0.1"
  0
  ```
- interpretation: making it direct changes `pyproject.toml` and the project entry of
  `uv.lock` but not the resolved version. It is still the root lockfile hotspot
  (`AGENTS.md` §8 case 3).

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `pyproject.toml`
- `uv.lock`
- `db/migrations/versions/**`
- `contracts/api/v1/**`
- `contracts/domain/v1/**`
- `src/auditmanager/executors/**`
- `src/auditmanager/api/**`
- `src/auditmanager/bootstrap/settings.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `src/auditmanager/shared/identity/**`
- `src/auditmanager/shared/errors/**`
- `src/auditmanager/jobs/events.py`
- `scripts/recovery/schema_coverage.py`
- `scripts/recovery/product_purge.py`
- `tests/integration/recovery/**`
- `infra/deploy/README.md`
- `infra/deploy/serve.py`
- `infra/deploy/proxy/nginx.conf`
- `web/src/app/bff/v1/[...path]/route.ts`
- `web/docs/PC01_UI_SEAM.md`
- `docs/program/ALPHA_ROADMAP.md`
- `docs/program/P02_SEAMS.md`
- `infra/deploy/env/alpha.env.example`
- `infra/deploy/env/provider.env.example`
- `tests/support/**`
- `tests/contract/**`
- `tests/integration/db/**`
- `tests/integration/api/**`
- `tests/integration/composition/**`
- `tests/integration/executors/**`
- `tests/unit/executors/**`
- `web/openapi/**`
- `web/FRONTEND_LOCK.json`
- `web/src/shared/api/**`
- `web/tests/**`
- `docs/manual-tests/PC-01_prototype.md`
- `docs/program/CONTRACT_PIN_REGISTRY.md`
- `docs/program/EXEC-SEAL-01.md`

## Forbidden hotspots

`src/auditmanager/runs/**`, `src/auditmanager/analysis/**`, `src/auditmanager/workers/**`
(the run path and the worker belong to `EXEC-HTTP-01`). Also forbidden:

- `web/src/**` outside `shared/api` and the one surface-count comment in the BFF route;
- `infra/**` outside the two env examples, and outside the surface-count prose in
  `infra/deploy/README.md`, `serve.py` and `nginx.conf` (comments only; no directive
  changes);
- `web/package.json` and `web/package-lock.json`;
- `CURRENT_STATE.md`, `DEBT_REGISTER.md`, refs, tags and the stand.

A pin file outside the grant that the step-0 probe finds is reported to the integrator,
who grants it as a one-line addendum. It is not edited first.

## Non-goals

No run-path change, no UI and no probe execution. No runner tokens or tasks: those belong
to `EXEC-PULL-01` and migration `0031`. SSH key generation *is* sealed here (`generateExecutorSshKey`, below); running SSH is
`EXEC-SSH-01`. No new
error code unless step 0 shows that no existing code can carry the meaning; prefer
`validation_failed`, `conflict`, `permission_denied` and `dependency_unavailable`, with a
typed `reason` detail. No paid call.

## Work

0. **Probe before granting.** On a disposable branch, add one dummy operation, one schema
   and an empty migration `0030`, run `pytest tests/contract` (container-free), and list
   every file that fails. Report that list before the real work; it is the pin sweep.
1. **New bounded context `src/auditmanager/executors/`:**
   - `model.py` (kinds, settings validation per kind, the route vocabulary `text_analysis`);
   - `sealing.py`: X25519 + HKDF-SHA256 + AES-256-GCM. The associated data is
     `secret_id|connection_id|purpose|kid|destination`. The destination is the
     normalised `scheme://host:port` for `http_api`, or `host:port` for SSH (plan §4.1).
     The module also holds a key ring, a public-only loader for the `api` and a private
     loader for the worker. There is no fingerprint; the API stores and returns only
     `last4`;
   - `repository.py` (the only writer of the new tables);
   - `commands.py`, following `workers/commands.py`: role check, command ledger, event,
     `succeed`;
   - `public.py` and a `README.md`.
2. **Migration `0030`:**
   - `executor_connection` (`exc_<ULID>`);
   - `executor_connection_revision` (`excr_<ULID>`, immutable);
   - `executor_secret`: only `replaced_at` is mutable. The ciphertext is `bytea`, and the
     row carries `kid`, `destination` and `last4`, plus nullable `public_material` for
     the public half of a generated SSH key;
   - `executor_connection_revision` carries the pin id and the gateway model name as
     separate fields (plan §3), neither derived from the other;
   - `executor_probe` (state and outcome vocabulary: `requested`, `ok`, `ip_refused`,
     `credential_refused`, `model_mismatch`, `rate_mismatch`, `timeout`, `unreachable`,
     `protocol_error`, `secret_unreadable`, `host_key_unpinned`, `host_key_changed`,
     `no_runner_online`);
   - `executor_route_event`, append-only, with a current view;
   - nullable `connection_revision_id` and `identity_basis` (`reported`, `declared`) on
     `model_call` and `provider_call_effect`;
   - the frozen revision on the run. `trg_audit_run_frozen_guard` is BEFORE UPDATE only
     (`0002:1289`, replaced in `0017:34-36`), so a column set at insert passes. Add the
     new column to that trigger's frozen list the way `0017` does, so it actually
     freezes;
   - `CostBasis` and `ck_model_call_cost_basis` (`0004`) gain `unmetered` (plan §5);
   - `scripts/recovery/product_purge.py` and `schema_coverage.py` classify every new
     table, command type and event type. Every `executor_*` table is KEEP; `executor_task`
     arrives in `0031`, as PRODUCT.

   Upgrade and downgrade are tested; downgrade refuses once data exists, as `0019` does.
   Identifier prefixes are checked against `contracts/domain/v1/identifiers.json` for
   collisions.
3. **Contract (additive), with the generated client and the frontend lock regenerated.**
   Proposed operations:
   - `listExecutorConnections`, `createExecutorConnection` and `getExecutorConnection`;
   - `reviseExecutorConnection` and `archiveExecutorConnection`;
   - `setExecutorSecret`, which takes a body, returns metadata only, and never has a GET
     counterpart;
   - `requestExecutorProbe`;
   - `generateExecutorSshKey`. The `api` generates an ed25519 pair, seals the private
     half to the connection's `host:port` and stores the public half as
     `public_material`. The response returns only the public half and the
     `authorized_keys` line;
   - `listExecutorRoutes` and `setExecutorRoute`.

   The final names are fixed here and reported. Writes go to admin in `OPERATION_ROLES`
   (`api/security.py`); reads go to any role, with the secret fields absent by schema.
4. **Settings.** Add `AUDITMANAGER_SECRETS_PUBLIC_KEYS` (for the `api`),
   `AUDITMANAGER_SECRETS_KEYS` and `AUDITMANAGER_SECRETS_ACTIVE_KID` (worker only), and
   document them in the two env examples. `setExecutorSecret` without public keys is a
   typed refusal; it never stores plaintext.
5. **The sentinel test** (plan §4.2). A sentinel key set through the API must not occur in
   any of these:
   - any API response;
   - an `audit_event` payload;
   - `command_record`;
   - a log captured by the test;
   - a `pg_dump --data-only` text of the lane database.

   The ciphertext opens only with the private ring. Every new guard is shown failing under
   a quoted mutation.

## Deliverables

The context, the migration, the contract reseal, the tests, and the report
`docs/program/EXEC-SEAL-01.md` (the step-0 pin list, the operation names, the column
placement, the commands with exit status, and what was deferred under `R-135`).

## Required tests

- command: `python3 -m pytest -q tests/contract/api_v1 tests/contract/program tests/contract/domain_p02` plus every contract file the step-0 probe names (container-free; `R-135` forbids the whole battery)
- expected: all passed.
- command: `python3 -m pytest -q tests/integration/recovery -k "purge or schema_coverage"` on the lane's own containers
- expected: the classification of every new table, command type and event type passes.
- command: `python3 -m pytest -q tests/unit/executors tests/integration/executors tests/integration/db/test_downgrade_chain_round_trip.py` on the lane's own containers
- expected: all passed; the upgrade from `0029` and the downgrade to `0029` on an empty
  database are both shown.
- command: `npm --prefix web run typecheck && npm --prefix web test -- --run web/tests/contract`
- expected: green after the client regeneration.
- `AGENTS.md` §8 case 3 applies (lockfile, contract, migration). Under `R-135` the
  integrator records whether the complete gate runs on this slice in a window or is carried
  to the final beta gate.

## Integration contract

After merge, `EXEC-HTTP-01` can rely on the following:

- the tables and operations above;
- `executors.public` exposing `resolve_route(work_kind)`, `open_secret(secret_id)` (worker
  only), `record_probe_result(...)` and `current_revision(connection_id)`;
- `connection_revision_id` columns that are writable at insert.

The integrator hands the composition-root slot to `EXEC-HTTP-01` after this merge.

## Failure/idempotency/security cases

- **Commands and refusals.**
  - Every command is idempotent under the ledger; a replay returns the same metadata.
  - An expert writing gets `permission_denied`.
  - An unpinned model in a revision is refused with `validation_failed` and reason
    `model_not_pinned` (`analysis/text/lock.py:69-83`).
  - A `base_url` with `?` or `#` is refused, as `proxy.py` refuses it.
  - Archiving a connection that a route still names is a `conflict`.
- **Secrets.**
  - A secret is never echoed, even in a validation error.
  - The ring is never logged.
  - A wrong-kid ciphertext opens as `secret_unreadable`, never as an exception carrying
    bytes.

## Rollback / feature flag

No behaviour switch exists yet: the provider source stays `environment`. Rollback is to
revert the merge; the migration downgrade refuses once data exists, as `0019` does.

## Handoff

- changed files: tabulated with the reason for each;
- commands/results: each with its exit status;
- known limits: probes stay `requested` until `EXEC-HTTP-01`;
- integration notes: the slot hand-over to `EXEC-HTTP-01`.
