# BETA-REAUDIT-COST-JOURNEY-1030 — queue step compatibility

Date2026-10-30. Completed narrowly after UI639f9d09. **Browser/API/model/worker execution UNVERIFIED**; no build, heavy gate or publication.

The existing `queue-reaudit-the-cancelled-run` now observes its selected source Run read and automatically loaded cost estimate, verifies the captured version/source relationship and finite recommended cap, presses the initially unchecked cost agreement, then presses «Подтвердить» by its exact text. It no longer relies on the first button's position, which now belongs to estimate refresh.

The existing `approve_run_cost` action keeps the same `run`/`ar_v3_group` scope set. Its optional captured `source_run_id` selects the current re-audit confirmation and observes auto-estimation. Re-audit preflight allows only version/source fields; routing/profile choices stay server-owned. The later repeat must address that same source Run and carry consent only, with the exact newly observed digest/cap and a real key. Source/version mismatch, routing override, forged agreement or wrong repeat endpoint fails. The six other starts and historical pending AR steps remain unchanged.

Changed files: exact existing-step edits in `tests/e2e/pc01/journey/manifest.json`; cost action/source receipt handling in `write.mjs`; instructions in `README.md`; narrow closed-source-field/identity-flow/negative tests in `tests/e2e/test_pc01_journey_conformance.py`; task and this report. Product source, API/contracts/generated, migrations, locks, composition/styles and unrelated journey modules are untouched by this commit.

Checks: **140 Python journey conformance tests passed in4.45s**; Node syntax and `write.test.mjs` passed; comparison static check retained14 steps/exact corpus bytes/56 operations; whitespace passed. No actual browser or charge is claimed. Root integrates after the UI/backend providers and runs the deferred exact-candidate browser window tomorrow, retaining the real source/estimate/start exchanges. Rollback must be coordinated with the mandatory repeat-consent policy.
