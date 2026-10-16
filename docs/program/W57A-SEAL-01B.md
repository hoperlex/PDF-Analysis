# W57A-SEAL-01B — API and stage reseal

**Base:** committed W57A-SEAL-01A `c71048f788e5d0bee39a312217dfd4c0912e5bc1` in isolated worktree `w57a-seal-01`. **Status:** static serial seal candidate; no PostgreSQL/S3 lane, remote publication, tag or deployment.

## Result

The W57a API now has 48 paths, 55 operations and 131 schemas. `getRunNormVerification` is registered for either active expert or admin role and invokes `RunPort.get_norm_verification`. The shipping adapter returns a typed `503 dependency_unavailable` before touching storage. This blocks all unverified report data until CITE supplies a reader that proves the persisted partition, stage, snapshot and set. V1/v2 observations omit citation and value properties; an explicit empty tuple on a certified v3 observation renders `norm_citations: []`, and Finding/FindingDetail mirror the canonical observation rather than carrying an independent answer.

The contract includes `NormCitation`, `NormCitationState`, `UngroundedReason`, per-observation and per-finding partition shapes, `NormVerificationReport`, and `NormRetrievalSetId`. Category and diagnostic-reason vocabularies each contain the 0023 twelve literals. The report keeps canonical and merged member partitions separate, includes withholding counts keyed by the closed reason enum, and marks textless pages as context only. `setCurrentNormSnapshot` and `reauditRun` document the existing `required_norm_unavailable` code with `reference_kind=norm_retrieval_set`; no error code was added.

`text_analysis` registry version is 1.1.0 with optional `norms.snapshot`. The active v1 text stage identity constant also became 1.1.0, so its StageResult and the W56a recorded v2 result agree with the registry. The separate text observation artifact version stays 1.0.0. `norm_verification` remains one existing 1.0.0 registry entry.

## Changed paths

- Formal task/report: `docs/program/tasks/W57A-SEAL-01B.md`, `docs/program/W57A-SEAL-01B.md`.
- Contracts/client: `contracts/api/v1/openapi.json`, `contracts/analysis/v1/stage-registry.json`, `web/openapi/openapi.json`, `web/FRONTEND_LOCK.json`, four `web/src/shared/api/generated/{client.gen.ts,index.ts,operations.gen.ts,types.gen.ts}` outputs.
- Served seam and vocabularies: `src/auditmanager/api/{security.py,app.py,README.md}`, `src/auditmanager/api/routers/{runs.py,ports.py,handlers.py,__init__.py,declarations.py,errors.py}`, `src/auditmanager/api/schemas/{models.py,findings.py,runs.py}`, `src/auditmanager/bootstrap/adapters.py`, `src/auditmanager/findings/grounding.py`, `src/auditmanager/analysis/text/stage.py`.
- Direct UI consumers: `web/src/entities/expert-decision/model/category-labels.ts`, `web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx`, `web/src/app/bff/v1/[...path]/route.ts`, `web/src/shared/api/authorization.ts`.
- Live prose/count consumers: `docs/program/{P02_SEAMS.md,ALPHA_ROADMAP.md}`, `docs/manual-tests/PC-01_prototype.md`, `infra/deploy/{README.md,proxy/nginx.conf,serve.py}`, `src/auditmanager/api/health.py`.
- Independent expectations and focused tests: `tests/support/expected_facts.json`, `tests/contract/api_v1/{test_openapi_conformance.py,test_finding_detail_composition.py,test_w55b_portal_bundle_seal.py,test_surface_counts_in_prose.py,test_w57a_citation_contract.py}`, `tests/integration/api/{conftest.py,test_role_register.py,test_w57a_seal_surface.py}`, `tests/integration/analysis/{test_ar_v2_recorded_artifact.py,test_ar_v2_recorded_stage_result.py,test_w57a_stage_version_compat.py}`, `tests/integration/findings/{test_grounding_gate.py,test_ungrounded_vocabulary_is_enforced.py}`, `tests/integration/p02_journey/test_ungrounded_diagnostic_path.py`.

## Evidence

- `tests/contract/api_v1/test_openapi_conformance_live.py`: **1 passed**; served FastAPI document semantically matches the frozen contract.
- `tests/contract/api_v1/test_openapi_conformance.py` plus FindingDetail composition: **101 passed**.
- New citation/route static tests: **7 passed**.
- W55a/W55b API contract tests: **95 passed** after the 01A `nrs_` identity-count pin was updated.
- Recorded v2 artifact and reason vocabulary: **37 passed**.
- V1/v2 stage version compatibility, stage policy and recorded result: **60 passed**; additional v1 text-stage/provider/validation tests: **81 passed**.
- Prose count mutation suite: **33 passed** after direct live claims were resealed.
- Full `tests/contract/api_v1` pass reached **290 passed, 4 failed** before prose reseal; the direct prose/count failures were fixed. The subsequent targeted prose run had only `CURRENT_STATE.md`'s two stale integrator-owned claims; the mutation suite is now green.
- `npm --prefix web run api:generate` and `npm --prefix web run api:verify`: **OK**, 55 operations and matching contract/snapshot SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`.
- Stage registry SHA-256 `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`; `git diff --check`, Python compilation, and direct task governance findings `[]`: **pass**.
- `npm --prefix web run typecheck` could not run: this isolated worktree has no `web/node_modules` (`tsc: not found`). No `npm ci` was attempted during the W55b resource-sensitive gate.
- `tests/integration/composition/test_every_port_implementation_is_whole.py` has a pre-existing first-test failure: its `DecisionAdapter(None)` severity call reaches a `NoneType` session, unrelated to this RunPort change. The expensive whole-tree continuation was stopped during the W55b gate. `RunPort`'s shipping and seam adapters both implement the new method, and the focused static route test passes.

## Integration and limits

The integrator owns `docs/program/CURRENT_STATE.md`; after cherry-picking 01B it must update the live migration head to `0023_norm_citations` and the API triple to 48/55/131. That is the only remaining known prose-guard blocker from this isolated worktree. Run `tests/integration/api/{test_operation_surface.py,test_role_register.py,test_served_document_and_health_plane.py}` on the next assigned isolated PostgreSQL/S3 lane; they were not run while W55b held the lane. Then run frontend typecheck with installed pinned dependencies. The new report is deliberately unavailable until the later CITE reader proves certified zero, all member partitions and exact run/snapshot/set identity. The RunStatus schema/view can render `norm_retrieval_set_id`, but the existing run repository projection does not yet read the 0023 column; v3 activation must wire that projection and the finding reader together. No verified set or runtime v3 activation is claimed.

**Hotspot proof.** `git diff -- infra/deploy/proxy/nginx.conf infra/deploy/serve.py src/auditmanager/api/app.py 'web/src/app/bff/v1/[...path]/route.ts'` was reviewed line by line. Nginx, serve and BFF changes are comments/docstring counts only; `app.py` changes comments/docstrings and the OpenAPI `_DESCRIPTION` metadata sentence only. A second source-level comparison printed `PROSE_ONLY_OK` for all four after stripping Nginx/JS comments and Python docstrings and normalizing `app.py`'s `_DESCRIPTION` metadata; their executable/config trees are identical to HEAD. No executable route, configuration directive, proxy target, BFF forwarding, security logic or deployment behavior changed in those four files. No old migration, 0023 migration, domain/error catalogue, root lock, composition wiring, W56 executor, `CURRENT_STATE.md`, global style or `P02_LOCK.json` changed. The exact source diff remains inside the formal task's enumerated grants.
