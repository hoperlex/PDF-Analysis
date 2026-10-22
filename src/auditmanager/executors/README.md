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
| `public.py` | the cross-context surface |

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

Create subfolders and classes only when a real use case requires them. Keep internal APIs private
by default.
