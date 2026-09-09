# Task P0-PLN-01 — complete the post-foundation prototype roadmap

> **Status: executed, revision 3; candidate on `agent/p0-pln-01`, awaiting primary
> review.** `P0-FND-00` was accepted on 2026-09-09 and this task ran in parallel with P01
> **dispatch readiness**; no P01 lane had been dispatched at the time of writing, which is
> why calibration is pending rather than measured. Its deliverables are
> `docs/program/PROTOTYPE_EXECUTION_PLAN.md` and 30 agent-ready task files. No P02–P05 task
> is dispatchable until the owner accepts them.

## Outcome

Agent-ready P02–P05 tasks for the real audit slice, expert workflow, prototype
acceptance, field validation and evidence-driven architecture revision, without changing
the accepted Foundation Freeze.

## Depends on

- `P0-FND-00` — must be completed with `FF-01 ACCEPTED` before dispatch

## Frozen inputs

- `docs/program/PROTOTYPE_FOUNDATION_FREEZE.md` at accepted integration commit
  `0b01a3eefe0e6724f6570ccebb9154daf1fdbaec`
- `docs/program/PROTOTYPE_PROFILE.md` foundation invariants at the same commit
- the candidate PC-01 AR text-consistency target in `PROTOTYPE_PROFILE.md` section 7 and
  `ROADMAP.md` P02/P03; it is not dispatch authority, but changing it in the detailed
  plan requires an explicit owner decision rather than silent scope drift
- proposed ADR-0019/P-23 decision-to-code navigation; it does not block P01, but its
  implementation is a required predecessor of P02 fan-out
- CP-00 contracts, architecture and golden fixtures at the `P0-FND-00` base
- migration head: produced only by `P1-DB-01`; read-only to this planning task
- foundation base commit: `0b01a3eefe0e6724f6570ccebb9154daf1fdbaec`;
  the launch prompt must also provide the literal task-spec commit and may not contain
  an unsubstituted SHA placeholder

## Allowed paths

- `docs/program/tasks/P0-PLN-01.md`
- new `docs/program/tasks/P1-NAV-*.md` — navigation implementation before P02 only
- new `docs/program/tasks/P2-*.md`, `P3-*.md`, `P4-*.md`, `P5-*.md`
- `docs/program/PROTOTYPE_EXECUTION_PLAN.md`
- `docs/program/ROADMAP.md` — P02–P05 detail only
- `docs/program/PROTOTYPE_PROFILE.md` — non-foundation scope/evidence clarification only
- `docs/program/CURRENT_STATE.md`, `docs/INDEX.md` — planning-status entries only

## Forbidden hotspots

- `docs/program/PROTOTYPE_FOUNDATION_FREEZE.md`
- foundation invariants in `docs/program/PROTOTYPE_PROFILE.md`
- every P01 task file except links in this task's handoff
- `contracts/**`, `fixtures/**`, `scripts/**`, `tests/**`
- runtime, infra, root locks, migration head, composition root and global styles
- CP-00 evidence and Git tags

## Non-goals

- No P01 remediation or implementation.
- No production implementation.
- No expansion to comparison, distributed workers, multi-tenant production or full
  production hardening without a measured P04 finding and owner decision.
- No mass rewrite of existing S00–S10 stage files.

## Deliverables

- concise P02–P05 task files with completed dependencies only at dispatch time
- a P02/P03 graph that implements exactly the bounded AR text-consistency slice, including
  its synthetic PDF, evidence-publication gate, live/recorded provider modes, UI review
  and CSV acceptance path
- an agent-ready pre-P02 navigation gate of **two** tasks implementing ADR-0019 with
  disjoint entry ownership, deterministic generation/validation and accepted-foundation
  mappings: `P1-NAV-01` creates the schema, tooling, index and planned entries, and
  `P1-NAV-02` flips the named foundation entries to `implemented` after `PF-01` and
  regenerates the index. Both are complete before P02 fan-out; neither blocks P01
- exact provider/consumer seams and disjoint allowed-path blocks
- user-validation protocol and success/failure metrics
- bottom-up P50/P80 forecast from the agent-ready graph, with assumptions and arithmetic
- P01 calibration state: use measured P01 throughput if it exists; otherwise record it as
  pending and name the exact PF-01-to-P02 update trigger rather than inventing a value
- one explicit next-investment decision after P04 evidence

## Required tests

- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`
  Expected: exit `0`, standalone `PASS`.
- Command: `git diff --check`
  Expected: exit `0`.
- Manual graph check: P02–P05 tasks may depend on the accepted Foundation Freeze but
  do not modify it; no implementation task depends on an uncompleted planning task at
  dispatch; navigation does not block P01 and is completed before P02 fan-out.
  Expected: pass.
- Manual estimate check: the first forecast is bottom-up from task rows; any unavailable
  P01 measurement is visibly pending and becomes a required update after PF-01 and before
  P02 dispatch.
  Expected: no invented implementation velocity and no planning wait on unfinished P01.

## Estimate

P50 is 1–2 elapsed days and P80 is 3–4 days after `FF-01 ACCEPTED`. This work runs in
parallel with P01 and is not added to the foundation critical path. It issues the first
PC-01 forecast after an agent-ready P02/P03 graph exists. If P01 has not yet produced a
usable measurement, the plan is still completable and labels calibration pending; the
integrator must recalibrate after PF-01 and before P02 dispatch.

## Integration contract

P02 begins only after the accepted foundation providers and this plan are present, the
navigation gate is accepted, and the forecast is recalibrated with measured P01
throughput. P01 implementation continues independently if this planning task is rejected
or revised.

## Failure/idempotency/security cases

- A planning defect cannot invalidate already accepted PostgreSQL/S3 behavior silently.
- New scope remains disabled unless a task and acceptance criterion enable it.
- A later plan records unknowns rather than inventing production policies.

## Rollback / feature flag

Documentation only. Revert the planning integration commit; P01 remains valid under its
own accepted freeze.

## Handoff

- changed files and containment proof
- commands/results
- unresolved owner decisions
- measured P01 throughput and the revised estimate if a measurement exists at handoff
  time; otherwise the recorded calibration-pending state and its trigger

### Executed handoff, 2026-09-09

- **Base:** task-spec commit `1cb86cd2708f11712a0cd2f481862652fac2e377`; accepted
  foundation `0b01a3eefe0e6724f6570ccebb9154daf1fdbaec`, verified an ancestor of it.
- **Produced:** `PROTOTYPE_EXECUTION_PLAN.md`; `P1-NAV-01` and `P1-NAV-02`; thirteen P02,
  eight P03, four P04 and three P05 task files — 30 in all; the P02–P05 detail in
  `ROADMAP.md`; the run-state vocabulary correction and the corpus restatement in
  `PROTOTYPE_PROFILE.md` §§8–9; planning entries in `CURRENT_STATE.md` and `docs/INDEX.md`.
- **Contracts, runtime, migration head, fixtures, scripts and tests:** unchanged. The plan
  specifies who will own those paths later; it writes none of them.
- **Calibration:** pending. No measured P01 throughput exists, because no P01 task has been
  dispatched. The recalibration trigger is recorded in the execution plan and in
  `ROADMAP.md`: after `PF-01` acceptance and before P02 dispatch.
- **Unresolved owner decisions:** 24, listed as `OD-01` to `OD-24` in the execution plan.
  Ids are append-only and are never renumbered. `OD-24` records the PC-01 `AuditRun`
  conformance subset; `OD-14` is now an explicit dispatch prerequisite of `P2-INT-00`.
  `OD-14` is the one that can move the whole graph: whether accepting this plan lifts the
  production-code hold for the P02 paths, or whether CP-00 acceptance round eleven and
  `W0-INT-03` are additional P02 predecessors.
- **ADR-0019:** not accepted by this task. `P1-NAV-01` implements it and its dispatch is
  conditioned on the owner accepting the ADR together with this plan.

### Executed handoff, revision 3

- **Base:** `3d4653afa2726d58c6edae36c75ba759148b9c6a` on `agent/p0-pln-01`. Documentation
  only. The accepted PC-01 slice, the 30 task files, the task graph and every estimate are
  unchanged; no task ID was added and no estimate figure moved.
- **Nine corrections.** One export policy under `OD-11`, keyed on the contract's
  `terminal_semantics.publishes_result` and stated identically in the plan, `P2-EXP-01`,
  `P2-API-01`, `P3-API-01`, `P3-WEB-04` and the `P3-QA-01` verifier. Two frozen bases
  corrected to the commits their own dependency blocks name. `OD-24` made a dispatch
  prerequisite of `P2-DOM-01`. `P2-RUN-01` enumerating the whole unevaluated guard subset,
  with cancellation and Attempt authority named separately as absent capabilities. The
  `Import` contradiction removed without adding an aggregate or a table. The P04 lifecycle
  split so the pre-session preflight and the validation-period ledger are distinct
  artifacts with one writer each. Navigation aggregation made status-aware and scoped.
  `P5-INT-01` given exactly the ADR authority its deliverable needs. Stale counts and the
  two-task navigation gate corrected.
- **Contracts, runtime, migrations, providers, fixtures, scripts and tests:** unchanged.
  `partial_result_not_publishable` and the `import` machine remain in the frozen contracts,
  untouched and now explicitly unused by PC-01. `state_transition_not_allowed` was already
  in the frozen catalog and was not invented.
- **Unresolved owner decisions:** still 24, `OD-01` to `OD-24`, ids append-only. `OD-11`
  and `OD-24` were restated, not renumbered. `OD-14` remains the one that can move the
  whole graph.
- **Known limitation.** Two adversarial reviews drove this revision; the second found that
  my first pass had left `P4-INT-01` invoking tool modes `P4-OPS-01` never defined, and had
  claimed aggregator scopes were disjoint while the table showed P02 covered twice. Both
  are fixed here. The ASCII graph in plan section 2 still omits declared edges; rather than
  redraw it, section 2 now states that the per-task predecessor blocks are jointly
  authoritative and lists the undrawn edges.
