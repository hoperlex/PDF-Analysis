# BETA-REAUDIT-COST-WEB-1030 — fresh approval for repeated Runs

Date2026-10-30. UI code completed after root-owned generated provider mergeb925e83c (6ea9459f). No browser, model, full build/gate, remote publication or deployment.

## Result
Selecting a terminal Run's «Повторный аудит» opens the existing confirmation and reads its current RunStatus once. The version from that response is sent with `reaudit_of_run_id` to the existing cost-estimate POST. The client selects no executor, preset, profile or raised-limit override. Backend source/route semantics remain authoritative.

The confirmation displays a fresh CostApproval and requires a sufficient finite cap and a new checkbox agreement. It never reads/reuses the parent's paid consent. Unknown-outcome retries send the identical new consent/body/key. A cap edit requires new agreement/key. Cancellation or another selected Run cannot inherit a late estimate; failed/mismatched/nonterminal reads cannot confirm. A stale-estimate conflict clears approval and asks for a refresh. Cancel, priority and pause commands retain their previous paths/confirmation behavior.

The granted integration correction makes metered approval require at least one micro-USD even for a zero estimate; only an unmetered connection can approve zero. Both existing start hooks and the pure shared CostApproval form now match that backend boundary.

## Files
- `web/src/features/reaudit-run/model/use-reaudit-cost-approval.ts`: abortable per-confirmation source/estimate query, fresh approval and stable retry identity.
- `web/src/features/reaudit-run/model/use-reaudit-run.ts`, `index.ts`: required fresh consent in the repeat command and public query hook.
- `web/src/_pages/queue/ui/queue-page.tsx`: connected cost confirmation, failures/stale refresh and consent-gated repeat branch.
- Existing `start-run/model/use-run-cost-approval.ts`, `start-ar-v3-group/model/use-ar-v3-cost-approval.ts`, `shared/ui/cost-approval/cost-approval.tsx`: narrowly granted positive metered minimum and explanation.
- `web/tests/unit/execution/reaudit-cost.test.ts`: five actual-dialog cases for new approval, exact body/key retry, failed estimate, stale refresh, cancelled/late source and unchanged cancel.
- `web/tests/unit/execution/execution-commands.test.ts`: explicit consent-bearing repeat request and retained invalidation assertions.
- `web/tests/unit/cost-approval/cost-approval.test.ts`: metered/unmetered zero boundary.
- Task and this report.

## Checks and integration
Focused `execution` plus `cost-approval` Vitest suites: **36 passed** in2.76s. TypeScript typecheck, scoped ESLint and whitespace checks passed. The query is a read and adds no mutation-hook inventory entry.

Root integrates this local provider after its backend. Generated/API/contracts, migrations, composition, locks and global styles were not edited in this commit; provider bytes came through the root merge. The specifically granted existing queue journey checkbox/receipt compatibility follows separately. Live billing, browser layout and end-to-end queue execution remain tomorrow's acceptance obligations. Preserve immutable paid commands/old Runs during any rollback; UI rollback must be coordinated with mandatory backend consent.
