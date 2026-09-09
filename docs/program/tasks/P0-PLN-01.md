# Task P0-PLN-01 — complete the post-foundation prototype roadmap

> **Status: dispatchable.** `P0-FND-00` was accepted on 2026-09-09. This task may run
> in parallel with the P01 PostgreSQL/S3 implementation lanes.

## Outcome

Agent-ready P02–P05 tasks for the real audit slice, expert workflow, prototype
acceptance, field validation and evidence-driven architecture revision, without changing
the accepted Foundation Freeze.

## Depends on

- `P0-FND-00` — must be completed with `FF-01 ACCEPTED` before dispatch

## Frozen inputs

- `docs/program/PROTOTYPE_FOUNDATION_FREEZE.md` at its accepted integration commit
- `docs/program/PROTOTYPE_PROFILE.md` foundation invariants at the same commit
- the candidate PC-01 AR text-consistency target in `PROTOTYPE_PROFILE.md` section 7 and
  `ROADMAP.md` P02/P03; it is not dispatch authority, but changing it in the detailed
  plan requires an explicit owner decision rather than silent scope drift
- proposed ADR-0019/P-23 decision-to-code navigation; it does not block P01, but its
  implementation is a required predecessor of P02 fan-out
- CP-00 contracts, architecture and golden fixtures at the `P0-FND-00` base
- migration head: produced only by `P1-DB-01`; read-only to this planning task
- base commit: the accepted `P0-FND-00` integration commit

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
- one agent-ready pre-P02 navigation task implementing ADR-0019 with disjoint entry
  ownership, deterministic generation/validation and accepted-foundation mappings
- exact provider/consumer seams and disjoint allowed-path blocks
- user-validation protocol and success/failure metrics
- P50/P80 estimate recalibrated against actual P01 throughput
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

## Estimate

P50 is 1–2 elapsed days and P80 is 3–4 days after `FF-01 ACCEPTED`. This work runs in
parallel with P01 and is not added to the foundation critical path. Its PC-01 estimate is
issued only after an agent-ready P02/P03 graph exists and the first P01 throughput is
measured.

## Integration contract

P02 begins only after both the accepted foundation providers and this plan are present.
P01 implementation continues independently if this planning task is rejected or revised.

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
- measured P01 throughput and revised estimate
