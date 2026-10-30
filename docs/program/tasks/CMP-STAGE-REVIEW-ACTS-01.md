# Task CMP-STAGE-REVIEW-ACTS-01 — expert review promotion and explicit card metadata

## Outcome
An expert can promote a service card or a masked text fragment into a recorded REVIEW card with a required reason. The review page groups cards by actual detail/materiality metadata and displays actual importance, without inferred facts.

## Depends on
- CMP-STAGE-PAGE-01
- CMP-STAGE-REVIEW-UI-01
- CMP-SEAL-C4

## Frozen inputs
- domain: ADR-0025, roadmap §1.2, root's R3-02 expert-act and explicit metadata followups
- API: root-generated `createStageReviewCard` and optional materiality/importance/detail fields, provider `703661f4`, client lock `80b6b9e3`
- whole-card source bound: root confirmed seal/runtime amendment `725fbbc5` accepts up to 400 sources without truncation
- migration: `0042_comparison_stage_review`
- base commit: `bef3b4f8` (root additionally owns provider/runtime merges)

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: root explicitly granted stage-changes, map/text-evidence and page callbacks for the additive expert act after the mounting commit; no shared seal edit belongs to this lane.

## Historical evidence
- correction_mode: addendum
- source_record: `CMP-STAGE-REVIEW-UI-01.md` (then lacked explicit card metadata)
- addendum_path: `CMP-STAGE-REVIEW-ACTS-01.md`

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `web/src/widgets/stage-changes/**`
- `web/src/widgets/stage-text-evidence/**`
- `web/src/widgets/stage-sheet-map/**`
- `web/src/_pages/stage-compare/**`
- matching scoped `web/tests/unit/{stage-changes,stage-text-evidence,stage-sheet-map,stage-compare}/**`
- this task, `docs/program/CMP-STAGE-REVIEW-ACTS-01.md`, ignored `web/node_modules` symlink

## Forbidden hotspots
- generated clients/contracts, root runtime/composition/polling, migrations, dependency locks, global styles, shared viewer, journey/exposure (transferred to seal agent), remote refs

## Non-goals
- no raw-evidence rewrite, expert verdict fabricated from AI, or guessed materiality/importance
- no browser/build/gate/heavy window or remote publication

## Deliverables
- keyed reason-required expert promotion on service cards and masked fragments, followed by the actual returned REVIEW card
- actual metadata sections/importance/unknown counts; fix partial-carryover wording and synthesis evidence source binding
- focused tests/typecheck and local commit

## Required tests
- focused Vitest, web typecheck, scoped ESLint and diff-check only

## Integration contract
Use generated clients only. Promotion sends canonical atomic source IDs and reason; retries retain a key. Root backend creates/audits the immutable REVIEW aggregate, and UI invalidates card/journal reads and selects its real run/card. Root owns runtime and publication.

## Failure/idempotency/security cases
- nonexpert/stale/dirty/historical mutation controls stay disabled or hidden
- empty reason sends no request; uncertain response keeps the intent key
- service/raw source rows remain unchanged; rejected requests show typed failure
- absent old metadata means unknown, never a new classification fact

## Rollback / feature flag
Existing stage module gate applies. Remove new controls/groups to restore prior UI; recorded expert cards remain server-owned.

## Handoff
- files: owned stage-changes, text-evidence request/panel, map/page callbacks and scoped tests plus this task/report
- checks: 42 focused Vitest passed; web typecheck, scoped ESLint and diff-check clean; final card-label change rechecked on its focused screen
- limits: browser execution deferred; root integrates the exact 400-source provider/runtime amendment `725fbbc5`
- contracts: none; root's sealed provider is consumed
- integration: local commit only; journey/exposure ownership stays with seal agent
