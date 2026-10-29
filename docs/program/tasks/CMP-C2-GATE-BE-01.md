# Task CMP-C2-GATE-BE-01 — reuse one static AST census in the composition port guard

## Outcome
The composition guard still checks every discovered `build_router` wiring and every declared port method, while parsing the immutable clean-tree Python sources once per test process. A focused run proves identical cases and a lower runtime before the C2 publication candidate's full gate.

## Depends on
- CMP-C2-GATE-FE-01
- CMP-C2-FIX-01

## Frozen inputs
- API contract: `1.11.0`, 176 paths / 198 operations / 517 schemas
- analysis/comparison/event contract: unchanged from `CMP-SEAL-C2`
- migration head: `0040_comparison_ai_reports`
- source guard: `tests/integration/composition/test_every_port_implementation_is_whole.py` at `06c312a3`
- base commit: `06c312a3f8d35b569019066fff9e47d38e69501c`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: the existing parametrized `PORT_FOR_ARGUMENT` guard and its source-derived wiring census

## Captured premise evidence
- premise: P-01 and P-02 establish the frozen candidate and repeated tree scan before any edit to the guard.

### P-01 — clean C2 base and frozen surface
- captured_at: 2026-10-29
- command: `git rev-parse HEAD; git status --short; python3 -c 'import json;x=json.load(open("contracts/api/v1/openapi.json"));print(x["info"]["version"],len(x["paths"]),sum(k in {"get","post","put","patch","delete","head","options","trace"} for p in x["paths"].values() for k in p),len(x["components"]["schemas"]))'; ls db/migrations/versions | tail -n 1`
- captured_output:
  ```text
  06c312a3f8d35b569019066fff9e47d38e69501c
  1.11.0 176 198 517
  20261029_0040_comparison_ai_reports.py
  ```
- interpretation: the tests-only repair starts on the unchanged clean C2 code candidate.

### P-02 — each port case repeats the full source scan
- captured_at: 2026-10-29
- command: `rg -n 'def _parsed|def _wirings|_class_definitions|for where, line, wired|parametrize' tests/integration/composition/test_every_port_implementation_is_whole.py`
- captured_output:
  ```text
  63:@pytest.mark.parametrize("severity", ["economic", None])
  190:def _parsed() -> dict[pathlib.Path, ast.Module]:
  200:def _class_definitions(
  277:def _wirings() -> list[tuple[str, int, str, str | None | Any]]:
  381:@pytest.mark.parametrize("argument", sorted(PORT_FOR_ARGUMENT))
  384:    classes = _class_definitions(_parsed())
  389:    for where, line, wired, resolved in _wirings():
  ```
- interpretation: the parametrized guard calls the all-file AST scan once for its class index and again through `_wirings()` on each port. The full C2 gate observed a long sequence of these cases at 61% while its process remained active.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `tests/integration/composition/test_every_port_implementation_is_whole.py`
- `docs/program/tasks/CMP-C2-GATE-BE-01.md`
- `docs/program/CMP-C2-GATE-BE-01.md`

## Forbidden hotspots
- every other test, application source, `contracts/**`, migrations, root dependencies and lockfiles, composition root, global styles, infrastructure, remote refs

## Non-goals
- no skipped port, changed protocol, relaxed assertion, test order change or altered product behavior
- no publication; `CMP-WAVE-C2-INT` alone owns `origin/dev`

## Deliverables
- cache the parsed source AST and derived class/wiring inventories within one test process, with the same live source scan at first use
- focused guard results before and after, including every parametrized port and source-derived wiring control
- report of the measured gate cost, commands, diff scope and risks

## Required tests
- focused guard before and after with the same environment, no parallel pytest competing with the running full gate
- governance, `git diff --check`, and final complete `make gate` on the integration publication commit

## Integration contract
Merge this tests-only repair into the C2 integration branch before its final documentation commit and complete gate. The guard reads a clean, immutable checkout; it must derive the same set of `build_router` calls and port classes, and must fail in a mutation copy that changes an implementation. No remote ref is touched by this task.

## Failure/idempotency/security cases
- a mutation to a wired implementation before the guard process starts remains visible to its first AST scan
- an unresolved wiring remains a failure; caching cannot turn it into a skip
- tests never rely on source changes during the same guard process

## Rollback / feature flag
Tests only; revert the scoped commit if the guard's mutation proof changes. No runtime flag or migration.

## Handoff
- changed files: pending
- commands/results: pending
- contracts: unchanged
- known limits: pending
- integration notes: pending
