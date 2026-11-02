# Task REVIEW-FIX-INT-1102 — integrate the review-fix wave and publish it to origin/dev

## Outcome
The six fix tasks of the 2026-11-02 code review are committed on `integration/review-fix-1102`
and the exact integrated tip is fast-forwarded to `origin/dev`.

## Depends on
- REVIEW-FIX-BOUNDS-1102
- REVIEW-FIX-SEAMS-1102
- REVIEW-FIX-ANALYSIS-1102
- REVIEW-FIX-CMP-RUNTIME-1102
- REVIEW-FIX-CMP-SPEC-1102
- REVIEW-FIX-TESTS-1102

## Frozen inputs
- domain contract: as left by the fix tasks
- API contract: 1.14.0
- analysis/comparison/event contract: unchanged
- migration head: as left by REVIEW-FIX-CMP-SPEC-1102
- base commit: `4ab295607806d030cf8066c2f21ab1cac45003e1` (`origin/dev` read by `git ls-remote` on 2026-11-02)
- owner instructions, 2026-11-02 (direct poll): run P0 and P1 of `.local/reports/code-review-2026-11-02.md`; publish to `origin/dev`; `origin/main` only on a separate instruction; mandatory checks may be skipped for the fixes

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the remote refs at dispatch

### P-01 — remote dev and main
- captured_at: 2026-11-02
- command: `git ls-remote origin refs/heads/dev refs/heads/main`
- captured_output:
  ```text
  4ab295607806d030cf8066c2f21ab1cac45003e1	refs/heads/dev
  158a815efbac29147c0396b09c91c4c4956e645e	refs/heads/main
  ```
- interpretation: the wave starts from the published dev tip; main is not a target.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `docs/program/tasks/REVIEW-FIX-BOUNDS-1102.md`
- `docs/program/tasks/REVIEW-FIX-SEAMS-1102.md`
- `docs/program/tasks/REVIEW-FIX-ANALYSIS-1102.md`
- `docs/program/tasks/REVIEW-FIX-CMP-RUNTIME-1102.md`
- `docs/program/tasks/REVIEW-FIX-CMP-SPEC-1102.md`
- `docs/program/tasks/REVIEW-FIX-TESTS-1102.md`
- `docs/program/tasks/REVIEW-FIX-INT-1102.md`
- `docs/program/REVIEW-FIX-INT-1102.md`

## Forbidden hotspots
- `origin/main`; force-push; any path a fix task owns

## Non-goals
- Documentation drift (P3) and interface/accessibility fixes (P2) of the review.

## Deliverables
- One commit per fix task with exactly its changed allowed paths; the integration record `docs/program/REVIEW-FIX-INT-1102.md` listing each task's commit, what was and was not done, and the checks that were or were not run.
- Fast-forward of the exact clean tip to `origin/dev`, read back with `git ls-remote`.

## Verification
- Optional per owner instruction; the integrator records which proof checks it ran.

## Integration contract
- Lanes never run git; the integrator commits each lane's paths after its hand-back.

## Rollback / feature flag
- Each fix task is one commit and reverts alone.
