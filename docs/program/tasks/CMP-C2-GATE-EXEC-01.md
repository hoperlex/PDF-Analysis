# Task CMP-C2-GATE-EXEC-01 — repair executor assertions at the 500-row list boundary

## Outcome
Two executor integration tests continue to prove routing and idempotent import when the shared test database contains at least 500 connections. The C2 candidate can be checked by a new complete gate without changing executor runtime or the list limit.

## Depends on
- CMP-C2-GATE-REM-01

## Frozen inputs
- domain contract: ADR-0025 and `CMP-SEAL-C2`
- API contract: `1.11.0`, 176 paths / 198 operations / 517 schemas
- migration head: `0040_comparison_ai_reports`
- failing clean candidate: `9d868e624cac01cd190be030db8c013ce52f560e`
- full-gate log: `/tmp/cmp-c2-gate-publication-2.log` (red; no `GATE OK`)

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: focused executor tests and the next complete `make gate`

## Captured premise evidence
- premise: P-01 and P-02 capture the independent test assertions before an edit.

### P-01 — archived connection omitted by the bounded list
- captured_at: 2026-10-29
- command: `rg -n 'KeyError:|list_connection_summaries|def list_connections' /tmp/cmp-c2-gate-publication-2.log tests/integration/executors/test_executor_commands.py src/auditmanager/executors/repository.py`
- captured_output:
  ```text
  /tmp/cmp-c2-gate-publication-2.log:545:E       KeyError: 'exc_01M63X7EN96DGB6JQRRT34DDTM'
  tests/integration/executors/test_executor_commands.py:503:    listed = {item.connection.connection_id: item for item in list_connection_summaries(session)}
  src/auditmanager/executors/repository.py:146:    def list_connections(self, session: Session, *, limit: int = 500) -> list[ConnectionRecord]:
  ```
- interpretation: the newly archived connection is ordered after active rows and can fall outside the first 500; a detail read by its identity still proves its route was removed.

### P-02 — idempotency compared the lengths of two full pages
- captured_at: 2026-10-29
- command: `rg -n 'assert 500 ==|before = len\(store.list_connections|assert len\(store.list_connections' /tmp/cmp-c2-gate-publication-2.log tests/integration/executors/test_http_operations.py`
- captured_output:
  ```text
  /tmp/cmp-c2-gate-publication-2.log:584:E       AssertionError: assert 500 == (500 + 2)
  tests/integration/executors/test_http_operations.py:242:    before = len(store.list_connections(session))
  tests/integration/executors/test_http_operations.py:265:    assert len(store.list_connections(session)) == before + 2
  ```
- interpretation: a bounded list cannot count new rows after saturation; the test must count all rows while retaining the assertions for the two created identities and replay.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

`CMP-WAVE-C2-INT` retains the sole `origin/dev` publication slot.

## Allowed paths
- `tests/integration/executors/test_executor_commands.py`
- `tests/integration/executors/test_http_operations.py`
- `docs/program/tasks/CMP-C2-GATE-EXEC-01.md`
- `docs/program/CMP-C2-GATE-EXEC-01.md`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, root dependencies/lockfiles, composition root, global styles, infrastructure
- all application source and other tests; all remote refs

## Non-goals
- no change to executor listing, archive, routing or import behavior
- no database cleanup or shared-fixture reset
- no C3 code, contract or migration

## Deliverables
- address-specific routing assertions for the archived and still-routed connections
- unbounded row-count assertion that import creates exactly two connections even after list saturation
- focused red/green evidence and repair report

## Required tests
- reproduce both failed test cases before edit on the shared C2 PostgreSQL stack
- rerun those cases and both edited modules after edit
- task-governance check and `git diff --check`
- new exact clean C2 publication commit receives a complete `make gate` with literal `GATE OK`

## Integration contract
This task owns only the two named tests. The integrator includes the repair and its report in a new C2 candidate, updates the wave report and INT task, commits cleanly, and reruns the entire gate on that SHA before any `origin/dev` fast-forward. The API, migration and runtime remain frozen.

## Failure/idempotency/security cases
- an archived connection remains addressable by ID and has no routed work kinds even when the list page omits it
- the surviving connection remains routed to `text_analysis`
- import replay returns the created ID and does not create a third row

## Rollback / feature flag
Revert these test-only corrections if they hide a real failure; no runtime behavior or feature flag changes. C2 remains off by default with `AUDITMANAGER_COMPARISON_MODULES=none`.

## Handoff
- changed files: `tests/integration/executors/test_executor_commands.py`, `tests/integration/executors/test_http_operations.py`, this task and `docs/program/CMP-C2-GATE-EXEC-01.md` only.
- commands/results: the exact two cases failed 2/2 before edit on the shared C2 database; both edited modules passed 35/35 after edit. Final governance and `git diff --check` are checked with this Handoff.
- contracts: unchanged API `1.11.0` (176/198/517), migration head `0040_comparison_ai_reports`.
- known limits: the `9d868e62` gate was red in its changed-context battery, so the canonical remainder did not run and a new complete gate is required.
- integration notes: include these test-only corrections in `CMP-WAVE-C2-INT`, update its report/Handoff, commit a clean candidate and rerun all of `make gate`; this task has no remote action. Its four allowed paths alone are changed; forbidden contracts, migrations, application source, root dependency/lockfiles, composition root, styles and infrastructure were not touched.
