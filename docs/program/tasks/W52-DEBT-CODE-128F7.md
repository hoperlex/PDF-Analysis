# Task W52-DEBT-CODE-128F7 — distinguish unknown run facts from absent ones

task_id: W52-DEBT-CODE-128F7

## Outcome

A run or comparison reading with an unrecognised `provider_mode` or `cost_basis` is
visibly marked as unrecognised; a field that is genuinely absent keeps its absent label.
No raw unknown value is echoed to a reviewer.

## Depends on

- `W52-INT-128A-01` — partial D-128 guard repair published at
  `baa1aca61fd4a278648fb6e040e469fa0d391498`.

## Frozen inputs

- Exact base `baa1aca61fd4a278648fb6e040e469fa0d391498`; domain revision 9 / 29
  identities, API 27 paths / 34 operations / 77 schemas, error catalog 23, migration
  head `0015_accounts_roles_registration`.
- D-128 F-7 in `reviews/W48-JUDGE-Z.md`; proposed W52 plan at
  `2b45a11ec558df1452a4822149e54d2fe0ddb57e` slots F-7 to DEBT-CODE.
- Owner direction 2026-10-08: proceed without approval; only basic tests and lint;
  stand, QA and full gate remain D-139/D-140.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: provider mode and cost basis currently conflate unknown with absent.

### P-01 — exact base and presentation entry points

- captured_at: 2026-10-08
- command: `git rev-parse HEAD && rg -n 'export function providerModeLabel|export function runCost|function providerModeText|data-cost-basis=\\{cost.basis' web/src/entities/audit-run/model/run-presentation.ts web/src/widgets/stage-comparison/ui/stage-comparison.tsx web/src/widgets/run-progress/ui/run-progress.tsx`
- captured_output:
  ```text
  baa1aca61fd4a278648fb6e040e469fa0d391498
  web/src/widgets/run-progress/ui/run-progress.tsx:240:            <dd data-cost-basis={cost.basis ?? 'unstated'}>
  web/src/widgets/stage-comparison/ui/stage-comparison.tsx:126:function providerModeText(value: string | number | null): string {
  web/src/entities/audit-run/model/run-presentation.ts:48:export function providerModeLabel(value: unknown): ProviderModeLabel {
  web/src/entities/audit-run/model/run-presentation.ts:379:export function runCost(status: {
  ```
- interpretation: these are the code sites, while the judge's F-7 probe demonstrates
  the actual ambiguity.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `web/src/entities/audit-run/model/run-presentation.ts`
- `web/src/entities/audit-run/index.ts`
- `web/src/widgets/run-progress/ui/run-progress.tsx`
- `web/src/widgets/stage-comparison/ui/stage-comparison.tsx`
- `web/tests/unit/run/provider-mode.test.ts`
- `web/tests/unit/run/cost.test.ts`
- `web/tests/unit/screens/run-progress.test.ts`
- `web/tests/unit/screens/stage-comparison.test.ts`
- `docs/program/W52-DEBT-CODE-128F7.md`

## Forbidden hotspots

Every other path, especially contracts, migration head, dependencies/locks, backend,
composition root, global styles and F-10/F-11.

## Non-goals

No D-128 closure, new wire vocabulary, full W52-DEBT-CODE lane, W52 freeze, QA,
stand, full gate, release, tag or `origin/main` publication.

## Deliverables

- Distinct typed presentation labels for missing and unrecognised provider modes, neither live.
- Distinct typed cost-basis state and Russian captions for missing and unrecognised values.
- Run-progress and comparison cells visibly distinguish both cases; tests prove the
  judge's F-7 unknown injections would be red under the old implementation.

## Required tests

- Focused Vitest files listed in allowed paths; `npm --prefix web run lint`; `git diff --check`.
  No stand, QA or full gate.

## Integration contract

Hand back a clean branch from the exact dispatch SHA with only allowed paths. Integrator
may publish this code preparation to `origin/dev` after exact remote-ref and fast-forward
verification. D-128 remains open for F-1/F-2/F-10/F-11 and validation.

## Failure/idempotency/security cases

Unknown raw values must not appear in the HTML or be recast as absence or live/measured.
Repeated rendering is stable, and valid values preserve their current display.

## Rollback / feature flag

Revert the code commit. No runtime feature flag.

## Handoff

- changed files, commands/results, contracts, risks, integration notes, forbidden-hotspot proof.
