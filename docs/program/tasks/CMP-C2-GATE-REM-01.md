# Task CMP-C2-GATE-REM-01 — repair two canonical-remainder test assumptions

## Outcome
The canonical remainder of the C2 gate no longer depends on a pre-existing executor-route ordering or on an implicit `PYTHONPATH` in the AR v3 private-database migration subprocess. The executor journey still verifies its own route and secret-free response; the XLSX export fixture still migrates its disposable database to the exact head.

## Depends on
- CMP-C2-GATE-W13-01
- CMP-C2-GATE-BE-01

## Frozen inputs
- domain contract: ADR-0025 and `CMP-SEAL-C2`
- API contract: `1.11.0`, 176 paths / 198 operations / 517 schemas
- migration head: `0040_comparison_ai_reports`
- failing candidate: `531f9cb026f0d8f93b7abe1be45ef5372cf8c516`
- full-gate log: `/tmp/cmp-c2-gate-publication.log` (interrupted after diagnostic failures; no `GATE OK`)

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: focused tests and the next complete `make gate`

## Captured premise evidence
- premise: P-01 and P-02 identify the two independent failure classes before a test edit.

### P-01 — executor journey route order
- captured_at: 2026-10-29
- command: `rg -n 'routes.json\(\)\["items"\]\[0\]' tests/integration/executors/test_executor_surface.py; rg -n 'FAILED tests/integration/executors' /tmp/cmp-c2-gate-publication.log`
- captured_output:
  ```text
  138:    assert routes.status == 200 and routes.json()["items"][0]["work_kind"] == "text_analysis"
  FAILED tests/integration/executors/test_executor_surface.py::test_the_journey_has_the_ruled_statuses_and_no_null_and_no_secret
  ```
- interpretation: the C2 route `comparison_pair_check` may precede this test's own `text_analysis` route. The test must identify the route it just created by work kind and connection id, without weakening its served-surface assertions.

### P-02 — private migration subprocess import
- captured_at: 2026-10-29
- command: `rg -n 'cwd=REPOSITORY_ROOT, env=' tests/integration/runs/test_v3_saved_text_layer_probe.py; rg -n 'ModuleNotFoundError: No module named' /tmp/cmp-c2-gate-publication.log | head -n 1`
- captured_output:
  ```text
  158:            cwd=REPOSITORY_ROOT, env={**os.environ, "DATABASE_URL": url},
  ModuleNotFoundError: No module named 'auditmanager'
  ```
- interpretation: pytest adds `src` to its own import path, while the spawned `python -m alembic` process gets neither that path nor an editable install under the scrubbed gate environment. The fixture must pass this checkout's absolute `src` path to that one child.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

`CMP-WAVE-C2-INT` retains the sole `origin/dev` publication slot.

## Allowed paths
- `tests/integration/executors/test_executor_surface.py`
- `tests/integration/runs/test_v3_saved_text_layer_probe.py`
- `docs/program/tasks/CMP-C2-GATE-REM-01.md`
- `docs/program/CMP-C2-GATE-REM-01.md`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, root dependencies/lockfiles, composition root, global styles, infrastructure
- all application source and other tests; all remote refs

## Non-goals
- no route sorting change or new executor behaviour
- no production Alembic/bootstrap change; no weakened XLSX assertions
- no C3 code, contract or migration

## Deliverables
- route assertion scoped to the route created by this journey
- disposable migration subprocess with an explicit checkout `src` import path
- focused red/green evidence and a report of the interrupted gate's distinct failure classes

## Required tests
- focused executor journey and XLSX export fixture tests on the C2 stack
- focused HTTP batch repeat after SIGINT to classify its `CancelledError`
- `git diff --check` and task-governance check
- next exact clean C2 publication commit receives a complete `make gate` with literal `GATE OK`

## Integration contract
This task owns only the two named tests. The integrator merges its repair into the C2 candidate, updates the wave report and INT task, commits cleanly, and reruns the entire gate on that new SHA before any `origin/dev` fast-forward. No change to the frozen API, migration or runtime is implied.

## Failure/idempotency/security cases
- a pre-existing comparison route must not make the test inspect the wrong item; the created connection's route remains asserted
- the migration child must import this checkout, never an installed or unrelated `auditmanager`
- the SIGINT-induced `CancelledError` is not classified as product failure unless the focused replay reproduces it

## Rollback / feature flag
Revert these test-only corrections if they hide a real failure; no runtime behaviour or feature flag changes. C2 remains off by default with `AUDITMANAGER_COMPARISON_MODULES=none`.

## Handoff
- changed files: `tests/integration/executors/test_executor_surface.py`, `tests/integration/runs/test_v3_saved_text_layer_probe.py`, this task and `docs/program/CMP-C2-GATE-REM-01.md` only.
- commands/results: red focused executor 1 failed; red focused XLSX 1 setup error; focused HTTP repeat after SIGINT 1 passed; green executor 1 passed, XLSX module 12 passed, both edited modules together 28 passed; governance 16 passed before edit. Final governance and diff are checked with this Handoff.
- contracts: unchanged API `1.11.0` (176/198/517), migration head `0040_comparison_ai_reports`.
- known limits: the diagnostic gate was interrupted at about 15% of the canonical remainder and cannot certify its unexecuted tests; the next exact clean candidate needs a new complete gate. The HTTP `CancelledError` did not recur without SIGINT.
- integration notes: bring these two test-only corrections into `CMP-WAVE-C2-INT`, update its report/Handoff, commit cleanly and rerun all of `make gate`; no remote action belongs to this task. Forbidden contracts, migrations, source, root dependency/lockfiles, composition root, styles and infrastructure were not touched (`git diff --name-only 531f9cb0..HEAD` plus the current diff names only this task's paths).
