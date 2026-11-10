# ADR-0026: Executor capacity, universal agent enrollment, and homogeneous executor groups with dispatch-time binding

- Status: accepted by the repository owner. The product decisions of the three design documents of 2026-11-02 are the owner's, the deviations are `R-149a`…`R-149d`, and the engineering choices below are the planner's inside them. They are revisable by a dated addendum.
- Date: 2026-11-02
- Owners: repository owner / EXEC-2 integrator (`R-149f`)
- Supersedes: the `executor_route_event` Primary/Standby route as the source of **new** routing decisions once an administrator cuts over (decision 17). The route history stays readable. The single-active-run rule of `EXEC-PAR-QUEUE-01` becomes the default capacity of one (decision 1).
- Related ADRs: `ADR-0024` (OpenRouter base connection, AI execution), `ADR-0025` (comparison spend journal, ceilings, `max_images`)
- Plan: `docs/program/dispatch/EXEC2-PLAN.md`

Every `EXEC2-*` task cites a decision of this ADR as «ADR-0026 decision n» instead of re-deciding it.

## Context

The owner's three design documents ask for:

1. several independent Audit Runs on one executor connection at once (Block 1);
2. a universal Ubuntu agent installed either over SSH from the UI (path A) or by one copied command (path B), both first-class (Universal Agent);
3. homogeneous executor groups chosen per kind of model work by rules, with model and connection frozen at dispatch rather than at request (Stage 3).

The code on `origin/dev` `9617c759` (code tree `4ab29560`) already has the following:

- per-connection exclusivity (`jobs/repository.py` `_hold_connection_limit`, an advisory lock per `connection_id`, mirrored by the comparison spend wrapper);
- worker slots;
- an explicit executor and a preset at run start;
- the pull channel with runner tokens;
- the CLI wrappers;
- SSH with host-key pinning;
- six `work_kind` values with a Primary/Standby route;
- immutable cost consent for runs (`RunCostConsent`) and comparison jobs (`comparison_ai_job` consent columns under `am_guard_comparison_ai_job_consent`).

It has no enrollment, no installer and no groups. The plan section 2 records the full reconciliation.

## Decision

### Capacity (Block 1)

1. **One capacity unit.** A connection's used capacity is the number of its Runs in `leased`, `running` or `retry_wait`, plus its `comparison_model_call` rows in `prepared` or `sent` whose attempt is live. Each counts one for its whole life. Capacity is `max_active_runs` of the connection's **current** revision (1–16; absent or legacy means 1). A lowered capacity governs new claims only and never stops work in flight. The decision is taken under the existing `connection_id` advisory lock, in the existing lock order, in three places: the Run claim, the dispatcher hint `_NEXT_JOB` (count, not existence), and the comparison call preparation.
2. **Coupled limits, validated on the revision.**
   - `pull`: `max_claimed_tasks ≥ max_active_runs`; otherwise surplus Runs would end `not_sent`.
   - `http_api`: `max_parallel_calls`, when set, `≥ max_active_runs`. A Run makes its calls one at a time, so this bounds concurrent calls without a new counter.
   - `ssh_command`: a value above one is accepted only after the task that implements decision 1 shows the wrappers isolate concurrent invocations.
3. **Pull claims are serialised per token.** The claim locks the runner-token row before counting held claims and claiming. An optional `runner_instance_id` in the claim body limits redelivery of a held claim to the same instance. A claim without it behaves as before. One token is served by one agent process (v1); the agent keeps a registry of task ids in work and never starts a duplicate. `D-215` closes in the same task.

### Universal agent (Universal Agent design, `R-149b`)

4. **Enrollment grant.**
   - A grant is stored as a hash only. It is single-use, expires after 15 minutes and is bound to one pull connection.
   - Its secret is shown once. A new grant revokes the previous unredeemed one.
   - `POST /runner/enroll` exchanges it for a runner token; a repeat within the exchange window is idempotent, a repeat after redemption is refused.
   - The grant never reaches the four task operations.
5. **Agent health lives on the runner token.**
   - It holds the agent version and, per CLI, `installed`, `version` and a sanitised `auth_state` enumeration.
   - It also holds concurrency, the execution profile and the declared features.
   - «Online» is the freshness of `last_seen_at`, under a bounded threshold.
   - No secret, path to a credential or document text is stored.
6. **Agent package.**
   - Built deterministically from `tools/executor-runner/` (sorted entries, zero mtime) and served by version without authentication. It is public code with no secret; integrity is the sha256 written into the generated command.
   - The enrollment secret reaches `install.sh` only through an environment variable, never argv.
   - `install.sh` is the same for paths A and B. It is idempotent, installs the systemd unit and a `0600` environment file, keeps the exit-code semantics (no restart loop on configuration or token refusal), writes `concurrency = 1`, and supports `--uninstall`.
7. **Path A is an install session executed by the worker.**
   - The admin first supplies SSH access: either a key the stand generates, whose public half the administrator adds, or a pasted private key, which is sealed. Passwords are not accepted.
   - The observed host-key fingerprint is confirmed explicitly.
   - A fixed script runs with the package on stdin and `sudo -n`; no command text comes from the UI.
   - The stand's key line is removed and its secret destroyed afterwards.
   - The worker executes it after the pattern of `probe_runner`, since only the worker opens secrets.
8. **Four CLI statuses stay distinct.** They are `installed`, `auth valid`, `authorised for this integration` (an administrator's mark on the connection) and `model probe passed`. Auth is read only through the CLI's official mechanism. The agent invokes the official CLIs in their documented non-interactive mode; no identity spoofing, human simulation, credential copying or limit evasion.
9. **Moving an agent to another host** is a new enrollment for the same connection. The old token is revoked once the new agent is online; work in flight follows the existing semantics.

### Groups and rules (Stage 3)

10. **Immutable group revision.**
    - It holds `pin_id`, `gateway_model`, `billing`, a rate snapshot, `strategy = least_loaded` and the members' **revision** snapshots.
    - Every member revision must match `pin_id` and `gateway_model` exactly, be of a served kind, and share `billing` and rates (option A of the design; mixed groups are refused).
    - Tables are `executor_group`, `executor_group_revision` and `executor_group_member`; the names do not collide with the run-group tables that existed when this ADR was written (removed 2026-11-10, `R-154c`).
11. **Rules.** One current rule per `work_kind`, append-only, targeting a group revision.
12. **Explicit binding state.** Every Run and comparison job has a `binding_state`:
    - `frozen_at_start` for every existing row, an explicit connection and a preset, with unchanged behaviour;
    - `pending` while admitted by rule or group;
    - `bound` after dispatch.

    The frozen-column triggers allow `connection_revision_id` NULL → value exactly once, on `pending` → `bound`; any later change is refused. The `environment` provider source refuses a group start, and its worker never claims a `pending` Run.
13. **Admission freezes intent, not executor.** Admission records:
    - the rule revision and the group revision;
    - the consent envelope: `work_kind`, group revision, `pin_id`, billing and rate basis, ceiling, estimate digest, actor and time.

    Because the group is homogeneous, the input budget and the estimate follow the group revision's `pin_id`. The canonical binding (`connection_revision_id`, `gateway_model`, cost basis) is written at dispatch.
14. **Dispatch inside the existing claim transaction.**
    - Lock order: worker intake → group → member connections in ascending `connection_id` → control → Run → Job.
    - Select among eligible members:
      - the member's current revision equals the snapshot;
      - the member is served;
      - the probe is `ok` on its current key;
      - a pull runner is online;
      - the member is not archived;
      - it has a free unit under decision 1.

      Pick the minimum `used / capacity`, breaking ties by a rotation persisted in the database.
    - Before commit:
      - re-check the consent envelope;
      - apply the `comparison_*` USD 10 per job and USD 50 per day ceilings against the selected member;
      - reserve the unit;
      - write the binding and a dispatch event.
    - Model I/O starts only after commit. A failed consent check sets `needs_reconsent` and calls nothing.
    - A comparison job binds at its first dispatched call, and its later calls stay on that member.
15. **Waiting is durable and visible.**
    - `wait_reason` (`waiting_for_capacity`, `waiting_for_executor`, `needs_reconsent`) and `waiting_since` are stored.
    - When every member is offline for longer than `AUDITMANAGER_GROUP_OFFLINE_WAIT_SECONDS`, default 1800 (`R-149c`), the work ends with `no_executor_online`.
    - Waiting for a busy member is unbounded.
16. **No re-routing after binding.** An Attempt retry stays on the bound member. `outcome_unknown` is never sent to another member.
17. **Cut-over.**
    - The routing mode is stored in the database (`legacy` by default, `rules`), and each change is journalled.
    - The preview proposes a one-member group per primary, never converts a standby, and flags incompatible routes.
    - The administrator's confirmation creates the groups, the rules and mode `rules` in one transaction.
    - Under `rules`, `setExecutorRoute` answers `conflict`, and a `work_kind` without a rule is a typed refusal.
    - Rollback is an explicit return to `legacy`. Work already admitted by rules finishes on its own group revisions and is never re-read through a legacy route.
18. **Refusals reuse the catalogue.** Only `validation_failed`, `conflict`, `dependency_unavailable` and `model_identity_mismatch` are used, with typed details. EXEC-2 adds no error code. *Addendum (`EXEC2-FOLLOWUP-01`, 2026-11-03):* a group whose rate snapshot no longer equals the provider lock is refused with the existing cost-preflight refusal `analysis_input_invalid` (`stage_id`, `reason: cost_estimate_binding_changed`), the word the Run side already uses for a consent whose rates no longer hold, and **only** on operations whose contract declares `422`; an estimate that declares none is computed at the snapshot and the start refuses. Still no new code.

### Deviations recorded by the owner

19. `allow_client_documents` is not enforced in EXEC-2 (`R-149a`, `D-291`). Capacity above one and group routing are for test data until it is, and the UI says so.
20. The acceptance tests of the three documents are written and not run in EXEC-2 (`R-149d`, `D-292`).

## Consequences

- Default behaviour is unchanged: capacity one, mode `legacy`, old agents and API callers unchanged.
- About 57 lines in 16 files outside `executors/` and `comparison/`, and 24 inside `comparison/`, read a Run's or job's frozen revision. Each must handle `pending`. That is the bulk of `EXEC2-GROUP-RUN-01` and `EXEC2-GROUP-CMP-01`.
- The stand serves one more unauthenticated route (the agent package) and one enrollment exchange. Both need throttling at the proxy.
- Without database runs (`R-149d`), races in capacity, binding and consent are first exercised on a stand.

## Alternatives considered

- **A reservation table for capacity.** Rejected for v1: the persisted states already identify every holder, and recovery semantics stay those of the queue.
- **Binding at admission with re-check at dispatch.** Rejected: the owner approved dispatch-time binding.
- **Re-probing the current revision of a member instead of a snapshot.** Rejected (the design's MVP choice): queued work must not adopt a new destination or credential silently.
- **Mixed-billing groups with a maximum-price quote (option B).** Not approved by the owner.
- **A per-call counter for `http_api`.** Unnecessary while a Run's calls are sequential (decision 2).

## Verification

Tests are written per `docs/program/dispatch/EXEC2-PLAN.md` section 9 and not run in EXEC-2 (decision 20). Each integration has a read-only review of the claim, binding, lock-order and consent diff.

## Revisit trigger

Any of these reopens this ADR:

- the first use with real client documents (decision 19);
- parallel model calls inside one Run (decision 2);
- a multi-instance pull protocol (decision 3);
- mixed-billing groups (decision 10);
- moving from subscriptions to direct APIs (decision 8, `R-149b`).
