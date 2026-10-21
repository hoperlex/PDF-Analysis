# Task EXEC-RULE-01 — record R-143 and the executor-connections plan

task_id: EXEC-RULE-01

## Outcome

The owner's poll answers of 2026-10-22 are recorded as `R-143a`–`R-143e`
(`OWNER_RULINGS_2026-09-17.md` §3.43). The design, the threat model and the ordered slices
are in `docs/program/dispatch/EXECUTOR-CONNECTIONS-PLAN.md`. One task file exists per slice.
The integrator can freeze and dispatch each slice from these files alone.

## Depends on

- none (planning).

## Frozen inputs

- base commit: `7cb317b0a6fa9ae74c8a5e152419027ec37aca2d` (`origin/dev`), branch
  `plan/executor-connections`;
- API 73 paths / 83 operations / 242 schemas, 27 error codes, migration head
  `0029_routing_refusal_codes`, contract `1.0.0`;
- rulings `R-29`, `R-105`, `R-133`, `R-135`, `R-136`, `R-141c`; `ADR-0002` W54 addendum;
  `EXPOSURE-REVIEW-01.md`; `CODE-FIRST-TO-BETA.md` §2.1–§2.2.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/OWNER_RULINGS_2026-09-17.md`
- `docs/program/dispatch/EXECUTOR-CONNECTIONS-PLAN.md`
- `docs/program/tasks/EXEC-RULE-01.md`
- `docs/program/tasks/EXEC-ADR-01.md`
- `docs/program/tasks/EXEC-SEAL-01.md`
- `docs/program/tasks/EXEC-HTTP-01.md`
- `docs/program/tasks/EXEC-PULL-01.md`
- `docs/program/tasks/EXEC-AGENT-01.md`
- `docs/program/tasks/EXEC-SSH-01.md`
- `docs/program/tasks/EXEC-VPN-01.md`

## Forbidden hotspots

Everything else: `src/**`, `web/**`, `contracts/**`, `db/migrations/**`, `infra/**`,
dependency and lock files, `docs/architecture/**` (that is `EXEC-ADR-01`),
`CURRENT_STATE.md`, `DEBT_REGISTER.md`, refs, tags and the stand.

## Non-goals

No code, no contract, no ADR text, no debt rows. The integrator opens the debt rows named
in plan §3 (`R-133` not enforced on the run path; recorded identity ≠ requested model)
when it merges this branch.

## Deliverables

The ruling section, the plan, and eight task files.

## Required tests

- command: `git diff --check origin/dev...HEAD`
- expected: no output.
- command: `python3 -m pytest -q tests/contract/program/test_wave_governance.py tests/contract/api_v1/test_doc_prose_facts.py`
- expected: all passed.

## Integration contract

A documentation-only merge into `origin/dev` by the integrator (`pdf-analysis-87 [98580e]`).
Slices are dispatched in plan §7 order, each from its own task file after the integrator
freezes the base and assigns the slots.

## Failure/idempotency/security cases

The ruling quotes the owner verbatim and states the option texts the owner chose. Nothing in
this branch contains a credential.

## Rollback / feature flag

Revert the merge; no behaviour changes.

## Handoff

- changed files: the ten allowed paths;
- commands/results: in the hand-back message;
- known limits: line references in the plan are from `7cb317b0` and are re-measured at
  each slice freeze;
- integration notes: plan §8 lists the owner notes that do not block code.
