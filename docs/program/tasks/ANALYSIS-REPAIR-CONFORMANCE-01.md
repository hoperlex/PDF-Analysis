# ANALYSIS-REPAIR-CONFORMANCE-01 — correct the 0.27.0 publication metadata

## Outcome
The same local served/frozen comparator that failed deployment reports zero differences for the repaired candidate. Keep the runtime analysis and migration unchanged.

## Depends on
- ANALYSIS-REPAIR-INT-01 — completed implementation at bed5a549f6df8221f3551bd492c103017e827f45.

## Frozen inputs
- Published candidate 590bafb074b36667f34c633b39c608c21b0eb57e; product 0.27.0, contract 1.55.0, migration 0068_reviewable_findings.
- Workflow 43427506750 applied migration 0068 and started healthy services, then refused publication on five schema differences. CSV lacked its declared ErrorEnvelope 422, and DecisionMemoryContent.unverified_reason used a different nullable-bound representation.
- Owner requires local/focused/basic checks only; no general checks, gate or full run. No verification-policy change.

## Ownership and allowed paths
Root owns this narrow contract/consumer correction. Allowed: this task and its completion entry in the release task; contracts/api/v1/openapi.json and README.md; src/auditmanager/api/routers/export.py; the stale CSV 422 description in api/app.py only; tests/contract/api_v1/test_reviewable_findings.py; generated web client, web/openapi/openapi.json and FRONTEND_LOCK.json; local release evidence.

## Forbidden hotspots / non-goals
No dependency/lock, composition, global style, workflow, verification rule, migration, analysis policy/builder, human decision or production setting change. No new operation/schema/error/version. Do not bypass the conformance check or roll back retained data.

## Deliverables / integration contract
Declare the existing CSV validation envelope, express the existing nullable string constraints in the generator's established form, regenerate and reseal the client. JSON values and bounds remain the same; no writer/consent policy or paid call changes. Existing 0.27.0 note remains accurate; it is not edited.

## Required focused checks
- Local test_openapi_conformance_live.py::test_the_served_document_conforms_to_the_frozen_contract — the exact failed publication boundary, no services.
- Local uncertain/memory nullable schema/value regressions.
- Generated client verification and frontend-lock guard for the changed digest.
- git diff --check and review that generated TypeScript types retain their semantics.

## Failure / rollback / handoff
The previous deploy is not a verified release, and no product tag exists. Preserve applied 0068 and all existing findings/decisions. Publish the corrected candidate to dev; main requires direct owner approval of its new exact SHA. Workflow evidence and check results are recorded before publication. This task completes before adding it as a release dependency.

## Completion
The two affected declarations are corrected without changing JSON values, bounds, API version, migration or analysis policy. Local served/frozen conformance and nullable/admission cases: 10 passed. Generated TypeScript declarations retain their semantics; only source digests changed. Client verification and the frontend-lock guard passed (8 focused guard tests); validation is recorded in `.local/evidence/release-0270/`. The patch and generated seal are reviewed before the corrected development candidate is published.
