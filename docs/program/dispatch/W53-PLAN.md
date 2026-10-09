# Wave 53 — durable execution, run journal and queue ∥ MinIO preparation and custody design

**Status:** revision 3 design adopted for W53 development on 2026-10-09 from judged planning commit
`2b45a11ec558df1452a4822149e54d2fe0ddb57e`; current-tree grants are issued by
`W53-FREEZE-01`. The planning worktree's uncommitted edits are not frozen inputs. Round 1
(design REJECT, grants REJECT) rebuilt the
plan as revision 2 (`a98daa6`); round 2 (both ACCEPT-WITH-FIXES, all fixes text or grant lines) is
applied here without a third round. Record: `docs/program/reviews/W53-PLAN-JUDGING.md`. Written by
the planning session on local branch `plan/roadmap-to-beta`. Dispatchable after `W52-INT-CLOSE` and
`W53-FREEZE-01`.
**Scope change in this revision (round-2 design judge's recommendation):** the custody
*implementation* — admission outbox, dispatcher, reconciler, migration, identifiers, the storage
role change of E-6 — moves to **W54 Stage B (lane B1, `W54-CUSTODY-01`)**. W53 freezes its design (`R-W2`, the rewritten custody
documents), because this host runs Stage-B lanes one after another (11 GiB RAM, ≈ 2 GiB free), custody
is not in `v0.4.0`, and its first consumer is the W54 upload.
**Controlling answers:** `ROADMAP-TO-BETA.md` §10.5 (Q-1), §10.10 (D-2.1, D-2.2, D-2.5), §10.11
(E-1…E-8). `W53-RULE-01` records the owner-backed decisions as R-75…R-79. W53 execution
placement is an implementation scope decision, not a new owner ruling.
**Roles and measures:** `IDENTITY-WAVES.md` §8 and §10; two cross-judges (contract, migration and
deploy are touched); `pin_sweep.py` on every grant plus the hand grants of `W53-FREEZE-01`.
**Exit:** a checked development candidate on `origin/dev`. A release verdict requires the
separately gated, exact-SHA path and the conditions below.
**2026-10-09 execution amendment on `origin/dev` `ff24263ed190227e704bc1e0fb411e25707c8203`:**
W52 is development-only. D-137–D-140 remain open, and neither `v0.3.0` nor a bundled-history
ruling exists. W53 implementation may advance independently, but `VERSION`, `0.4.0` notes,
`INT-MAIN` and the release claim stay closed. The owner has deferred W53 database backup work;
`W53-BACKUP-01` receives no dispatch grant. The owner placed database backup in a separate beta
wave; its exact task, policy and inputs will be frozen there. Section 3.4's backup design is
retained as a proposal, not frozen policy.
`W53-SEAL-01` and `W53-MINIO-01` may start from the freeze SHA. The MinIO lane may build and
test on disposable copies, but no working-stand upgrade is authorized. `W53-EXEC-01` and
`W53-EXEC-WEB` depend on the SEAL merge, not on deferred backup work. The Stage-C rehearsal
may cover execution and disposable MinIO only; backup/pull/restore acceptance remains deferred.
This amendment supersedes the backup dispatch, release and ordering sentences below wherever
they conflict. Its task files carry the executable grants.

## 1. Objective

- **Track 2 — E1, durable execution** (the critical path). The run queue becomes durable on W48's
  `job`/`attempt`/`lease`: Job at acceptance, priority dispatch with `SKIP LOCKED`, leases with a
  deadline, a heartbeat thread, periodic reclaim, automatic retry only when provably not processed,
  bounded resume, cancel, re-audit, pause; a transactional execution journal; «Журнал выполнения» and
  «Очередь». Execution stays in the API process; the worker service and «Исполнители» are W54 by scope
  (`ADR-0002` allows separate execution workers).
- **Track 1 — data safety.** Build and test the source-pinned MinIO security release on disposable
  data; freeze the custody design and rewrite its documents. A working-stand image upgrade and
  the proposed PostgreSQL/S3 backup flow await a separate owner-controlled recovery boundary.

## 2. Where it starts (measured on `integration/w49` at `1b25955`; re-checked at `631794c`)

| Fact | Source |
| --- | --- |
| `job`, `attempt`, `lease` exist (W48); frozen columns are only `job_id, run_id, created_at` and `lease_id, job_id, attempt_id, acquired_at`; the job edges `running→retry_wait`, `retry_wait→queued`, `queued→cancelled`, `retry_wait→dead_letter` already exist in `JOB_EDGES` | `20261002_0014_durable_analysis_effects.py:56-223, 479-494` |
| a Job is created by `start_execution`; no lease deadline; a second Attempt is impossible (`_SET_CURRENT`); `fail_for_run` returns silently without a current Attempt | `jobs/repository.py:33-36, 235-314` |
| `provider_call_effect` has no state for "never processed"; a `completed` effect needs tokens, latency and a `model_call` row | `0014` `ck_provider_effect_state`, `ck_provider_effect_response_shape` |
| `analysis_artifact_publication` knows only `prepared → bound` | `0014` `ck_analysis_artifact_state` |
| **live retry never fires**: any live adapter `DomainError` becomes `outcome_unknown`; 429/503/504 and `URLError` all map to `dependency_unavailable`; post-send exceptions escape untyped | `analysis/text/stage.py:285-297`; `analysis/text/proxy.py:146-320`; `runs/retry.py:66-82` |
| `dependency_unavailable` declares `safe_detail_keys: ["dependency"]` only; other keys raise `UnsafeDetailKey` | `contracts/domain/v1/error-codes.json`; `shared/errors/envelope.py:147-153` |
| the `RunCarrier` façade (`submit`/`drain`/`shutdown`, `InlineCarrier`, `app.state.run_carrier`) is used by 14 drivers; 12 more files call `start_audit_run` then `execute_run(cost_meter=…, sleep=…)` directly; `RunAdapter(..., carrier=InlineCarrier())` is built in tests outside any lane | `runs/carrier.py`; `api/app.py:273-314, 436-439`; `tests/integration/{exports,p02_journey}/**`; `p02_journey/test_retry_provenance_seam.py:120-279` |
| test apps often never enter the lifespan (`TestClient` without `with`) | `test_version_blocks_wire_shape.py:55-65`; characterization `journey.py:693-695` |
| start-up fails every `queued`/`running` run (`STARTUP_THRESHOLD = "0 seconds"`); `abandon_stale_commands` uses the same threshold | `runs/reconciliation.py:59-221` |
| the executor's final transaction locks `audit_run`, then `job` and `attempt` | `runs/executor.py:836`; `jobs/repository.py:55` |
| a terminal run is never reopened; correction is a re-audit (new run); retry inside a run is a new Attempt (PD-03) | `contracts/domain/v1/state-machines.json` `audit_run.run_creation` |
| backup exists only inside the destructive wipe, with quiesced checks; S3 restore never rehearsed with real objects | `infra/deploy/reset.sh:482-586, 191-346`; `/root/w47k-r52-restore.log` |
| this machine: 119 GB disk, ≈ 30 GB free, 11 GiB RAM (≈ 2 GiB available), 8 CPU | measured 2026-10-06 |

## 3. Design decisions bound by this plan

### 3.1 Durable execution (track 2)

- **Seams kept.** The dispatcher implements `RunCarrier`: `submit` wakes it, `drain` waits for this
  process's work, `shutdown` stops it. New behaviour lives **inside the carrier object** — no new
  required attribute or keyword on `RunAdapter` or `RunCarrier`. `start_audit_run` and
  `execute_run(cost_meter=…, sleep=…)` keep their signatures; `execute_run` claims the Job that
  `start_audit_run` created. An unclassified `dependency_unavailable` raised by a test double keeps
  today's retry. `ProxyAdapter(opener=…)` keeps its contract.
- **Where claiming runs.** Database-wide claiming and periodic reclaim run **only in a process that
  entered the serving lifespan**; outside it a carrier executes only what it was submitted, and
  `execute_run` holds its own heartbeat.
- **Job at acceptance:** `startRun` creates the Job (`queued`). The claim (`FOR UPDATE SKIP LOCKED`,
  `priority DESC, created_at`, the pause flag, configured concurrency, default 1) re-checks the run's
  state in the same transaction (`queued`, or `running` for a resumed Job); a Job whose run is no
  longer runnable goes `queued → cancelled`; `fail_for_run` handles a Job without a current Attempt.
- **Lock order, everywhere:** `audit_run → job → attempt → lease`, one statement each (a multi-table
  `FOR UPDATE` does not guarantee order). All lease times are database time.
- **Lease and heartbeat:** `lease.expires_at`, `lease.heartbeat_at`. A heartbeat thread with its own
  connection updates only `lease … WHERE released_at IS NULL AND expires_at > statement_timestamp()`
  under `SET LOCAL lock_timeout`, extending to 60 s every 20 s; it cannot revive an expired lease.
  `require_current` reads the lease last and checks `expires_at > statement_timestamp()`. The serving
  dispatcher reclaims expired leases every 30 s. `abandon_stale_commands` gets a 10-minute threshold.
  Start-up fails only `running` runs with no Job or a terminal Job; `STRANDED_STATES` drops `queued`.
- **Watchdog:** an Attempt may run at most `3 × 200 s + 2 s + 8 s + 2 × 60 s = 730 s` in
  `text_analysis` plus the local stages' budget (≈ 15 min in all). On expiry it stops that Attempt's
  heartbeat and moves the Attempt to `lost` in the database, so the next `require_current` refuses;
  the thread cannot be killed, so its slot stays counted until it returns (at concurrency 1 nothing
  else starts meanwhile), and its stale-attempt or cancel errors never take the crash path.
- **Provider dispatch classification (E-2, E-8):** the proxy transport records whether request bytes
  were written. A new effect terminal **`not_processed`** covers every provably-unprocessed outcome:
  no bytes written (name resolution, refused connection, TLS failure), 429, the proxy's own 503
  envelope (format measured and kept as a named fixture), and definite refusals (400, 401, 413, the
  proxy's non-retryable envelopes). The classification is stored on the effect row
  (`dispatch_class`), **never as an error detail key**. Retried: no bytes, 429 (`Retry-After` ≤ 60 s),
  own 503 — within the budget of 3 tries, 2 s / 8 s (E-7). Not retried: definite refusals (the run
  fails with the existing code). Everything else — another 503, 504, a timeout, reset or incomplete
  read after sending — is `outcome_unknown`; nothing is re-spent. The `live.py` SDK path stays
  `outcome_unknown`-only.
- **Proxy idempotency key per run:** `ModelRequest` gains an optional `idempotency_scope` excluded from
  `request_sha256`; the executor passes the run id; absent, today's key is used (the norms repair
  runner is unchanged). The proxy's replay semantics are measured and recorded.
- **Resume (E-7):** a Job whose lease expired goes `running → retry_wait → queued` ("lease lost") with
  a new Attempt **only if the lost Attempt holds no provider effect other than `not_processed`**;
  otherwise the run fails `outcome_unknown`. A Job has at most 3 Attempts, then `dead_letter` and the
  run `failed`. `CostMeter` is seeded from the run's `model_call` rows, so the per-run ceiling holds
  across Attempts; a pre-spent meter reports `estimated`, as the existing cost rule pins. Unbound
  artifact publications of a lost Attempt stay reported as today (no new state).
- **Commands (E-1, E-5):** `cancelRun`, `reauditRun` — expert or administrator; `setJobPriority`,
  `setExecutionPaused` — administrator. Cancel moves run, Job and Attempt to `cancelled` in one
  transaction in the lock order; the thread stops at its next boundary. Re-audit is allowed only from
  a terminal run, uses its own command type `reaudit_run` whose fingerprint includes
  `reaudit_of_run_id`, creates a new run over the same frozen inputs, and refuses while another
  re-audit of the same source run is not terminal. Rules live in `runs`/`jobs`, tested without the
  router.
- **Journal:** run, Job and Attempt transitions, stage finish and provider outcomes append an
  `audit_event` in the transaction that makes the change; a stage start is its own transaction. The
  payload allowlist (`ADR-0015`) excludes every `non_identity` value of `identifiers.json` (model name,
  provider request id, idempotency key) as well as prompts, response text, keys, paths, URLs and
  tokens.
- **Context:** journal and queue reads live in a new bounded context `auditmanager.execution`, a
  declared read projection in the sense of `ADR-0012` (the `dashboard` precedent), with a `public`
  module; it is new because `operations/` is reserved for operator commands and `workers/` for W54.
- **Migration `0017_execution_queue`:** `job.priority`, `job.available_at`, `lease.expires_at`,
  `lease.heartbeat_at`, `execution_control` (one row created lazily: `paused`, `changed_at`; the actor
  is in the journal — no account foreign key), `audit_run.reaudit_of_run_id` (the `BEFORE UPDATE`
  frozen trigger dropped and recreated with it, in the upgrade and the downgrade),
  `provider_call_effect` state `not_processed` and column `dispatch_class` (constraints and guard
  edge), the journal's run index. Backfill: unreleased leases get `expires_at = now()`; `queued` runs
  without a Job get one. Downgrade refuses with retained data and counts no seeded row.

### 3.2 Operations (names are the seal's to confirm)

| Operation | Method / path | Roles (any of) | Notes |
| --- | --- | --- | --- |
| `listExecutionQueue` | `GET /execution/queue` | every active complete account | Jobs `queued`, `leased`, `running`, `retry_wait`, then recent terminal; `paused`; cursor pagination |
| `listExecutionJournal` | `GET /execution/journal` | same | optional `run_id`; newest first; cursor pagination |
| `cancelRun` | `POST /runs/{run_id}/cancel` | `expert`, `admin` | `Idempotency-Key` |
| `reauditRun` | `POST /runs/{run_id}/reaudit` | `expert`, `admin` | `Idempotency-Key`; 202 with the new run |
| `setJobPriority` | `PUT /execution/queue/{job_id}/priority` | `admin` | queued Jobs only |
| `setExecutionPaused` | `PUT /execution/dispatch` | `admin` | body `{paused}` |

`RunStatus` gains `reaudit_of_run_id` — **optional, absent when null** (as `terminal_reason`), so
existing typed fixtures and characterization records stay valid. Skeleton routers answer through
port stubs; the seal's tests assert shapes, never empty pages or stub statuses. No error code and no
detail key is added.

### 3.3 Screens

- **«Журнал выполнения»** (`/logs`, graduating from the prepared-sections stubs): entries by run and
  stage with time, outcome and code; filter by run; a link from the run page.
- **«Очередь»** in Система (the stub W50 places, confirmed by the integrator): state, priority, age;
  cancel and re-audit for experts and administrators, priority and pause for administrators;
  confirmations name the run; the `paused` banner. Code namespace `execution`, never `queue`.
- Refresh on focus, after an action and by «Обновить»; no timer.
- The `/workers` stub stops claiming there are no job tables.

### 3.4 MinIO and proposed later backups (track 1)

Only the MinIO image build and disposable-copy checks are in the W53 development grant.
The backup design below is advisory until its owner policy, capacity and later task grant are set.

- **MinIO (D-2.1):** the server is rebuilt from the official source of `RELEASE.2025-10-15T17-29-55Z`
  with today's discipline (archive SHA-256, digest-pinned Go — moving if the release's toolchain is
  not `go1.24.2` — and Alpine, ldflags, version grep, labels); `mc` stays. **Rollback = the old server
  plus a restore from the S3-level backup.**
- **Backup on a live system:** `infra/deploy/backup.sh`. The PostgreSQL dump first, taken under an
  exported snapshot (`pg_export_snapshot`, `pg_dump --snapshot`); the list of `available` blobs is read
  in the same snapshot; then the objects. Available blobs are immutable and never deleted, so every
  listed blob's bytes exist when the mirror runs; newer objects are harmless orphans. Verification:
  the mirror holds every listed blob; the attribute sidecar is built **from the mirrored set** and
  equals it; the temporary prefix is excluded. The wipe keeps its quiesced check; shared functions
  move to `infra/deploy/lib/dump.sh`.
- **Stand side:** the staging directory and the `flock` file live **outside the stand's checkout**
  (every deploy refuses on an untracked file); need = `pg_database_size` + the sum of available
  `size_bytes`; the script refuses below need + 2 GB; one staged copy, deleted after a verified pull.
- **Transport (E-3):** `pull-backup.sh` here; a key the owner installs on the stand as
  `restrict,from="<this host>",command="…/backup-serve.sh"`; `backup-serve.sh` accepts exactly
  `make` and `stream <stamp>`, parses strictly, takes the `flock`, streams a tar on stdout. No data
  passes through GitHub or a third service; the key never enters the repository, a report or a chat.
  **Stated risk:** the key's account must run `docker`, which is root-equivalent; the forced command is
  the boundary.
- **Retention (E-4):** one latest verified copy here; a new pull lands beside the old one, is verified,
  then replaces it; a failed pull deletes its partial copy; a pull refuses unless two backups plus
  10 GB fit.
- **Restore rehearsal with real objects** (≥ 2 000 objects from a named corpus subset); if 29 000
  objects extrapolate past one hour, the restore loop is parallelised.
- **Capacity:** `readiness.sh` reports the stand's disk, memory and CPU (non-blocking).

### 3.5 Custody design frozen now, built in W54 (D-2.2, E-6)

Recorded in `R-W2` and in the rewritten `NORM_CORPUS_CUSTODY.md`, NORM-Q05, the `ADR-0020` addendum and
`NORM-CUSTODY-W53-ADDENDUM.md` (preserving the completed historical task `tasks/NORM-CUSTODY-01.md`):

- **Roles live on bindings.** Storage objects are content-identified bytes; a binding or manifest says
  what they are. `publish` of bytes already `available` under the same id **reuses** them after
  verifying size, SHA-256 and media type, whatever role the caller names, and returns the first
  publisher's role (documented); a different media type stays a conflict; an existing object without
  a recorded SHA-256 is refused, not reused. Equal bytes in the corpus and in a project are stored once.
- **A mismatch rejects the admission or the Attempt, never the content-derived Blob row.** Custody
  case 3 is reworded accordingly; `reject_unpublished` refuses while a non-terminal custody admission
  (through `norms.public`) or a non-terminal Attempt declares the blob.
- **Erasure:** removing a corpus or a project removes bindings, never bytes; bytes may be erased only
  when no live binding of any kind (document manifest, norm binding, analysis publication) references
  them, checked through each context's public module.
- **Anchors and identities:** the drop's opaque `doc_…`/`blk_…`/`page_index` references, stored as text,
  never parsed as `document_uid`; minted `nad`/`nbd` ids; one storage role `norm_source`; per-blob
  serialisation by an advisory lock inside storage's metadata repository, shared with ingest.
- **Outbox, commands, retry:** as revision 2 §3.1 — `admit|dispatch --until-idle|reconcile|report|requeue`,
  five tries (30 s … 2 h), then `poisoned` (E-7).

## 4. Tasks

### `W53-RULE-01` (integrator)

Standard form; records after the owner confirms the text:

- `R-W1` MinIO (D-2.1) and the rollback definition; `D-119` closes on the rehearsal evidence.
- `R-W2` the custody design of §3.5 (D-2.2, E-6), superseding the one-role rule of `storage/s3.py`,
  NORM-Q05's sentence and `ADR-0020` L35-37; the drop's references as anchors and the single
  `norm_source` role are this plan's design, confirmed with the rule; implementation in W54.
- `R-W3` backup transport/retention answers (D-2.5, E-3, E-4) may be recorded as historical
  owner answers, but no W53 backup implementation ruling or RPO/schedule is inferred.
- `R-W4` execution control (E-1, E-5): reads for everyone signed in; cancel and re-audit for experts and
  administrators — a narrow exception to `R-60`; priority and pause for administrators.
- `R-W5` retry numbers (E-7, E-8, OQ-04) as §3.1.
- `R-W6` execution stays in the API process in W53; the worker service is W54 by scope.

### `W53-FREEZE-01` (integrator)

Standard form, plus: migration `0017` assigned (custody takes `0018` in W54); `pin_sweep.py` for
`reseal-surface migration table route`; **hand grants** for what it cannot see (state-machine
documents, query namespaces, the carrier seam, prepared sections, the journey manifest, the address
builders); the corpus subset for the restore rehearsal named by document id; after W52 lands,
`git grep -n '0\.3\.0' tests web/tests`; ports for seven lanes; `W53-RUNTIME-EVAL` scheduled outside
the stages in a window the integrator has confirmed idle.

### Stage A — from the freeze SHA (executor)

**`W53-SEAL-01`** — the six operations and the optional `RunStatus` field of §3.2 with port-stubbed
skeleton routers; role registers and their sweep tests (six new rows in `test_role_register.py`; the
OpenAPI capability prose `role:admin|expert`); migration `0017_execution_queue` (§3.1); the run/job
notes in `state-machines.json` (resume path, `queued → cancelled`); the four-document reseal; the
facts file; the custody document rewrites of §3.5. Allowed — **`W52-SEAL-01`'s list verbatim**, then:

- `contracts/**`; `web/openapi/openapi.json`, `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json`;
- `src/auditmanager/api/**` except `app.py`; `src/auditmanager/bootstrap/{adapters,composition}.py`;
- `db/migrations/versions/<date>_0017_execution_queue.py`;
- `tests/contract/**` except W52's guard files and `tests/contract/release_notes/**`;
  `web/tests/contract/**` except `narrow-sets.contract.test.ts`;
- `tests/integration/{api,auth,db}/**`; `tests/integration/composition/**` except
  `test_minio_image_contract.py`, `test_reset_script_refusals.py`, `test_readiness_command.py`,
  `test_backup_script_refusals.py`, `test_reset_rehearsal_counts_base_tables.py`,
  `test_the_run_leaves_the_request_thread.py`, `test_a_published_run_reports_itself.py`;
- `tests/integration/p02_journey/journey.py` (`P02_TABLES`); `tests/e2e/pc01/test_acceptance.py` (route
  count; the mutating set gains `cancelRun`, `reauditRun`, `setJobPriority`, `setExecutionPaused`);
- `tests/support/expected_facts.json`, `docs/program/CONTRACT_PIN_REGISTRY.md`;
- the count sentences in `web/src/app/bff/v1/[...path]/route.ts`, `web/src/shared/api/authorization.ts`,
  `infra/deploy/README.md` (count row), `infra/deploy/serve.py`, `infra/deploy/proxy/nginx.conf`,
  `src/auditmanager/api/README.md`; `docs/program/P02_SEAMS.md` §7 (rows, counts, idempotency rule)
  with `tests/contract/domain_p02/test_seam_register.py`;
- the head sentence in `docs/manual-tests/PC-01_prototype.md`; the live surface-triple and head
  sentences in `docs/program/CURRENT_STATE.md` and `docs/program/ALPHA_ROADMAP.md`;
- `docs/program/NORM_CORPUS_CUSTODY.md`, `docs/program/NORM_CORPUS_DECISION_BACKLOG.md`,
  `docs/architecture/adr/ADR-0020-normative-corpus-alpha-runtime.md` (addendum only),
  `docs/program/NORM-CUSTODY-W53-ADDENDUM.md` (new; historical task remains unchanged);
- every further path `pin_sweep.py` prints at the freeze; `docs/program/W53-SEAL-01.md`.
Required: `pin_sweep.py --check` clean; contract tests; a fresh upgrade, an upgrade of a database at
`0016` with rows (an unreleased lease, a queued run without a Job), a refused downgrade with retained
data; `make gate`.

**`W53-MINIO-01`** (§3.4). Allowed: `infra/minio/**`, the MinIO tags in
`infra/deploy/compose.server.yml` and `infra/local/docker-compose.yml` (and its comments L19-20),
`docs/program/FOUNDATION_LOCK.json` (the MinIO server entry and `minio_build_inputs`),
`tests/integration/composition/test_minio_image_contract.py`, `docs/program/W53-MINIO-01.md`. Required:
the build from pinned inputs; old-server-writes → new-server-reads on a disposable copy; the rollback
definition exercised; `make gate`.

**`W53-BACKUP-01` — deferred; no W53 dispatch grant.** The following judged design is retained
for later revalidation: `infra/deploy/{backup,backup-serve,pull-backup}.sh` (new),
`infra/deploy/lib/dump.sh` (new), `infra/deploy/reset.sh` (shared functions; the parallel restore loop),
`infra/deploy/readiness.sh`, `infra/deploy/README.md` (file table L25-41 and backup sections),
`infra/deploy/env/alpha.env.example` (only if a variable is added), `docs/program/DEPLOYMENT_RUNBOOK.md`
(backup sections), `tests/integration/composition/{test_reset_script_refusals,test_backup_script_refusals,test_readiness_command,test_reset_rehearsal_counts_base_tables}.py`,
`docs/program/W53-BACKUP-01.md`. Required: a refusal test per guard; a backup taken **while uploads
run** verifies and restores; both floors refuse; the forced command refuses every other verb, a
malformed stamp and a concurrent run; nothing staged inside the checkout; `shellcheck`; `make gate`.
Rebased after the seal merge (the README's count row is the seal's).

### Stage B — from the Stage-A merge (executor; on this host the lanes run one after another)

**`W53-EXEC-01`** (§3.1). Allowed: `src/auditmanager/{jobs,runs,execution}/**` (`execution` new),
`src/auditmanager/api/app.py` (lifespan only), `src/auditmanager/api/routers/{runs,execution}.py`
(bodies), `src/auditmanager/bootstrap/{adapters,composition}.py` (wiring),
`src/auditmanager/analysis/text/{proxy,stage,adapter}.py` (transport, classification, the optional
`idempotency_scope`), `tests/integration/{jobs,runs,execution}/**` (`jobs`, `execution` new),
`tests/integration/analysis_text/{test_proxy_adapter,test_live_adapter_shape,test_provider_modes}.py`,
`tests/integration/composition/{test_the_run_leaves_the_request_thread,test_a_published_run_reports_itself,test_composition_root}.py`,
`tests/e2e/pc01/driver.py`, `fixtures/proxy/error-envelope-503.json` (new; outside
`fixtures/recorded/text_analysis/`), `docs/program/W53-EXEC-01.md`. Required:

- no bytes written and the proxy's own 503 are retried and the run publishes with `not_processed`
  effects; 429 honours a capped `Retry-After`; 400/401 end `failed` with `not_processed`; a reset after
  sending, a foreign 503 and a 504 end `outcome_unknown` with zero further calls;
- a restart within 60 s leaves a live lease alone; the periodic reclaim takes it after expiry;
  resume only without an effect other than `not_processed`; the third Attempt dead-letters; a seeded
  meter stops at the ceiling across Attempts;
- two-connection tests: cancel ∥ claim, cancel ∥ the final transaction, heartbeat ∥ fenced write —
  no deadlock, no crash-path failure;
- the watchdog fences a blocked Attempt and keeps its slot until the thread returns;
- a second serving process does not disturb a live lease; a non-serving test app claims nothing;
- re-audit only from terminal runs, its own command type, one non-terminal re-audit per source; cancel
  from each state in one transaction; priority; pause;
- every transition has exactly one journal entry, and a forced rollback leaves none;
- the 14 drivers and the 12 direct `execute_run` files pass unchanged; `make gate`.

**`W53-EXEC-WEB`** (§3.3). The current W50 stub routes are `web/src/app/logs/page.tsx`
and `web/src/app/queue/page.tsx`; the page modules are `web/src/_pages/logs/**` and
`web/src/_pages/queue/**`, not `execution-queue`. Allowed: `web/src/app/{logs,queue}/**`,
`web/src/_pages/{logs,queue,workers,run}/**` (`run` — the journal link only),
`web/src/widgets/{execution-journal,execution-queue}/**`,
`web/src/features/{cancel-run,reaudit-run,set-job-priority,pause-execution}/**`,
`web/src/entities/execution/**`, `web/src/shared/lib/routes.ts` with
`web/tests/unit/screens/routes.test.ts` (the `built` map), `web/src/shared/config/screen-registry.ts`
(the two entries), `web/src/shared/api/query-keys.ts` (namespace `execution`) with
`web/tests/guards/query-key-shape.guard.test.ts`, `web/docs/PC01_UI_SEAM.md` (§6),
`web/tests/unit/api/configuration-and-cache-keys.test.ts` (namespaces),
`web/tests/contract/narrow-sets.contract.test.ts` (namespaces),
`web/tests/guards/prepared-sections.guard.test.ts` (`/logs` and the queue graduate; the workers
sentence), `web/tests/guards/dashboard-invalidation.guard.test.ts` (map entries),
`web/tests/guards/rendered-language.guard.test.ts` (matrix), `web/tests/unit/styles/screens.ts`,
`tests/e2e/pc01/journey/manifest.json`, the web capability map if W50/W51 introduced one (the
`role:admin|expert` entry), `web/tests/unit/execution/**`, `docs/program/W53-EXEC-WEB.md`. Required:
each refusal for a role without the action is a typed state; 780 px with long run names; lint,
typecheck, `npm test`, the journey manifest check.

### Stage C — from the Stage-B merge

**`W53-REHEARSAL-01`** (executor; disposable stand here; report and scripts only):

1. old MinIO with objects → upgrade → reads verified; rollback by the old server plus an S3-level
   restore;
2. backup, forced-command pull, database/S3 restore and their timing are deferred to the separate
   beta backup wave; this task must not report them as passed;
3. execution with a fault-injecting proxy: no bytes written, own 503, 429 with `Retry-After`, a reset
   after sending, a foreign 503, a 400; kill the process mid-run; a second serving process;
4. the capacity report.
Allowed: `docs/program/W53-REHEARSAL-01.md`, `scripts/rehearsal/w53/**` (new; no surface-count
phrases — `scripts/` is live prose for the prose guard).

**`W53-RELNOTES-01` — blocked until actual `v0.3.0` release or an owner-approved bundled
history/version ruling.** Its proposed grant was: `release-notes/0.4.0.json` (Журнал выполнения, Очередь, more reliable
runs, cancel and re-audit) and `VERSION` → `0.4.0`. Allowed: `release-notes/0.4.0.json`,
`release-notes/dictionary.json` (additions), `VERSION`, `docs/program/W53-RELNOTES-01.md`.

### Stage D — judging (fresh contexts), then FIX

- `W53-QA-01`: standard form; `tests/integration/qa_w53/**`, `web/tests/unit/qa_w53/**`.
- `W53-JUDGE-X` (built stand): provider faults of §3.1; the queue actions as every role; S3
  unreachable, disk full; the forced command attacked (other verbs, traversal in the stamp, concurrent
  pulls); a deploy right after a backup (nothing untracked in the checkout); no secret in any log.
- `W53-JUDGE-Y`: restore equals the source by manifest; ALR-05 for `execution`; journal entries equal
  transitions one-to-one; the lock order holds in every code path; rules in `runs`/`jobs`.
- `W53-NOTES-JUDGE`: `0.4.0.json` against the diff; re-run on the INT-CLOSE candidate.
- `W53-FIX`: standard form.

### `W53-INT-CLOSE` (integrator)

Standard form; register work: retain `D-119` until the working-stand image upgrade has its
required inventory, recoverable copy and post-upgrade checks; the MinIO
prose in `CURRENT_STATE.md`; the "no retry in the executor" sentence of `ALPHA_ROADMAP.md`; the
`outbox` line of `runs/scope.py` stays until custody lands (W54); register this wave's debts (at least:
live updates of queue and journal; the worker service; the `mc` client left at its release; the
backup account's root-equivalence; the watchdog cannot free a blocked thread's slot).

### `W53-INT-MAIN-01` (integrator, on the owner's instruction naming the SHA)

1. the owner has installed the forced-command key on the stand;
2. `pull-backup.sh`; verify — **the `D-123` inventory** (objects, sizes, attributes);
3. restore it here under the old MinIO, upgrade that copy, verify reads — D-2.1's rehearsal on real
   data; count equal-bytes collisions between the stand's blobs and the corpus, read-only (input to
   W54's custody);
4. `origin/main`; deploy (the MinIO upgrade happens here); verify object reads on the stand;
5. live acceptance: cancel and re-audit by an expert and by an administrator; priority and pause by an
   administrator; the journal shows each step; «Что нового» shows `0.4.0`; runs use `provider_mode`
   `proxy`, which release acceptance counts as live (owner ruling `R-65`, recorded after this plan was
   judged); a provider fault is observed only if the proxy produces one, never through a test hook on
   the stand;
6. tag `v0.4.0`; `RELEASES.md` row; close `D-123`.

## 5. Integration order

1. `W53-RULE-01`, `W53-FREEZE-01`; `W53-RUNTIME-EVAL` in an idle window.
2. Stage A: SEAL ∥ MINIO; merge SEAL, then MINIO. BACKUP is deferred to beta.
3. Stage B: EXEC, then EXEC-WEB (sequential on this host; EXEC-WEB can start from the seal against the
   skeleton pages).
4. Stage C: the execution and disposable MinIO parts of REHEARSAL; RELNOTES remains blocked.
5. Stage D: QA ∥ X ∥ Y; cross-examination and FIX. NOTES-JUDGE follows only after RELNOTES opens.
6. `W53-INT-CLOSE`; `W53-INT-MAIN-01` on instruction.

## 6. Ownership matrix

| Hotspot / path family | Owner (stage) | Parallel writer |
| --- | --- | --- |
| `contracts/**`, migration `0017`, `api/**` (but `app.py` and the two routers' bodies), generated client, `FRONTEND_LOCK.json`, facts file, custody documents, the ADR addendum | SEAL (A) | none |
| `infra/deploy/README.md` | SEAL (A, count row), then BACKUP (A, file table and backup sections, rebased) | none at the same time |
| `bootstrap/{adapters,composition}.py`, `api/routers/{runs,execution}.py` | SEAL (A), then EXEC (B) | none at the same time |
| `infra/minio/**`, MinIO tags and comments, the `FOUNDATION_LOCK.json` MinIO keys, `test_minio_image_contract.py` | MINIO (A) | none |
| backup scripts, `lib/dump.sh`, `reset.sh`, `readiness.sh`, their four tests, runbook backup sections | no W53 owner; beta backup wave to regrant | none |
| `{jobs,runs,execution}/**`, `api/app.py` (lifespan), `analysis/text/{proxy,stage,adapter}.py`, the three composition tests, `e2e/pc01/driver.py`, the envelope fixture | EXEC (B) | none |
| web screens, web guards and documents named | EXEC-WEB (B) | none |
| `VERSION`, `release-notes/0.4.0.json`, dictionary additions | no active W53 grant until predecessor-release evidence or owner version ruling | none |
| `CURRENT_STATE.md` (other sentences), `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand | integrator | none |

## 7. Stop conditions

`W48-PLAN.md` §14, plus: a frozen state machine forbids a transition of §3.1; the transport cannot tell
"no bytes written" from "written", or the proxy's own envelope from an upstream one; a change would need
a new error detail key or code; the MinIO release does not build from pinned inputs or cannot read old
data; a pull would need more reach than the forced command; free space here or on the stand below its
floor; the runtime evaluation would overlap a gate; any lane would write custody objects.

## 8. Non-goals

Backup implementation, working-stand MinIO upgrade, custody implementation, the storage role change, the corpus upload, the 121 repairs, embeddings (W54;
D-2.4 open); the worker service and «Исполнители» (W54); live push of queue or journal; off-host
encrypted backups (after beta); replacing MinIO (after 1.0).

## 9. Estimate

Critical path in active hours, with Stage B sequential on this host: freeze 1.0; Stage A (SEAL with
one stop) 3.5 + merges 1.5; Stage B EXEC 5.0 then EXEC-WEB 3.0 + merges 1.0; Stage C 2.0; Stage D
1.5, FIX rounds 3.0, gate 0.5; INT-CLOSE 1.0 — **≈ 22 h**. **P50 ≈ 4 working days, P80 ≈ 5.5** (several
FIX rounds are expected: W48's durable-effects work needed four). Not counted: the key installation,
the `main` instruction, the runtime evaluation's idle window.
