# Task DEV-API-INTEGRATION-REDS-01 — clear the database-backed API and composition reds on the clean dev tip

task_id: DEV-API-INTEGRATION-REDS-01
status: completed in development candidate, one named residue (`[runner]`, outside this task's paths)

## Outcome

Seven integration files that run against the real PostgreSQL and S3 of a lane stack stop failing for causes that are hand-kept expectations lagging the sealed surface: the runner table, the 422 set, the placeholder samples, the contract-version literals and the GET partition counts of the absent-parent sweep now name the operations and parameters that `EXEC-SEAL-01`, `EXEC-IMAGE-DELIVERY-01`, `AR-V3-BETA-SIX-RUN-02`, `AR-V3-BETA-GROUP-API-SEAL-01`, `AR-V3-BETA-PACK-STATUS-API-01` and the contract reseals added. 22 of 23 reds are cleared; none was a product defect. The 23rd (`[runner]` of the port-completeness guard) is a stub in a file this task may not edit and is handed to the integrator with the exact patch.

## Depends on

- `AR-V3-BETA-PACK-STATUS-API-01` — completed; sealed contract `1.5.0` and `getArV3BetaPackStatus`.
- `AR-V3-BETA-PACK-STATUS-WEB-01` — completed; the integration tip's last merge before this base.
- `EXEC-IMAGE-DELIVERY-01` — completed; `getExecutorTaskImage` and `RunnerPort.read_image`.

## Frozen inputs

- domain contract: unchanged (`contracts/domain/v1/**` read, never edited)
- API contract: `contracts/api/v1/openapi.json` `info.version` `1.5.0`, read and never edited
- analysis/comparison/event contract: unchanged
- migration head: `0032_ar_v3_run_group`
- base commit: `b4fcf817281c9eb802b5f0280e592d9844df8a39` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No route, screen, error code or migration is added: the maintained sets are the sealed API surface and the contract; this task only brings seven test-side copies of them up to that surface.

## Captured premise evidence

- premise: 23 tests of the seven files fail at the base; each cluster is a stale hand-kept expectation or a stub missing a port method, and none is a framework body or a wrong status reaching a client

### P-01 — the seven files at the base tree

- captured_at: 2026-10-26
- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/api/test_authorization.py tests/integration/api/test_no_framework_body_reaches_a_client.py tests/integration/api/test_operation_surface.py tests/integration/api/test_served_document_and_health_plane.py tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py tests/integration/composition/test_every_port_implementation_is_whole.py tests/integration/composition/test_router_answers.py -rf --tb=line`
- captured_output:
  ```text
  FAILED tests/integration/api/test_authorization.py::test_every_operation_but_the_register_is_behind_the_seam
  FAILED tests/integration/api/test_authorization.py::test_the_open_surface_is_exactly_the_register
  FAILED tests/integration/api/test_no_framework_body_reaches_a_client.py::test_the_framework_never_answers_for_itself[starlette's 404 for an undeclared path]
  FAILED tests/integration/api/test_no_framework_body_reaches_a_client.py::test_the_framework_never_answers_for_itself[starlette's 405 for an undeclared method on a declared path]
  FAILED tests/integration/api/test_no_framework_body_reaches_a_client.py::test_the_framework_never_answers_for_itself[fastapi's 422 for a missing required header]
  FAILED tests/integration/api/test_no_framework_body_reaches_a_client.py::test_the_framework_never_answers_for_itself[fastapi's 422 for a header outside its pattern]
  FAILED tests/integration/api/test_no_framework_body_reaches_a_client.py::test_the_framework_never_answers_for_itself[fastapi's 422 for a malformed path identity]
  FAILED tests/integration/api/test_no_framework_body_reaches_a_client.py::test_the_framework_never_answers_for_itself[fastapi's 422 for a body that is not JSON]
  FAILED tests/integration/api/test_no_framework_body_reaches_a_client.py::test_the_framework_never_answers_for_itself[fastapi's 422 for a body that is not an object]
  FAILED tests/integration/api/test_no_framework_body_reaches_a_client.py::test_the_framework_never_answers_for_itself[fastapi's 422 for a property outside a closed model]
  FAILED tests/integration/api/test_no_framework_body_reaches_a_client.py::test_the_framework_never_answers_for_itself[fastapi's 422 for a property that breaks a declared bound]
  FAILED tests/integration/api/test_no_framework_body_reaches_a_client.py::test_the_framework_never_answers_for_itself[fastapi's 422 for a query parameter outside its enum]
  FAILED tests/integration/api/test_no_framework_body_reaches_a_client.py::test_the_framework_never_answers_for_itself[fastapi's 422 for a query parameter outside its bounds]
  FAILED tests/integration/api/test_no_framework_body_reaches_a_client.py::test_the_framework_never_answers_for_itself[fastapi's 400 for a body its parser cannot read]
  FAILED tests/integration/api/test_no_framework_body_reaches_a_client.py::test_the_framework_never_answers_for_itself[fastapi's own 401 from HTTPBearer]
  FAILED tests/integration/api/test_no_framework_body_reaches_a_client.py::test_an_exception_no_handler_is_registered_for_still_leaves_as_an_envelope
  FAILED tests/integration/api/test_operation_surface.py::test_every_declared_operation_is_reachable
  FAILED tests/integration/api/test_served_document_and_health_plane.py::TestTheDocumentedAndTheWiredApplicationAgree::test_the_two_schemas_fastapi_would_have_added_are_not_in_it
  FAILED tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py::test_the_surface_partitions_into_the_two_halves_of_the_rule
  FAILED tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py::test_every_get_that_names_a_parent_refuses_an_identity_that_names_nothing
  FAILED tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py::test_a_collection_that_names_no_parent_answers_a_page
  FAILED tests/integration/composition/test_every_port_implementation_is_whole.py::test_every_wired_implementation_carries_the_whole_port[runner]
  FAILED tests/integration/composition/test_router_answers.py::test_the_composed_product_version_reports_the_sealed_contract_version
  23 failed, 100 passed, 1 warning in 820.21s (0:13:40)
  ```
- interpretation: the integration stack `auditmanager-ar-close` (PostgreSQL 58640, S3 62140) answered every request; the 23 reds are those listed. The 13 `fastapi's` / `starlette's` parametrised cases and the unregistered-exception case are one cluster (P-02).

### P-02 — the contract-version literals say `1.0.0`; the served envelope says `1.5.0`

- captured_at: 2026-10-26
- command: `git show b4fcf817:tests/integration/api/test_no_framework_body_reaches_a_client.py | grep -n '^CONTRACT_VERSION'; git show b4fcf817:tests/integration/composition/test_router_answers.py | grep -n '"1.0.0"'; python3 -c "import json;print(json.load(open('contracts/api/v1/openapi.json'))['info']['version'], json.load(open('tests/support/expected_facts.json'))['contract_version'])"`
- captured_output:
  ```text
  39:CONTRACT_VERSION = "1.0.0"
  419:    assert body["contract_version"] == "1.0.0", body
  1.5.0 1.5.0
  ```
- interpretation: every refused request in the no-framework sweep returned a well-formed `ErrorEnvelope` (`error_code`, `correlation_id`, no `detail`) whose `contract_version` is the sealed `1.5.0`; the assertion that failed is only `body["contract_version"] == CONTRACT_VERSION`. Same for `getProductVersion`. `tests/support/expected_facts.json` is the hand-kept figure that `tests/contract/api_v1/test_contract_seal.py` pins to the seal.

### P-03 — the runner table lacks the operation the seam already treats as a runner operation

- captured_at: 2026-10-26
- command: `git show b4fcf817:tests/integration/api/test_authorization.py | sed -n '/^RUNNER = (/,/^)/p' | grep -o '"[a-zA-Z]*"' | grep -v '"POST"' ; grep -n -A3 '^RUNNER_OPERATIONS' src/auditmanager/api/security.py`
- captured_output:
  ```text
  "claimExecutorTask"
  "extendExecutorTaskClaim"
  "submitExecutorTaskAnswer"
  "failExecutorTask"
  261:RUNNER_OPERATIONS: Final[frozenset[str]] = frozenset({
  262-    "claimExecutorTask", "extendExecutorTaskClaim", "submitExecutorTaskAnswer",
  263-    "failExecutorTask", "getExecutorTaskImage",
  264-})
  ```
- interpretation: `EXEC-IMAGE-DELIVERY-01` registered `getExecutorTaskImage` in the seam's `RUNNER_OPERATIONS` and not in the test's `RUNNER` table, so the two sweeps of `test_authorization.py` that compare the table with the seam's set and with the router's operation IDs report exactly that one name.

### P-04 — the reachability samples lack four path parameters

- captured_at: 2026-10-26
- command: `python3 -c "import json,re,subprocess,ast; d=json.load(open('contracts/api/v1/openapi.json')); t=ast.parse(subprocess.run(['git','show','b4fcf817:tests/integration/api/test_operation_surface.py'],capture_output=True,text=True).stdout); s={k.value for n in ast.walk(t) if isinstance(n,ast.Assign) and getattr(n.targets[0],'id','')=='samples' for k in n.value.keys}; m={}; [m.setdefault(x,[]).append(o['operationId']) for p,i in d['paths'].items() for k,o in i.items() if k in ('get','post','put','patch','delete') for x in re.findall(r'[{](\w+)[}]',p) if x not in s]; print({k:len(v) for k,v in m.items()})"`
- captured_output:
  ```text
  {'connection_id': 8, 'token_id': 1, 'task_id': 4, 'blob_id': 1}
  ```
- interpretation: the sample table stopped before the executor operations (`EXEC-SEAL-01`, `EXEC-PULL-01`, `EXEC-IMAGE-DELIVERY-01`); the test fails on the first of them in sort order (`archiveExecutorConnection`), and would fail on thirteen operations in all.

### P-05 — the pinned 422 set lacks two operations that declare the catalog's validation envelope

- captured_at: 2026-10-26
- command: `PYTHONPATH=src:$BS .venv/bin/python -c "import re,subprocess;from auditmanager.api.app import create_documentation_app as c;d=c().openapi();g={o['operationId'] for p in d['paths'].values() for m,o in p.items() if m in('get','post','put','patch','delete') and '422' in o['responses']};s=subprocess.run(['git','show','b4fcf817:tests/integration/api/test_served_document_and_health_plane.py'],capture_output=True,text=True).stdout;b=s[s.index('assert declared_422 == {'):s.index('}, declared_422')];e=set(re.findall(r'\"(\w+)\"',b));print('served 422 declarers not in the pinned set:',sorted(g-e));print('pinned but not served:',sorted(e-g))"`
- captured_output:
  ```text
  served 422 declarers not in the pinned set: ['getExecutorTaskImage', 'startArV3BetaGroup']
  pinned but not served: []
  ```
- interpretation: the served document equals the frozen one (the sibling conformance test is green), so the two additions are declared by the contract; the pinned set is one-sided stale. FastAPI's own `HTTPValidationError` is still absent.

### P-06 — the GET partition of the absent-parent sweep moved by seven operations

- captured_at: 2026-10-26
- command: `python3 -c "import json; d=json.load(open('contracts/api/v1/openapi.json')); g=[(o['operationId'],p) for p,i in d['paths'].items() for m,o in i.items() if m=='get']; a=[x for x in g if '{' in x[1] and x[0]!='getSectionSpecification']; u=[x for x in g if '{' not in x[1]]; print(len(g), len(a), len(u)); c=json.load(open('contracts/domain/v1/identifiers.json'))['identifiers']; print({k:c.get(k) for k in ('group_id','ar_v3_run_group_id','connection_id','executor_connection_id','task_id','executor_task_id')})"`
- captured_output:
  ```text
  56 35 20
  {'group_id': None, 'ar_v3_run_group_id': 'arg', 'connection_id': None, 'executor_connection_id': 'exc', 'task_id': None, 'executor_task_id': 'ext'}
  ```
- interpretation: 35 addressed and 20 unaddressed GETs against the test's 31 and 17. Addressed since the literal was last moved: `getExecutorConnection`, `getExecutorTaskImage`, `getArV3BetaGroup`, `getArV3BetaGroupReview`; unaddressed: `listExecutorConnections`, `listExecutorRoutes`, `getArV3BetaPackStatus`. The catalog keys its identities by entity (`ar_v3_run_group_id`, `executor_connection_id`, `executor_task_id`) while the routes name the parameters `group_id`, `connection_id`, `task_id`, so the sweep's lookup by parameter name finds no prefix. `getArV3BetaPackStatus` answers `{'state': 'not_installed'}`, a singleton the page check cannot accept.

### P-07 — two hand-kept `RunnerPort` stubs lack `read_image`

- captured_at: 2026-10-26
- command: `grep -n "def read_image\|def claim_task\|^class StubRunner" tests/integration/executors/test_runner_seam.py src/auditmanager/api/routers/ports.py`
- captured_output:
  ```text
  tests/integration/executors/test_runner_seam.py:27:class StubRunner:
  tests/integration/executors/test_runner_seam.py:36:    def claim_task(self, *, runner, wait_seconds):
  src/auditmanager/api/routers/ports.py:170:    def claim_task(
  src/auditmanager/api/routers/ports.py:173:    def read_image(
  ```
- interpretation: the guard reports `StubRunner` (`test_runner_seam.py:69`) and its subclass `DeliveringRunner` (`test_runner_client_wire.py:81`) as lacking `read_image`; the one-method stub below fixes both. The file is outside this task's allowed paths.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `tests/integration/api/test_authorization.py`
- `tests/integration/api/test_no_framework_body_reaches_a_client.py`
- `tests/integration/api/test_operation_surface.py`
- `tests/integration/api/test_served_document_and_health_plane.py`
- `tests/integration/api/test_role_register.py`
- `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`
- `tests/integration/composition/test_every_port_implementation_is_whole.py`
- `tests/integration/composition/test_router_answers.py`
- `tests/support/**`
- `docs/program/tasks/DEV-API-INTEGRATION-REDS-01.md`
- `docs/program/DEV-API-INTEGRATION-REDS-01.md`

A product defect in `src/` would have added exactly one more path with its reason; none was found.

## Lane resources

The integrator's existing stack for the integration worktree was used for tests only and was never started, stopped or modified.

- foundation_instance: `auditmanager-ar-close`
- postgres_port: `58640`
- s3_api_port: `62140`
- s3_console_port: `not_assigned_to_this_lane`
- postgres_db: `the stack's own`
- s3_bucket: `the stack's own`

## Forbidden hotspots

Contracts, migration head, root dependency/lock files, `Makefile`, `infra/**`, composition root (`src/auditmanager/bootstrap/**`), all of `src/`, `web/**`, global styles, `tests/integration/executors/**`, `docs/program/DEBT_REGISTER.md`, `docs/program/CURRENT_STATE.md`, other task files, `origin/main`, tags and the deployment host.

## Non-goals

No product change and no contract reseal. No new operation, error code or migration. The `[runner]` stubs are not edited here (see the integration contract). No sweep of other pinned `1.0.0` literals in files outside the seven (`tests/integration/api/test_release_routes.py`, `tests/unit/executor_runner/_support.py` carry `1.0.0` in their own stand-ins and were not examined). The slow per-parameter AST parse of `test_every_port_implementation_is_whole.py` (about 25 s per case, 13 minutes for the file) is not changed.

## Deliverables

- `test_authorization.py`: `getExecutorTaskImage` in the `RUNNER` table (a GET with a `blob_` identity), prose "four" to "five".
- `test_operation_surface.py`: samples for `connection_id`, `token_id`, `task_id`, `blob_id`.
- `test_served_document_and_health_plane.py`: `getExecutorTaskImage` and `startArV3BetaGroup` in the pinned 422 set, each with its task named.
- `test_no_framework_body_reaches_a_client.py`, `test_router_answers.py`: the expected contract version is `FACTS.contract_version`.
- `test_an_absent_parent_is_not_an_empty_page.py`: counts 35 and 20 with the seven operations named; an explicit table from the three differently named path parameters to their catalog keys; `RUNNER_ADDRESSED` (exempt from the 404 sweep) with `test_a_runner_token_read_is_not_answered_to_a_users_credential`; `SERVER_STATUS_OPERATIONS` (exempt from the page check) with `test_the_server_pack_status_answers_its_own_shape`; the fixture drops `AR_V3_BETA_PACK_MANIFEST` from the environment it builds the application with, so the "not installed" state is the suite's own.
- This task and its report.

## Required tests

- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider` on the seven files above, on the lane stack
- expected: 1 failed (`test_every_wired_implementation_carries_the_whole_port[runner]`) until the integrator applies the stub patch below, then 0 failed

## Integration contract

Tests only. The integrator can rely on: every changed expectation names the task that moved it; no assertion was loosened (counts and sets grew by named members; the contract-version check still compares an exact string, now from the independently hand-kept facts file); the two exemptions are narrow and each has a test of the shape it excuses.

The one residue needs a one-method stub in `tests/integration/executors/test_runner_seam.py` (outside this task's paths), after which `[runner]` passes (verified on this lane by applying it, running `-k "carries_the_whole_port and runner"`, 1 passed, and reverting):

Add to `class StubRunner`, beside `issue_token` and `revoke_token`:

```python
    def read_image(self, **_):  # pragma: no cover - not reached here
        raise AssertionError
```

`DeliveringRunner` in `test_runner_client_wire.py` subclasses `StubRunner` and is fixed by it.

## Failure/idempotency/security cases

Each changed expectation was shown failing under one mutation (see the report). The two new tests were mutated on the code under test: the adapter answering `installed` for an empty registry, and the seam no longer treating `getExecutorTaskImage` as a runner operation (a user's credential then gets `403` instead of the `401`).

## Rollback / feature flag

Forward-revert. No behaviour or flag is involved.

## Handoff

- changed files: seven test files, this task and its report
- commands/results: see the report
- known limits: `[runner]` residue; every figure here comes from one lane stack run (PostgreSQL + MinIO of `auditmanager-ar-close`)
- integration notes: merge with or after the lanes that add operations or ports to the surface, because three of the expectations are counts of it; apply the stub patch in the integration contract, then re-run the seven files on the integration stack
