# Task GATE-SUITE-AUDIT-01 — evidence-based review of the test corpus

task_id: GATE-SUITE-AUDIT-01

## Outcome

A reviewer can see the current test inventory, the heaviest measured suites and setup
costs, which checks exercise distinct product or release claims, and a ranked list of
safe optimisation candidates with the evidence still required before changing tests.

## Depends on

- `GATE-OPT-01` — completed locally at `5842d01ce9a1a38fe2097dae080f9792c213ff37`;
  its duration instrumentation makes the next complete-gate baseline comparable.

## Frozen inputs

- code base: `5842d01ce9a1a38fe2097dae080f9792c213ff37` from verified
  `origin/dev=8069220909e40c39e2329d5f5cb9585a5a5714ec`
- domain candidate revision 13, 32 opaque identities
- API 47 paths / 54 operations / 124 schemas; error catalog 25
- analysis/comparison/event contracts unchanged; migration head `0022_findings_v2`
- product version `0.6.0`; complete development gate deferred by `R-135`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the audit follows the completed local gate optimization commit

### P-01 — source commit

- captured_at: 2026-10-15
- command: `git rev-parse 5842d01ce9a1a38fe2097dae080f9792c213ff37`
- captured_output:
  ```text
  5842d01ce9a1a38fe2097dae080f9792c213ff37
  ```
- interpretation: this identifies the implementation tree audited, without claiming a full gate.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/GATE-SUITE-AUDIT-01.md`
- `docs/program/GATE-SUITE-AUDIT-01.md`
- `.local/tasks.md`
- `.local/handoff/gate-optimization-2026-10-15.md`

The last two paths are ignored local coordination files in the shared root checkout.

## Forbidden hotspots

- `Makefile`, test source and fixtures, `contracts/**`, migrations and root dependencies
- composition roots, global styles, runtime code, deploy scripts and refs

## Non-goals

- Deleting tests from raw counts alone or weakening real DB, image and deployment checks.
- Running a complete gate or full frontend suite in the `R-135` code-first period.
- Claiming current performance from a historical gate log without naming its SHA.

## Deliverables

- A report of counts by layer and test family, measured heavy tests and setup patterns,
  duplication candidates and an order for later optimisation tasks.

## Required tests and checks

- Inventory tracked Python/Vitest files and collection where the available toolchain allows.
- Read existing complete-gate logs/reports with their exact SHA and environmental caveats.
- Use bounded, container-free `--durations` probes for plausible heavy guards.
- `git diff --check` and a diff limited to Allowed paths.

## Integration contract

This is evidence and recommendations only. A later task owns each test or fixture it
changes, proves anti-vacuity and isolation, and compares a complete gate on an exact SHA
under the project's beta-gate schedule. Neither this report nor `gate-fast` is `GATE OK`.

## Failure / idempotency / security

Missing or voided timing evidence is called out, never filled with an estimate. Read-only
inventory has no data or external side effect.

## Rollback / feature flag

Revert the task/report documents; no behavior or data changes.

## Handoff

- changed files: Allowed paths
- commands/results, known limits and integration notes: `docs/program/GATE-SUITE-AUDIT-01.md`
