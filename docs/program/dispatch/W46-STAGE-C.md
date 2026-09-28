# Wave 46, sub-stage C: what both cross-judges found, repaired before the final gate

Written 2026-09-29 by the integrator, `pdf-analysis-0c [548707]` (the same conversation as
`pdf-analysis-4f [73faf8]`, resumed). Inputs: `docs/program/reviews/W46-JUDGE-X.md`
(`agent/w46-judge-x`) and `docs/program/reviews/W46-JUDGE-Y.md` (`agent/w46-judge-y`), both
judging `d5c9be5`. X ran the full gate on that tip and got `GATE OK` (battery 2504, frontend
1118 in 79 files).

**The two judges worked independently and converged three times.** On defects two independent
judges each found, the repair does not wait for the cross-examination:

| defect | X | Y |
|---|---|---|
| the screen fills an omitted row with `0` and drops an unknown value, `F-1`'s shape on the client | X-3 | Y5-a |
| creating a project leaves the dashboard stale for up to 30 s | X-6 | Y6-a |
| the guards prove "nothing invented", not "each number in its place" or "each number computed" | X-2 (server) | Y5 M5/M6 (screen) |

The integrator's own findings (X-8, X-5, X-10) were repaired in `ce25e14`.

## Two streams, in parallel

| stream | lane | worktree / branch | owns |
|---|---|---|---|
| `W46-CLIENT` | `gate-w46b` | `/root/w46dash` · `agent/w46-client` | X-3/Y5-a, X-6/Y6-a, Y5 M5/M6, Y2-a, Y2-b, X-9 |
| `W46-GUARD` | `gate-w46a` | `/root/w46seal` · `agent/w46-guard` | X-1, X-2, X-4, X-7, X-11 (a description-only reseal) |

`W46-GUARD`'s reseal changes a **description**, not a shape: `spend` gains the sentence saying
what its absence means. The generated types do not change their shape, so the two streams do not
couple. The integrator merges `W46-GUARD` first and runs typecheck on the join.

## Then one judge, then the final gate

`W46-JUDGE-Z` closes sub-stage C on `gate-w46j`, alone: the cross-judging this wave owes has
already happened (X and Y, each ruling on the other). Z re-takes both judges' reproductions
against the repair and goes off the trail. Then the integrator runs the final `make gate` and tags
`alpha-w46` **locally**. A push waits for the owner.

## To the register, not to this stage

| row | finding | why not here |
|---|---|---|
| `D-110` | the analysis is tuned to АР, but a document stored as `KM` is analysed with the same profile, and nothing at intake or run start looks at the section (Y2-a) | whether intake refuses, a run skips, or a profile per section exists is the owner's; `W46-CLIENT` makes the sentences true |
| `D-111` | `documents_by_project` is unbounded: 63 rows and 6906 px, where the old panel showed 50 and said so | a paging or a cap is a contract question |
| `D-112` | a 200-character project name overflows `/dashboard` and `/projects` | pre-existing and product-wide |
| `D-109` addendum | the dashboard's failure state says *операция*, *адаптер*, *транспорт исполнителя* through the shared catalog | the owner's line, as before |
