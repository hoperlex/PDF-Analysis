# W52-DEBT-GUARDS-128F1 — executor handoff

Task: `docs/program/tasks/W52-DEBT-GUARDS-128F1.md`. Exact code base:
`3bf74d37f8538a2969a838fc270d1e3a4bb575c1`; dispatch commit `7060945`.
This repairs D-128 F-1 only.

The D-97 guard now walks `tests/unit/screens` as well as guards and styles, while
excluding `harness.ts`, which owns the provider implementations. Its import check accepts
the local `./harness` path. A probe for a new private provider in a unit screen is red
under the guard's classification, and the discovery assertion requires at least five
unit-screen consumers. Five tracked files now use `renderScreen` instead of private
router copies. The language guard seeds registration requests on the same client it
passes to `renderScreen`, removing its private query provider.

Changed files: `web/tests/guards/screen-set.guard.test.ts`,
`web/tests/guards/rendered-language.guard.test.ts`,
`web/tests/unit/screens/cold-load.test.ts`,
`web/tests/unit/screens/forms-and-pages.test.ts`,
`web/tests/unit/screens/stage-comparison.test.ts`,
`web/tests/unit/screens/run-cache-shape.test.ts`,
`web/tests/unit/screens/project-sections.test.ts`, and this report. The shared
`harness.ts` was read but not changed.

Basic checks: focused D-97 and five screen files passed **89/89** tests. The language
guard's screen-reachability assertion passed; the complete language guard passed
**23/24** tests. Its one red branch-coverage assertion names the same 17 branches on
both the original `3bf74d3` base and this tree; it predates this task and is recorded
in `CURRENT_STATE.md`. Frontend lint and `git diff --check` passed. No temporary stand,
QA or full gate was run under D-139/D-140.

No runtime code, wire contract, migration, dependency/lock, composition root or global
style changed. D-128 remains open for F-10 and validation. The integrator may merge
this clean test correction to `origin/dev` after exact ancestry and basic checks.
Rollback is the test commit's revert; no feature flag.
