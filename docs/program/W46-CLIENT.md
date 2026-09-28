# W46-CLIENT — session log

`task_id`: `W46-CLIENT` · wave 46, sub-stage C · lane `gate-w46b` · worktree `/root/w46dash` ·
branch `agent/w46-client`, based on `dbba753`.

Opened before the first measurement, per the brief's discipline clause. Committed after each
step; entries are appended, not rewritten, once the step they describe is done.

Read: `docs/program/dispatch/W46-CLIENT.md`, `docs/program/dispatch/W46-STAGE-C.md`,
`docs/program/reviews/W46-JUDGE-X.md` (`git show agent/w46-judge-x:…`, findings X-3, X-6,
X-9, and the cross-examination of Y), `docs/program/reviews/W46-JUDGE-Y.md`
(`git show agent/w46-judge-y:…`, sections 2, 5, 6). `AGENTS.md` read in full.

## Coordinator narrowing, received mid-task

1. C1, the run-state panel: `by_state` carrying only some states (e.g. `published: 2`)
   currently hides the rest rather than showing a fault (`?? 0` feeds a `> 0` filter); the
   panel invents zeros only when the whole array is empty. And unknown members
   (`escalated`, `ZZ`) vanish silently. Both are faults under the same rule: an omitted or
   unknown member is a visible fault, whatever the shape of the omission. The completeness
   check below covers both facets by construction (closed-set membership, not "any row
   present").
2. C4/Y2-a: the contradiction predates wave 46 — one profile, `DISCIPLINE = "AR"`, nothing
   in runs/analysis reads `.section`. The «правило приёма» sentences came in `9bb9385`
   (09-22). Repair is sentences only, matching this brief: the analysis is built for АР
   and applied to any uploaded document; a stated section is stored and counted, but
   neither selects nor refuses the analysis. No behaviour change. `startRun` refusing by
   section is the owner's call (`D-110`).

## Plan

1. **C1** — `section-breakdown.ts`, `verdict-breakdown.ts` and a new
   `run-state-breakdown.ts` stop filling an omitted member with `0` and stop silently
   dropping an unknown one: each returns `{ ok: false }` over a response that does not
   carry exactly its closed vocabulary, once each, no more no less. The three panels
   render the failure shape `dashboard-failure.ts` already has instead of any number when
   that happens. Driven under three mutations (omitted row, unknown row, and X's partial
   `by_state`), shown failing without the fix and passing with it.
2. **C2** — per-row keyed assertions in `dashboard.test.ts`, reading each row by its own
   `data-section`/`data-verdict`/`data-run-state` attribute rather than `toContain`
   anywhere on the page. Y's M5 (neighbour-shifted section counts) and M6
   (accepted/rejected swapped) shown failing under the new assertions, plus one of my own
   (published/failed swapped in the run-state panel), then reverted.
3. **C3** — `use-create-project.ts` invalidates `queryKeys.dashboard.summary()` on success.
   A new guard enumerates every mutation hook under `web/src/features/**` and asserts
   whether it invalidates the dashboard key, failing on a hook the map does not name and
   on a mapped hook whose invalidation cannot be found. Shown failing with
   `create-project`'s new line removed.
4. **C4** — `sections-panel.tsx`, `project-sections.tsx` (Y2-a): the sentences say the
   analysis is built for the text of АР documents and applied to any uploaded document
   regardless of its stored section, never that intake refuses or restricts by section.
   `verdicts-panel.tsx` (Y2-b): the caption's «ожидает решения» becomes «не решено», the
   row's own label. `run-activity-panel.tsx`, `dashboard.test.ts`,
   `rendered-language.guard.test.ts` (X-9): the four comments saying the generated client
   "still types `spend` required today" are corrected — it is optional now.
5. **C5** — drive `npm --prefix web run e2e:pc01` against API `127.0.0.1:56381` and Next
   `127.0.0.1:56383`, quote the summary.
6. Verification: `npm --prefix web test`, `npm --prefix web run typecheck` during
   development; one final `make gate > /root/w46c-gate.log 2>&1`, verdict from `GATE OK`.

## Log

