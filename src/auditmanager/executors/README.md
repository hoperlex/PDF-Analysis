# `executors` boundary

Where a process sends model work, configured by an administrator (owner rulings `R-143` and
`R-144`; `docs/program/dispatch/EXECUTOR-CONNECTIONS-PLAN.md`). `EXEC-SEAL-01` is the enabling
slice: the tables, the contract, the sealing and the commands. **A run's behaviour does not
change**: the provider source stays `environment` until `EXEC-HTTP-01`.

| Module | What it owns |
|---|---|
| `model.py` | the vocabulary, the settings each kind takes, `destination_for`, the records. Pure. |
| `sealing.py` | X25519 + HKDF-SHA256 + AES-256-GCM, the associated data, the key rings: public-only for the `api`, private for the worker |
| `repository.py` | the only reader and writer of the `executor_*` tables (migration `0030`) |
| `commands.py` | the administrator's commands, idempotent under the command ledger, each with a journal event |
| `queries.py` | lists, a connection's detail, `resolve_route`, the probe sweep |
| `public.py` | the cross-context surface of the `api` side |
| `runtime.py` | the run-path and worker surface (`EXEC-HTTP-01`): freeze a route, bind a connection, probes, destination rules, the kind registry |
| `destinations.py` | where the worker may send a key (plan T-9): the policy, the pinned connection, the allowed-hosts list |
| `http_adapter.py` | the `http_api` kind as a model adapter: `openai_chat` through `ProxyAdapter`, `anthropic_messages` through the SDK, both pinned |
| `identity.py` | the identity and rate check of a probe (ported from `tools/provider/identity_probe.py`) |
| `probes.py` / `probe_runner.py` | «Проверить»: the smallest completion read into an outcome; the worker thread that takes `requested` probes |
| `kinds.py` | one adapter factory per kind: **the seam a new kind plugs into** (`register_adapter_factory`) |
| `usability.py` | served by this release, and probed `ok` on its current key: the two conditions for a route and for a run start |
| `resolver.py` | `freeze_connection` at run start, `bind_connection` per Attempt |
| `operations.py` / `__main__.py` | `python -m auditmanager.executors import-env | rewrap | reach` |

## Rules that hold here

- **A secret is write-only.** No operation, event, log line or ledger row carries one. The `api`
  seals on write and holds public keys only; only the worker opens, through
  `public.open_secret(session, ring, secret_id=…, destination=…)`.
- **A key opens only for the destination it was entered for.** The associated data is
  `secret_id|connection_id|purpose|kid|destination`, with the destination
  `transport|ssh_endpoint|origin` recomputed by the caller from the revision it is about to
  call. The stored `destination` column is informational. A revision that changes the address
  leaves the old secret `secret_unreadable` for it.
- **A revision is immutable**; a changed setting is a new revision. A rotated secret is a new
  row, not a new revision.
- **No silent fallback.** `resolve_route` returns the route with each side's current revision
  and hides nothing; the standby is used only when a caller journals it.
- **Refusals reuse the catalogue**: `validation_failed` (`field`, `constraint`), `conflict`
  (`conflict_reason`), `dependency_unavailable` (`dependency`), `permission_denied`.

## Settings (`api` and worker)

| Variable | Where | Meaning |
|---|---|---|
| `AUDITMANAGER_SECRETS_PUBLIC_KEYS` | `api`, worker | `kid:base64-public-key`, comma-separated |
| `AUDITMANAGER_SECRETS_ACTIVE_KID` | `api`, worker | the key id new secrets are sealed to |
| `AUDITMANAGER_SECRETS_KEYS` | worker only | `kid:base64-private-key`, comma-separated; refused on the `api` |

Without a public key `setExecutorSecret` and `generateExecutorSshKey` answer
`dependency_unavailable` (`secrets_public_key_missing`); nothing is stored in the clear.

## The run path (`EXEC-HTTP-01`)

With `AUDITMANAGER_PROVIDER_SOURCE=database` a run **freezes** the `text_analysis` route's revision at
start (`audit_run.connection_revision_id`; the input budget follows the revision's pinned model) and
**binds** it per Attempt: the connection's current key is opened for the destination recomputed from
the frozen revision, so a rotated key is picked up by the next Attempt and an address that changed
since the key was entered is `secret_unreadable`. Only a revision with an `ok` probe on its current
key can be routed or started on; the standby is used at run start only, and every use is an
`audit_run.standby_used` event. `environment` keeps today's path, with `R-133` enforced.

Destination rules (T-9) hold in the probe **and** in every call, by the resolved address: loopback,
link-local, compose service names and the compose network are refused; a private range only for
`transport: vpn`; `AUDITMANAGER_EXECUTOR_ALLOWED_HOSTS` narrows further.

Create subfolders and classes only when a real use case requires them. Keep internal APIs private
by default.
