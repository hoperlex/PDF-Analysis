# Task CMP-PRESENTATION-1030 — runnable seven-minute comparison presentation

## Outcome
A presenter can demonstrate the two existing comparison modules in 5–7 minutes on an already prepared local synthetic stand, using exact committed fixtures, flags, screen controls and honest recorded/synthetic provenance labels.

## Depends on
- CMP-STAGE-REVIEW-ACTS-01
- CMP-JOURNEY-C4-01

## Frozen inputs
- source snapshot: integration worktree `.local/worktrees/cmp-int`, root `01d76dff` (2026-10-30)
- fixture keys: `cmp-vs1-answer-key/1`, `cmp-sp1-answer-key/1`
- existing journey README, manifest, C4 fixture/worker helpers and actual mounted UI
- API `1.13.0` / migration `0043_stage_ai_generations`; no changes to the frozen contracts
- owner permits a presentation scenario, no browser/model/deployment/heavy execution in this task

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the current root contains both mounted comparison modules and the explicit synthetic C4 helper; the presentation must distinguish synthetic response generation from model recordings.

### P-01 — source snapshot and existing helper
- captured_at: 2026-10-30
- command: `git -C .local/worktrees/cmp-int log -1 --oneline`
- captured_output:
  ```text
  01d76dff merge: validate every PDF page in bounded background source preparation
  ```
- interpretation: source-level presentation plan only; no deployment or browser acceptance follows from the commit.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `docs/program/tasks/CMP-PRESENTATION-1030.md`
- `docs/program/CMP-PRESENTATION-1030.md`

## Forbidden hotspots
All application source, fixtures/helpers/journey code, contracts, migrations, bootstrap, dependencies, refs and stacks are read-only. No browser, external deployment, model calls, full gates or new seeder.

## Non-goals
No acceptance claim, benchmark, screenshot fabrication, new runtime/helper, state mutation or broad audit.

## Deliverables
One concise Russian presentation runbook: fixture paths/flags, pre-show preparation via existing helpers, timed screen actions/results, exact limitations and provenance phrasing. Concrete source blockers are relayed immediately to root.

## Required tests
Read the named controls/helper signatures from current source; verify every local path in the runbook exists; `git diff --check`. No runtime checks.

## Integration contract
Docs-only cherry-pick from this lane after `66460f0f`. Root owns candidate publication, local demo preparation and any runtime follow-up. No shared wiring or contract changes.

## Rollback / feature flag
Revert the two docs; no runtime behavior changes.

## Handoff
- report: `docs/program/CMP-PRESENTATION-1030.md`
- verified read-only: 16 source links, 16 exact UI labels, 3 existing helper CLI options; diff whitespace check
- contracts/application/fixtures/stack/browser/model/remote mutations: none
- source limitation relayed to root and accepted: no ready C2 recorded worker, so runnable VS-1 portion is deterministic; stage helper supplies only explicitly synthetic C4 replies
- integration: cherry-pick the final docs commit; candidate preparation remains root/operator owned
