# EXEC-SSH-CROPS-01 — SSH command image delivery

task_id: EXEC-SSH-CROPS-01

## Result

An SSH command executor that has passed its host-key and model probe receives one
verified PNG alongside the text prompt on stdin. A changed host key or an invalid
crop is refused before an SSH model call. The result reports the actual model.

## Frozen inputs and dependencies

- Base: `4ad7e470b493bd97fbfaf755037216c205e13f5d` (`origin/dev`).
- Completed: `EXEC-HTTP-01`, `EXEC-AGENT-01`, `EXEC-IMAGE-CHANNELS-01`,
  `EXEC-ENV-OPENROUTER-01`.
- API contract 1.1.0; migration head `0031_executor_pull_channel`.
- `contracts/analysis/v1/crop-manifest.schema.json`, stage registry and
  `ModelRequest.image_bytes` are read only. No new image stage is enabled.
- SSH transport and forced-command preparations from `EXEC-SSH-01` are inputs;
  this task does not declare that broader task complete.

## Paths

Allowed: `src/auditmanager/executors/**`, `tools/executor-runner/**`,
`tests/unit/executors/**`, `tests/integration/executors/**`,
`docs/program/tasks/EXEC-SSH-CROPS-01.md`, `docs/program/EXEC-SSH-CROPS-01.md`,
`docs/program/DEPLOYMENT_RUNBOOK.md`.

Forbidden: `contracts/**`, `db/migrations/**`, dependency/lock files,
composition root, `infra/deploy/compose.server.yml`, generated client,
global styles, `origin/main`.

## Non-goals

No prompt or evidence policy for the separate image-analysis stage. No automatic
route change. SSH tunnel is a separate connection shape and needs both SSH and
HTTP secrets; it stays unserved until its dual-secret path is verified.

## Deliverables and checks

- SSH command adapter, probe, registry wiring and a bounded image envelope.
- Tests for a verified crop, changed crop, model mismatch, host-key gate,
  bounded output and probe; focused unit and integration checks.
- Report with files, check results, limitations, integration steps.

## Integration contract and rollback

`ssh_command` is served only with a pinned host key and a successful current
probe. The model response must name the configured gateway model. Rollback is
to remove its route or revert this commit; no persisted data is changed.

Publication: `origin/dev` only; no authority for `origin/main`.
