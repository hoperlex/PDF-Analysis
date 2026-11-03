# EXEC2-INT-2 — stage 2 of EXEC-2 (agent installation, groups store)

Unverified development candidate published to `origin/dev`. Plan `dispatch/EXEC2-PLAN.md`, decisions `ADR-0026`, rulings `R-149a`…`R-149g`.

## What is in

| Task | Result |
|---|---|
| `EXEC2-SEAL-2` | Contract 1.16.0: 250 paths, 277 operations, 674 schemas. Migrations `0047_executor_groups_rules` (groups, immutable revisions and members, append-only rules and routing-mode events) and `0048_dispatch_time_binding` (`binding_state` on `audit_run` and `comparison_ai_job`, write-once binding to a member of the group revision). |
| `EXEC2-ENROLL-SSH-01` | Path A: the worker installs the agent over SSH. It checks the destination policy, pins the host key, issues the grant itself and sends a constant remote bootstrap with the secret on stdin only. It removes the stand's `authorized_keys` line on every exit. |
| `EXEC2-WEB-WIZARD-01` | «Добавить подключение»: two equal paths A and B, one lifecycle on the card, the OpenRouter preset, moving an agent. Path A uses the stand-generated key only, so no private key exists in client code. |
| `EXEC2-GROUP-STORE-01` | Eight group and rule operations: homogeneity validation, least-loaded selection with a persisted rotation, any-role reads. Until `EXEC2-GROUP-RUN-01`, a `startRun` or `estimateRunCost` that names `executor_group_id` is refused explicitly. |

## Integrator edits

- Label for `needs_reconsent`.
- Contract prose of the four any-role reads; client regenerated; `FRONTEND_LOCK` digests.
- `PORT_FOR_ARGUMENT` gains `enrollment` and `executor_groups`.
- `polling.test.ts` allows the wizard's poll file.
- The worker/api environment parity test names the new worker-only variable.
- `origin/dev` `49875efe` merged in.

## Checks (`R-149d`: no test, build, typecheck, lint, database or browser run)

- `git diff --check` clean.
- 231 changed files: Python parses, JSON loads, `bash -n` passes.
- `node web/scripts/generate-api-client.mjs --check`: OK, 277 operations.
- Contract operations declared by routers: 275 of 277; the two missing are listed under Known limits.
- Independent read-only review of `27fb952e..c5199b2c`: no BLOCKER or HIGH. Fixed before publication:
  - MEDIUM: membership closed by `member_count`.
  - LOW: archive reads `FOR SHARE`; group delete guard; gap-free mode events; binding must name a member; install runner pre-grant ownership; model read in the grant transaction.

## Owner ruling

`R-149g`: path A reaches private-range targets only with `AUDITMANAGER_AGENT_INSTALL_ALLOW_PRIVATE=1`. The setting is worker-only and off by default.

## Known limits

- `previewExecutorRouting` and `setExecutorRoutingMode` are declared and not served until `EXEC2-CUTOVER-01`. Conformance and role-register totality stay red until then.
- Group dispatch, admission and cut-over come in stage 3. Groups can be created, but nothing routes by them yet.
- An install result is lost if the database fails after the SSH call: the session reads `failed` while the agent may be enrolled. The administrator can see the runner token.
- Schema counts in `schema_coverage.py` are derived from the DDL. A capable runner must reseal them.
- `D-291` and `D-292` still hold.

## Next

Stage 3: `EXEC2-GROUP-RUN-01`, `EXEC2-GROUP-CMP-01`, `EXEC2-WEB-GROUPS-01`, then `EXEC2-CUTOVER-01` and `EXEC2-INT-3`.
