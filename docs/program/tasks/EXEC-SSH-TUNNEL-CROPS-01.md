# EXEC-SSH-TUNNEL-CROPS-01 — HTTP image delivery over SSH tunnel

task_id: EXEC-SSH-TUNNEL-CROPS-01

## Result

An `http_api` connection over `ssh_tunnel` opens a short-lived SSH forward,
uses the existing OpenAI Chat or Anthropic HTTP adapter through that forward,
and delivers the same verified PNG as direct HTTP. Its current HTTP key and
SSH key must both be valid at probe and call time. A probe requested before
either current key was issued cannot make the connection routable.

## Frozen inputs and dependencies

- Base: `d4cd2ac3` on `origin/dev`.
- Completed: `EXEC-HTTP-01`, `EXEC-AGENT-01`, `EXEC-IMAGE-CHANNELS-01`,
  `EXEC-SSH-CROPS-01`.
- API contract 1.1.0; migration head `0031_executor_pull_channel`.
- Existing `executor_probe.requested_at`, `executor_secret.set_at`, SSH
  transport and HTTP image adapter; no schema change.

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

TRANSPORTS in `src/auditmanager/executors/model.py` already lists `ssh_tunnel` and KINDS already lists `ssh_command` at the base (see P-01 here and in `EXEC-SSH-CROPS-01`), so this task adds no member to either tuple; the commit that added this task file (`d855ebbc`) touched no `contracts/**`, `db/migrations/**` or API file. This section was added on 2026-10-26 by `DEV-TASK-GOVERNANCE-01`; the original task text did not carry it.

## Captured premise evidence
- premise: executor_probe.requested_at, executor_secret.set_at, the SSH command transport and the HTTP adapter's ssh_tunnel seam exist at the base, while the ssh_tunnel adapter module does not

### P-01 — schema columns and adapters already present, tunnel adapter absent
- captured_at: 2026-10-26
- command: `git grep -n -E 'requested_at +timestamptz|set_at +timestamptz|CREATE TABLE executor_(probe|secret)' d4cd2ac32501d451eea3999f4400d4ae0b2deedb -- db/migrations/versions/20261022_0030_executor_connections.py; git ls-tree --name-only d4cd2ac32501d451eea3999f4400d4ae0b2deedb src/auditmanager/executors/ssh_adapter.py src/auditmanager/executors/ssh_probe.py src/auditmanager/executors/http_adapter.py src/auditmanager/executors/ssh_tunnel_adapter.py; git grep -n -E 'transport == "ssh_tunnel"|^TRANSPORTS' d4cd2ac32501d451eea3999f4400d4ae0b2deedb -- src/auditmanager/executors/http_adapter.py src/auditmanager/executors/model.py`
- captured_output:
  ```text
  d4cd2ac32501d451eea3999f4400d4ae0b2deedb:db/migrations/versions/20261022_0030_executor_connections.py:213:        CREATE TABLE executor_secret (
  d4cd2ac32501d451eea3999f4400d4ae0b2deedb:db/migrations/versions/20261022_0030_executor_connections.py:222:            set_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
  d4cd2ac32501d451eea3999f4400d4ae0b2deedb:db/migrations/versions/20261022_0030_executor_connections.py:263:        CREATE TABLE executor_probe (
  d4cd2ac32501d451eea3999f4400d4ae0b2deedb:db/migrations/versions/20261022_0030_executor_connections.py:277:            requested_at      timestamptz NOT NULL DEFAULT clock_timestamp(),
  d4cd2ac32501d451eea3999f4400d4ae0b2deedb:db/migrations/versions/20261022_0030_executor_connections.py:351:            set_at                timestamptz NOT NULL DEFAULT clock_timestamp(),
  src/auditmanager/executors/http_adapter.py
  src/auditmanager/executors/ssh_adapter.py
  src/auditmanager/executors/ssh_probe.py
  d4cd2ac32501d451eea3999f4400d4ae0b2deedb:src/auditmanager/executors/http_adapter.py:339:    if transport == "ssh_tunnel":
  d4cd2ac32501d451eea3999f4400d4ae0b2deedb:src/auditmanager/executors/model.py:65:TRANSPORTS: Final[tuple[str, ...]] = ("direct", "vpn", "ssh_tunnel")
  d4cd2ac32501d451eea3999f4400d4ae0b2deedb:src/auditmanager/executors/model.py:199:        if settings.transport == "ssh_tunnel":
  d4cd2ac32501d451eea3999f4400d4ae0b2deedb:src/auditmanager/executors/model.py:205:        if kind == "http_api" and settings.transport == "ssh_tunnel":
  d4cd2ac32501d451eea3999f4400d4ae0b2deedb:src/auditmanager/executors/model.py:237:    if kind == "http_api" and settings.transport == "ssh_tunnel":
  ```
- interpretation: Re-captured on 2026-10-26 from base commit d4cd2ac32501d451eea3999f4400d4ae0b2deedb with git grep against that tree (not at dispatch time). At the base, migration 0030 creates executor_secret (213) with set_at (222) and executor_probe (263) with requested_at (277); line 351 is another set_at column in the same migration (its table is outside the captured lines). git ls-tree lists executors/http_adapter.py, ssh_adapter.py and ssh_probe.py and does not list ssh_tunnel_adapter.py. http_adapter.py:339 branches on transport == "ssh_tunnel" and TRANSPORTS in executors/model.py:65 already contains ssh_tunnel. This supports the 'no schema change' input only in the sense that the columns exist; it does not prove that the task adds no migration. This evidence block was added on 2026-10-26 by DEV-TASK-GOVERNANCE-01; the original task text had no governance sections.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

This section was added on 2026-10-26 by `DEV-TASK-GOVERNANCE-01`; it records no correction and rewrites no history.

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

This section was added on 2026-10-26 by `DEV-TASK-GOVERNANCE-01` from the task's own closing line (`Publication: origin/dev only; no authority for origin/main.`).

## Paths

Allowed: `src/auditmanager/executors/**`, `tests/unit/executors/**`,
`tests/integration/executors/**`, `docs/program/DEPLOYMENT_RUNBOOK.md`,
`docs/program/CURRENT_STATE.md`,
`docs/program/tasks/EXEC-SSH-TUNNEL-CROPS-01.md`,
`docs/program/EXEC-SSH-TUNNEL-CROPS-01.md`.

Forbidden: `contracts/**`, `db/migrations/**`, dependency/lock files,
composition root, generated client, global styles, `infra/deploy/compose.server.yml`,
`origin/main`.

## Non-goals

No graphical-analysis prompt or evidence policy, route change, long-lived
tunnel, agent forwarding or jump host. The tunnel target is governed by the
remote account's `authorized_keys` `permitopen` rule.

## Deliverables and checks

- Dual-secret adapter binding and probe on the current revision.
- Readiness after both secrets' `set_at`; key rotation invalidates old probe.
- Short-lived HTTP-over-SSH adapter with original HTTP host/TLS identity.
- Tests for both HTTP flavours, PNG, pin, secrets and rotation; local SSH smoke.
- Report with checks, risks and integrator steps.

## Integration contract and rollback

`http_api` revisions with `transport=ssh_tunnel` gain the existing adapter seam.
The probe is stored against the current API key and must have been requested
after the SSH key and API key were both issued. Revert this commit or remove the
route to roll back; no data migration or implicit fallback.

Publication: `origin/dev` only; no authority for `origin/main`.
