# W56A-PLAN-PATH-FIX-01 — category-label path correction

**Task:** `tasks/W56A-PLAN-PATH-FIX-01.md`. **Base:** `f47c129e6d08d509ad3d2288926244afe265468b`.

## 1. Result

The W56a plan's §A2 source map, §A4 SEAL/WEB grants and §A5 ownership table now identify
`web/src/entities/expert-decision/model/category-labels.ts` as the exhaustive
`FindingCategory` label map owned by SEAL. The knowledge-base page's category filter is a WEB
path at `web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx`; it consumes SEAL's map.
The WEB entity-family grant explicitly excludes the map, so there is one writer for it.

This corrects a moved source path in the current plan. It does not change the seven-category
design, SEAL/WEB sequence, frozen contracts, code or task status.

## 2. Checks and changed-path proof

The source query in the task file located the exhaustive map at line 20 and its page filter
consumer at lines 60 and 62 on the frozen base. The governance/prose command in the task file
passed: 93 tests. `git diff --check` passed; the post-commit exact changed-path proof is
reported to the integrator with this branch's SHA.

## 3. Freeze handoff and limits

`W56A-FREEZE-01` should grant SEAL the exact label-map file and exclude it from WEB's broad
`expert-decision/**` paths. WEB may change the page filter while consuming the map. The plan
correction is not a freeze or code grant. No gateway identity probe, database test or full gate
was run by this document-only task. Revert its commit if the plan must return to its prior
wording; no runtime rollback applies.

Only the plan and this task/report are in the changed-path proof. Contracts, migrations,
dependencies, composition roots, styles, source files and prior reports are untouched.
