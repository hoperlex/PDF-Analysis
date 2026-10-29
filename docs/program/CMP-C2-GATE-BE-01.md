# CMP-C2-GATE-BE-01 — composition guard census reuse

Task: [`CMP-C2-GATE-BE-01`](tasks/CMP-C2-GATE-BE-01.md). Base: clean C2 code commit `06c312a3f8d35b569019066fff9e47d38e69501c`, API `1.11.0` (176/198/517), migration head `0040_comparison_ai_reports`.

## Cause and change

The source-derived `D-74` guard parametrizes every `build_router` port. Before this repair, each port case called `_parsed()` for `_class_definitions` and again through `_wirings()`. `_parsed()` reread and parsed every Python file under `src/` and `tests/` each time. During the full C2 code-candidate gate, this guard kept the first integration battery near 61% from roughly 09:03 to 09:46 UTC while completing its port cases one by one. That unchanged first battery finished **6,592 passed / 13 skipped** in 1:48:38; its canonical remainder later exposed the separate W13 baseline failure, so the overall gate was red.

`functools.cache` now holds the parsed tree, the derived wiring rows and the class index for the lifetime of that guard process. The first call still scans the complete checkout; no port, source file, protocol method, unresolved-wiring refusal or assertion is removed. The guard runs against a clean immutable commit, so all its parametrized cases should see the same tree. A separate process or mutation copy starts with an empty cache and reads its own source.

## Verification

- Focused `tests/integration/composition/test_every_port_implementation_is_whole.py` on the repaired branch: **44 passed in 17.16 s** (`/tmp/cmp-c2-gate-be-focused.log`). All 39 parametrized ports and five controls ran.
- A disposable copy of this repaired tree renamed `DecisionAdapter.append_decision` to `append_decision_missing` before pytest started. The `decisions` port case failed in 17.38 s with five concrete `DecisionAdapter lacks ['append_decision']` wiring sites (`/tmp/cmp-c2-gate-be-mutation.log`). No mutation was committed to the branch.
- `py_compile` and `git diff --check` passed. Governance and final integration-gate evidence are recorded in the task Handoff after completion.

## Scope and limits

Only `tests/integration/composition/test_every_port_implementation_is_whole.py`, this report and the task record are owned by this repair. There is no product, contract, migration, dependency, composition-root, global-style or infrastructure change. The cache assumes no test rewrites repository source inside the same guard process; that is consistent with the clean-commit gate and the guard's own source-only assertions. `CMP-WAVE-C2-INT` retains the only `origin/dev` publication right.
