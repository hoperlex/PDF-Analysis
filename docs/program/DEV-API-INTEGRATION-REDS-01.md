# DEV-API-INTEGRATION-REDS-01 — the database-backed API and composition reds

Seven integration files had 23 failing tests on the integration tip `b4fcf817` (22 of them on the clean `origin/dev` tip `354a9092`; the 23rd is the new `getArV3BetaPackStatus` read meeting the absent-parent sweep). Every cluster was a hand-kept expectation or a hand-kept stub that lagged the sealed surface. **No cluster was a product defect**: in each, the product answered correctly (a well-formed `ErrorEnvelope` for every refusal, `401` to a user's credential on a runner read, `{state: not_installed}` for an empty registry) and the test did not know the operation, parameter or version. No file under `src/` was edited.

## Per-cluster classification

| Cluster | Tests | Class | Root cause | Fix |
|---|---|---|---|---|
| Runner table | `test_authorization.py` (2) | TEST-LAG | `EXEC-IMAGE-DELIVERY-01` put `getExecutorTaskImage` in the seam's `RUNNER_OPERATIONS` but not in the test's `RUNNER` table | the row (a GET with `ext_` and `blob_` identities); prose "four" to "five" |
| Contract version | `test_no_framework_body_reaches_a_client.py` (14), `test_router_answers.py` (1) | TEST-LAG | literals `1.0.0`; the family is sealed at `1.5.0`. The envelopes themselves were correct (no `detail`, catalog code, correlation id) | `FACTS.contract_version`, the hand-kept figure of `tests/support/expected_facts.json` that `test_contract_seal.py` pins to the seal; the literal stays independent of the catalog the adapter reads |
| Reachability samples | `test_operation_surface.py` (1) | TEST-LAG | no sample for `connection_id`, `token_id`, `task_id`, `blob_id` (13 operations of `EXEC-SEAL-01`, `EXEC-PULL-01`, `EXEC-IMAGE-DELIVERY-01`) | four well-formed samples |
| Pinned 422 set | `test_served_document_and_health_plane.py` (1) | TEST-LAG | `getExecutorTaskImage` and `startArV3BetaGroup` declare the catalog's validation envelope and were not in the pinned set | the two names, each with its task |
| Absent-parent sweep | `test_an_absent_parent_is_not_an_empty_page.py` (3) | TEST-LAG | counts 31 / 17 against 35 / 20; the catalog keys `ar_v3_run_group_id`, `executor_connection_id`, `executor_task_id` where the routes say `group_id`, `connection_id`, `task_id`; `getArV3BetaPackStatus` is a singleton, not a collection | counts 35 / 20 with the seven operations named; an explicit parameter-to-key table (an unlisted parameter is still an error); `RUNNER_ADDRESSED` and `SERVER_STATUS_OPERATIONS` exemptions, each with a test of the shape it excuses |
| Port completeness | `test_every_port_implementation_is_whole.py[runner]` (1) | TEST-LAG, **residue** | `StubRunner` (`tests/integration/executors/test_runner_seam.py`) and its subclass `DeliveringRunner` lack `RunnerPort.read_image` | not done: both files are outside this lane's allowed paths. The one-method patch is in the task file's integration contract and was verified (`-k "carries_the_whole_port and runner"`: 1 passed, then reverted) |

## The two exemptions

- `RUNNER_ADDRESSED = {getExecutorTaskImage}`: a runner-token read cannot answer `404` to a user's credential, so it leaves the `404` sweep. `test_a_runner_token_read_is_not_answered_to_a_users_credential` asserts the answer is `401 authentication_required` for the sweep's administrator (not `404`, which would say which tasks exist, and not `403`).
- `SERVER_STATUS_OPERATIONS = {getArV3BetaPackStatus}`: a singleton, so it leaves the page check. `test_the_server_pack_status_answers_its_own_shape` asserts exactly `{"state": "not_installed"}`. The fixture now builds the application without `AR_V3_BETA_PACK_MANIFEST` from the process environment, so a lane that names a manifest does not turn this suite red for the wrong reason; the installed shape is covered by `tests/integration/api/test_ar_v3_pack_status_route.py` and `tests/integration/composition/test_v3_pack_install.py`.

## Mutation proofs

Each mutation was applied to one file, the named tests were run on the lane stack, and the file was restored with `git checkout` (the `__pycache__` of the tests was cleared each time).

| Changed expectation | Mutation | Red result |
|---|---|---|
| `RUNNER` row | row removed | 2 failed: `assert {'claimExecut...orTaskAnswer'} == frozenset({'c...rTaskAnswer'})` and the register sweep's set comparison |
| Reachability sample | `task_id` sample removed | 1 failed: `extendExecutorTaskClaim: unfilled placeholder in /runner/tasks/{task_id}/extend` |
| Pinned 422 set | `startArV3BetaGroup` removed; separately `getExecutorTaskImage` removed | 1 failed each: `declared_422` set comparison |
| Contract version (no-framework) | `CONTRACT_VERSION = "1.0.0"` | 14 failed, 2 passed (the sweep's anti-vacuity and the planted-framework-body test stay green) |
| Contract version (composed adapter) | `== "1.0.0"` | 1 failed: `contract_version: '1.5.0'` |
| Addressed count | `EXPECTED_ADDRESSED = 31` | 1 failed: `the surface now has 35 GET operations addressing a parent identity, not 31` |
| Unaddressed count | `EXPECTED_UNADDRESSED = 17` | 1 failed: `the surface now has 20 GET operations addressing no parent identity, not 17` |
| Parameter table | `group_id` / `connection_id` / `task_id` entry removed (three runs) | 1 failed each: `the catalog declares no prefix for the path parameter '<name>'` |
| `RUNNER_ADDRESSED` | emptied | 1 failed: `getExecutorTaskImage ... 401 authentication_required` in the 404 sweep |
| `SERVER_STATUS_OPERATIONS` | emptied | 1 failed: `getArV3BetaPackStatus answered 200 without a page: {'state': 'not_installed'}` |
| `test_the_server_pack_status_answers_its_own_shape` (new) | `get_ar_v3_pack_status` answers `state="installed"` for an empty registry (adapter, restored) | 1 failed: `answered {'state': 'installed'} with no reviewed pack installed` |
| `test_a_runner_token_read_is_not_answered_to_a_users_credential` (new) | `getExecutorTaskImage` removed from `RUNNER_OPERATIONS` in `security.py` (restored) | 1 failed: `getExecutorTaskImage answered 403 ... permission_denied` |

## Verification

- Base (`b4fcf817`, seven files): **23 failed, 100 passed** in 820 s. The list is in the task file (P-01).
- Final tree (the same command, the seven files, lane stack): **1 failed, 124 passed** in 848 s (123 tests at the base plus the two new ones). The one failure is `test_every_wired_implementation_carries_the_whole_port[runner]`; with the stub patch applied (verified and reverted) it passes, so the expected result on the merged tree is 0 failed.
- `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py` alone: 12 passed in 5 s. The 13 minutes of the seven-file run are almost entirely `test_every_port_implementation_is_whole.py`, which parses every Python file of `src` and `tests` once per parametrised case (about 25 s each); that is a cost, not a defect, and was left alone.
- The task's `governance_findings`: empty.

## Known limits

- `[runner]` stays red until the integrator adds the stub method (task file, integration contract).
- Pinned `1.0.0` literals remain in `tests/integration/api/test_release_routes.py` and `tests/unit/executor_runner/_support.py`; they belong to their own stand-ins, were not red and were not examined.
- The sweeps are counts of the surface: a lane that adds a GET operation will move `EXPECTED_ADDRESSED` / `EXPECTED_UNADDRESSED` again, which is what they are for.
