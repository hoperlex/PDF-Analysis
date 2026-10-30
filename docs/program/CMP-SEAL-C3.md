# CMP-SEAL-C3 — deterministic stage-comparison seal

Task: [`CMP-SEAL-C3`](tasks/CMP-SEAL-C3.md). The candidate is on `integration/cmp-seal-c3`, separate from the C2 integration worktree. The disposable probe was discarded before the real implementation.

## Disposable pin probe, 2026-10-29

The throwaway worktree `scratch/cmp-seal-c3-probe` added one GET path and one schema to a copy of API `1.11.0`, set its version to `1.12.0`, and added a minimal `0041_comparison_stage_core` migration. The probe intentionally did not add a real C3 API or durable schema. It established which independent pins reject even the smallest reseal.

Command: `PYTHONPATH=src .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider --basetemp=/tmp/cmp-seal-c3-probe-pytest tests/contract/api_v1/test_openapi_conformance.py tests/contract/api_v1/test_doc_prose_facts.py` in the throwaway worktree. Result: **9 failed, 121 passed in 47.42 s**. The failing checks named the frozen operation and schema sets/counts, effective-security inventory, migration head, independent expected facts, and live prose claims in `docs/program/CURRENT_STATE.md`, `docs/program/ALPHA_ROADMAP.md` and `docs/manual-tests/PC-01_prototype.md`. This is expected red evidence, not a seal result. Full output: `/tmp/cmp-seal-c3-probe-contract.log` on this host.

`python3 tools/plan/pin_sweep.py contract-version migration reseal-surface route table --check docs/program/tasks/CMP-SEAL-C3.md` also returned an advisory missing-path inventory. It includes broad pattern matches that may require no edit. The task was amended to name the proved live documentation claims, the shared `contracts/analysis/**` and `contracts/events/**` version pins found by literal search, and explicit router paths accepted by the checker. Any further real edit outside its grants requires another task amendment first. The product `VERSION` stays `0.9.0`; the probe has not established a reason to edit it.

Before writing a stage router, the integration inspection found its dependency protocols live in `src/auditmanager/api/routers/ports.py`; the seal task now grants that exact file for five new stage ports, including the separate upload port. This grant does not permit application logic in the router or changes to any C2 port.

A literal pin inventory found current `1.11.0` error envelopes in both proxy configurations and existing web tests, plus the analysis result constant and `tests/support/expected_facts.json`. The task now grants only their version/surface/head pins. Historical statements about prior contracts are not targets of a mechanical replacement.

The existing `comparison_pdf` upload service is PDF-only: `complete_file` publishes with `application/pdf` and validates one PDF before placing it into a set. C3 ZIP-set admission therefore needs its own stage upload command and durable candidate state, with 16 MiB chunk transport and the D-262 raw-byte, admission, disk and PDF checks at the first caller. The C3 seal must expose that boundary without routing ZIP bytes through the C0 PDF completion path.

The task scope now names `comparison_stage_uploads.py` and its fifth stage port explicitly. The migration deliverable includes candidate state so a resumed upload and its cleanup can be reconciled across restarts; the stage-pair lane owns the actual reader call and all D-262 first-use controls.

## Boundary decisions for the real seal

These decisions are implemented by the candidate contract and migration:

| Family | Durable/contract boundary |
| --- | --- |
| Stage upload | Separate resumable batch, file and candidate identities. File names only suggest labels. The caller checks raw compressed bytes, admission and disk before extraction; each PDF is validated before publication. |
| Pair and assembly | `stp_` binds one П `DocumentUid` to one Р `DocumentUid` or a `sas_` assembly. Suggestions do not bind documents; an expert's keyed confirmation does. Completeness is explicit. |
| Sheet map | `slk_` revisions append the expert's full map, including explicit unpaired sheets. A stale base revision is refused. Page-profile identities address evidence; sheet numbers are display values. |
| Deterministic text | Fragments, exclusions, differences and cross-sheet hints are separate immutable evidence. A later AI layer can reference them but cannot remove or rewrite a raw difference. |
| Chain run | `crn_` pins exact version identities, the link revision and input digests for steps 01–07. New document versions mark a run stale by digest comparison. |

The four established prefixes and the raw-evidence rule come from ADR-0025 decisions 2, 3 and 21; the upload boundary follows the C0 PDF-only implementation and the D-262 review.

## Candidate inventory

The authored and served OpenAPI documents agree at `1.12.0`: **204 paths, 230 operations, 570 component schemas**. C3 adds **28 paths, 32 operations, 53 schemas** to C2's `1.11.0` surface. Sixteen C3 operations are reads; sixteen are keyed expert writes. Every new operation declares bearer security, the shared error envelope and a typed `503 dependency_unavailable` response. The five adapters refuse with `comparison_modules` while stages are disabled and with their own lane name when enabled but unwired. The module default remains `none`.

| Lane | New operation IDs | `0041` tables |
| --- | --- | --- |
| Upload (10) | `createStageUpload`, `listStageUploads`, `getStageUpload`, `uploadStageUploadPart`, `completeStageUploadFile`, `confirmStageUploadCandidate`, `rejectStageUploadCandidate`, `pauseStageUpload`, `resumeStageUpload`, `cancelStageUpload` | `stage_upload`, `stage_upload_file`, `stage_upload_part`, `stage_upload_candidate` |
| Pair and assembly (7) | `listStagePairs`, `getStagePair`, `listStagePairSuggestions`, `confirmStagePair`, `createStageAssembly`, `reviseStageAssembly`, `setStagePairCompleteness` | `stage_pair`, `stage_assembly`, `stage_assembly_member` |
| Sheet map (6) | `listStageSheetPassports`, `listStageSheetSuggestions`, `getStageSheetMap`, `applyStageSheetMap`, `listStageSheetMapHistory`, `getStageSheetMapRevision` | `stage_link_revision`, `stage_link_item` |
| Text evidence (5) | `listStageTextFragments`, `listStageTextExclusions`, `listStageRawDifferences`, `listStageTextHints`, `recomputeStageTextEvidence` | `stage_text_fragment`, `stage_text_exclusion`, `stage_text_difference`, `stage_text_hint` |
| Seven-step chain (4) | `startStageChainRun`, `listStageChainRuns`, `getStageChainRun`, `cancelStageChainRun` | `stage_chain_run`, `stage_chain_step` |

Fourteen new opaque identifier prefixes are registered in `contracts/domain/v1/identifiers.json` and the shared identity types. All fifteen tables have a foreign-key path to `project`; none depends on a job or attempt row. The migration's database triggers enforce project scope on pairs, candidates, assembly members, page profiles, text evidence and pinned chain versions. Sheet-map revisions reject a stale base under a pair-level transaction lock. Assemblies, link revisions, link items and raw text evidence are immutable after insertion; mutable aggregate rows freeze their identity columns. A populated `0041` database refuses downgrade. Empty-table downgrade and re-upgrade are exercised against PostgreSQL.

The recovery inventories name all fifteen tables, their 28 triggers, the new upload Blob references, the product purge classification and nonterminal erase guards. A real PostgreSQL test fills upload, candidate, assembly, pair, map revision, chain run and step rows, derives the project scope from the catalog, deletes that scope through the project-erase implementation, and proves another project and document survive.

## Candidate checks and limits

Observed so far: the exact `Makefile` contract battery passes **1317 tests and 19283 subtests** in 183 seconds on clean commit `8d4217e3` (`/tmp/cmp-seal-c3-contract-exact-8d.log`). The battery excludes three historical CP00 files under D-220. Full web Vitest passes **219 files and 3685 tests** in 429 seconds under gate-equivalent local permissions (`/tmp/cmp-seal-c3-vitest-full-escalated-7f.log`); current web lint and typecheck pass. The complete DB directory passes **951 tests** on a separate C3 PostgreSQL instance at `0041` (`/tmp/cmp-seal-c3-db-isolated-full-7f.log`); the complete recovery directory passes **531 tests** against that stack (`/tmp/cmp-seal-c3-recovery-isolated-full-7f.log`). The P02 journey directory passes **80 tests** and journey conformance passes **135 tests**. HTTP composition exercises every C3 route with stages off and on (**65 passed**) and rejects an over-limit 16 MiB part before the stub (**2 passed**). Migration/invariant tests include populated downgrade refusal, populated C3 project erase, stale sheet-map revision, immutable update/delete and raw-text difference guards. The two focused stage Blob-reference tests, clean-install relation inventory and **18 synthetic recovery drills** pass. Generated-client `api:verify` reports **230 operations**; `git diff --check` passes. The integration task owns the later exact-candidate full `make gate`.

The first API sweep exposed independent pins for the 32 authentication cases, five subject-reader routers, seven path identities, twelve query-bearing sealed stubs, 32 role cases and 22 catalog `422` responses. The contract and implementation already agreed; these five existing test files were brought up to the sealed surface. API files were then checked in ordered segments on the isolated stack: each already passed prefix was retained while the next named pin was corrected, and the remaining suffix passed. The initial recovery retry on the shared C2 stack was interrupted by C2 foundation restarting PostgreSQL (`AdminShutdown`); the independent 531-test C3 retry above is the result used for handoff. The initial sandboxed Vitest could not spawn ESLint or listen on loopback (`EPERM`); the gate-equivalent retry above is the result used for handoff.

Composition files were likewise checked in ordered segments on the isolated stack. The seal corrected independent enumerators for sixteen addressed GETs, the C1 operation census, five new ports and the module-off GET sweep. Each focused file then passed; the final suffix after `test_router_answers.py` passed **393 tests, one skipped** in 222 seconds (`/tmp/cmp-seal-c3-composition-after-router-7f.log`), and that router file passed **14 tests** (`/tmp/cmp-seal-c3-router-answers-isolated-7f.log`). Every file in the directory has been exercised after its relevant correction, although there is no single green whole-directory invocation. This distinction also applies to the API directory.

The C3 ports remain stubs and do not admit a ZIP. `CMP-STAGE-PAIR-01` must enforce the D-262 first-use controls: raw compressed byte bound, admission and disk bound, and per-PDF validation before storage. The ZIP reader's agent code review and the decision to reject `__MACOSX/` are recorded separately in `docs/program/compare/CMP-ZIP-SECURITY-REVIEW.md`; that fix is on `agent/cmp-zip-fix-01`, awaiting the C2 publication boundary. The C3 branch has no remote publication authority. No `origin/main` action is implied by this seal.

The scope audit currently compares 164 changed paths since the clean C2 base with the task's 62 `allowed_paths` rules, including untracked files: **0 outside**. The same audit found no changed root dependency/lock file, global style, C2 jobs/runtime file, server compose file or stage UI. The contract, migration head, composition root and generated client changes are owned explicitly by `CMP-SEAL-C3`.
