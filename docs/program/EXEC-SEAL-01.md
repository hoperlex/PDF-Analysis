STATUS: step 7/7 done, stack down (12:42 +05)

# EXEC-SEAL-01 report

Worktree `.local/worktrees/exec-line`, branch `agent/exec-line-01`, base `origin/dev` `fa4ef645` plus the two ruling
commits (`24e15247`). Owner rulings `R-143`, `R-144`; the checks are the minimal set of `R-144b`. Nothing was pushed,
merged or tagged. Final commit: see section 9.

## 1. Operation names, identifiers and the migration

Ten additive operations (surface 73/83/242 -> 81/93/272; contract label stays `1.0.0`, the integrator's call):

| operationId | method and path | role |
|---|---|---|
| `listExecutorConnections` | `GET /executor-connections` (also `pinned_models`) | any |
| `createExecutorConnection` | `POST /executor-connections` | admin |
| `getExecutorConnection` | `GET /executor-connections/{connection_id}` | any |
| `reviseExecutorConnection` | `POST /executor-connections/{connection_id}/revisions` | admin |
| `archiveExecutorConnection` | `POST /executor-connections/{connection_id}/archive` | admin |
| `setExecutorSecret` | `POST /executor-connections/{connection_id}/secrets` (write-only, no GET) | admin |
| `generateExecutorSshKey` | `POST /executor-connections/{connection_id}/ssh-key` | admin |
| `requestExecutorProbe` | `POST /executor-connections/{connection_id}/probes` (202) | admin |
| `listExecutorRoutes` | `GET /executor-routes` | any |
| `setExecutorRoute` | `PUT /executor-routes` | admin |

`CostBasis` gains `unmetered`. `generateExecutorSshKey` answers `sealed_private_key` (secret metadata), `public_key` and
`authorized_keys_line`; the property is not called `secret` because `test_no_schema_property_names_an_address_or_a_secret`
bans that name. No new error code: the new `constraint`, `conflict_reason` and `dependency` values are notes on
`validation_failed`, `conflict` and `dependency_unavailable` in `contracts/domain/v1/error-codes.json`.

Identifier prefixes (no collision with the 40 existing): `exc` connection, `excr` revision, `exs` secret, `epb` probe,
`ert` route event.

Migration revision id: **`0030_executor_connections`** (`db/migrations/versions/20261022_0030_executor_connections.py`).

Column placement:

- `executor_connection(connection_id, kind, display_name, created_at, created_by, archived_at, archived_by)`; frozen
  guard plus write-once `archived_*`.
- `executor_connection_revision`: `pin_id` and `gateway_model` are two columns, neither derived from the other;
  `host_key` is the full public key line (the fingerprint is derived on read); immutable (`am_immutable_row`).
- `executor_secret(secret_id, connection_id, purpose, kid, destination, ciphertext bytea, last4, public_material,
  set_at, set_by, replaced_at)`; only `replaced_at` moves, once; one current row per connection and purpose (partial
  unique index).
- `executor_probe` with the columns of the task text and `ck_executor_probe_state_shape`; `(revision_id,
  connection_id)` is a composite foreign key.
- `executor_route_event` (append-only, `route_no` per work kind) and the view `executor_route_current`.
- `audit_run.connection_revision_id` (added to the frozen list of `trg_audit_run_frozen_guard`), and
  `connection_revision_id` + `identity_basis` on `model_call` and `provider_call_effect` (both or neither;
  `ck_*_basis_with_revision`). `ck_model_call_cost_basis` accepts `unmetered`.
- Every foreign-key identity column carries its format CHECK (`ck_executor_*_format`; found by `test_schema_shape`).
- Downgrade refuses once any executor row, any run/call/effect naming a revision, or any `unmetered` call exists.

## 2. Sealing

`src/auditmanager/executors/sealing.py`: X25519 + HKDF-SHA256 + AES-256-GCM; associated data
`secret_id|connection_id|purpose|kid|destination`, destination `transport|ssh_endpoint|origin` built by
`model.destination_for` and recomputed by the caller of `public.open_secret(session, ring, secret_id=, destination=)`;
the stored `destination` column is informational. Rings: `load_public_ring` (api, public keys only) and
`load_private_ring` (worker). `settings.load` refuses `AUDITMANAGER_SECRETS_KEYS` on `EXECUTION_ROLE=api`. Without a
public key `setExecutorSecret` is `503 dependency_unavailable` (`secrets_public_key_missing`) and nothing is stored.
`set_secret`'s idempotency fingerprint excludes the value (an unkeyed hash of a secret is refused by the plan), so a
repeat under the same key replays the first answer.

## 3. Changed files, with the reason for each (`git diff --name-only 24e15247..HEAD`, 85 files, all inside `allowed_paths`)

| Files | Reason |
|---|---|
| `contracts/api/v1/openapi.json`, `web/openapi/openapi.json` | ten operations, thirty schemas, `CostBasis.unmetered`, `StateConflict` and `info` prose; spliced as text, mirror byte-identical |
| `contracts/domain/v1/identifiers.json`, `error-codes.json`, `src/auditmanager/shared/identity/{__init__,ids}.py` | five identifier prefixes with their types; notes for the new `constraint`, `conflict_reason`, `dependency` values (no new code) |
| `db/migrations/versions/20261022_0030_executor_connections.py` | the migration (section 1) |
| `src/auditmanager/executors/**` (new: `model`, `sealing`, `repository`, `commands`, `queries`, `public`, `README`, `__init__`) | the bounded context |
| `src/auditmanager/api/{routers/executors.py,routers/ports.py,routers/__init__.py,schemas/models.py,security.py}` + prose files | the ten routes, `ExecutorPort`, Pydantic models, `OPERATION_ROLES` (reads any role, writes admin), surface-count prose |
| `src/auditmanager/bootstrap/{adapters,composition,settings}.py`, `jobs/events.py` | `ExecutorAdapter`, wiring over the public ring, the three env names, journal payload allowlist |
| `src/auditmanager/analysis/{public.py,text/lock.py}` | export-only `pinned_models()` |
| `scripts/recovery/{schema_coverage,product_purge}.py` | five tables KEEP, seven command types KEEP, `executor.` events KEEP, `HEAD`, constraint and index counts, view and triggers |
| `pyproject.toml`, `uv.lock` | `cryptography==50.0.1` direct (the version the lock already held) |
| `infra/deploy/{README.md,serve.py,proxy/nginx.conf}`, `env/{alpha,provider}.env.example` | surface-count prose only (no directive changed); the ring documented |
| `web/src/shared/api/**` (generated), `web/FRONTEND_LOCK.json` | client regenerated with `node scripts/generate-api-client.mjs` (`--check` OK), lock digests, counts (81/93/272) and content commit `c00b276a` |
| `web/src/{shared/ui/run-state-badge.tsx, entities/audit-run/model/run-{presentation,comparison}.ts, widgets/run-progress/ui/run-progress.tsx, widgets/dashboard/ui/run-activity-panel.tsx, widgets/stage-comparison/ui/stage-comparison.tsx}` | the six `CostBasis` consumers: only the `unmetered` case |
| `tests/support/expected_facts.json`, `tests/contract/**`, `docs/program/{P02_SEAMS,ALPHA_ROADMAP}.md`, `docs/manual-tests/PC-01_prototype.md` | the pin sweep (section 4) |
| `tests/unit/executors/**` (48), `tests/integration/executors/**` (41), `tests/integration/db/test_executor_connections_migration.py` (17), `web/tests/**` | new tests; moved pins |
| `tests/integration/{db,api,recovery}/**` | pins moved by the migration and the surface (section 4) |

## 4. Step-0 pin sweep (what the surface and the migration move)

The planned dummy-operation probe was refused by the permission classifier ("modify shared resources"), so I did not
work around it. I made the real contract change first and ran the three contract directories, and I swept the tree
statically. The files that name the surface, the schemas, the migration head or the identifier set, all now moved:

- `tests/support/expected_facts.json` (path count, operations, schema names, head);
- `tests/contract/api_v1/test_surface_counts_in_prose.py` and thirteen prose files it names (`docs/program/P02_SEAMS.md`,
  `infra/deploy/{README.md,proxy/nginx.conf,serve.py}`, `src/auditmanager/api/{README.md,app.py,health.py}`,
  `api/routers/{__init__,declarations,errors}.py`, `web/src/app/bff/v1/[...path]/route.ts`,
  `web/src/shared/api/authorization.ts`, `ALPHA_ROADMAP.md`) and the contract's own `info` prose (a sealed paragraph
  stated "73 paths, 83 operations, 242 schemas" as a count; I reworded it to carry no count);
- `tests/contract/api_v1/test_openapi_conformance.py` (404 count 58 to 65), `test_w55b_portal_bundle_seal.py` (identity
  count 40 to 45), `tests/contract/domain_p02/test_openapi_document.py` (declared capabilities, keyed writes, input-less
  set; its secret-property detector bans the name `secret`, hence `sealed_private_key`), `test_seam_register.py` through
  `P02_SEAMS.md` (table rows and the idempotency rule);
- `tests/integration/api/{test_role_register,test_authorization,test_served_document_and_health_plane}.py`;
- `tests/integration/db/{test_downgrade_chain_round_trip,test_schema_invariant_inventory,test_migration_lifecycle,test_schema_shape}.py`,
  `tests/integration/recovery/{test_product_purge,test_synthetic_drill_seed,test_synthetic_drill_compare}.py`,
  `scripts/recovery/schema_coverage.py` (`HEAD`, constraint and index counts);
- `docs/manual-tests/PC-01_prototype.md` (head), `web/FRONTEND_LOCK.json`;
- **outside the grant, reported not edited:** `docs/program/CURRENT_STATE.md`. The two failing assertions in
  `tests/contract/api_v1/test_doc_prose_facts.py` are exactly:
  `CURRENT_STATE.md: 'migration head is **`0029_routing' names head 0029, tree has 0030_executor_connections` and
  `CURRENT_STATE.md: '73 paths / 83 operations / 242 schemas' states ..., tree has SurfaceTriple(paths=81, operations=93, schemas=272)`.
  The integrator closes both in the merge.

## 5. Checks and results (commands, exit status, counts)

Container-free (this tree, system `python3`, `nice -n 19 ionice -c3`):

| Command | Result |
|---|---|
| `python3 -m pytest -q -p no:cacheprovider tests/unit/executors tests/contract/api_v1 tests/contract/program tests/contract/domain_p02` | 551 passed, 2 failed (the two `CURRENT_STATE.md` assertions above) |
| `npm --prefix web run typecheck` | exit 0 |
| `npm --prefix web run lint -- --quiet` | exit 0 |
| `node web/scripts/generate-api-client.mjs --check` | OK, 93 operations |
| the frontend lock, recomputed in Python (digests of contract, snapshot, generator, four generated files; counts 81/93/272) | True |
| `git diff --check` | clean |

Container-backed, on the lane stack `auditmanager-exec-line` (57660 / 61460 / 61461), single files, one process at a time,
gate at 89-91% and `END` absent at every run (never 96%); times HH:MM:SS +05:

| Start - end | What | Result |
|---|---|---|
| 12:26:05 - 12:26:16 / 12:26:20 - 12:26:22 | `make up`, `make migrate` (0001 to 0030) | ok |
| 12:26:46 - 12:26:55 | `tests/integration/db/test_executor_connections_migration.py` | 11 passed (final: 17 passed, 12:39:19 - 12:39:31) |
| 12:27:11 - 12:27:57 | `tests/integration/executors/{test_executor_commands,test_executor_surface,test_secret_never_leaves}.py` | 26 + 10 + 5 passed (final reruns 12:39:31 - 12:39:52 on a fresh database: the same) |
| 12:27:52 - 12:28:40 | `tests/integration/db/test_schema_invariant_inventory.py` | red once, resealed from the measurement, then 2 passed |
| 12:28:44 - 12:29:07 | `tests/integration/db/test_downgrade_chain_round_trip.py` | 14 passed (after the CHECK fix: 12:37:42 - 12:38:04, 14 passed) |
| 12:29:12 - 12:30:27 | `tests/integration/recovery/{test_schema_coverage,test_product_purge}.py` | 30 passed; 61 passed and 1 red (KEEP count 23 to 28), fixed, rerun passed |
| 12:30:39 - 12:32:34 | `tests/integration/api/{test_authorization,test_served_document_and_health_plane,test_role_register}.py` | 35 + 1 red fixed (`executors.py` joins the subject readers), 10, 24 passed |
| 12:32:45 - 12:33:01 | `tests/integration/composition/{test_composition_root,test_settings_defaults,test_api_token_channel}.py` | 21, 34, 10 passed |
| 12:35:04 - 12:36:20 | `tests/integration/db/{test_every_immutable_table_refuses_a_write,test_migration_lifecycle,test_schema_shape}.py` | 7 passed; two lists and a view moved; `test_schema_shape` found seven foreign-key columns without an identity-format CHECK, fixed in the migration |
| 12:36:58 - 12:39:07 | database dropped and recreated, `make migrate`, then `test_schema_invariant_inventory`, `test_schema_shape`, `test_schema_coverage`, the migration test, the downgrade chain, `test_synthetic_drill_seed` (60 tables) and `test_synthetic_drill_compare` | all passed |
| 12:40:55 - 12:41:12 | `make down` | stack down, ports free |

Measured, matching what I predicted from the DDL before the first run: constraints c 510 / f 120 / p 59 / t 8 / u 42,
indexes 168, triggers 79, relations 72, views 5, columns 682.

Quoted mutations (each red, then reverted with `git checkout`): the associated data without the destination (3 sealing
tests red); `base_url` query accepted (4 red); pin check skipped (1); the api accepts the private ring (1); an api key's
destination ignoring the SSH endpoint (1); `open_secret` building the associated data from the row's destination
(`test_revising_the_address_leaves_the_old_secret_unreadable_for_it` red); archive ignoring routes (red); the probe sweep
never ending an untaken probe (red); the secret value written into the journal payload (the sentinel test red); the
run's frozen list without `connection_revision_id` (`test_a_run_never_changes_its_frozen_revision` red); `executor_secret`
dropped from KEEP (two red).

## 6. What was not run

No `make gate`, no whole directory, no battery (R-144b); **no vitest** (the host-gate owner excluded it), so the web unit
tests I added (`cost.test.ts`, `run-progress.test.ts`, `run-comparison.test.ts`), the rendered-language guard with the new
`unmetered-run` state, and `frontend-lock.guard.test.ts` are unexecuted (typecheck and lint are green; the lock was
recomputed in Python); no `next build`; no live journey or e2e; the rest of `tests/integration/recovery` (restore drills,
object copy, product-purge script), `tests/integration/api` beyond the three files, `tests/integration/composition`
beyond three, `tests/integration/workers`.

## 7. Risks and known limitations

- Actor columns (`created_by`, `set_by`, `requested_by`, `archived_by`) hold a `usr` identity with a format CHECK and **no
  foreign key to `app_user`**: a key would have to be registered in `access/references.py`, outside this grant. A purged
  account leaves its id in the history.
- `setExecutorSecret`'s idempotency fingerprint excludes the value (an unkeyed digest of a secret is refused by the plan),
  so a repeat under one key replays the first answer. The UI must send a fresh key per submission.
- `last4` is shown only for an `api_key` of at least 16 characters (half of a short key must not be revealed); a generated
  SSH key shows the last four of its public blob.
- **Deployment hazard:** today both `api` and `worker` read the same `provider.env`; the `api` refuses to start when
  `AUDITMANAGER_SECRETS_KEYS` is set. Until `EXEC-HTTP-01` gives the worker its own file, only the public ring may be put
  there (documented in `provider.env.example`).
- The migration changed after `63540e80` (seven identity-format CHECKs on foreign-key columns): a database migrated at the
  earlier 0030 has not got them. The lane database was dropped and rebuilt; the `exec-http` lane, based on `63540e80`,
  should rebuild its database before relying on the constraint counts.
- The sentinel dump test commits rows to the lane database on purpose (`pg_dump` reads its own snapshot). They are
  append-only and harmless; every assertion is keyed to ids the test created.
- The contract label (`info.version`) stays `1.0.0`; the label of the additive reseal is the integrator's call.
- `docs/program/P02_LOCK.json` was not touched (not in the grant); no test requires a record for `cryptography`.
- A running probe whose worker vanished ends as `timeout` after its revision's timeout plus 30 s: this is my addition to the
  120 s `no_worker` rule, in the same sweep.
- `GET .../secrets` answers the `not_found` envelope (the application maps an unrouted method to it), not 405.

## 8. Integration notes

- Hand the composition-root slot and the contract slot to `EXEC-HTTP-01` after this merge; it relies on
  `executors.public.{resolve_route, current_revision, pinned_models, record_probe_started, record_probe_result,
  open_secret}`, the nullable `connection_revision_id` / `identity_basis` columns (writable at insert) and
  `sealing.load_private_ring`.
- Merge also needs: `CURRENT_STATE.md` (head `0030_executor_connections`, 81/93/272), and the contract version label.
- A worktree needs a `.venv` and `.env` to run the container-backed files; I used an untracked `.venv` symlink to the main
  checkout's environment and an untracked `.env` with the lane values (both git-ignored).
- Forbidden hotspots untouched: `git diff --name-only 24e15247..HEAD` has no path under `src/auditmanager/runs/**`,
  `src/auditmanager/workers/**` or `src/auditmanager/analysis/**` other than `analysis/public.py` and
  `analysis/text/lock.py` (the export-only `pinned_models()`), no `infra/**` outside the two env examples and three prose
  files, no `web/package*.json`, no `CURRENT_STATE.md`, `DEBT_REGISTER.md`, ref or tag.

## 9. Final state

Branch `agent/exec-line-01`; the last code commit is `9cae7589`, and the head after this report is recorded in the
hand-back. The report itself lives at `docs/program/EXEC-SEAL-01.md`.
