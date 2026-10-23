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
