# ADR-0026: Executor capacity, universal agent enrollment, and homogeneous executor groups with dispatch-time binding

- Status: accepted
- Date: 2026-11-02; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: the owner's three design documents of 2026-11-02 (product decisions are the owner's, engineering choices the planner's inside them); deviations `R-149a`…`R-149d`; `R-149b`, `R-149c`; `EXEC2-FOLLOWUP-01`; plan `docs/program/dispatch/EXEC2-PLAN.md`. Revisable by a dated addendum.
- Amends: the `executor_route_event` Primary/Standby route stops being the source of **new** routing decisions once an administrator cuts over (decision 17; history stays readable); the single-active-run rule of `EXEC-PAR-QUEUE-01` becomes the default capacity of one (decision 1). · Amended by: `ADR-0028` (decisions 1, 2, 3, 5, 8, 9, 10, 12–15, 17, for runs with a `stage_plan`).
- Related: `ADR-0024` (OpenRouter base connection, AI execution), `ADR-0025` (comparison spend journal, ceilings, `max_images`). Owner: repository owner / EXEC-2 integrator (`R-149f`).

Every `EXEC2-*` task cites a decision of this ADR as «ADR-0026 decision n» instead of re-deciding it.

## Context

The owner's three design documents ask for:

1. several independent Audit Runs on one executor connection at once (Block 1);
2. a universal Ubuntu agent installed over SSH from the UI (path A) or by one copied command (path B), both first-class (Universal Agent);
3. homogeneous executor groups chosen per kind of model work by rules, with model and connection frozen at dispatch rather than at request (Stage 3).

Before this ADR a connection is exclusive per run and there is no enrollment, installer or group (`docs/program/dispatch/EXEC2-PLAN.md` section 2).

## Decision

### Capacity (Block 1)

1. **One capacity unit.** A connection's used capacity is the number of its Runs in `leased`, `running` or `retry_wait`, plus its `comparison_model_call` rows in `prepared` or `sent` whose attempt is live; each counts one for its whole life. Capacity is `max_active_runs` of the connection's **current** revision (1–16; absent or legacy means 1); a lowered capacity governs new claims only and never stops work in flight. The decision is taken under the existing `connection_id` advisory lock, in the existing lock order, in three places: the Run claim, the dispatcher hint (a count) and the comparison call preparation.
2. **Coupled limits, validated on the revision.** `pull`: `max_claimed_tasks ≥ max_active_runs`, else surplus Runs would end `not_sent`. `http_api`: `max_parallel_calls`, when set, `≥ max_active_runs` (a Run's calls are sequential, so this bounds concurrent calls without a new counter). `ssh_command`: above one only after the task implementing decision 1 shows the wrappers isolate concurrent invocations.
3. **Pull claims are serialised per token.** The claim locks the runner-token row before counting held claims. An optional `runner_instance_id` limits redelivery of a held claim to the same instance; a claim without it behaves as before. One token is served by one agent process (v1), which keeps a registry of task ids in work and never starts a duplicate. `D-215` closes in the same task.

### Universal agent (Universal Agent design, `R-149b`)

4. **Enrollment grant.** Stored as a hash only; single-use, expires after 15 minutes, bound to one pull connection. Its secret is shown once; a new grant revokes the previous unredeemed one. `POST /runner/enroll` exchanges it for a runner token (a repeat within the exchange window is idempotent, a repeat after redemption is refused). The grant never reaches the four task operations.
5. **Agent health lives on the runner token.** It holds the agent version, per CLI `installed`, `version` and a sanitised `auth_state`, concurrency, the execution profile and the declared features. «Online» is the freshness of `last_seen_at` under a bounded threshold. No secret, credential path or document text is stored.
6. **Agent package.** Built deterministically from `tools/executor-runner/` and served by version without authentication (public code, no secret; integrity is the sha256 in the generated command). The enrollment secret reaches `install.sh` only through an environment variable, never argv. `install.sh` is the same for paths A and B: idempotent, installs the systemd unit and a `0600` environment file, no restart loop on configuration or token refusal, `concurrency = 1`, `--uninstall`.
7. **Path A is an install session executed by the worker.** The admin supplies SSH access: a key the stand generates (the administrator adds its public half) or a pasted private key, which is sealed; passwords are not accepted. The observed host-key fingerprint is confirmed explicitly. A fixed script runs with the package on stdin and `sudo -n`; no command text comes from the UI. The stand's key line is removed and its secret destroyed afterwards. The worker executes it (only the worker opens secrets).
8. **Four CLI statuses stay distinct:** `installed`, `auth valid`, `authorised for this integration` (an administrator's mark on the connection) and `model probe passed`. Auth is read only through the CLI's official mechanism. The agent invokes the official CLIs in their documented non-interactive mode; no identity spoofing, human simulation, credential copying or limit evasion.
9. **Moving an agent to another host** is a new enrollment for the same connection. The old token is revoked once the new agent is online; work in flight follows the existing semantics.

### Groups and rules (Stage 3)

10. **Immutable group revision.** It holds `pin_id`, `gateway_model`, `billing`, a rate snapshot, `strategy = least_loaded` and the members' **revision** snapshots. Every member revision must match `pin_id` and `gateway_model` exactly, be of a served kind and share `billing` and rates (option A of the design; mixed groups are refused).
11. **Rules.** One current rule per `work_kind`, append-only, targeting a group revision.
12. **Explicit binding state.** Every Run and comparison job has a `binding_state`: `frozen_at_start` (every existing row, an explicit connection and a preset; behaviour unchanged), `pending` (admitted by rule or group), `bound` (after dispatch). The frozen-column triggers allow `connection_revision_id` NULL → value exactly once, on `pending` → `bound`; any later change is refused. The `environment` provider source refuses a group start, and its worker never claims a `pending` Run.
13. **Admission freezes intent, not executor.** Admission records the rule revision, the group revision and the consent envelope (`work_kind`, group revision, `pin_id`, billing and rate basis, ceiling, estimate digest, actor, time); the input budget and the estimate follow the group revision's `pin_id`. The canonical binding (`connection_revision_id`, `gateway_model`, cost basis) is written at dispatch.
14. **Dispatch inside the existing claim transaction.** Lock order: worker intake → group → member connections in ascending `connection_id` → control → Run → Job. An eligible member has a current revision equal to the snapshot, is served, has probe `ok` on its current key, a pull runner online, is not archived and has a free unit under decision 1; pick the minimum `used / capacity`, ties broken by a persisted rotation. Before commit: re-check the consent envelope, apply the `comparison_*` USD 10 per job and USD 50 per day ceilings against the selected member, reserve the unit, write the binding and a dispatch event. Model I/O starts only after commit; a failed consent check sets `needs_reconsent` and calls nothing. A comparison job binds at its first dispatched call and its later calls stay on that member.
15. **Waiting is durable and visible.** `wait_reason` (`waiting_for_capacity`, `waiting_for_executor`, `needs_reconsent`) and `waiting_since` are stored. When every member is offline longer than `AUDITMANAGER_GROUP_OFFLINE_WAIT_SECONDS`, default 1800 (`R-149c`), the work ends `no_executor_online`; waiting for a busy member is unbounded.
16. **No re-routing after binding.** An Attempt retry stays on the bound member; `outcome_unknown` is never sent to another member.
17. **Cut-over.** The routing mode is stored in the database (`legacy` by default, `rules`), each change journalled. The preview proposes a one-member group per primary, never converts a standby and flags incompatible routes; the administrator's confirmation creates groups, rules and mode `rules` in one transaction. Under `rules`, `setExecutorRoute` answers `conflict` and a `work_kind` without a rule is a typed refusal. Rollback is an explicit return to `legacy`; work already admitted by rules finishes on its own group revisions and is never re-read through a legacy route.
18. **Refusals reuse the catalogue.** Only `validation_failed`, `conflict`, `dependency_unavailable` and `model_identity_mismatch` are used, with typed details; EXEC-2 adds no error code. A group whose rate snapshot no longer equals the provider lock is refused with the existing cost-preflight refusal `analysis_input_invalid` (`stage_id`, `reason: cost_estimate_binding_changed`) **only** on operations whose contract declares `422`; an estimate that declares none is computed at the snapshot and the start refuses (`EXEC2-FOLLOWUP-01`, 2026-11-03).

### Deviations recorded by the owner

19. `allow_client_documents` is not enforced in EXEC-2 (`R-149a`, `D-291`). Capacity above one and group routing are for test data until it is, and the UI says so.
20. The acceptance tests of the three documents are written and not run in EXEC-2 (`R-149d`, `D-292`).

## Consequences

- Positive: default behaviour is unchanged — capacity one, mode `legacy`, old agents and API callers.
- Cost: every reader of a Run's or job's frozen revision must handle `pending` (`EXEC2-GROUP-RUN-01`, `EXEC2-GROUP-CMP-01`).
- Cost: the stand serves one more unauthenticated route (the agent package) and one enrollment exchange; both need throttling at the proxy.
- Cost: without database runs (`R-149d`), races in capacity, binding and consent are first exercised on a stand.

## Alternatives considered

- **A reservation table for capacity** — rejected for v1: the persisted states identify every holder.
- **Binding at admission** — rejected: the owner approved dispatch-time binding.
- **Re-probing a member's current revision instead of a snapshot** — rejected: queued work must not adopt a new destination or credential silently.
- **Mixed-billing groups with a maximum-price quote (option B)** — not approved by the owner.
- **A per-call counter for `http_api`** — unnecessary while a Run's calls are sequential (decision 2).

## Verification

Acceptance tests are per `docs/program/dispatch/EXEC2-PLAN.md` section 8, written and not run in EXEC-2 (decision 20, `D-292`). Each integration has a read-only review of the claim, binding, lock-order and consent diff.

## Revisit trigger

The first use with real client documents (decision 19); parallel model calls inside one Run (decision 2); a multi-instance pull protocol (decision 3); mixed-billing groups (decision 10); a move from subscriptions to direct APIs (decision 8, `R-149b`).

## History

- 2026-11-02 — accepted on the owner's design documents (deviations `R-149a`…`R-149d`).
- 2026-11-03 — addendum `EXEC2-FOLLOWUP-01` (`analysis_input_invalid` / `cost_estimate_binding_changed` for a stale group rate snapshot) folded into decision 18.
- 2026-11-09 — amended by `ADR-0028` for runs with a `stage_plan`; 2026-11-10 — the AR v3 run-group tables (`ar_v3_run_group`, `ar_v3_run_group_member`), whose names decision 10's `executor_group`, `executor_group_revision` and `executor_group_member` avoided, are removed (`R-154c`); decision 10's tables stay.
- 2026-11-18 — compressed (ADR-OPTIMISE-01); the full earlier text: git show fb6c2203e:docs/architecture/adr/ADR-0026-executor-capacity-enrollment-groups.md
- 2026-11-18 — status statements updated to dev fb6c2203e: `D-215` is closed, `D-291` and `D-292` are still open (`docs/program/DEBT_REGISTER.md`).
