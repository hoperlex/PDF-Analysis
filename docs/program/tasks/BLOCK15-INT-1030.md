# BLOCK15-INT-1030 — parameter context for comprehensive review

task_id: BLOCK15-INT-1030

## Outcome

Fresh local/global comprehensive, critic and correction requests can use bounded source-cited parameter candidates already extracted before visuals, with separate provided-context receipts and no extra model steps.

## Depends on

- BLOCK10-INT-1030
- BLOCK14-INT-1030

## Frozen inputs

- Dev `7e4b3364a2e75f0123ca0551eb19e94ec592a214`, API1.14.0/migration0044.
- Existing8-call project_parameters_policy and early B10 project_parameter_context_policy; original comprehensive/critic/corrector source allowlists, actual facts/quotes and durable paid responses.
- No tests/runtime/model/synthetic work, root sole integrator/dev publisher, owner deploys.

## Allowed paths

- `src/auditmanager/analysis/extended/parameter_review_context.py`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/runs/preflight.py`
- `src/auditmanager/runs/cost_policy.py`
- `src/auditmanager/runs/extended_review.py`
- `web/src/widgets/extended-review/ui/project-parameters.tsx`
- `web/src/entities/audit-run/lib/extended-report.ts`
- `docs/program/**`

## Forbidden hotspots

Existing coverage/core/workflow/review/PP/visual-context/native-piece/norm-context builders, contracts/API/generated, routers/composition root, migrations, dependencies/locks, global styles, tests/fixtures, other paths, main/deployment. No tests/build/compile/import/lint/typecheck/runtime/browser/DB/model checks.

## Non-goals

No extra parameter extraction/calls/output quota, source/citation allowlist expansion, normative threshold or expert passport authority, observations/evidence rewrites, earlier-policy request expansion or trusted AR-v3 change.

## Deliverables

Independent fresh project_parameter_review_context_policy binds its actual helper and PP bundle, with comprehensive_analysis/finding_review/finding_correction local/global scopes, at most16 complete facts/16000 encoded context characters. Same-page facts are preferred, omitted candidates counted; input70k per existing scoped request reserved before consent. Only fresh batched paths already planning early B10 parameters opt in. Validate helpers before early paid work, keep old no-field requests unchanged. Dataclass replacement preserves original request evidence/schema/image bytes; context facts remain hints with real provenance and cannot create output source IDs. Save prepared/received/replayed context receipts per local/global request, aggregate into PP report and expose paged UI/full MD/HTML/JSON/XLSX saved exports.

## Required tests

- command: none, explicitly deferred by owner.
- expected: UNVERIFIED source candidate.

## Integration contract

Root owns named exact slots, no current paid helper/contract/migration change. Existing PP8-call and global quotas remain; old missing policy acquires no new input/work. Normal clean dev push/read-back preserving incoming owner changes; owner deploys.

## Rollback / feature flag

AUDITMANAGER_PROJECT_PARAMETER_REVIEW_CONTEXT=0 omits fresh review context and its input reservation. Existing visual-only context remains independent; accepted flags/hashes persist.

## Handoff

Changed paths, no-check status, unchanged contracts/steps, context/allowlist limitations, publication receipt and D-290.
