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

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

KINDS in `src/auditmanager/executors/model.py` already lists `ssh_command` at the base (see P-01), so this task adds no member to that tuple; the commit that added this task file (`d4cd2ac3`) touched no `contracts/**`, `db/migrations/**` or API file. Registering an adapter factory in `kinds.py` is wiring, not a maintained contract set. This section was added on 2026-10-26 by `DEV-TASK-GOVERNANCE-01`; the original task text did not carry it.

## Captured premise evidence
- premise: the crop manifest schema, ModelRequest.image_bytes and the SSH forced-command script exist at the base, while the ssh_command kind has no adapter module there

### P-01 — read-only inputs and the unserved ssh_command kind
- captured_at: 2026-10-26
- command: `git ls-tree --name-only 4ad7e470b493bd97fbfaf755037216c205e13f5d contracts/analysis/v1/crop-manifest.schema.json tools/executor-runner/ssh-forced-command.sh src/auditmanager/executors/ssh_adapter.py src/auditmanager/executors/ssh_probe.py; git grep -n -E 'image_bytes: bytes|^KINDS' 4ad7e470b493bd97fbfaf755037216c205e13f5d -- src/auditmanager/analysis/text/adapter.py src/auditmanager/executors/model.py; git grep -n -E 'ssh_command' 4ad7e470b493bd97fbfaf755037216c205e13f5d -- src/auditmanager/executors/kinds.py src/auditmanager/executors/usability.py`
- captured_output:
  ```text
  contracts/analysis/v1/crop-manifest.schema.json
  tools/executor-runner/ssh-forced-command.sh
  4ad7e470b493bd97fbfaf755037216c205e13f5d:src/auditmanager/analysis/text/adapter.py:43:    image_bytes: bytes | None = field(default=None, repr=False, compare=False)
  4ad7e470b493bd97fbfaf755037216c205e13f5d:src/auditmanager/executors/model.py:59:KINDS: Final[tuple[str, ...]] = ("http_api", "ssh_command", "pull")
  4ad7e470b493bd97fbfaf755037216c205e13f5d:src/auditmanager/executors/usability.py:7:  ``http_api`` over ``direct`` or ``vpn`` and ``pull`` (`EXEC-PULL-01`); ``ssh_command`` and the
  ```
- interpretation: Re-captured on 2026-10-26 from base commit 4ad7e470b493bd97fbfaf755037216c205e13f5d with git grep against that tree (not at dispatch time). At the base, git ls-tree lists contracts/analysis/v1/crop-manifest.schema.json and tools/executor-runner/ssh-forced-command.sh and does not list src/auditmanager/executors/ssh_adapter.py or ssh_probe.py (ls-tree prints only existing paths). ModelRequest declares image_bytes (analysis/text/adapter.py:43). KINDS in executors/model.py:59 already contains ssh_command; the only mention of ssh_command in kinds.py or usability.py is the usability.py:7 docstring (the sentence continues on the next line, not captured, and says such connections are refused at route time), and kinds.py has none. Not covered: the stage registry named in Frozen inputs. This evidence block was added on 2026-10-26 by DEV-TASK-GOVERNANCE-01; the original task text had no governance sections.

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
