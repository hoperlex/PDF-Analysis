# CMP-SEAL-C3 — deterministic stage-comparison seal

Task: [`CMP-SEAL-C3`](tasks/CMP-SEAL-C3.md). The seal is in progress on a separate worktree. No C3 contract or migration from the disposable probe has been merged into this branch.

## Disposable pin probe, 2026-10-29

The throwaway worktree `scratch/cmp-seal-c3-probe` added one GET path and one schema to a copy of API `1.11.0`, set its version to `1.12.0`, and added a minimal `0041_comparison_stage_core` migration. The probe intentionally did not add a real C3 API or durable schema. It established which independent pins reject even the smallest reseal.

Command: `PYTHONPATH=src .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider --basetemp=/tmp/cmp-seal-c3-probe-pytest tests/contract/api_v1/test_openapi_conformance.py tests/contract/api_v1/test_doc_prose_facts.py` in the throwaway worktree. Result: **9 failed, 121 passed in 47.42 s**. The failing checks named the frozen operation and schema sets/counts, effective-security inventory, migration head, independent expected facts, and live prose claims in `docs/program/CURRENT_STATE.md`, `docs/program/ALPHA_ROADMAP.md` and `docs/manual-tests/PC-01_prototype.md`. This is expected red evidence, not a seal result. Full output: `/tmp/cmp-seal-c3-probe-contract.log` on this host.

`python3 tools/plan/pin_sweep.py contract-version migration reseal-surface route table --check docs/program/tasks/CMP-SEAL-C3.md` also returned an advisory missing-path inventory. It includes broad pattern matches that may require no edit. The task was amended to name the proved live documentation claims, the shared `contracts/analysis/**` and `contracts/events/**` version pins found by literal search, and explicit router paths accepted by the checker. Any further real edit outside its grants requires another task amendment first. The product `VERSION` stays `0.9.0`; the probe has not established a reason to edit it.

Before writing a stage router, the integration inspection found its dependency protocols live in `src/auditmanager/api/routers/ports.py`; the seal task now grants that exact file for four new stage ports. This grant does not permit application logic in the router or changes to any C2 port.

A literal pin inventory found current `1.11.0` error envelopes in both proxy configurations and existing web tests, plus the analysis result constant and `tests/support/expected_facts.json`. The task now grants only their version/surface/head pins. Historical statements about prior contracts are not targets of a mechanical replacement.

## Seal result

Pending. The real `1.12.0` operation list, `0041` table inventory, migrations, checks, rollback evidence, risks and forbidden-hotspot proof will be recorded here before integration.
