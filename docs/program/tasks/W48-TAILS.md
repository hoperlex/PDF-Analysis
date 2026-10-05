# Task W48-TAILS — close the remaining bounded audit tails

## Outcome

Every remaining closed-vocabulary lookup is classified, hostile history text is contained, and
the proxy/local-S3 comments describe the executable tree.

## Depends on

- `W48-RULE-01`

## Frozen inputs

- domain/API/analysis contracts: unchanged W48 set
- migration head: `0014_durable_analysis_effects`
- base commit: `03c04a1d87fda862d085a6a49d0a46f2692f7ffd`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: ten unrepaired lookup sites remain on the task base

### P-01 — lookup inventory

- captured_at: 2026-10-05
- command: `rg -n 'LABELS\[|_LABEL\[|as ProviderMode' web/src/widgets web/src/entities web/src/shared/ui -l`
- captured_output:
  ```text
  web/src/entities/expert-decision/ui/decision-history.tsx
  web/src/entities/expert-decision/ui/verdict-badge.tsx
  web/src/entities/expert-decision/ui/verdicts-panel.tsx
  web/src/shared/ui/run-state-badge.tsx
  web/src/shared/ui/stage-status-badge.tsx
  web/src/widgets/dashboard/ui/run-activity-panel.tsx
  web/src/widgets/export-panel/ui/export-panel.tsx
  web/src/widgets/knowledge-base/ui/knowledge-base.tsx
  web/src/widgets/run-progress/model/run-presentation.ts
  web/src/widgets/run-progress/ui/run-progress.tsx
  web/src/widgets/run-progress/ui/stage-table.tsx
  web/src/widgets/stage-comparison/ui/stage-comparison.tsx
  ```
- interpretation: twelve files match on the pre-repair checkout; two were already repaired in
  Stage B, leaving ten for classification.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `web/src/widgets/**`
- `web/src/entities/**`
- `web/src/shared/ui/run-state-badge.tsx`
- `web/src/shared/ui/stage-status-badge.tsx`
- `web/src/app/globals.css` (history containment only)
- `web/tests/unit/**`
- `infra/deploy/proxy/nginx.conf` (comment only)
- `infra/local/README.md`
- `infra/local/bucket-init.sh` (comment only)
- `docs/program/W48-TAILS.md`

## Forbidden hotspots

- contracts, migrations, backend, root locks, composition and all other global styles

## Non-goals

- no documentary closeout owned by the integrator

## Deliverables

- T-1/T-2/T-4/T-7 repairs, typed-fault injections, style test and report

## Required tests

- full frontend tests, lint, typecheck, API contract tests and `git diff --check`

## Integration contract

Unknown vocabulary is visible as a typed fault and user-controlled history strings cannot widen
the 780 px viewport.

## Failure/idempotency/security cases

- a lookup proven total is documented with executable evidence; it is never changed by guess

## Rollback / feature flag

Revert the bounded UI/comment changes; no stored data or feature flag.

## Handoff

- changed files: allowed paths only
- commands/results: report includes site-by-site classification
- known limits: live 780 px drive remains `W48-JUDGE-Z`
- integration notes: merge after GUARDS-2; this lane owns the only style edit
