# CMP-C2-GATE-SPEND-01 — spend guard repair

The exact C2 candidate `a72d0d0` failed two static spend-call tests in `/tmp/cmp-c2-gate-publication-4.log`: both counted `PublishedPullAdapter.complete` delegating to its underlying adapter as an unjournalled second call. The caller still records the comparison call before invoking that route. The guard now permits exactly the `self._adapter.complete` call inside that named method, and still reports any other `.complete` call in the comparison tree.

Focused checks: `tests/unit/comparison/spend/test_wiring_and_pins.py`, `test_pull_images.py` and `tests/unit/comparison/work/test_model_route_binding.py`: **23 passed in 2.48 s**. `git diff --check` passed. No production source, contract, migration, dependency or composition file changed.

This test-only commit changes the C2 candidate SHA. The integrator must run a new complete `make gate` and see literal `GATE OK` on a clean exact SHA before updating `origin/dev`. The earlier red gate authorizes no publication. `origin/main` remains outside this task.
