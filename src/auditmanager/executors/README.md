# `executors` boundary

Where a process sends model work, configured by an administrator (owner rulings `R-143` and
`R-144`; `docs/program/dispatch/EXECUTOR-CONNECTIONS-PLAN.md`). `EXEC-SEAL-01` is the enabling
slice: the tables, the contract, the sealing and the commands. `EXEC-HTTP-01` made the `http_api`
kind serve a run (the provider source `database`; the default stays `environment`) and
`EXEC-PULL-01`, wired by `EXEC-CANDIDATE-2`, the `pull` kind: a **channel kind** (no key, no
address; the remote party calls the stand), registered in `kinds.py` with `register_channel_kind`
and built from the worker's `KindRuntime`.

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
| `kinds.py` | one adapter factory per kind: **the seam a new kind plugs into** (`register_adapter_factory`; `register_channel_kind` for a kind whose remote party calls the stand, as `pull`) |
| `usability.py` | served by this release, and probed `ok` on its current key: the two conditions for a route and for a run start |
| `resolver.py` | `freeze_connection` at run start, `bind_connection` per Attempt |
| `operations.py` / `__main__.py` | `python -m auditmanager.executors import-env | rewrap | reach` |
| `runner_repository.py` | the only reader and writer of `executor_runner_token` and `executor_task` (migration `0031`, `EXEC-PULL-01`) |
| `runner.py` | the pull channel's `api` side: issue and revoke a runner token, authenticate it, claim (long poll), extend, answer and fail a task |
| `answers.py` | a runner's answer held to the task's output schema (a small validator for the keywords the stage's schemas use; anything else is refused) |
| `pull.py` | the `pull` kind as a model adapter (writes a task and waits inside the Attempt) and its «Проверить» |

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
- **A runner token is a credential, not an account.** Only its SHA-256 is stored; the value is
  returned once, by `issue_runner_token`, and never again (an identical repeat is
  `conflict`/`token_shown_once`). It opens the tasks of its own connection and nobody else's, it
  reaches only the four runner operations, and a revoked, expired or archived-connection token is
  the same `None` as a wrong one. It is in no event, no log line and no error detail.
- **The worker waits inside its Attempt.** `PullAdapter.complete` writes a task and waits until
  `min(revision deadline, watchdog remaining - 60 s)`. A task nobody claimed is `not_sent`
  (`dependency: no_executor_online`); a claimed task that was not answered, or that a runner
  failed, is `outcome_unknown`. Neither is `retry_safe`. A claim joins the live, current Attempt:
  a dead Attempt's task is never served. The declared model is an assertion
  (`identity_basis: declared`), and the api already held it equal to the revision's gateway model.
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

## Analysis presets (`ANALYSIS-PRESETS-01`, `R-146av`)

A preset is a named, saved choice of the one setting a run start can take: the executor connection
(`presets.py`, `preset_store.py`, `preset_commands.py`, `preset_audit.py`; table
`analysis_preset_revision`, migration `0037`). The cost ceiling is a process-wide setting and no
threshold is an input of a start, so a preset holds neither. Revisions are append-only and an archive is
a revision; a preset and each revision are identified by the `evt_` id of the audit event written with
them. Writing a preset is an administrator's act like every executor write; a run start resolves the
preset's **current** revision in its own transaction (`choose_preset`) and then starts exactly as if the
caller had named that connection, and the run records the revision (`audit_run.preset_revision_id`).

Destination rules (T-9) hold in the probe **and** in every call, by the resolved address: loopback,
link-local, compose service names and the compose network are refused; a private range only for
`transport: vpn`; `AUDITMANAGER_EXECUTOR_ALLOWED_HOSTS` narrows further.

Create subfolders and classes only when a real use case requires them. Keep internal APIs private
by default.
