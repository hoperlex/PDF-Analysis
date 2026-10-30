# BLOCK13-INT-1030 — retraceable normative searches

task_id: BLOCK13-INT-1030

## Outcome

The expert can retrace actual already executed normative searches and distinguish no search hits, unavailable corpus, refused lookup, unsearched queries and truncated search pages without new model/database work.

## Depends on

- BLOCK12-INT-1030

## Frozen inputs

- Dev `679a0dc91de8f74ceb199942b5e456efcf7f0f3b`, API1.14.0/migration0044.
- Existing _norms search behavior/query cache/first3 hits/timeout/call limits and source-bound observation IDs.
- Original missing_norms_queue is provenance for the manual follow-up workflow; no Norms-main or document-absence claim is introduced.

## Allowed paths

- `src/auditmanager/runs/extended_review.py`
- `web/src/widgets/extended-review/**`
- `web/src/entities/audit-run/lib/extended-report.ts`
- `web/src/entities/audit-run/lib/extended-xlsx.ts`
- `docs/program/**`

## Forbidden hotspots

Frozen paid builders/analysis helpers/norm-context helpers, norms queries/repositories/public API, contracts/API/generated, routers/composition root, migrations, dependencies/locks, global styles, tests/fixtures, other paths, main/deployment. No tests/build/compile/import/lint/typecheck/runtime/browser/DB/model checks.

## Non-goals

No extra search/model request, normative edition/applicability/absence assertion, catalog/intake queue mutation, expert act or historical data rewrite. This is saved search evidence for manual follow-up, not original external missing-norms ingestion.

## Deliverables

Separate result receipts retain original proposed queries, per-query execution/cache status and actual snapshot/hits/next-page/truncation/error evidence, bound to original observation ordinal/ID/source IDs. Capture only existing batched local/global searches; no added metadata in paid payloads/observations or request hashes. Unavailable is distinct from zero hits; unknown cursor tails remain explicit. Root aggregates original scope, paged UI provides search/status filters and source-run navigation. Existing full MD/HTML/JSON/XLSX contain all receipts independent of UI filtering, no extra provider/database writes.

## Required tests

- command: none, explicitly deferred by owner.
- expected: UNVERIFIED source candidate.

## Integration contract

Root sole writer/publisher to origin/dev. Metadata-only receipts may accompany previously accepted batched requests without additional authority or changed model content. No API/migration/paid budget change; source context B12 helpers remain unchanged. Fresh fetch/preserve incoming/clean normal push/read-back; owner deploys.

## Rollback / feature flag

Revert capture/UI/export block; no underlying search behavior, saved provider answer, canonical finding or expert decision is mutated.

## Handoff

Changed paths, no-check status, unchanged contracts, first-page-only search scope/manual follow-up limitations and D-290.
