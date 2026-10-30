# BLOCK9-INT-1030 — honest incomplete specification diagnostics

task_id: BLOCK9-INT-1030

## Outcome

The specification screen shows a real source/cached-answer readiness failure before a new job, and an incomplete empty change list does not say there are no changes.

## Depends on

- BLOCK8-INT-1030

## Frozen inputs

- Base dev `c5cfc04e5e33a380b57741eccc13d9d3dd116912`, API1.14.0 /migration0044.
- Existing ComparisonSpecification incomplete/reason/optional coverage/totals and SPEC_NOT_PARSED/SPEC_SOURCE_INCOMPLETE/SPEC_ANSWER_UNCONFIRMED/SPEC_STORED_ANSWER_UNCONFIRMED codes.
- Owner continuous source-only/dev permission; root sole writer, owner deploys.

## Allowed paths

- `src/auditmanager/comparison/specification/service.py`
- `web/src/widgets/version-series/ui/specification-panel.tsx`
- `docs/program/**`

## Forbidden hotspots

Contracts/API/generated, routers/composition root, migrations, dependencies/locks, global styles, tests/fixtures, extraction/paid-runtime code and budgets, other paths, main/deployment. No tests/build/compile/import/lint/typecheck/runtime/browser/DB/model checks.

## Non-goals

No job, model, PDF rasterization, fake zero totals, automatic expert act, hidden retry, source reclassification or historical result rewrite. Unread but otherwise ready text remains not_started, not an extraction failure.

## Deliverables

Read-only free outcome can return an actual incomplete diagnostic for a known blocked source/cached answer, without creating a job/comparison row. It retains real coverage/IDs, omits absent totals rather than inventing zeros, and uses the existing closed fields. UI explains existing reasons in Russian and distinguishes absent confirmed result from a completed no-change comparison; refresh remains read-only.

## Required tests

- command: none, explicitly deferred by owner.
- expected: UNVERIFIED source candidate.

## Integration contract

Exact internal read projection/UI changes only, no frozen wire shape or paid-plan change. Normal clean dev publication/read-back with owner changes preserved. All acceptance deferred under D-290.

## Rollback / feature flag

Revert exact read/UI files; no stored data or consent mutated.

## Handoff

Changed paths, no-check status, unchanged contracts, readiness-vs-paid-extraction limitations, publication receipt.
