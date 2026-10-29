# CMP-SEAL-C3 — deterministic stage-comparison seal

Task: [`CMP-SEAL-C3`](tasks/CMP-SEAL-C3.md). The seal is in progress on a separate worktree. No C3 contract or migration from the disposable probe has been merged into this branch.

## Disposable pin probe, 2026-10-29

The throwaway worktree `scratch/cmp-seal-c3-probe` added one GET path and one schema to a copy of API `1.11.0`, set its version to `1.12.0`, and added a minimal `0041_comparison_stage_core` migration. The probe intentionally did not add a real C3 API or durable schema. It established which independent pins reject even the smallest reseal.

Command: `PYTHONPATH=src .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider --basetemp=/tmp/cmp-seal-c3-probe-pytest tests/contract/api_v1/test_openapi_conformance.py tests/contract/api_v1/test_doc_prose_facts.py` in the throwaway worktree. Result: **9 failed, 121 passed in 47.42 s**. The failing checks named the frozen operation and schema sets/counts, effective-security inventory, migration head, independent expected facts, and live prose claims in `docs/program/CURRENT_STATE.md`, `docs/program/ALPHA_ROADMAP.md` and `docs/manual-tests/PC-01_prototype.md`. This is expected red evidence, not a seal result. Full output: `/tmp/cmp-seal-c3-probe-contract.log` on this host.

`python3 tools/plan/pin_sweep.py contract-version migration reseal-surface route table --check docs/program/tasks/CMP-SEAL-C3.md` also returned an advisory missing-path inventory. It includes broad pattern matches that may require no edit. The task was amended to name the proved live documentation claims, the shared `contracts/analysis/**` and `contracts/events/**` version pins found by literal search, and explicit router paths accepted by the checker. Any further real edit outside its grants requires another task amendment first. The product `VERSION` stays `0.9.0`; the probe has not established a reason to edit it.

Before writing a stage router, the integration inspection found its dependency protocols live in `src/auditmanager/api/routers/ports.py`; the seal task now grants that exact file for five new stage ports, including the separate upload port. This grant does not permit application logic in the router or changes to any C2 port.

A literal pin inventory found current `1.11.0` error envelopes in both proxy configurations and existing web tests, plus the analysis result constant and `tests/support/expected_facts.json`. The task now grants only their version/surface/head pins. Historical statements about prior contracts are not targets of a mechanical replacement.

The existing `comparison_pdf` upload service is PDF-only: `complete_file` publishes with `application/pdf` and validates one PDF before placing it into a set. C3 ZIP-set admission therefore needs its own stage upload command and durable candidate state, with 16 MiB chunk transport and the D-262 raw-byte, admission, disk and PDF checks at the first caller. The C3 seal must expose that boundary without routing ZIP bytes through the C0 PDF completion path.

The task scope now names `comparison_stage_uploads.py` and its fifth stage port explicitly. The migration deliverable includes candidate state so a resumed upload and its cleanup can be reconciled across restarts; the stage-pair lane owns the actual reader call and all D-262 first-use controls.

## Boundary decisions for the real seal

These are design inputs, not a claim that the `1.12.0` contract has been frozen:

| Family | Durable/contract boundary |
| --- | --- |
| Stage upload | Separate resumable batch, file and candidate identities. File names only suggest labels. The caller checks raw compressed bytes, admission and disk before extraction; each PDF is validated before publication. |
| Pair and assembly | `stp_` binds one П `DocumentUid` to one Р `DocumentUid` or a `sas_` assembly. Suggestions do not bind documents; an expert's keyed confirmation does. Completeness is explicit. |
| Sheet map | `slk_` revisions append the expert's full map, including explicit unpaired sheets. A stale base revision is refused. Page-profile identities address evidence; sheet numbers are display values. |
| Deterministic text | Fragments, exclusions, differences and cross-sheet hints are separate immutable evidence. A later AI layer can reference them but cannot remove or rewrite a raw difference. |
| Chain run | `crn_` pins exact version identities, the link revision and input digests for steps 01–07. New document versions mark a run stale by digest comparison. |

The four established prefixes and the raw-evidence rule come from ADR-0025 decisions 2, 3 and 21; the upload boundary follows the C0 PDF-only implementation and the D-262 review. Exact operation and table inventories remain part of the pending seal result.

## Seal result

Pending. The real `1.12.0` operation list, `0041` table inventory, migrations, checks, rollback evidence, risks and forbidden-hotspot proof will be recorded here before integration.
