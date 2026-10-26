# AR-V3-BETA-GROUP-API-SEAL-01 — six-scope review read

The authenticated `getArV3BetaGroupReview` operation reads a durable AR v3 beta group and returns six ordered scope outcomes from the existing verified review service. Each member exposes its Run/state, explicit review state and, where available, only topic statuses and provisional citation evidence. Failed, pending and verification-refused members remain visible. No Blob pointer, request or reply digest, model answer or numeric verdict enters the response. The existing group start/read operations are unchanged, and production trusted-pack registries remain empty.

## Contract and ownership

- Task: [AR-V3-BETA-GROUP-API-SEAL-01](tasks/AR-V3-BETA-GROUP-API-SEAL-01.md), frozen from `e55192dc6141c3fb5762ae8f7292c09866aaa963`, dependent on completed `AR-V3-BETA-GROUP-REVIEW-01`.
- Shared API/domain/analysis/events contract: `1.3.0` → `1.4.0`, additive. API: **91 paths / 103 operations / 298 schemas**. Error catalogue: 27 codes. Migration head: `0032_ar_v3_run_group`. Product `VERSION`: `0.8.0`.
- Exact OpenAPI content commit: `b84c068b`. Generated client and mirror derive from its bytes; `web/FRONTEND_LOCK.json` pins the commit and all eight digests.
- Domain catalogue revision 22 carries no new identity, code or machine. Its existing `ar_v3_run_group_id` was added to the `distinct_identities` schema enum, correcting a mismatch found by the expanded contract tests.

## Verification

- `tests/contract/api_v1 tests/contract/analysis_packages`: **383 passed** before response-reference normalization. The post-normalization conformance/prose/route/role pass: **80 passed**.
- `tests/contract/domain_p02 tests/contract/test_domain_identifiers_schema.py`: **154 passed**.
- `tests/integration/api/test_ar_v3_group_review_route.py` and the independent role-register assertion: **2 passed**.
- `npm --prefix web run api:verify`: **passed**, 103 operations. Pin inventory with `reseal-surface route error-code --check`: **passed**. Frontend lock: **8 digests, exact content commit and 91/103/298 checked**. `git diff --check`: **passed**.
- `tests/integration/api` was attempted: 383 tests passed before a real-database case stopped setup because `DATABASE_URL` is absent. `npm --prefix web run test:guards` was attempted and cannot start because this checkout has no `vitest` installation. Full `make gate` remains deferred by R-135.

## Handoff

Changed paths are the task-owned API router/port/schema/security and thin bootstrap adapter; the frozen contract families; generated web API and lock; independently pinned tests, live surface prose and this result. The exact list is in the task handoff JSON. No migration, root dependency/lockfile, composition root, global style, provider transport or normative pack data changed. `origin/main`, tags and deployment host were not touched.

The next UI task should consume `getArV3BetaGroupReview` as a distinct review-only response, showing each Run's scope and failure even when some reviews are available. Do not turn provisional citations into legal or numeric conclusions. Before beta acceptance, install an approved six-map/six-set pack, import/designate the qualified snapshot on the stand, and run real PostgreSQL/Blob/provider and frontend checks.
