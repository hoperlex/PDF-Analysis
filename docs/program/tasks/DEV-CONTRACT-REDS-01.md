# Task DEV-CONTRACT-REDS-01 — clear the three cheap contract-suite reds on the clean dev tip

task_id: DEV-CONTRACT-REDS-01
status: completed in development candidate

## Outcome

`tests/contract`, run as the gate runs it, no longer fails for the four tests that were red on the clean development tip: the worker reaches the executors context only through `executors/public.py`, the NotFound-reference count of the conformance test matches the frozen contract, and the acceptance-command fixture derives the served contract version from the contract instead of pinning an old literal. The fifth red of that run (`test_wave_governance`) belongs to another lane and is untouched.

## Depends on

- `AR-V3-BETA-GROUP-API-SEAL-01` — completed; sealed contract `1.4.0` and the group review operation.
- `EXEC-ENV-OPENROUTER-01` — completed; added the worker's baseline import.

## Frozen inputs

- domain contract: unchanged
- API contract: `contracts/api/v1/openapi.json` `info.version` `1.4.0`, read and never edited
- analysis/comparison/event contract: unchanged
- migration head: `0032_ar_v3_run_group`
- base commit: `0d218e38dd34cc34495bc26983af2f99789667c2` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: three independent causes, none of them a served-contract defect

### P-01 — the worker imports two internal modules of the executors context

- captured_at: 2026-10-26
- command: `git show 0d218e38:src/auditmanager/workers/__main__.py | grep -n "auditmanager.executors"`
- captured_output:
  ```text
  54:        from auditmanager.executors.operations import OperationRefused, import_env
  55:        from auditmanager.executors.runtime import DestinationPolicy
  ```
- interpretation: these are the two deep imports `test_backend_cross_context_imports_use_public_modules` reports. `executors/public.py` cannot import `operations` at module level: `operations`, `probe_runner` and `resolver` all import `public`, so the two `operations` names are resolved on first use (module `__getattr__`) and `DestinationPolicy` is imported from its defining module.

### P-02 — the count of operations that reference the NotFound response is 74, and the served document equals the frozen one

- captured_at: 2026-10-26
- command: `python3 -c "import json; d=json.load(open('contracts/api/v1/openapi.json')); refs=[(m.upper(),p) for p,i in d['paths'].items() for m,o in i.items() if isinstance(o,dict) and o.get('responses',{}).get('404',{}).get('\$ref')=='#/components/responses/NotFound']; print(len(refs)); print([r for r in refs if 'ar-v3' in r[1]])"`
- captured_output:
  ```text
  74
  [('POST', '/ar-v3-beta/groups'), ('GET', '/ar-v3-beta/groups/{group_id}'), ('GET', '/ar-v3-beta/groups/{group_id}/review')]
  ```
- interpretation: the test plants a changed `NotFound` target into a copy of the contract and counts the operations that reference it; it does not read the served document. The extra line in the report is the group review read that `AR-V3-BETA-GROUP-API-SEAL-01` added (its comment in the test stopped at `AR-V3-BETA-SIX-RUN-02`). The line `the contract has ErrorEnvelope, the generated document has Finding` describes the planted copy, not a served route.

### P-03 — the served document conforms to the frozen contract

- captured_at: 2026-10-26
- command: `PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/api_v1/test_openapi_conformance_live.py`
- captured_output:
  ```text
  .                                                                        [100%]
  1 passed in 2.20s
  ```
- interpretation: `differences(contract, create_documentation_app().openapi())` is empty, so `startArV3BetaGroup` and its two siblings are declared as the contract says; no router edit is needed.

### P-04 — the fixture pinned `1.0.0` while the verifier reads the contract

- captured_at: 2026-10-26
- command: `git show 0d218e38:tests/contract/test_alpha_acceptance_command.py | grep -n '"contract_version"'; python3 -c "import json;print(json.load(open('contracts/api/v1/openapi.json'))['info']['version'])"`
- captured_output:
  ```text
  74:                "contract_version": "1.0.0",
  1.4.0
  ```
- interpretation: `verify-acceptance.mjs` compares the served `contract_version` with `contracts/api/v1/openapi.json` `info.version` and reports `served contract version differs from candidate`; the fixture's literal could only be right until the next reseal.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/workers/__main__.py`
- `src/auditmanager/executors/public.py`
- `src/auditmanager/api/routers/**`
- `tests/contract/architecture/test_alr05_boundaries.py`
- `tests/contract/api_v1/test_openapi_conformance.py`
- `tests/contract/test_alpha_acceptance_command.py`
- `tests/e2e/pc01/journey/**`
- `tests/support/**`
- `scripts/manual-alpha-check.sh`
- `docs/program/tasks/DEV-CONTRACT-REDS-01.md`
- `docs/program/DEV-CONTRACT-REDS-01.md`

## Forbidden hotspots

Contracts, migration head, root dependency/lock files, `Makefile`, `infra/**`, composition root (`src/auditmanager/bootstrap/**`), `web/**`, global styles, other task files, `origin/main`, tags and the deployment host.

## Non-goals

No behaviour change in the worker, the executors context or any served route. No contract reseal. No change to the other `test_wave_governance` red. No sweep of the other `1.0.0` literals in unrelated tests (`tests/integration/api/test_release_routes.py`, `tests/unit/executor_runner/_support.py`).

## Deliverables

- `executors/public.py` re-exports `DestinationPolicy`, `OperationRefused` and `import_env`; the worker imports them from there.
- A cycle guard in `test_alr05_boundaries.py` (a fresh interpreter imports `operations` first, then `public` first).
- The conformance count moved to 74 with the sealing task named in the comment.
- The acceptance fixture derives the served contract version; one test stages a mismatch and requires the verifier's refusal.
- This task and its report.

## Required tests

- command: `PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py` with `BS` the bootstrap venv's `site-packages` and the lane's `.venv` linked to the shared one.
- expected: only `test_wave_governance` remains red (another lane); the four targeted tests pass.

## Integration contract

Pure test and re-export change. The integrator can rely on: `auditmanager.executors.public` exposing the three names above with the same objects as their defining modules; no import cycle in any import order; the verifier still refusing a served contract version that differs from the candidate's.

## Failure/idempotency/security cases

Each guard was shown failing under one mutation (see the report): the deep import restored, an eager `operations` import in `public.py`, the served review route losing its 404, the count set back to 73, the fixture pinning `1.0.0` again, and the verifier no longer comparing the contract version.

## Rollback / feature flag

Forward-revert. No behaviour or flag is involved.

## Handoff

- changed files: `src/auditmanager/executors/public.py`, `src/auditmanager/workers/__main__.py`, three contract tests, this task and its report
- commands/results: see the report
- known limits: the fifth red, `test_wave_governance`, is not addressed here
- integration notes: merge after nothing in particular; the acceptance test needs a clean checkout, so run the contract suite on the merged tree
