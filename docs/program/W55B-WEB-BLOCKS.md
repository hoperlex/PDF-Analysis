# W55B-WEB-BLOCKS — report (the «Блоки» screen shows a portal bundle; the budget refusal shows its figures)

> **Living report.** Written while the lane runs, updated with every commit, so a restarted session resumes from
> `git log` and this file. Final form: the six items of `AGENTS.md` §5 (a later commit rewrites this file into them).

## 0. Status

- Lane: `W55B-WEB-BLOCKS` (plan `docs/program/dispatch/W55-PLAN.md` §B3.9, grant §B4 item 5). Branch `agent/w55b`, base
  `f94283d2` (the GEOMETRY report). Writer: one session; the wave executor verifies afterwards.
- Done: orientation (plan, seam, the four predecessor reports, the guards the grant names).
- Next: the entity (`entities/block`), the widget (`widgets/portal-blocks`), the two tabs on `/blocks`, the budget
  refusal's figures, the guard entries and the census screens, the tests with their mutation proofs, the live journey.

## 1. Decisions (each names the alternative rejected; each open to the integrator's veto)

1. **The re-audit control does not go through `classifyRunFailure`.** The brief expected it to; the tree says otherwise:
   `QueuePage` (`web/src/_pages/queue`) classifies a re-audit failure with `executionFailure` from
   `web/src/entities/execution/model/failure.ts`. One classification of the budget figures therefore lives in
   `entities/audit-run` (beside `classifyRunFailure`, which start-run uses), and `entities/execution` imports it through
   `@/entities/audit-run`'s public API (an entity reading another entity's public API has a precedent:
   `entities/user` imports `@/entities/account`). Both files are outside the grant and are flagged in the report.
   Rejected: two copies of the figure sentence (one per classifier), and a helper in `shared/api` (a frozen seam file
   outside the grant, for a sentence only two run classifiers print).
2. **The journey manifest has no route-level sentence.** The grant asks for the `not_produced` sentence in the `/blocks`
   entry of `tests/e2e/pc01/journey/manifest.json`. Measured: a route entry carries `name`, `path`, `page_module`,
   `expects_api`, `optional_api`, `follow`, `redirects_to` and `$comment`; `expects_rendered` exists only on write steps
   and refusal cases, which `test_pc01_journey_conformance.py` and the language guard read; nothing reads a sentence on a
   route, and a cold load of `/blocks` chooses no version, so the sentence cannot be on that screen. Recorded as a
   contradiction in the hand-back; what the `/blocks` entry gets instead is decided below when it is written.
