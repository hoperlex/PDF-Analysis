STATUS: step 6/7 done, waiting for END of the host gate; then client+lock regeneration, migration, lane stack (12:13 +05)

# EXEC-SEAL-01 report

Worktree `.local/worktrees/exec-line`, branch `agent/exec-line-01`, base `origin/dev` `fa4ef645` plus the
two ruling commits (`24e15247`). Owner rulings `R-143`, `R-144`; the checks are the minimal set of
`R-144b`. The result is written to `docs/program/EXEC-SEAL-01.md` only; nothing was pushed, merged or tagged.

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
