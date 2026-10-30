# Task CMP-STAGE-REVIEW-UI-01 — stage review, journal and launch controls

## Outcome
An expert can launch and follow stage runs after an estimate/consent, review evidence-backed change cards with saved verdict history, and download the grouped final journal. The catalog can launch selected pairs and manage assembly decisions through available sealed operations.

## Depends on
- CMP-STAGE-UI-01
- CMP-STAGE-AI-CORE-01
- CMP-SEAL-C4

## Frozen inputs
- domain contract: ADR-0025 A-9/A-10, Q-CMP-10 and `COMPARE-MODULES-PLAN.md` §1.2/C4
- API contract: C4 `1.13.0` schemas/operations owned by `CMP-SEAL-C4`; root integrated its generated provider and additive read seams, including `StageAssembly.member_revision_no` and the resume estimate's `stage_chain_run_id` query
- migration head: C4 seal owns `0042_comparison_stage_review`; no database change in this UI lane
- base commit: `f4f6e1ecd37a0d25e3be018b245e497629d84068`
- root-provided integration baseline before this lane's commit: `656d84e34ffde4e42fd19b6f51a4b1dcd2b66b66`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: tab mounts belong to root; this lane adds the connected widgets against sealed C4 clients.

### P-01 — base
- captured_at: 2026-10-30
- command: `git rev-parse HEAD; rg -n '^export function StagePairCatalog' web/src/widgets/stage-pair-catalog/ui/stage-pair-catalog.tsx`
- captured_output:
  ```text
  f4f6e1ecd37a0d25e3be018b245e497629d84068
  26:export function StagePairCatalog({ projectUid, mayAct }: StagePairCatalogProps) {
  ```
- interpretation: the existing catalog can be extended within its owned widget; root mounts the new tab widgets.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `web/src/widgets/stage-changes/**`
- `web/src/widgets/stage-run-controls/**`
- `web/src/widgets/stage-pair-catalog/**`
- `web/tests/unit/stage-changes/**`
- `web/tests/unit/stage-run-controls/**`
- `web/tests/unit/stage-pair-catalog/**`
- `docs/program/tasks/CMP-STAGE-REVIEW-UI-01.md`
- `docs/program/CMP-STAGE-REVIEW-UI-01.md`
- `web/node_modules`

## Forbidden hotspots
- page mounts, shared viewer, generated client/contracts, migrations, root dependencies/locks, global styles, remote refs and deployment

## Non-goals
- no invented canonical identity, model choice, simulated success or model output as expert decision
- no backend runtime or full gate/build

## Deliverables
1. Tab 3 change cards with class/category/system, grouped sections, explicit before/after/evidence and PDF callback, expert draft decisions with rejection reasons, keyed bulk save and verdict/carryover history.
2. Tab 4 journal grouped by designation/section/system with XLSX/PDF/HTML downloads through generated stream clients.
3. Full-run estimate/consent/start/cancel/resume controls, selected-pair batch launch and queue stop, actual latest run date/state/counts.
4. Assembly completeness/create/revise controls using actual server identities and revision numbers, preserving explicit unavailable state when required read data is absent.

## Required tests
- short focused Vitest and typecheck; `git diff --check`; heavy gates/build deferred by the owner

## Integration contract
Root mounts public `StageChanges`/`StageJournal` with `runId`, `mayAct` and `onOpenEvidence`; run/catalog controls expose callbacks for the root's selected run. C4 provider is integrated by root before typecheck. Generated clients are the only transport; model names and canonical IDs come from server data only.

## Failure/idempotency/security cases
- a rejected card needs a nonblank reason; optimistic verdict revision comes from that card's server verdict
- one command intent reuses its key on retry; stale cards/runs remain visibly stale
- downloads revoke object URLs; a failed request shows its typed failure rather than a fake completed state
- paid AI launch requires the exact displayed estimate digest and explicit consent; deterministic launch is explicit

## Rollback / feature flag
The parent stage screen already gates the module. Removing the widgets restores earlier UI without persisted/schema changes; saved expert verdicts remain server-owned.

## Handoff
- changed files: owned `stage-changes`, `stage-run-controls`, `stage-pair-catalog` source/tests, this task and its report
- commands/results: focused Vitest 16 passed; web typecheck, scoped ESLint and `git diff --check` passed
- contracts: none
- known limits: browser journey/heavy checks deferred; card DTO has no materiality field; historical catalog model route is not in the run DTO; historical fragment text may need a fresh evidence read
- integration notes: root mounts public exports and evidence callbacks; runtime supplies journal groups `{key,label,rows}`, exact `counts.project_changes` and other server counts; no remote authority
