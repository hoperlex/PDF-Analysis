# Task CMP-C2-GATE-SPEND-01 — restore the spend-call architecture guard

## Outcome
The static guard accepts exactly the known crop-publication adapter delegation while still rejecting every other direct model completion in the comparison context.

## Depends on
- CMP-SEAL-C2

## Frozen inputs
- domain contract: ADR-0025, one journalled model-call entrypoint
- API contract: `1.11.0`, 176 paths / 198 operations / 517 schemas
- migration head: `0040_comparison_ai_reports`
- base commit: `a72d0d0507a8917674438435ba10bdfa67c4c7e7`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/comparison/spend/test_wiring_and_pins.py`

## Captured premise evidence
- premise: P-01

### P-01 — exact C2 gate found a stale AST guard
- captured_at: 2026-10-29
- command: `rg -n 'test_only_the_spend_wrapper|test_the_wrapper_is_the_only|pull_images.py:76' /tmp/cmp-c2-gate-publication-4.log`
- captured_output:
  ```text
  668:____ test_only_the_spend_wrapper_calls_an_adapter_in_the_comparison_context ____
  684:E         Left contains one more item: 'src/auditmanager/comparison/spend/pull_images.py:76'
  688:__ test_the_wrapper_is_the_only_caller_of_an_adapter_inside_the_spend_package __
  702:E         Left contains one more item: ('pull_images.py', 76)
  717:FAILED tests/unit/comparison/spend/test_wiring_and_pins.py::test_only_the_spend_wrapper_calls_an_adapter_in_the_comparison_context
  718:FAILED tests/unit/comparison/spend/test_wiring_and_pins.py::test_the_wrapper_is_the_only_caller_of_an_adapter_inside_the_spend_package
  ```
- interpretation: `PublishedPullAdapter.complete` checks and publishes crop blobs before delegating to the underlying adapter. The C2 caller journals the route before invoking this wrapper. The guard counts the known delegation as a second unjournalled entrypoint.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `docs/program/tasks/CMP-C2-GATE-SPEND-01.md`
- `docs/program/CMP-C2-GATE-SPEND-01.md`
- `tests/unit/comparison/spend/test_wiring_and_pins.py`

## Forbidden hotspots
- `src/**`, `contracts/**`, `db/migrations/**`, root dependency/lock files, composition root, global styles, `infra/**`, `origin/main`

## Non-goals
- no change to model dispatch, spend accounting, image publication or client behavior
- no remote publication and no claim of a green full gate from targeted tests

## Deliverables
- scope the AST exception to the single `PublishedPullAdapter.complete -> self._adapter.complete` delegation, and keep the guard failing for any other `.complete` call
- focused guard and route-binding tests, `git diff --check`, a scope report

## Required tests
- `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/comparison/spend/test_wiring_and_pins.py tests/unit/comparison/spend/test_pull_images.py tests/unit/comparison/work/test_model_route_binding.py`
- `git diff --check`

## Integration contract
Merge the committed test repair into the C2 integration candidate. That changes its SHA; the integration owner must run a new complete `make gate` with literal `GATE OK` before any `origin/dev` publication. This task grants no publication authority.

## Rollback / feature flag
Revert this test-only repair if the architecture is changed to remove the wrapper. The comparison module flag still defaults to `none`.

## Handoff
- changed files: this task, `docs/program/CMP-C2-GATE-SPEND-01.md`, `tests/unit/comparison/spend/test_wiring_and_pins.py`
- tests/results: 23 passed in 2.48 s; `git diff --check` clean
- contracts: none
- known limits: the repair tests architecture, not a live model call
- integrator: include this exact commit and run a fresh full gate
