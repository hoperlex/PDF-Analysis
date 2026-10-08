# Task W52-INT-GATE-PC01-ENV-01 — confine PC-01 provider mode to each test

task_id: W52-INT-GATE-PC01-ENV-01

## Outcome

The PC-01 suite still composes its recorded application from the configured
local services, but `AUDITMANAGER_PROVIDER_MODE=recorded` is present only while
one PC-01 test runs. It cannot leak into another suite in the same pytest worker.

## Depends on

- `W52-INT-GATE-PARTITION-01` — completed on `origin/dev` at
  `ba6b2066398978d66e388640950a90f98d590ac8`.

## Frozen inputs

- Exact development base `ba6b2066398978d66e388640950a90f98d590ac8`.
- Domain candidate revision 9 / 29 opaque identities; API 27 paths / 34 operations /
  77 schemas; error catalog 23; migration head `0015_accounts_roles_registration`.
- `docs/program/dispatch/W52-PLAN.md` §3.7 item 3, read from the
  planning-owned `plan/roadmap-to-beta` worktree. This is one code preparation,
  not `W52-GATE-01` or W52 freeze/close.
- Owner's code-first direction: basic tests and lint; QA and full gate remain
  D-139/D-140. No temporary stand.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: a session-scoped autouse fixture sets the process provider mode and
  yields without removing it; the session-scoped client depends on that fixture.

### P-01 — current fixture lifetime

- captured_at: 2026-10-08
- command: `rg -n 'fixture\\(scope="session", autouse=True\\)|def recorded_provider_mode|os\\.environ\\["AUDITMANAGER_PROVIDER_MODE"\\]|^    yield$|def client\\(recorded_provider_mode' tests/e2e/pc01/conftest.py && git rev-parse HEAD && git status --short`
- captured_output:
  ```text
  45:@pytest.fixture(scope="session", autouse=True)
  46:def recorded_provider_mode() -> Iterator[None]:
  55:    os.environ["AUDITMANAGER_PROVIDER_MODE"] = "recorded"
  60:    yield
  92:def client(recorded_provider_mode: None) -> Any:
  ba6b2066398978d66e388640950a90f98d590ac8
  ```
- interpretation: mode remains set after each test until session shutdown;
  the empty status confirms the exact clean base. The client itself already
  passes `AUDITMANAGER_PROVIDER_MODE="recorded"` explicitly.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `tests/e2e/pc01/conftest.py` — provider and service-env fixtures, client
  dependency only
- `docs/program/tasks/W52-INT-GATE-PC01-ENV-01.md`
- `docs/program/W52-INT-GATE-PC01-ENV-01.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/DEBT_REGISTER.md`

## Forbidden hotspots

Everything else, especially tests outside PC-01, contracts, migration head,
root dependency/lock files, composition root, global styles, deployment files
and `origin/main`.

## Non-goals

No xdist, database-template change, bucket/throttle isolation, provider
contract change, live model call, temporary stand, full gate, QA or release.

## Deliverables

- A session-scoped service-env loader separate from a function-scoped provider
  fixture, and an explicit recorded override on the session client.
- Evidence of teardown after a selected local PC-01 test and a report with
  deferred validation status.

## Required tests

- Run selected no-service PC-01 tests with a teardown probe that checks the
  provider mode after each test.
- Run focused governance/prose tests, frontend lint and `git diff --check`.
- Leave full JUnit parity and `make gate` with D-140.

## Integration contract

The root pytest fixture still strips ambient provider configuration. PC-01
loads its local service connection environment once, supplies recorded mode
explicitly to its session client, and sets process mode for only one test at a
time. The integrator publishes a fast-forward to `origin/dev` after focused
checks and exact remote-ref review.

## Failure/idempotency/security cases

- A leaked provider mode before a PC-01 test is an assertion failure.
- Provider credentials remain absent; a recorded test cannot spend money by
  inheriting a shell credential.
- Teardown removes the mode even if a test fails.

## Rollback / feature flag

Revert this integration commit to restore the earlier fixture lifetime. No
runtime feature flag applies to test isolation.

## Handoff

- Changed files, checks/results, contracts, risks, integration instruction
  and forbidden-hotspot proof are in `docs/program/W52-INT-GATE-PC01-ENV-01.md`.
