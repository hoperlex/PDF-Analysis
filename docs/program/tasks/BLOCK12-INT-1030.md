# BLOCK12-INT-1030 — source-bound normative paragraph context

task_id: BLOCK12-INT-1030

## Outcome

Fresh batched section reviews can assess their real corpus search quotes with bounded text around the actual paragraph and adjacent paragraphs, preserving query-specific quotes per observation and exact source identities.

## Depends on

- BLOCK10-INT-1030
- BLOCK11-INT-1030

## Frozen inputs

- Dev `8f5c9c45bc86cb8cca66e66ed9058df4afc98e66`, API1.14.0/migration0044.
- Existing immutable normative snapshots, reliable corpus search candidates, norm_verification8-call caps/12000 output tokens and saved paid-call custody.
- Owner allows own corpus and provisional findings; unavailable material remains unverified. Source-only work/dev publication, no deployment.

## Allowed paths

- `src/auditmanager/norms/paragraph_context.py`
- `src/auditmanager/norms/public.py`
- `src/auditmanager/runs/norm_context.py`
- `src/auditmanager/runs/preflight.py`
- `src/auditmanager/runs/cost_policy.py`
- `src/auditmanager/runs/extended_review.py`
- `web/src/widgets/extended-review/**`
- `web/src/entities/audit-run/lib/extended-report.ts`
- `web/src/entities/audit-run/lib/extended-xlsx.ts`
- `docs/program/**`

## Forbidden hotspots

Frozen analysis paid builders/coverage/workflow/project-parameter helpers, contracts/API/generated, routers/composition root, migrations, dependencies/locks, global styles, tests/fixtures, other source paths, main/deployment. No tests/build/compile/import/lint/typecheck/runtime/browser/DB/model checks.

## Non-goals

No current-edition/legal applicability certification, Norms-main access, complete section normative engine, extra model calls/output quotas, expert findings/decisions, changed source evidence, hidden fallback or historical request rewrite.

## Deliverables

Read-only normative-context public seam validates exact snapshot/document/paragraph and reads genuine bounded paragraph/neighbor text with Unicode ranges/reliability/excerpt hashes and explicit truncation. Separate fresh norm_paragraph_context_policy binds actual helpers and reserves100000 extra input tokens per already planned local/global norm request, without adding calls. At most12 candidate paragraphs and18000 encoded context characters per request; unavailable/omitted context remains explicit. Norm candidates retain their own per-input quotes; model/parser citation allowlist remains the original candidates, not neighbor context. Durable request/response receipts and paged UI/full saved exports retain identities/coverage. Missing policy preserves previous requests.

## Required tests

- command: none, explicitly deferred by owner.
- expected: UNVERIFIED source candidate.

## Integration contract

Root owns the new internal normative read seam and named application/UI slots. No transport contract/migration or composition change. Clean normal origin/dev push/read-back with incoming changes preserved; owner deploys. Existing paid builders remain byte-stable, new policy alone enables request decoration.

## Rollback / feature flag

AUDITMANAGER_NORM_PARAGRAPH_CONTEXT=0 excludes context and added input reservation from fresh starts. Old absent-policy commands retain prior behavior; accepted policy validates exact source helper hashes before new paid work.

## Handoff

Changed paths, no-check status, new internal public read seam (no API contract), bounded context/quote limitations and D-290.
