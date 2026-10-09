# Task W53-GATE-SURFACE-REPAIR-01 — restore total API surface guards

task_id: W53-GATE-SURFACE-REPAIR-01

## Outcome

The existing API authorization, served-document, composition and PC-01 immutability guards cover all six sealed W53 operations and the new execution port without weakening the older assertions. These tests pass against the frozen 43-operation surface.

## Depends on

- `W53-FREEZE-01` and `W53-SEAL-01` (completed). The integrated EXEC and WEB candidate is a frozen input below, with its owner stops still open.

## Frozen inputs

- Diagnostic product base: `9a121cf28de619d6ff8f5fcb765aa1c62d522307`; dispatch worktree base is the exact grant commit supplied by the integrator.
- OpenAPI SHA-256 `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`, version `1.0.0-draft.1`; domain state-machine SHA-256 `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`; migration head `0017_execution_queue`.
- First full gate log `/tmp/w53-int-gate/gate.log`, SHA-256 `0178e881a6f7571abd8909ceb95d67a9b24da386f9fee3733c119fc791c6434e`.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `tests/integration/api/test_authorization.py`
- enumerator_owner: `W53-GATE-SURFACE-REPAIR-01`
- totality_query: `git grep -n -E 'GUARDED|OPEN|subject_readers' -- tests/integration/api/test_authorization.py`

## Captured premise evidence
- premise: full gate identified stale surface guards for six sealed W53 operations

### P-01 — full gate's surface-guard failure set
- captured_at: 2026-10-09
- command: `grep -n -E '^FAILED (tests/e2e/pc01/test_acceptance.py|tests/integration/api/test_authorization.py|tests/integration/api/test_served_document_and_health_plane.py|tests/integration/composition/)' /tmp/w53-int-gate/gate.log`
- captured_output:
  ```text
  729:FAILED tests/e2e/pc01/test_acceptance.py::test_c3_the_surface_declares_no_operation_that_can_mutate_a_version
  730:FAILED tests/integration/api/test_authorization.py::test_every_operation_but_the_register_is_behind_the_seam
  731:FAILED tests/integration/api/test_authorization.py::test_the_open_surface_is_exactly_the_register
  732:FAILED tests/integration/api/test_authorization.py::test_a_subject_is_published_and_only_one_operation_reads_who_it_is
  733:FAILED tests/integration/api/test_authorization.py::test_a_default_credential_reaches_exactly_the_register
  735:FAILED tests/integration/api/test_served_document_and_health_plane.py::TestTheDocumentedAndTheWiredApplicationAgree::test_the_two_schemas_fastapi_would_have_added_are_not_in_it
  736:FAILED tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py::test_the_surface_partitions_into_the_two_halves_of_the_rule
  737:FAILED tests/integration/composition/test_every_port_implementation_is_whole.py::test_build_router_still_takes_the_ports_this_module_names
  ```
- interpretation: exact owned subset of the 13 full-gate failures; the log contains full traceback. Other failures are owned separately by the integrator and peers.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `tests/e2e/pc01/test_acceptance.py`
- `tests/integration/api/test_authorization.py`
- `tests/integration/api/test_served_document_and_health_plane.py`
- `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`
- `tests/integration/composition/test_every_port_implementation_is_whole.py`
- `docs/program/W53-GATE-SURFACE-REPAIR-01.md` (handback only)

## Forbidden hotspots

All other paths, especially `contracts/**`, production code, migration head, root locks, composition roots, global styles, working stand, refs and tags. Do not alter the gate or hide new operations from the assertions.

## Non-goals

No contract reseal, behavior change, W53 owner-stop decision, deployment or release. `test_query_surface.py` belongs to a separate repair grant.

## Deliverables

Exact strengthened test changes and six-item `AGENTS.md` §5 handback with branch/SHA, complete changed-path audit and targeted results.

## Required tests

- Run the five owned test modules with the private `gate-w53surface` DB/S3 lane (ports 56920, 60520/60521) if they need services. Verify those ports are free and preflight disk before a substantial test.
- Include adjacent anti-vacuity cases and `git diff --check`. The integrator owns the later complete gate.

## Integration contract

Work in a separate worktree from the exact dispatch SHA. Update enumerations to the actual sealed six W53 operations, including authorization and `CurrentSubject` semantics; preserve all existing refusals and C3's document/version immutability check. The execution port must be checked by the composition guard. Report branch, exact SHA and all six §5 items; no publication, tags or stand access.

## Failure/idempotency/security cases

Every guarded operation must still be swept for anonymous and default credentials; a new unregistered operation must red the guards. No W53 mutation route may address a DocumentVersion.

## Rollback / feature flag

Test-only repair; revert the commit if a guard is weakened. No feature flag applies.
