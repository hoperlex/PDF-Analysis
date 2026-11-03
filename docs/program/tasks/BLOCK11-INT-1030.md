# BLOCK11-INT-1030 — exact saved finding correspondence

task_id: BLOCK11-INT-1030

## Outcome

Saved same-version run comparison can pair identical grounded finding content despite fresh per-run finding IDs, with explicit correspondence basis and separate expert-state differences.

## Depends on

- BLOCK5-SAVED-RESULTS-1030
- BLOCK10-INT-1030

## Frozen inputs

- Dev `82b472ddf9a21225b3e62e379ab0f89cd7d0f17d`, API1.14.0/migration0044.
- Findings publication allocates a fresh finding_uid per run; immutable same-version source and existing public Evidence/merged observations are the only correspondence inputs.
- Existing complete saved reader, explicit read action, terminal guards and64MiB export limit.

## Allowed paths

- `web/src/widgets/stage-comparison/api/read-saved-results.ts`
- `web/src/widgets/stage-comparison/model/saved-results.ts`
- `web/src/widgets/stage-comparison/model/saved-results-report.ts`
- `web/src/widgets/stage-comparison/ui/saved-results.tsx`
- `docs/program/**`

## Forbidden hotspots

Contracts/API/generated files, canonical finding publication/identity, migrations, dependencies/locks, composition root, global styles, tests/fixtures, all other source paths, main/deployment. No tests/build/compile/import/lint/typecheck/runtime/browser/DB/model checks.

## Non-goals

No semantic matching, finding identity merge/carryover, expert-decision writes, historical verdict reconstruction, cross-version repair claims or source revalidation by this coding session.

## Deliverables

Durable UID correspondence takes priority. Unmatched findings may pair one-to-one only on exact category/text/recommendation/value and complete nonempty source-anchor sets, including every merged observation, bound to the same project/version. Invalid/unbound records remain unpaired. Display and JSON/CSV/HTML retain original IDs, all raw records, explicit basis and separate current expert-state differences. Reader validates all observation run identities, not just finding headers. Source-only documentation and publication receipt.

## Required tests

- command: none, explicitly deferred by owner.
- expected: UNVERIFIED source candidate.

## Integration contract

Root owns these slots and sole Git publication to origin/dev, preserving fresh incoming changes with clean normal fast-forward push/read-back. No domain/API/migration or paid-authority change. Owner deploys.

## Rollback / feature flag

Revert this local read-only comparison block; saved findings, expert decisions and model authority remain untouched.

## Handoff

Changed paths, no-check status, unchanged contracts, strict matching limits and D-290.
