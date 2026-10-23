# AR-V3-BETA-GROUP-REVIEW-SCREEN-01 — browser read for six AR v3 Runs

«Настройки анализа» now accepts a group ID from the address (`/analysis-settings?group_id=arg_…`) or a read-only GET form. A valid ID invokes `getArV3BetaGroupReview` and shows all six ordered Run IDs, scope states, failures and available provisional quotes. The panel refuses an incomplete, duplicate or mixed-group answer before displaying evidence. Every visible topic/citation says that expert verification is required; no numerical or legal verdict is shown.

## Handoff

- Task: [AR-V3-BETA-GROUP-REVIEW-SCREEN-01](tasks/AR-V3-BETA-GROUP-REVIEW-SCREEN-01.md), frozen from `b4291c1261225d4cfaeb75ad9194e5ded87e2079` with completed dependency `AR-V3-BETA-GROUP-API-SEAL-01`.
- Changed files: the existing analysis-settings route and page, the audit-run group-ID shape guard/export, the Runs query key and shared failure-message export, the new `ar-v3-beta-review` widget and rendered-state test, this task/result note, current state and code queue. The task handoff JSON contains the exact paths.
- Checks: `npm --prefix web run api:verify` passed (103 operations); TypeScript's `transpileModule` parsed all 10 changed TS/TSX files without syntax errors; a direct pure-model check accepted a complete six-scope group and rejected invalid ID, missing scope, duplicate Run ID, wrong group ID and missing available review. `git diff --check` passed.
- Frontend checks attempted: `npm --prefix web run typecheck` → `tsc: not found`; `npm --prefix web run test:guards` → `vitest: not found`. This checkout has no `web/node_modules`; the rendered-state test is committed for the beta environment with installed dependencies. Full `make gate` remains deferred by R-135.
- Contracts: unchanged at shared `1.4.0`; API 91 paths / 103 operations / 298 schemas, 27 errors, migration head 0032. The new cache key is under the existing `runs` namespace.
- Limits: no approved six-map/six-set pack is installed, so production group starts still refuse. No target-stand PostgreSQL/Blob/provider journey or browser build was available here. A future group-start control should link to `/analysis-settings?group_id=<returned group ID>`.
- Rollback: remove the query panel, shape guard and query key together. No migration or API rollback is needed.
- Forbidden hotspots: `contracts/**`, migration head, root dependencies/lockfiles, composition root, global styles, generated API, normative pack data, provider transports, existing finding review, `origin/main`, tags and deployment host were untouched.
