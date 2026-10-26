# DEV-CONTRACT-REDS-01 — three cheap-guard reds on the clean dev tip

Four tests of `tests/contract` were red on the clean development tip `0d218e38`. They had three unrelated causes; none was a served-contract defect.

## What was wrong and what changed

1. **ALR-05 boundary** (`test_backend_cross_context_imports_use_public_modules`). The worker's baseline import (`EXEC-ENV-OPENROUTER-01`) reached into `auditmanager.executors.operations` and `.runtime`. `executors/public.py` now exports `DestinationPolicy` (imported from `destinations`, the module that defines it; `runtime` only re-exports it), `OperationRefused` and `import_env`, and `workers/__main__.py` imports all three from `public`. `operations`, `probe_runner` and `resolver` import `public`, so `public` cannot import `operations` at module level: importing `operations` first would fail on the cycle. The two `operations` names are therefore resolved on first use by a module `__getattr__` (with a `TYPE_CHECKING` import for type checkers). A new test in `test_alr05_boundaries.py` imports `operations` first and `public` first in fresh interpreters and checks the three names are the defining modules' own objects.
2. **Conformance count** (`test_changed_component_target_is_caught`). The brief's diagnosis (a wrong 404 model on the served `startArV3BetaGroup`) does not hold, and the fix is in the test, not in a router. The test plants a changed `NotFound` target into a copy of the frozen contract and counts the operations that reference it; the served document is not involved, and the `generated document has Finding` wording describes that planted copy. The frozen contract has 74 such operations; the count (73) stopped at `AR-V3-BETA-SIX-RUN-02` and was not moved when `AR-V3-BETA-GROUP-API-SEAL-01` added `getArV3BetaGroupReview` with its own 404. The count is now 74 with that task named in the comment. `test_openapi_conformance_live.py`, which compares `create_documentation_app().openapi()` with the frozen contract and requires no difference, passes, so no AR v3 beta route has a served-versus-frozen mismatch; no router was edited.
3. **Acceptance fixture** (two tests in `test_alpha_acceptance_command.py`). The local API fixture served `contract_version: "1.0.0"`, while `verify-acceptance.mjs` compares it with the frozen contract's `info.version` (`1.4.0`). The fixture now reads that version from `contracts/api/v1/openapi.json` through `_candidate_contract_version()`. A new test serves `<version>-stale` and requires exit 1, `apiBuild` `FAIL`, the served version in the evidence and the finding `served contract version differs from candidate`, so the verifier's refusal stays proven.

## Mutation proofs

| Guard | Mutation (then reverted) | Red result |
|---|---|---|
| `test_backend_cross_context_imports_use_public_modules` | the worker's import restored to `executors.operations` / `executors.runtime` | 1 failed: `deep ...workers/__main__.py:54 auditmanager.executors.operations` and `:55 ...runtime` |
| `test_worker_baseline_names_resolve_from_executors_public_in_any_import_order` | `public.py` imports `OperationRefused, import_env` from `operations` at module level | 1 failed: `ImportError: cannot import name 'OperationRefused' from partially initialized module 'auditmanager.executors.operations' (most likely due to a circular import)` |
| `test_the_served_document_conforms_to_the_frozen_contract` (the live comparison that proves item 2's premise) | `getArV3BetaGroupReview` declares `envelope_responses(401, 403, 500, 503)` | 1 failed: `paths./ar-v3-beta/groups/{group_id}/review.get.responses.404: missing from the generated document` |
| `test_changed_component_target_is_caught` | expected count set back to 73 | 1 failed: `assert 74 == 73` |
| the two original acceptance tests | fixture pins `"contract_version": "1.0.0"` again | 2 failed with `served contract version differs from candidate` |
| `test_served_contract_version_must_equal_the_candidates_contract_version` | `verify-acceptance.mjs` no longer compares the contract version | 1 failed |

## Verification

- `tests/contract` with the gate's invocation and the three CP-00 files ignored (`PYTHONPATH=src:<bootstrap site-packages> .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py`, clean checkout of the lane branch, about 85 s): **1 failed, 1116 passed**. The one failure is `tests/contract/program/test_wave_governance.py::test_every_task_added_after_governance_activation_satisfies_the_rules` (17 other task files, none of them this task); its lane is separate. Baseline on `0d218e38`: 5 failed, 1015 passed by the brief's count.
- `tests/unit/executors` and `tests/unit/runs/test_serving_start_sweeps_temporaries.py`: 441 passed.
- This task's `governance_findings`: empty.

## Known limits

- The DB-backed worker tests (`tests/integration/workers`, `tests/integration/executors`) were not run: no PostgreSQL or MinIO is started in this lane. The change is an import path plus a lazy re-export of the same objects; the worker's baseline branch itself has no test that runs without a database.
- `test_release_command_cannot_turn_skips_recorded_mode_or_outage_into_pass` requires a clean checkout (the script refuses uncommitted changes), so it is green only on a committed tree.
- Mutating a source file and restoring it within the same second, at the same byte size, leaves a stale compiled test module that pytest trusts (seen once while proving the count test; clearing `__pycache__` cleared it). Not a repository defect.
- Other pinned `1.0.0` contract-version literals exist in `tests/integration/api/test_release_routes.py` and `tests/unit/executor_runner/_support.py`; they are outside this lane's paths and were not examined.
