# Task AR-V3-BETA-GROUP-REVIEW-SCREEN-01 — read six Run outcomes in the browser

## Outcome
An expert or administrator can open `/analysis-settings?group_id=<arg_...>` or enter a group ID there, then read all six AR v3 beta scope outcomes and provisional citation evidence without mistaking them for accepted findings.

## Depends on
- `AR-V3-BETA-GROUP-API-SEAL-01`

## Frozen inputs
- shared API/domain/analysis/events contract: `1.4.0`, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `b4291c1261225d4cfaeb75ad9194e5ded87e2079`
- `getArV3BetaGroupReview` response: six ordered members, review-only projection

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the browser shows the frozen C01–C22 source preview but has no group-review consumer
### P-01 — existing screen
- captured_at: 2026-10-23
- command: `rg -n 'ArV3BetaStatus|getArV3BetaGroupReview' web/src/_pages/analysis-settings web/src/widgets web/src/shared/api/generated/client.gen.ts`
- captured_output: `AnalysisSettingsPage` mounts `ArV3BetaStatus`; the generated client exports `getArV3BetaGroupReview`; no widget calls it.
- interpretation: the existing authenticated settings screen can host a linkable beta review panel without adding a new screen route or changing the API.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `web/src/app/analysis-settings/page.tsx`
- `web/src/_pages/analysis-settings/ui/analysis-settings-page.tsx`
- `web/src/entities/audit-run/model/ar-v3-group-id.ts`
- `web/src/entities/audit-run/index.ts`
- `web/src/shared/api/query-keys.ts`
- `web/src/shared/api/index.ts`
- `web/src/widgets/ar-v3-beta-review/**`
- `web/tests/unit/analysis-settings/**`
- `docs/program/tasks/AR-V3-BETA-GROUP-REVIEW-SCREEN-01.md`
- `docs/program/AR-V3-BETA-GROUP-REVIEW-SCREEN-01.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots
- `contracts/**`, migration head, root dependencies/lockfiles, composition root, global styles
- generated API files, normative pack data, provider transports, old finding review screen
- `origin/main`, tag and deployment host

## Non-goals
- Starting a group or installing reviewed six-map/six-set packs.
- Publishing a numeric or legal verdict, accepting citations, or altering canonical findings.
- New navigation entry or route; the existing settings screen carries the beta lookup.

## Deliverables
- Shareable group-ID query on the existing authenticated screen, validated before requesting.
- Six-scope read panel with pending/failed/refused/available states, cautious evidence labels and explicit no-verdict text.
- Focused rendered-state coverage or documented frontend test limitation.

## Required tests
- command: `npm --prefix web run api:verify`
- command: `npm --prefix web run test:guards`
- command: `npm --prefix web run typecheck`
- expected: generator check passes; frontend checks need installed web dependencies. A focused source/markup guard and `git diff --check` may be used when this disk-constrained checkout cannot install them. Full make gate deferred by R-135.

## Integration contract
The query sends only a syntactically valid opaque group ID to `getArV3BetaGroupReview`. A missing ID sends no request. A completed scope shows only the API's provisional topics and quotes, with explicit expert review required; a failed, pending or verification-refused scope shows no fabricated citation. The panel never calls the legacy canonical finding/decision API.

## Failure/idempotency/security cases
- Invalid address is rejected locally after the route's existing screen guard.
- API errors use the shared Russian failure message and correlation ID; retry is a read only.
- A partial six-Run group always shows all members. No caller-provided text is rendered as HTML.

## Rollback / feature flag
Remove the panel and query key as one reversible UI change; the server read and contract remain. No migration.

## Handoff
- changed files: result note
- checks/results: result note
- known limits: live beta stand, installed frontend dependencies and approved pack remain
- integration notes: future start control can link to this query using the returned group ID
