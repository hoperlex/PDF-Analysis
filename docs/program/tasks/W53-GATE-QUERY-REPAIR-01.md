# Task W53-GATE-QUERY-REPAIR-01 — drive W53 query parameters in the totality guard

task_id: W53-GATE-QUERY-REPAIR-01

## Outcome

The exhaustive query-surface guard drives every declared `listExecutionQueue` and `listExecutionJournal` parameter through a behavior-changing request and passes on the frozen W53 API.

## Depends on

- `W53-FREEZE-01` and `W53-SEAL-01` (completed). The integrated EXEC candidate is a frozen input below, with its owner stops still open.

## Frozen inputs

- Diagnostic product base: `9a121cf28de619d6ff8f5fcb765aa1c62d522307`; dispatch worktree base is the exact grant commit supplied by the integrator.
- OpenAPI SHA-256 `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`, `1.0.0-draft.1`; domain state-machine SHA-256 `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`; migration head `0017_execution_queue`.
- Full gate log `/tmp/w53-int-gate/gate.log`, SHA-256 `0178e881a6f7571abd8909ceb95d67a9b24da386f9fee3733c119fc791c6434e`.

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `tests/integration/api/test_query_surface.py`
- enumerator_owner: `W53-GATE-QUERY-REPAIR-01`
- totality_query: `git grep -n -E 'targets =|listExecution|_declared_query_parameters' -- tests/integration/api/test_query_surface.py`

## Captured premise evidence
- premise: the W53 query operations are absent from the exhaustive query guard

### P-01 — missing parameter owners
- captured_at: 2026-10-09
- command: `grep -n -A3 '^FAILED tests/integration/api/test_query_surface.py' /tmp/w53-int-gate/gate.log`
- captured_output:
  ```text
  734:FAILED tests/integration/api/test_query_surface.py::test_every_declared_query_parameter_is_read_by_the_router_that_declares_it
  735-FAILED tests/integration/api/test_served_document_and_health_plane.py::TestTheDocumentedAndTheWiredApplicationAgree::test_the_two_schemas_fastapi_would_have_added_are_not_in_it
  736-FAILED tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py::test_the_surface_partitions_into_the_two_halves_of_the_rule
  737-FAILED tests/integration/composition/test_every_port_implementation_is_whole.py::test_build_router_still_takes_the_ports_this_module_names
  ```
- interpretation: traceback at gate log line 501 reports the exact symmetric difference `listExecutionJournal`, `listExecutionQueue`; adjacent failures are assigned elsewhere.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `tests/integration/api/test_query_surface.py`
- `docs/program/W53-GATE-QUERY-REPAIR-01.md` (handback only)

## Forbidden hotspots

All other paths, particularly `contracts/**`, production code, migration head, root locks, composition roots, global styles, working stand, refs and tags.

## Non-goals

No API reseal or implementation change. Other surface guards belong to `W53-GATE-SURFACE-REPAIR-01`.

## Deliverables

Totality guard amended for W53 parameters, behavioral assertions, and six-item §5 handback with branch/SHA and exact changed-path audit.

## Required tests

- Run the full owned module with private `gate-w53query` DB/S3 lane (ports 56921, 60522/60523); verify ports and disk before substantive tests.
- Prove the guard reds if a W53 parameter is accepted but ignored. Run `git diff --check`.

## Integration contract

Work in separate worktree at exact dispatch SHA. Preserve the set equality against frozen OpenAPI and existing query behavior tests; create distinct fixture rows as needed so each W53 query value demonstrably changes the response. Do not merely add operation IDs to `targets` and skip them. Return branch, exact SHA and all six §5 items. No publication, tags or working stand.

## Failure/idempotency/security cases

Pagination cursor/limit and journal filters must be exercised through the public router without leaking unfiltered events or weakening the exhaustive declaration guard.

## Rollback / feature flag

Test-only repair; revert if coverage weakens. No feature flag applies.
