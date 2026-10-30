# BLOCK5-SAVED-RESULTS-1030

task_id: BLOCK5-SAVED-RESULTS-1030

## Outcome

The existing two-run comparison screen can explicitly read and compare actual saved findings and preliminary observations, beyond stage/count metadata, without new model calls.

## Depends on

- BLOCK4-INT-1030

## Frozen inputs

- Base dev `0dd8132806086044b9815842ef0cbf20eef34acc`.
- API1.14.0, 233 paths / 259 operations / 620 schemas; migration0043.
- Existing public listRunFindings/getRunStatus/getExtendedRunReview; existing two-run same-version screen.

## Allowed paths

- `web/src/widgets/stage-comparison/**`
- `docs/program/BLOCK5-SAVED-RESULTS-1030.md`

## Forbidden hotspots

Other lane paths, contracts, API/generated files, migrations, dependencies/locks, composition root, global styles, tests, fixtures, main/deployment. No tests/build/compile/import/lint/typecheck/runtime/browser/DB/model checks.

## Non-goals

No semantic matching claim, automatic fix verdict, expert decision/carryover, cross-version input change, new route/API, historical expert-verdict reconstruction.

## Deliverables

Root alone owns this independent exact widget slot. Public source reader traverses all findings cursor pages with identity, count, repeat-cursor/ID and resource guards; missing unpublished findings or unavailable preliminary data are explicit rather than zero. Pure model pairs durable finding IDs and exact source-bound preliminary wording, preserving multiplicity and all raw records. Same-version differences are differences of analysis, never proof of repaired document. Explicit user read action, progress/cancellation, paging and full JSON/CSV/HTML exports. Current expert state is labelled current; no atomic historical snapshot promise.

## Required tests

- command: none, explicitly deferred by owner.
- expected: UNVERIFIED source candidate.

## Integration contract

Existing widget only; no changes to entity public API or other UI lane. Root sole Git writer/dev publisher; preserve originals and all API authorization. Runtime global-cross-window work is independent and both can publish in BLOCK5.

## Rollback / feature flag

Feature performs explicit read only; revert the local widget integration without changing saved data or paid authority.

## Handoff

Changed paths, no-check status, unchanged contracts, resource/matching limits and publication via BLOCK5 root.
