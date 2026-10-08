# W52-INT-GATE-PC01-ENV-01 — PC-01 provider mode isolation

Code commit `4acf5b1aa7c42b90ade1fd31987eb9da9391f403` builds on exact
`origin/dev` base `ba6b2066398978d66e388640950a90f98d590ac8`.
The PC-01 conftest now loads local service addresses once, separately from
provider selection. Its autouse provider fixture is function-scoped and removes
`AUDITMANAGER_PROVIDER_MODE` in `finally`; the session client still passes
`AUDITMANAGER_PROVIDER_MODE="recorded"` directly to composition. Each test
asserts that the root fixture removed ambient provider credentials and that a
prior test did not leave a provider mode behind.

## Checks

- Two selected PC-01 composition-refusal tests: **2 passed** without a service
  stand. An in-process pytest plugin asserted `recorded` during each test and
  absence of the mode after each teardown; both assertions held.
- Programme governance and live-prose contract tests: **60 passed**.
- Frontend lint and `git diff --check`: passed.
- No live model call, temporary stand, full `make gate`, JUnit outcome parity,
  QA or manual acceptance was run. No `GATE OK` is claimed; D-139/D-140 remain
  open. The service-backed PC-01 journey remains for deferred validation.

## Handoff

Changed tracked files: `tests/e2e/pc01/conftest.py`,
`docs/program/tasks/W52-INT-GATE-PC01-ENV-01.md`, this report,
`docs/program/CURRENT_STATE.md` and `docs/program/DEBT_REGISTER.md`.
No contract, migration, root dependency/lock, composition root, global style,
runtime application or deployment file changed. This is one part of planned
`W52-GATE-01` item 3; the remaining bucket and throttle isolation, template
database, full gate and JUnit comparison remain open. The integrator may
publish this code and documentation together as a fast-forward of `origin/dev`
after exact remote-ref review. `origin/main` has no authority in this task.
Revert the integration commits to restore the prior fixture lifetime.
