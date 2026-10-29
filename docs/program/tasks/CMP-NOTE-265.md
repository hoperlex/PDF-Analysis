# Task CMP-NOTE-265 — name the unavailable action on each comparison-only screen

## Outcome
A comparison-only set's specification, optimisation and blocks screens explain the action each screen withholds. None describes a Run start or claims a server refusal that does not exist. D-265's misleading shared note is removed from those three screens.

## Depends on
- CMP-DEBT-261

## Frozen inputs
- domain contract: C2 identifier catalog, unchanged
- API contract: `1.11.0`, 176 paths / 198 operations / 517 schemas, unchanged
- analysis/comparison/event contract: `Q-CMP-5` and the comparison-only `upload_kind` semantics, unchanged
- migration head: `0040_comparison_ai_reports`, unchanged
- base commit: `8f23322df1ced8aaa253b2b495e76993104e41af`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the three screens display the Run-start note for a read or a pass action.

### P-01 — shared note on the three screens
- captured_at: 2026-10-29
- command: `git rev-parse HEAD; rg -n 'COMPARISON_ONLY_START_NOTE' web/src/widgets/specification-prices/ui/specification-prices-section.tsx web/src/widgets/optimisation-proposals/ui/optimisation-proposals.tsx web/src/_pages/blocks/ui/blocks-page.tsx`
- captured_output:
  ```text
  8f23322df1ced8aaa253b2b495e76993104e41af
  web/src/_pages/blocks/ui/blocks-page.tsx:56:  COMPARISON_ONLY_START_NOTE,
  web/src/_pages/blocks/ui/blocks-page.tsx:203:          {COMPARISON_ONLY_START_NOTE}
  web/src/widgets/optimisation-proposals/ui/optimisation-proposals.tsx:44:  COMPARISON_ONLY_START_NOTE,
  web/src/widgets/optimisation-proposals/ui/optimisation-proposals.tsx:136:            {COMPARISON_ONLY_START_NOTE}
  web/src/widgets/specification-prices/ui/specification-prices-section.tsx:31:  COMPARISON_ONLY_START_NOTE,
  web/src/widgets/specification-prices/ui/specification-prices-section.tsx:114:            {COMPARISON_ONLY_START_NOTE}
  ```
- interpretation: the three paths use the Run-start sentence unchanged; the Run list itself remains entitled to use it.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `web/src/entities/document-version/model/upload-kind.ts`
- `web/src/entities/document-version/index.ts`
- `web/src/widgets/specification-prices/ui/specification-prices-section.tsx`
- `web/src/widgets/optimisation-proposals/ui/optimisation-proposals.tsx`
- `web/src/_pages/blocks/ui/blocks-page.tsx`
- `web/tests/unit/comparison-only-pickers/comparison-only-pickers.test.ts`
- `docs/program/tasks/CMP-NOTE-265.md`
- `docs/program/CMP-NOTE-265.md`
- `web/node_modules`

## Forbidden hotspots
- contracts, migrations, root dependency and lock files, composition root, global styles, server handlers and all other UI paths
- the existing Run-start sentence and Run-list behavior
- remote refs, especially `origin/main`

## Non-goals
- no new `upload_kind` value, server refusal, access policy, data query or screen layout
- no C2 publication change; its exact gate candidate remains untouched

## Deliverables
1. Three exact, action-specific sentences from the document-version entity, used by the specification read, optimisation pass and blocks read.
2. Update the existing rendered picker tests to assert each screen's sentence and preserve its disabled choice and accessible description.
3. A report with checks and integration notes.

## Required tests
- `npm --prefix web test -- tests/unit/comparison-only-pickers/comparison-only-pickers.test.ts`
- `npm --prefix web run lint`, `npm --prefix web run typecheck`, `git diff --check`

## Integration contract
Merge after the exact C2 candidate is published to `origin/dev`. The shared Run-start sentence remains for actual Run controls. The three new sentences are presentation only and do not change the server's source-of-truth checks.

## Failure/idempotency/security cases
- a comparison-only option remains disabled and annotated; a portal-bundle, absent or unknown future kind stays unchanged
- accessible `aria-describedby` still points to the visible reason on each screen

## Rollback / feature flag
Revert this branch to restore the old copy. No behavior or feature flag changes.

## Handoff
- changed files: the document-version note constants and public exports, three chooser/picker components, their existing rendered test, this task and `docs/program/CMP-NOTE-265.md`.
- commands/results: targeted Vitest **48 passed**; web lint, typecheck and `git diff --check` passed.
- contracts: API `1.11.0` and migration head `0040_comparison_ai_reports` unchanged.
- known limits: presentation only; no new server-side refusal is asserted or implemented. The normal Run-start note remains in its Run controls.
- integration notes: merge after the exact C2 publication candidate reaches `origin/dev`, then close D-265. No remote ref or forbidden hotspot is owned by this branch.
