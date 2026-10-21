# PROGRAM-GOVERNANCE-REPAIR-01 — historical task metadata addendum

**Frozen base:** `e61fc4570e49d0411b72e5363a2bafd5eeb5da97`.
**Date:** 2026-10-16. **Status:** docs-only governance correction; no
publication, W54 launch, real restore or beta verdict.

## Original findings and correction

The active governance test found ten task documents at the frozen base:

| Historical tasks | Base finding | Addendum |
| --- | --- | --- |
| `W54-CORPUS-OPERATE-01`, `W54-CORPUS-PROMOTION-01` | Premise date, command and substantive output absent | Captured the unchanged source reports on 2026-10-16 and explicitly labeled the evidence retrospective. Old resource values remain historical. |
| `W56A-INT-GENERATOR-01`, `W56A-INT-MATCHER-CORE-01`, `W56A-INT-MERGE-CORE-01`, `W56A-INT-SEAL-01` | Missing governed premise/history/publication sections and noncanonical `no` declaration | Added `premise: none` because those integration tasks recorded their frozen inputs and predecessor but no separate captured premise. Their existing dev-only publication grant is restated; `origin/main` remains unauthorized. |
| `W56A-MATCHER-CORE-PREP-01`, `W56A-MERGE-CORE-PREP-01` | Existing premise used an older heading without captured command/output; history/publication sections absent | Kept the original prose, dated a retrospective plan capture, and stated that the lane had no Git ref authority. |
| `W59-INT-DECISION-CARRYOVER-PREP-01`, `W59-INT-PROFILE-READINESS-GAP-01` | Missing explicit `premise`; second also lacked machine-readable output | Added one-sentence premise declarations and an exact frozen-tree file-list capture for the profile gap. No executable profile grant is inferred. |

Each amended task names this report as its addendum and points back to the
task document at the frozen base. Existing outcomes, dependencies, frozen
hashes, allowed paths, forbidden hotspots, checks and implementation reports
were preserved. The W54 promotion task remains incomplete because its dump
still needs restore verification; this correction changes no operational gate.

## Evidence

- Baseline `governed_task_findings()` identified exactly the ten paths above;
  their original findings were recorded before editing.
- The complete `tests/contract/program/test_wave_governance.py` run is
  **16 passed** on the amended tree, compared with **15 passed / 1 failed**
  on the frozen base. Direct `governed_task_findings()` returns `{}`.
- `git diff --check` and exact changed-path containment passed. An automated
  comparison of the original Outcome, Depends on, Frozen inputs/contracts,
  Allowed paths/publication prose, Forbidden hotspots, Non-goals, Deliverables,
  checks and integration sections found no changed lines in those sections.
- Contract files, migration head, source/runtime/tests, root locks,
  composition root and global styles were not changed. No ref or tag was
  pushed.

## Integration and limitations

The integrator may fast-forward this commit into the code-first branch after
verifying its exact base and twelve-file diff. The historical dev-only grants
do not authorize a new dev push by this task, and no historical task grants a
main deployment. New task authors must provide evidence at dispatch time;
retrospective capture here repairs traceability, not original timing.

Rollback is a revert of this docs-only commit. No feature flag or data
migration applies.
