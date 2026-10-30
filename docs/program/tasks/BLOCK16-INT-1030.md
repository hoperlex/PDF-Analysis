# BLOCK16-INT-1030 — exact preliminary source ranges

task_id: BLOCK16-INT-1030

## Outcome

Read-only saved-run comparison cannot pair identical wording bound to different positions of one page or different quoted evidence.

## Depends on

- BLOCK11-INT-1030
- BLOCK15-INT-1030

## Frozen inputs

- Dev `f6e19de7f1a547a23f138346c8c22c700f28dc14`, API1.14.0/migration0044.
- Saved preliminary sources expose real character_field/ranges/artifact/entry identity and optional source_evidence quotes.

## Allowed paths

- `web/src/widgets/stage-comparison/model/saved-results.ts`
- `web/src/widgets/stage-comparison/model/saved-results-report.ts`
- `web/src/widgets/stage-comparison/ui/saved-results.tsx`
- `docs/program/**`

## Forbidden hotspots

All backend/paid helpers, contracts/API/generated, routers/composition root, migrations, dependencies/locks, global styles, tests/fixtures, other paths, main/deployment. No tests/build/compile/import/lint/typecheck/runtime/browser/DB/model checks.

## Non-goals

No semantic pairing, new source extraction, model call, evidence/canonical/expert mutation or historical reconstruction.

## Deliverables

Source fingerprint retains actual immutable page/field/range/artifact/entry identity; malformed ranges/pages cannot enable exact pairing. Optional quote-level source_evidence is resolved through the actual source catalogue rather than run-local IDs and included as a full multiplicity-preserving exact key. Distinct ranges/quotes remain separate; unbound evidence is unpaired. UI/export limitations reflect strict range/quote matching; raw records and all existing reader/cancellation/limits remain.

## Required tests

- command: none, explicitly deferred by owner.
- expected: UNVERIFIED source candidate.

## Integration contract

Root owns exact local comparison slots, sole normal clean dev push/read-back with incoming changes preserved. No API/migration/paid authority change, owner deploys.

## Rollback / feature flag

Revert this read-only matcher change; stored results/decisions and source evidence remain unchanged.

## Handoff

Changed files, no-check status, unchanged contracts, strict matching limits and D-290.
