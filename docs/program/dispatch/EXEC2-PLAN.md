# EXEC-2 — executor capacity, universal agent, executor groups: wave plan

- Date: 2026-11-02
- Integrator: the planning session (`R-149f`). Executors never merge or push.
- Architecture: `docs/architecture/adr/ADR-0026-executor-capacity-enrollment-groups.md`. Tasks cite «ADR-0026 decision n».
- Owner inputs: `R-149a`…`R-149f` (`OWNER_RULINGS_2026-09-17.md` §3.49). Deviations: `D-291`, `D-292`.
- Sources: the owner's three design documents of 2026-11-02 — Block 1 parallel scheduler (**B1**), Universal Executor Agent (**B2**), Stage 3 routing groups (**B3**). They were handed to the session as text and are not in the repository.
- Base: `origin/dev` `9617c759` (code tree `4ab29560`): VERSION 0.9.0, API 1.14.0 with 233 paths, migration head 0044. `REVIEW-FIX-INT-1102` (`integration/review-fix-1102`) adds migration 0045 and must be on `origin/dev` before `EXEC2-SEAL-1` is dispatched.
- Owner-facing Russian plan: `.local/reports/executor-wave-plan-2026-11-02.md`. It is a local file and not part of the repository.

## 1. Owner inputs

### 1.1. Poll answers

`R-149a`…`R-149f` are in §3.49 of `OWNER_RULINGS_2026-09-17.md`:

| Ruling | Answer |
|---|---|
| `R-149a` | `allow_client_documents` enforcement is deferred. |
| `R-149b` | Consumer subscriptions are used through the official CLIs for the development and closed-beta period, and agents may move between hosts. |
| `R-149c` | Group work whose members are all offline waits 30 minutes by default. |
| `R-149d` | No database runs in this wave. |
| `R-149e` | No fresh-judge round. |
| `R-149f` | The planning session integrates the wave. |

### 1.2. Defaults taken from the design documents without a poll

1. Billing option A: identical billing and rates within a group.
2. Group revisions snapshot the members' revisions.
3. `least_loaded` with a tie-break persisted in the database.
4. No group-targeting presets.
5. A standby is never converted into a group member.
6. One process per runner token.
7. The installer writes `concurrency = 1`.
8. No new error codes.

## 2. Reconciliation with the code (Phase 0 of B1, B2 and B3)

Read on `4ab29560`. Each row shows what the code does and what the plan does about it.

| Claim of a design document | Code | Plan consequence |
|---|---|---|
| B1: per-connection exclusivity with an advisory lock, counting active runs and comparison calls | `jobs/repository.py:58,69,955`; mirror in `comparison/spend/repository.py:255-266` | Count instead of existence in claim, hint and call preparation (ADR-0026 decision 1) |
| (not in B1) | `_NEXT_JOB` (`jobs/repository.py:94`) holds a connection on **any** active run | The hint must count too, or a slot skips connections with free units |
| B1: comparison calls compete with runs | They also exclude **each other** (`connection_has_active_call`) | One formula for used units |
| B1: `http_api.max_parallel_calls` | Stored and validated, applied nowhere (only `api/schemas/models.py:4022` outside the executor model and repository) | Coupled validation instead of a counter (decision 2) |
| B1: `pull.max_claimed_tasks` enforced server-side | Enforced (`runner.py:485-496`), but count and claim are two statements with no per-token lock (`runner_repository.py:349-394`) | Per-token row lock (decision 3) |
| B1: a repeated claim at limit 1 redelivers the held task | Yes (`runner.py:492`) | `runner_instance_id`; agent registry (decision 3) |
| B1: agent `concurrency` | 1–8 with a semaphore (`agent.py:89,199,405`); no in-flight registry | Registry in `EXEC2-PULL-01` |
| B1: purge ignores claimed tasks | Known as `D-215` (`scripts/recovery/product_purge.py:224`) | Closed in `EXEC2-PULL-01` |
| B2: enrollment | None (the only `enroll` match is the unrelated «Worker enrollment» in `contracts/analysis/v1/stage-registry.json`) | New (decision 4) |
| B2: health and last seen | `executor_runner_token.last_seen_at` / `last_seen_address` exist (`runner_repository.py:253-256`) | Health on the token (decision 5) |
| B2: installer | None; a hand-written unit `tools/executor-runner/pdf-analysis-agent.service` | New (decision 6) |
| B2: SSH install | SSH with host-key pinning and stand-generated keys exist; `pull` may hold no secret (`executors/model.py:114`) | A separate install session (decision 7) |
| B2: `allow_client_documents` | Checked nowhere | Deferred (`R-149a`, `D-291`) |
| B3: six `work_kind` values | Exact (`executors/model.py:71-78`) | — |
| B3 question 1: is comparison consent an immutable estimate and ceiling? | Yes: the `comparison_ai_job` consent columns change only with `consent_no + 1` (`am_guard_comparison_ai_job_consent`, migration 0040). But `connection_revision_id text NOT NULL` is written at consent (`0040:602`). | NULL until dispatch; a write-once trigger exception (decision 12) |
| B3: run consent | `RunCostConsent` (`estimate_digest`, `ceiling_micros`, `confirmed`) on `startRun` | Reused, with the group snapshot (decision 13) |
| B3: frozen run revision | `trg_audit_run_frozen_guard`, re-created by migrations 0002, 0017, 0023, 0030 and 0037 | Re-created again with the write-once exception (decision 12) |
| B3 question 2: a revision probe after a key rotation | `usability.py`: `ok` on the **current** key of the current revision | Rotation needs a new probe; a member is ineligible while its current revision differs from the snapshot |
| B3: the `environment` source never runs group work | A Run without a revision takes no lock and is never limited (`jobs/repository.py:969`) | Explicit `binding_state`; `environment` refuses `pending` (decision 12) |
| B3: «group» | Already `ar_v3_run_group` (migration 0032) and `group=` in `runs/preflight.py:149` | `executor_group*`; «Группа исполнителей» in the UI |
| Readers of the frozen revision | 57 lines in 16 files outside `executors/` and `comparison/`; 24 lines in 8 files of `comparison/` | The bulk of `GROUP-RUN-01` and `GROUP-CMP-01` |

## 3. Contradictions between the documents, resolved

1. **B2 «concurrency 1 in v1» against B1's parallel pull.** The installer writes 1. Raising it is an explicit act after stage 1.
2. **B2 §6 on subscriptions against `R-143f`.** Resolved by `R-149b`.
3. **B3 «choose the model at dispatch» against homogeneity.** The `pin_id` of a group revision fixes the model at admission. The canonical binding is written at dispatch (ADR-0026 decision 13).
4. **Client documents.** Resolved by `R-149a`.
5. **Stress tests.** Resolved by `R-149d`.
6. **«Run/job» binding for comparison jobs.** A comparison job binds at its first dispatched call (decision 14).

## 4. Stages and tasks

Task files are `docs/program/tasks/EXEC2-*.md`. The estimates are executor hours.

### Stage 1 — capacity and the agent's base

| Task | Outcome | Depends on | Estimate |
|---|---|---|---|
| `EXEC2-SEAL-1` | Contract 1.15.0, migration 0046, regenerated models and client, pins | P-1 | 3 h |
| `EXEC2-CAP-01` | Capacity units in claim, hint and comparison call; coupled validation | SEAL-1 | 3 h |
| `EXEC2-PULL-01` | Per-token claim lock, `runner_instance_id`, agent registry, `D-215` | SEAL-1 | 3 h |
| `EXEC2-ENROLL-01` | Enrollment grant and exchange, health, package route, host move | SEAL-1 | 3 h |
| `EXEC2-AGENT-01` | `install.sh`, deterministic package, CLI detection, health report | SEAL-1; `agent.py` after PULL-01 | 4 h |
| `EXEC2-WEB-CAP-01` | Capacity field, occupancy, waiting reason, `R-149a` notice | SEAL-1 | 2 h |
| `EXEC2-INT-1` | Merge, read-only review, `CURRENT_STATE`, publish to `origin/dev` | all of the above | 2 h |

### Stage 2 — agent installation and the group store

| Task | Outcome | Depends on | Estimate |
|---|---|---|---|
| `EXEC2-ENROLL-SSH-01` | Path A install session executed by the worker | INT-1 | 5 h |
| `EXEC2-WEB-WIZARD-01` | Two-path wizard, lifecycle, OpenRouter preset, host move | INT-1 | 4 h |
| `EXEC2-SEAL-2` | Contract 1.16.0, migrations 0047–0048, models and client, pins | INT-1 | 4 h |
| `EXEC2-GROUP-STORE-01` | Group and rule commands, validation, `least_loaded` selection function | SEAL-2 | 3 h |
| `EXEC2-INT-2` | Merge, review, publish to `origin/dev` | all of the above | 2 h |

### Stage 3 — dispatch by group and the cut-over

| Task | Outcome | Depends on | Estimate |
|---|---|---|---|
| `EXEC2-GROUP-RUN-01` | Run admission and dispatch-time binding | INT-2 | 6 h |
| `EXEC2-GROUP-CMP-01` | The same for the five `comparison_*` kinds | INT-2 | 5 h |
| `EXEC2-WEB-GROUPS-01` | «Группы», «Правила», start selector, queue and run details | INT-2 | 5 h |
| `EXEC2-CUTOVER-01` | Preview, confirm, mode, read-only legacy routes, rollback, operator guide | GROUP-RUN-01, GROUP-CMP-01 | 3 h |
| `EXEC2-INT-3` | Merge, reviews, release note, publish to `origin/dev` | all of the above | 3 h |

P-1 is `REVIEW-FIX-INT-1102` on `origin/dev`.

An optional owner act after INT-2: accept paths A and B on a clean Ubuntu LTS host.

## 5. Hotspot ownership

| Hotspot | Stage 1 | Stage 2 | Stage 3 |
|---|---|---|---|
| `contracts/**`, generated models and client, version and path-count pins | SEAL-1 | SEAL-2 | frozen |
| Migration head | SEAL-1 (0046) | SEAL-2 (0047, 0048) | frozen |
| `src/auditmanager/api/security.py` | SEAL-1, then ENROLL-01 (sequential) | SEAL-2, then GROUP-STORE-01 | — |
| `src/auditmanager/api/app.py` | SEAL-1 (pin comment), then ENROLL-01 (router) | SEAL-2, then GROUP-STORE-01 | — |
| `infra/deploy/proxy/{nginx,tls-server}.conf` | SEAL-1 (literals), then ENROLL-01 (throttle) | SEAL-2 (literals) | — |
| `src/auditmanager/bootstrap/composition.py` | — | ENROLL-SSH-01 | GROUP-RUN-01 |
| `src/auditmanager/jobs/repository.py` | CAP-01 | — | GROUP-RUN-01 |
| `src/auditmanager/comparison/spend/**` | CAP-01 | — | GROUP-CMP-01 |
| `src/auditmanager/executors/runner*.py`, `tools/executor-runner/agent.py` | PULL-01, then AGENT-01 | — | — |
| `web/src/widgets/executor-connections/**` | WEB-CAP-01 | WEB-WIZARD-01 | — |
| `src/auditmanager/shared/errors/**` | untouched | untouched | untouched |

«Sequential» means the second task is dispatched after the first is merged into the stage's integration branch.

## 6. Dispatch rules

1. **Push before dispatching dependents.** A stage's lanes are dispatched from that stage's SEAL tip once the integrator has merged it. The next stage starts from the previous `EXEC2-INT-*` tip once it is on `origin/dev`.
2. **Re-capture the premises.** Before each dispatch, the integrator re-runs every task's premise commands on the actual base and corrects line numbers.
3. **Lane hygiene.**
   - Lanes run on Sonnet; data gathering runs on Haiku.
   - Lanes do not run git; the integrator commits exactly the allowed paths.
   - Lanes report a five-minute heartbeat.
   - A process is stopped only by its own confirmed PID, never by a name pattern.
4. **Disk.** The host has 1.4 GB free. At most three lane worktrees exist at once; merged worktrees are removed after integration.
5. **Ports and services.** None. No lane starts PostgreSQL or S3 (`R-149d`).

## 7. Checks (`R-149d`)

**Done in every lane:**
- write the tests named in section 8, marked when they need a database;
- regenerate models and client from the contract;
- `git diff --check`.

**Done by the integrator at each integration:** a read-only review of the claim, binding, lock-order and consent diff:
- stage 1: claim, hint and per-token lock;
- stage 3: lock order, write-once binding, `environment` refusal, ceilings.

**Not done:** test runs, builds, typecheck, lint, database, browser, models.

Every `CURRENT_STATE` entry of this wave says «unverified development candidate».

Before any `origin/main` promotion of stage 1 or stage 3, `D-292` asks for the written database and stress tests to run on a capable runner.

## 8. Acceptance tests mapped to tasks

| Task | B1 §6 | B2 §11 | B3 §11 |
|---|---|---|---|
| CAP-01 | 1–6, 15 | — | — |
| PULL-01 | 7–12, 14 | 11 (pull regression) | — |
| WEB-CAP-01 | 13 | — | — |
| ENROLL-01, AGENT-01 | — | 2, 3, 4, 5, 7, 8 | — |
| ENROLL-SSH-01 | — | 1 | — |
| WEB-WIZARD-01 | — | 6, 9, 10 | — |
| GROUP-STORE-01 | — | — | 1, 2, 19 |
| GROUP-RUN-01 | — | — | 3–12, 14, 17, 18, 20 (runs) |
| GROUP-CMP-01 | — | — | 3–5, 9–14, 17 (comparison) |
| CUTOVER-01 | — | — | 15, 16, 22 |
| INT-3 | — | — | 21 |

## 9. Risks

| # | Risk | Measure |
|---|---|---|
| R1 | Races in capacity, binding or consent go unseen until a stand (`R-149d`) | Single-transaction decisions under the advisory lock; integration reviews; tests written; mode `rules` only by explicit act |
| R2 | A `pending` Run (NULL revision) is taken for an `environment` Run (also NULL) | `binding_state` with a database CHECK; claim filter; `environment` refuses group starts |
| R3 | Deadlock across group members | One documented lock order (ADR-0026 decision 14) |
| R4 | `max_claimed_tasks < max_active_runs` makes Runs end `not_sent` | Coupled validation (decision 2) |
| R5 | Client documents unchecked | UI notice, `D-291`, blocker for real client data |
| R6 | Subscription quotas are shared with interactive development | Capacity one by default and a visible refusal. Proposal outside the documents for the next wave: the agent reports «subscription limit» and the group dispatcher excludes that member until the limit resets. |
| R7 | Hand-kept table inventories drift with migrations (`D-213`) | SEAL-1 and SEAL-2 own them; unverified without database runs |
| R8 | `REVIEW-FIX-1102` changes the same files (`comparison/*`, migration 0045) | Start only after P-1; premises re-captured |
| R9 | Path A executes commands on a foreign host | Fixed script, host-key confirmation, `sudo -n`, key removal, sanitised failures |
| R10 | One of about 80 revision readers misses `pending` | Each task starts from its `git grep` inventory and closes every line; the integration review checks the inventory |

## 10. Estimate

| Stage | Effort | Calendar (critical path) |
|---|---|---|
| 1 | ~20 h | SEAL 3 h → lanes ≈ 4 h → INT 2 h ≈ 9 h |
| 2 | ~18 h | max(ENROLL-SSH 5 h; SEAL-2 4 h + STORE 3 h) → INT 2 h ≈ 9 h |
| 3 | ~22 h | GROUP-RUN 6 h → CUTOVER 3 h → INT 3 h ≈ 12 h |
| Total | ~60 h | ~30 h, P50 four working days, range 3–6 |

**Measured anchor:** `EXEC-PAR` on 2026-10-26. Three lanes (contract slot START, QUEUE, WEB) went from dispatch to an integrated tree in 2 h 10 min (14:35 → 16:45).

**Extrapolated:** every task figure, scaled by size. The largest is `GROUP-RUN-01` at about 57 reader lines.

**Excluded:**
- the wait for P-1;
- owner acts;
- Ubuntu acceptance;
- running the written tests before `main`, about 0.5–1 day on a host with 6 GiB free (`D-205`).

## 11. Owner acts

1. Optional: provide a clean Ubuntu LTS host for path A and B acceptance.
2. After stage 3 is deployed, confirm the six-`work_kind` cut-over preview on the stand.
3. Before `main`: free at least 6 GiB of disk for the `D-292` test run.
