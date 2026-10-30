# BLOCK10-INT-1030 — parameter context before visual review

task_id: BLOCK10-INT-1030

## Outcome

Fresh explicitly planned runs extract their already-budgeted parameter candidates before visual review and supply bounded preliminary context to image requests, with saved context receipts and no additional model-call count.

## Depends on

- BLOCK6-INT-1030
- BLOCK9-INT-1030

## Frozen inputs

- Base dev `f68f832ba9ce0149ec950248c86b921aedfcde92`, API1.14.0/migration0044.
- Existing8-call parameter policy, visual16-source/8-image requests, durable saved replies/unknown-effect guards.
- Owner continuous source-only/dev instruction; root sole writer, owner deploys.

## Allowed paths

- `src/auditmanager/analysis/extended/parameter_context.py`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/runs/preflight.py`
- `src/auditmanager/runs/cost_policy.py`
- `src/auditmanager/runs/extended_review.py`
- `web/src/widgets/extended-review/ui/project-parameters.tsx`
- `web/src/entities/audit-run/lib/extended-report.ts`
- `web/src/entities/audit-run/lib/extended-xlsx.ts`
- `docs/program/**`

## Forbidden hotspots

Existing coverage/core/workflow/project_parameters.py paid builders, contracts/API/generated, routers/composition root, migrations, dependencies/locks, global styles, tests/fixtures, other paths, main/deployment. No tests/build/compile/import/lint/typecheck/runtime/browser/DB/model checks.

## Non-goals

No expert parameter/normative authority, OCR, changed output schema/source allowlist, new model-call budget or additional images, rewriting old accepted requests or stored evidence, claimed model reasoning/visual confirmation.

## Deliverables

Independent fresh project_parameter_context_policy binds helper and parameter bundle; at most16 complete fact records /16000 encoded context characters per visual call, explicit omission/status markers. Reserve70000 extra input tokens per at-most2 visual requests/localwindow before consent. Parameter extraction runs once before new visual work, then reuses durable replies/result; older commands without context policy retain order/inputs. Decorator preserves ModelRequest image bytes/descriptors via dataclass replacement and restricts output source_ids to original visual sources. Save exact provided context/fact IDs/hash per request, labelled provided-not-confirmed. Separate metadata/display only, no canonical findings/decisions. Fresh env rollback excludes context.

## Required tests

- command: none, explicitly deferred by owner.
- expected: UNVERIFIED source candidate.

## Integration contract

Root owns exact slots and publishes normal clean dev/ref read-back, preserving incoming owner changes. Existing v3 rules and parameter modules remain byte-stable; only fresh optional policy enables changed order/requests and cost reservation. No wire/migration/route change; no provider execution in this coding session.

## Rollback / feature flag

AUDITMANAGER_PROJECT_PARAMETER_CONTEXT=0 excludes context from fresh starts. Existing accepted commands keep frozen policy, source/request hashes and saved responses; absence never acquires new context/work.

## Handoff

Changed paths, no-check status, contracts, conservative context/selection limits and publication receipt, D-290.
