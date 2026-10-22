STATUS: candidate 67b18d4d handed to the EXEC integrator; one container-free recheck owed after the gate completion (14:15 +05)

# EXEC-CANDIDATE-1 - R-144b basic acceptance of the merged EXEC candidate

Branch `agent/exec-line-01`, worktree `.local/worktrees/exec-line`. Tree checked: `5098ba15`
(the merge `95f1b44c` plus one whitespace fix). Every command ran under
`nice -n 19 ionice -c3`, one test process at a time, memory available at least 2500 MiB before
each run, no container, no lane stack. `COMPLETION.START` of `night-b315655d` never existed
(that directory holds `START`, `END`, `rc`, `gate.log` of the finished night gate).

Base for the diff: `origin/dev` = `ddcef5b2` (merge-base `24e15247`). The tree does NOT contain
the newer `origin/dev` the coordinator asked to merge (see "Not done").

## Commands

| # | Command | Exit | Count |
|---|---------|------|-------|
| 1 | `git diff --check origin/dev...HEAD` | 2 at `95f1b44c` (two findings), 0 after the fix | `operations.py:294` and `probes.py:258`: new blank line at EOF |
| 2 | `python3 -m pytest -q -p no:cacheprovider tests/unit/executors tests/unit/executor_runner` | 0 | 390 passed, 58 s |
| 3 | `python3 -m pytest -q -p no:cacheprovider tests/contract/api_v1 tests/contract/program tests/contract/domain_p02` | 1 | 503 passed, 2 failed (both the integrator's, below), 36 s |
| 4 | `python3 -m pytest -q -p no:cacheprovider tests/e2e/test_pc01_journey_conformance.py tests/contract/tools/test_pin_sweep.py` | 0 | 125 passed, 3 s |
| 5a | `npm --prefix web run typecheck` | 0 | tsc --noEmit clean |
| 5b | `npm --prefix web run lint -- --quiet` | 0 | eslint clean |
| 6 | `npm --prefix web test -- --run tests/guards tests/unit/workers tests/unit/dispatcher tests/unit/session` | 0 | 41 files, 672 tests passed, 107 s |
| 7 | `npm --prefix web run build` (next build; available memory 4462 MiB, no completion window) | 0 | compiled with two autoprefixer warnings (`end` value in `norm-catalogue.module.css:5`, `norm-search.module.css:42`; not from this candidate), `/workers` listed as server-rendered |

Check 3 failures, both in `tests/contract/api_v1/test_doc_prose_facts.py`, both on
`docs/program/CURRENT_STATE.md` and both the integrator's to move:

- `test_the_scanned_docs_state_the_migration_head_this_tree_has`: the prose names head `0029`
  (the `0029_routing...` line); the tree has `0030_executor_connections`.
- `test_the_scanned_docs_state_the_contract_surface_this_tree_has`: the prose states the
  previous surface triple (73 / 83 / 242); the tree has 81 / 93 / 272.

Check 4: the journey conformance guard (`tests/e2e/test_pc01_journey_conformance.py`) reads
`tests/e2e/pc01/journey/manifest.json` against the route tree and the OpenAPI document; the
pin-sweep test also reads it. Both pass, so the manifest update for `/workers` agrees with the
merged contract and screens.

## Fixes made

- `5098ba15`: removed the trailing blank line at the end of
  `src/auditmanager/executors/operations.py` and `src/auditmanager/executors/probes.py`
  (both added by EXEC-HTTP-01). Not a merge conflict: a whitespace defect of that lane that
  `git diff --check` reports. Check 1 rerun: exit 0. Check 2 ran after it.

No other failure; nothing in `contracts/**` or `db/migrations/**` was touched.

## Not done

1. `git fetch -q origin && git merge --no-edit origin/dev` was refused by the permission
   classifier ("Modify Shared Resources"). It was not retried or worked around. All checks above
   ran on the tree without the newer dev; the coordinator said dev moved with docs and task
   freezes only. The integrator (or a session with that permission) merges dev and reruns at
   least checks 1, 3 and 4.
2. The contract label commit `contract: label 1.1.0 (minor, additive executor operations)` was
   not made: the script that would have edited `contracts/**` was refused by the same classifier
   and not retried. The working tree was left unmodified by that attempt. Findings that the
   executor of that commit needs (read-only, measured on this tree):
   - `python3 tools/plan/pin_sweep.py contract-version` lists 72 paths. Real holders of the
     literal `1.0.0` as the contract version: `contracts/api/v1/openapi.json` (`info.version`
     line 5 and the `ErrorEnvelope.contract_version` const line 6861) and its byte copy
     `web/openapi/openapi.json`; every `contract_version` / `name_map_contract_version` key and
     const under `contracts/analysis|domain|events/v1` (38 values in 24 files plus 15 consts in
     12 files plus the name-map pair); `src/auditmanager/analysis/engine/result.py:35`,
     `src/auditmanager/api/routers/__init__.py:197`, `src/auditmanager/api/schemas/models.py:689`;
     the four edge bodies in `infra/deploy/proxy/nginx.conf` (lines 429, 442) and
     `tls-server.conf` (lines 190, 196); `web/src/shared/api/credentialed-forward.ts:212`;
     the generated client (`types.gen.ts` lines 9, 17, 821, `operations.gen.ts`, `client.gen.ts`,
     `index.ts` headers) via `npm --prefix web run api:generate`; `tests/support/expected_facts.json`
     (`contract_version`); `tools/executor-runner/RUNNER_API.md:38` (example body); and the test
     pins named by the sweep (`test_contract_seal.py` has `SEALED = "1.0.0"`).
   - No script in `web/package.json` or `web/scripts` writes `web/FRONTEND_LOCK.json`;
     `web/tests/guards/frontend-lock.guard.test.ts` only verifies it, so its sha256 values are
     recomputed and written by hand; `openapi.info_version`,
     `openapi.sha256`, `snapshot_sha256` and the four `generated.files` digests move, and its
     `commit_note` says "info.version stays 1.0.0" and must be reworded.
   - `tests/contract/api_v1/test_contract_seal.py` walks every `const` that starts with `1.0.0`
     and demands it equals the sealed label. `contracts/analysis/v1/crop-manifest.schema.json`
     carries `artifact_version` const `1.0.0`, an independent artifact version, so the walker
     needs an `/artifact_version` exclusion beside its `/supersedes` one, or that check goes red
     at 1.1.0.
   - Open question for the integrator: `supersedes` in the three domain catalogs and their
     schemas is `1.0.0-draft.1`; at 1.1.0 it would truthfully be `1.0.0`. It was left out of the
     "leave revision/status" instruction and out of this note's scope.
3. `tests/e2e/pc01/journey/prove_the_guard_can_fail.py` was not run: it rewrites
   `manifest.json` repeatedly (its own docstring keeps it out of the gate and out of shared
   trees).
4. The `web/tests/unit` suites beyond `workers`, `dispatcher`, `session` and the whole
   `tests/integration` tree (they need a database or a stack) were not run, nor was `make gate`.

## Contract facts for the integrator

- Error code set: 27 in `contracts/domain/v1/error-codes.json` at this tip and at
  `origin/dev` `ddcef5b2`, the same 27 names; `contract_version` `1.0.0`, `candidate_revision`
  19, `status` frozen on both. EXEC-SEAL-01 changed only note text in that file (the detail-key
  vocabulary notes for the executor connection refusals), no code and no envelope field.
- Surface at this tip: 81 paths, 93 operations, 272 schemas. Migration head
  `0030_executor_connections` (the only new migration).
- `pyproject.toml` and `uv.lock` differ from `origin/dev`: one added pin,
  `cryptography==50.0.1` (EXEC-SEAL-01, R-143b), already in the lock transitively.
- Changed files against `origin/dev`: 217 (120 added, 97 modified): `src/auditmanager` 56,
  `web/src` 53, `tests/integration` 24, `tests/unit` 21, `web/tests` 12, `tools/executor-runner`
  10, `tests/fixtures` 8, `infra/deploy` 8, `docs/program` 8 (before this file), `tests/contract` 4,
  `contracts/domain` 2, and one each of `contracts/api`, `db/migrations`, `web/openapi`,
  `web/FRONTEND_LOCK.json`, `pyproject.toml`, `uv.lock`, `tests/support`, `tests/e2e`,
  `docs/manual-tests`, `scripts/recovery` 2. The full list:

```
M contracts/api/v1/openapi.json
M contracts/domain/v1/error-codes.json
M contracts/domain/v1/identifiers.json
A db/migrations/versions/20261022_0030_executor_connections.py
M docs/manual-tests/PC-01_prototype.md
M docs/program/ALPHA_ROADMAP.md
M docs/program/DEPLOYMENT_RUNBOOK.md
A docs/program/EXEC-HTTP-01-WEB.md
A docs/program/EXEC-HTTP-01.md
A docs/program/EXEC-SEAL-01.md
A docs/program/EXEC-SSH-TRANSPORT.md
A docs/program/EXEC-TOOLS-01.md
M docs/program/P02_SEAMS.md
M infra/deploy/Dockerfile.api
M infra/deploy/README.md
M infra/deploy/compose.server.yml
M infra/deploy/env/alpha.env.example
M infra/deploy/env/provider.env.example
M infra/deploy/proxy/nginx.conf
M infra/deploy/readiness.sh
M infra/deploy/serve.py
M pyproject.toml
M scripts/recovery/product_purge.py
M scripts/recovery/schema_coverage.py
M src/auditmanager/analysis/public.py
M src/auditmanager/analysis/text/__init__.py
A src/auditmanager/analysis/text/binding.py
M src/auditmanager/analysis/text/cost.py
M src/auditmanager/analysis/text/lock.py
M src/auditmanager/analysis/text/stage.py
M src/auditmanager/api/README.md
M src/auditmanager/api/app.py
M src/auditmanager/api/health.py
M src/auditmanager/api/routers/__init__.py
M src/auditmanager/api/routers/declarations.py
M src/auditmanager/api/routers/errors.py
A src/auditmanager/api/routers/executors.py
M src/auditmanager/api/routers/ports.py
M src/auditmanager/api/schemas/models.py
M src/auditmanager/api/security.py
M src/auditmanager/bootstrap/adapters.py
M src/auditmanager/bootstrap/composition.py
A src/auditmanager/bootstrap/providers.py
M src/auditmanager/bootstrap/settings.py
M src/auditmanager/dashboard/repository.py
A src/auditmanager/executors/README.md
A src/auditmanager/executors/__init__.py
A src/auditmanager/executors/__main__.py
A src/auditmanager/executors/claude_output.py
A src/auditmanager/executors/commands.py
A src/auditmanager/executors/destinations.py
A src/auditmanager/executors/http_adapter.py
A src/auditmanager/executors/identity.py
A src/auditmanager/executors/kinds.py
A src/auditmanager/executors/model.py
A src/auditmanager/executors/operations.py
A src/auditmanager/executors/probe_runner.py
A src/auditmanager/executors/probes.py
A src/auditmanager/executors/public.py
A src/auditmanager/executors/queries.py
A src/auditmanager/executors/repository.py
A src/auditmanager/executors/resolver.py
A src/auditmanager/executors/runtime.py
A src/auditmanager/executors/sealing.py
A src/auditmanager/executors/ssh_transport.py
A src/auditmanager/executors/usability.py
M src/auditmanager/jobs/events.py
M src/auditmanager/jobs/lease.py
M src/auditmanager/jobs/public.py
M src/auditmanager/jobs/repository.py
M src/auditmanager/runs/__init__.py
M src/auditmanager/runs/carrier.py
M src/auditmanager/runs/commands.py
M src/auditmanager/runs/executor.py
A src/auditmanager/runs/provider.py
M src/auditmanager/runs/repository.py
M src/auditmanager/shared/identity/__init__.py
M src/auditmanager/shared/identity/ids.py
M src/auditmanager/workers/__main__.py
M src/auditmanager/workers/service.py
M tests/contract/api_v1/test_openapi_conformance.py
M tests/contract/api_v1/test_surface_counts_in_prose.py
M tests/contract/api_v1/test_w55b_portal_bundle_seal.py
M tests/contract/domain_p02/test_openapi_document.py
M tests/e2e/pc01/journey/manifest.json
A tests/fixtures/sshd/Dockerfile
A tests/fixtures/sshd/README.md
A tests/fixtures/sshd/down.sh
A tests/fixtures/sshd/entrypoint.sh
A tests/fixtures/sshd/forced-command.sh
A tests/fixtures/sshd/rotate-host-key.sh
A tests/fixtures/sshd/sshd_config
A tests/fixtures/sshd/up.sh
M tests/integration/api/test_authorization.py
M tests/integration/api/test_role_register.py
M tests/integration/api/test_served_document_and_health_plane.py
M tests/integration/composition/test_every_port_implementation_is_whole.py
M tests/integration/composition/test_readiness_command.py
M tests/integration/dashboard/test_section_breakdown.py
M tests/integration/db/test_downgrade_chain_round_trip.py
A tests/integration/db/test_executor_connections_migration.py
M tests/integration/db/test_migration_lifecycle.py
M tests/integration/db/test_schema_invariant_inventory.py
M tests/integration/db/test_schema_shape.py
A tests/integration/executors/conftest.py
A tests/integration/executors/http_support.py
A tests/integration/executors/test_executor_commands.py
A tests/integration/executors/test_executor_surface.py
A tests/integration/executors/test_http_operations.py
A tests/integration/executors/test_http_probe_worker.py
A tests/integration/executors/test_http_run_path.py
A tests/integration/executors/test_http_sentinel.py
A tests/integration/executors/test_secret_never_leaves.py
A tests/integration/executors/test_ssh_sshd.py
M tests/integration/recovery/test_product_purge.py
M tests/integration/recovery/test_synthetic_drill_compare.py
M tests/integration/recovery/test_synthetic_drill_seed.py
M tests/support/expected_facts.json
A tests/unit/executor_runner/_support.py
A tests/unit/executor_runner/test_agent.py
A tests/unit/executor_runner/test_mcp_bridge.py
A tests/unit/executor_runner/test_readme.py
A tests/unit/executor_runner/test_runner_client.py
A tests/unit/executor_runner/test_ssh_forced_command.py
A tests/unit/executor_runner/test_workspace.py
A tests/unit/executors/conftest.py
A tests/unit/executors/fake_gateway.py
A tests/unit/executors/test_claude_output.py
A tests/unit/executors/test_destinations.py
A tests/unit/executors/test_http_adapter.py
A tests/unit/executors/test_http_probe.py
A tests/unit/executors/test_model.py
A tests/unit/executors/test_probe_loop.py
A tests/unit/executors/test_provider_source_settings.py
A tests/unit/executors/test_sealing.py
A tests/unit/executors/test_settings.py
A tests/unit/executors/test_ssh_key.py
A tests/unit/executors/test_ssh_transport.py
A tests/unit/executors/test_unmetered_cost.py
A tools/executor-runner/README.md
A tools/executor-runner/RUNNER_API.md
A tools/executor-runner/agent.example.toml
A tools/executor-runner/agent.py
A tools/executor-runner/mcp_bridge.py
A tools/executor-runner/pdf-analysis-agent.service
A tools/executor-runner/runner_client.py
A tools/executor-runner/ssh-forced-command.sh
A tools/executor-runner/workspace/.claude/settings.json
A tools/executor-runner/workspace/.claude/skills/pdf-analysis-runner/SKILL.md
M uv.lock
M web/FRONTEND_LOCK.json
M web/openapi/openapi.json
M web/src/_pages/workers/index.ts
A web/src/_pages/workers/model/tabs.ts
A web/src/_pages/workers/ui/workers-page.module.css
M web/src/_pages/workers/ui/workers-page.tsx
A web/src/_pages/workers/ui/workers-tabs.tsx
M web/src/app/bff/v1/[...path]/route.ts
M web/src/app/workers/page.tsx
M web/src/entities/audit-run/model/run-comparison.ts
M web/src/entities/audit-run/model/run-presentation.ts
M web/src/entities/execution/model/presentation.ts
A web/src/entities/executor-connection/api/use-executor-connections.ts
A web/src/entities/executor-connection/index.ts
A web/src/entities/executor-connection/model/changes.ts
A web/src/entities/executor-connection/model/destination.ts
A web/src/entities/executor-connection/model/failure.ts
A web/src/entities/executor-connection/model/readiness.ts
A web/src/entities/executor-connection/model/vocabulary.ts
A web/src/features/manage-executor-connection/index.ts
A web/src/features/manage-executor-connection/model/settings.ts
A web/src/features/manage-executor-connection/model/use-command-key.ts
A web/src/features/manage-executor-connection/model/use-manage-executor-connection.ts
A web/src/features/manage-executor-connection/model/use-set-executor-route.ts
A web/src/features/manage-executor-connection/ui/archive-control.tsx
A web/src/features/manage-executor-connection/ui/command-failure.tsx
A web/src/features/manage-executor-connection/ui/create-connection-form.tsx
A web/src/features/manage-executor-connection/ui/host-key-control.tsx
A web/src/features/manage-executor-connection/ui/probe-button.tsx
A web/src/features/manage-executor-connection/ui/revise-connection-form.tsx
A web/src/features/manage-executor-connection/ui/settings-fields.tsx
A web/src/features/manage-executor-connection/ui/ssh-key-control.tsx
A web/src/features/set-executor-secret/index.ts
A web/src/features/set-executor-secret/model/exchange.ts
A web/src/features/set-executor-secret/ui/set-executor-secret-form.tsx
M web/src/features/transition-assignment/ui/assignment-actions.tsx
M web/src/shared/api/authorization.ts
M web/src/shared/api/generated/client.gen.ts
M web/src/shared/api/generated/index.ts
M web/src/shared/api/generated/operations.gen.ts
M web/src/shared/api/generated/types.gen.ts
M web/src/shared/api/query-keys.ts
M web/src/shared/ui/run-state-badge.tsx
M web/src/widgets/assignment-board/ui/assignment-board.tsx
M web/src/widgets/assignment-board/ui/assignment-history.tsx
M web/src/widgets/dashboard/ui/run-activity-panel.tsx
A web/src/widgets/executor-connections/index.ts
A web/src/widgets/executor-connections/ui/connection-card.tsx
A web/src/widgets/executor-connections/ui/executor-connections.module.css
A web/src/widgets/executor-connections/ui/executor-connections.tsx
A web/src/widgets/executor-routes/index.ts
A web/src/widgets/executor-routes/ui/executor-routes.module.css
A web/src/widgets/executor-routes/ui/executor-routes.tsx
M web/src/widgets/run-progress/ui/run-progress.tsx
M web/src/widgets/stage-comparison/ui/stage-comparison.tsx
M web/tests/guards/dashboard-invalidation.guard.test.ts
M web/tests/guards/rendered-language.guard.test.ts
M web/tests/unit/run/cost.test.ts
M web/tests/unit/run/run-comparison.test.ts
M web/tests/unit/screens/run-progress.test.ts
M web/tests/unit/styles/screens.ts
A web/tests/unit/workers/executor-commands.test.ts
A web/tests/unit/workers/executor-connections.test.ts
A web/tests/unit/workers/executor-fixtures.ts
A web/tests/unit/workers/executor-secret-door.test.ts
A web/tests/unit/workers/executor-settings.test.ts
A web/tests/unit/workers/workers-tabs.test.ts
```


## Dispatcher addendum (pdf-analysis-33, 2026-10-22 14:15 +05)

The two steps the lane could not take were taken by the dispatcher with the owner's direct
permission (poll ~14:00 +05, «Сделай сам»):

1. `git merge origin/dev` (ddcef5b2, docs and task freezes only) -> `adacbd1a`, no conflict;
   `git diff --check origin/dev...HEAD` exit 0.
2. **Label 1.1.0: attempted and parked, not in the candidate.** Mirroring the 149
   version lines of the 1.0.0 seal commit `c957e7d9` across 107 files, regenerating the
   client and recomputing FRONTEND_LOCK left 20 contract tests red: the seal's own guards
   (`test_contract_seal.py`: domain catalogs frozen at the sealed round, schemas refusing an
   unfrozen catalog, the envelope pinning the sealed version) and
   `test_alpha_acceptance_command.py` encode 1.0.0 as the frozen family version. Moving the
   label is therefore a reseal of those guards, not a pin sweep. The attempt is preserved on
   branch `agent/exec-label-110` (`404d8935`) for a separate slice; the candidate keeps
   `1.0.0`.

On `adacbd1a` (dispatcher, `nice -n 19 ionice -c3`, before the gate owner's STOP):
`pytest tests/contract` with the gate's three ignores plus
`tests/e2e/test_pc01_journey_conformance.py` -> **1098 passed, 3 failed** (5 min 53 s):
- `test_doc_prose_facts.py` x2: CURRENT_STATE.md still says head 0029 and 73/83/242 — the
  integrator's;
- `test_domain_identifiers_schema.py::test_each_identifier_name_enum_admits_every_catalog_name`:
  a real EXEC-SEAL-01 defect (the five executor identifiers were in identifiers.json but not
  in the schema's two name enums). Fixed in `67b18d4d`; its rerun waits for the gate
  completion's quiet window to end.
