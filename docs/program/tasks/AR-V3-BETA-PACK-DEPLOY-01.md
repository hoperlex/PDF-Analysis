# Task AR-V3-BETA-PACK-DEPLOY-01 — deploy pass-through of the sealed AR v3 beta pack manifest

task_id: AR-V3-BETA-PACK-DEPLOY-01
status: completed (deploy wiring only; no pack is installed and none is sealed)

## Outcome

An operator can install a sealed reviewed pack on the deployed stack without a code change: `alpha.env` names the manifest file, and the `api` and `worker` containers see it read-only. With the variable blank (the shipped default) nothing changes: group starts still refuse with `dependency_unavailable`.

## Depends on

- `AR-V3-BETA-PACK-INSTALL-01` — merged: the loader that reads `AR_V3_BETA_PACK_MANIFEST` in both composition roots and refuses start on a bad file.

## Frozen inputs

- domain contract: unchanged (error catalogue 27).
- API contract: `1.4.0`, unchanged.
- analysis/comparison/event contract: unchanged.
- migration head: `0032_ar_v3_run_group`, unchanged.
- base commit: `519129dcd63680a483e095628283d80a6cccd87a` (`integration/ar-close-1026`).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the runs loader reads AR_V3_BETA_PACK_MANIFEST at the base commit while no deploy file passes it to a container

### P-01 — the loader reads exactly this variable name, and no deploy file passes it yet
- captured_at: 2026-10-26
- command: `git grep -n "AR_V3_BETA_PACK_MANIFEST" 519129dc -- src infra/deploy/compose.server.yml infra/deploy/env/alpha.env.example`
- captured_output:
  ```text
  519129dc:src/auditmanager/bootstrap/composition.py:79:    Without ``AR_V3_BETA_PACK_MANIFEST`` the registry stays empty and group starts refuse. With
  519129dc:src/auditmanager/runs/v3_pack_manifest.py:6:by ``AR_V3_BETA_PACK_MANIFEST``. No variable means the empty registry, exactly as before: group
  519129dc:src/auditmanager/runs/v3_pack_manifest.py:36:PACK_MANIFEST_ENV: Final = "AR_V3_BETA_PACK_MANIFEST"
  ```
- interpretation: the variable is defined in the runs context and used by the composition root; the compose file and the environment example at the base do not mention it, so a deployed container could never receive it.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `infra/deploy/compose.server.yml`
- `infra/deploy/env/alpha.env.example`
- `infra/deploy/ar-v3-pack/README.md`
- `infra/deploy/ar-v3-pack/.gitignore`
- `tests/integration/composition/test_session_register_volume.py`
- `tests/integration/workers/test_worker_composition.py`
- `docs/program/tasks/AR-V3-BETA-PACK-DEPLOY-01.md`

## Forbidden hotspots

- contracts, migrations, root dependency/lock files, composition root, global styles
- `infra/deploy/deploy.sh`, `readiness.sh`, the proxy and TLS files

## Non-goals

- sealing a pack, naming a reviewer, or choosing any map, set or snapshot
- changing how the loader behaves; any change to `AR_V3_BETA_PACK_MANIFEST` semantics belongs to the runs context

## Deliverables

- the variable passed to `api` and `worker`; the directory `infra/deploy/ar-v3-pack` mounted read-only at `/run/ar-v3` in both; the example documented; the two guards that said "the worker has no volume" now say "the worker's only mount is this read-only directory".

## Required tests

- command: `tests/integration/workers/test_worker_composition.py tests/integration/composition/{test_api_token_channel,test_session_register_volume,test_deployed_stack_probe,test_readiness_command,test_proxy_config_follows_checkout,test_stand_copy_refusals,test_reset_script_refusals,test_bundle_transport_refusals,test_the_served_application_routes_by_section}.py tests/integration/releases/test_deployment_flow.py` with the lane `.env` loaded
- expected: 450 passed, 2 skipped (measured 2026-10-26 on the integration tree)

## Integration contract

The operator copies the sealed manifest into `infra/deploy/ar-v3-pack/` (git-ignored), sets `AR_V3_BETA_PACK_MANIFEST=/run/ar-v3/<file>` in `alpha.env`, and restarts `api` and `worker`. The file must be readable by container uid 10001. A set-but-invalid value stops both services at start by design.

## Failure/idempotency/security cases

- the mount is read-only and the file holds no secret; a missing file with the variable set fails start (loader), a missing directory fails `docker compose up` (the directory is tracked through its README).
- the guard that keeps the worker off every named volume still fails if a named volume is added: the test pins the single allowed mount.

## Rollback / feature flag

Blank the variable and restart (registry empty again), or forward-revert this commit.

## Handoff

- changed files: see the allowed paths.
- commands/results: as in Required tests; `docker compose config` was not run against a real `alpha.env` (no deploy secrets on this host).
- known limits: the real deploy path (`deploy.sh`) was not executed; the bind source is relative to the compose file directory.
- integration notes: none beyond the integration contract.
