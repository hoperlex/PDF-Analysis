# Task W50-LAZY-01 — lazy loading of the five heavy widgets without blinding the instruments

## Outcome

`widgets/evidence-viewer`, `widgets/stage-comparison`, `widgets/run-progress`,
`widgets/knowledge-base` and `widgets/dashboard` load through `next/dynamic` with a typed loading
state; the `next build` route table shows no measured route's first-load JS got worse; the screen
harness, the contrast census and the language guards still render every one of those widgets
eagerly through one seam, and a guard holds the census' screen and pair counts at or above the
baseline. `CATEGORY_LABELS` lives in the `expert-decision` entity, no `_pages/**` module imports a
lazy widget statically, and the false sentence about accounts and roles on `/projects` is gone.

## Depends on

- `W50-REGISTRY-01` merged into `integration/w50` (Stage A); runs in parallel with
  `W50-SHELL-UI` and `W50-HOME-01` on disjoint paths

## Frozen inputs

- API contract: 27 paths / 34 operations / 77 schemas — frozen; W50 makes no contract change
- error catalog: 23 codes; domain candidate revision 9, 29 opaque identities — frozen
- migration head: `0015_accounts_roles_registration` — frozen
- code base: the commit that carries `docs/program/W50-FREEZE-01.md` on `integration/w50` (published to `origin/dev`); lane base:
  `<integration/w50 commit merging W50-REGISTRY-01>` (named by the integrator in the dispatch message)
- controlling plan: `docs/program/dispatch/W50-PLAN.md` at the freeze commit, as amended by owner
  ruling `R-66`
- the lazy baseline: the `next build` route table recorded by `W50-FREEZE-01` (first-load JS per
  route); the lane also records the table at its own base, because `W50-REGISTRY-01` adds six
  routes the freeze table does not have
- dependency set: `next` 15.5.25 as pinned; `next/dynamic` is part of it — no new dependency

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: five `_pages` modules import the five heavy widgets statically, and `_pages/knowledge-base` also imports `CATEGORY_LABELS` from its widget

### P-01 — the static imports this task replaces

- captured_at: 2026-10-06
- command: `git grep -n -E "from '@/widgets/(evidence-viewer|stage-comparison|run-progress|knowledge-base|dashboard)'" ead639f -- web/src/_pages`
- captured_output:
  ```text
  ead639f:web/src/_pages/dashboard/ui/dashboard-page.tsx:18:import { Dashboard } from '@/widgets/dashboard';
  ead639f:web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx:31:import { CATEGORY_LABELS, KnowledgeBase } from '@/widgets/knowledge-base';
  ead639f:web/src/_pages/review/ui/review-page.tsx:49:import { EvidenceViewer } from '@/widgets/evidence-viewer';
  ead639f:web/src/_pages/run/ui/run-page.tsx:15:import { RunProgress } from '@/widgets/run-progress';
  ead639f:web/src/_pages/stage-comparison/ui/stage-comparison-page.tsx:37:import { StageComparison } from '@/widgets/stage-comparison';
  ```
- interpretation: measured on `ead639f`; `W50-REGISTRY-01` does not touch these modules, so the
  lane re-measures the same five lines at its base. The new guard must be red on each of them.

### P-02 — the label map and the sentence that move

- captured_at: 2026-10-06
- command: `git grep -n -E 'CATEGORY_LABELS|Ролей и разделения' ead639f -- web/src`
- captured_output:
  ```text
  ead639f:web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx:31:import { CATEGORY_LABELS, KnowledgeBase } from '@/widgets/knowledge-base';
  ead639f:web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx:60:  ...CATEGORY_LABELS,
  ead639f:web/src/_pages/projects/ui/projects-page.tsx:18:      subtitle="Одна учётная запись на эту установку. Ролей и разделения на организации пока нет."
  ead639f:web/src/widgets/knowledge-base/index.ts:4:export { CATEGORY_LABELS, KnowledgeBase } from './ui/knowledge-base';
  ead639f:web/src/widgets/knowledge-base/ui/knowledge-base.tsx:49:export const CATEGORY_LABELS: Readonly<Record<FindingCategory, string>> = {
  ead639f:web/src/widgets/knowledge-base/ui/knowledge-base.tsx:121:              <span className="am-kb__category">{CATEGORY_LABELS[record.category]}</span>
  ```
- interpretation: the plan quotes the sentence as «Одна учётная запись… Ролей нет»; the exact
  subtitle is the line above, and it is false since W49 (accounts and a role set exist). No test
  pins it.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/dispatch/W50-PLAN.md`
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

From `W50-PLAN.md` §4 Stage B, `LAZY allowed paths`, verbatim:

- `web/src/_pages/**` except `home`, `sign-in`, `account`, `forbidden`
- the `loading.tsx` files REGISTRY created (`web/src/app/projects/loading.tsx`,
  `web/src/app/projects/[project_uid]/loading.tsx`, `web/src/app/dashboard/loading.tsx`,
  `web/src/app/knowledge-base/loading.tsx` — the lane confirms the four paths at its base)
- `web/src/widgets/knowledge-base/**` and `web/src/entities/expert-decision/**` (only to move
  `CATEGORY_LABELS`)
- `web/tests/unit/screens/cold-load.test.ts`, `web/tests/unit/screens/harness.ts` (the eager seam)
- `web/tests/guards/lazy-boundary.guard.test.ts` (new)
- `docs/program/W50-LAZY-01.md`

## Forbidden hotspots

- every path not listed above; `contracts/**`; `web/src/shared/**`; `web/src/app/**` except the
  four `loading.tsx` bodies (no `page.tsx`, no `layout.tsx`, no `globals.css`); `web/src/_app/**`
  (including the composition root `providers.tsx`); `web/src/_pages/home/**`,
  `web/src/_pages/sign-in/**`, `web/src/_pages/account/**`, `web/src/_pages/forbidden/**`;
  `web/src/widgets/**` other than `knowledge-base`; the five widgets' internals (they are wrapped,
  not rewritten); `web/tests/unit/styles/**` (`W50-SHELL-UI`'s this stage);
  `web/tests/guards/rendered-language.guard.test.ts`; `web/tests/unit/screens/route-screens.ts`;
  `next.config.mjs`, `web/vitest.config.ts`; migrations; `src/**`; root locks, `web/package.json`,
  `web/package-lock.json`, `web/FRONTEND_LOCK.json`; refs, tags, deployment and secrets;
  `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`

## Non-goals

- no change to what any widget renders or requests; no new API call on any route (the live
  journey's `expects_api` must not move because of this task)
- no `admin` `loading.tsx` (W51's); no home, sign-in, account or forbidden page change
- no new dependency, no bundler configuration

## Deliverables

- `W50-PLAN.md` §3.4: each of the five widgets is reached from `_pages/**` only through a lazy
  wrapper (`next/dynamic`) whose `loading` renders a typed state from `shared/ui/states`; the four
  `loading.tsx` bodies render the typed state of their segment
- one eager seam through which the screen harness (`web/tests/unit/screens/harness.ts`,
  `renderToStaticMarkup`) — and every instrument that renders through it: the contrast census and
  the language guards — renders the eager widget, for example each lazy wrapper module also
  exporting the eager component and the harness resolving it; the seam lives in `harness.ts` and
  the wrappers, and no production render path takes the eager branch. Note on the plan's example:
  a wrapper module that also exports the eager component holds a static import of the widget; if
  that module sits under `_pages/**` it contradicts guard (a) below and may keep the widget in the
  page's chunk. The lane picks a seam that keeps both checks honest (for example, `harness.ts`
  imports the five eager widgets itself and supplies them through a seam the wrappers read), says
  which in the report, and lets the route table prove the split
- `CATEGORY_LABELS` moved to `entities/expert-decision` (exported from its public `index.ts`);
  `widgets/knowledge-base` and `_pages/knowledge-base` import it from there; no `_pages/**`
  module keeps a static import of a lazy widget
- the `_pages/projects` subtitle «Одна учётная запись на эту установку. Ролей и разделения на
  организации пока нет.» removed (no replacement claim about accounts or roles)
- `web/tests/guards/lazy-boundary.guard.test.ts`: (a) no `_pages/**` module imports any of the
  five widgets statically (read by an import walk, not a text grep of one spelling); (b) the
  census' screen count and measured pair count are at or above the baseline literal measured at
  the lane base, with the command that produced it written beside the literal; (c) every one of
  the five widgets appears eagerly in the census markup
- the report `docs/program/W50-LAZY-01.md` with the six items of `AGENTS.md` §5 and the
  `next build` route table before (the lane base, and the freeze table quoted) and after, per
  route, first-load JS, with the command

## Required tests

- mutations, each red with its output in the report:
  - a static import of a lazy widget in `_pages/**` is red (one per widget, or one shown and the
    walk's coverage of the five asserted)
  - a census screen or pair count lower than the baseline is red (disable the seam: the census
    loses the widgets and the guard is red)
  - a lazy wrapper whose `loading` renders a raw string or English is red (language guards)
- the route table before and after in the report; any measured route whose first-load JS grows is
  a stop (`W50-PLAN.md` §7), not a note
- `npm --prefix web test -- --run`; `npm --prefix web run lint -- --quiet`;
  `npm --prefix web run typecheck`; `npm --prefix web run build`
- the live journey on the lane stand (`npm --prefix web run e2e:pc01 -- --phase all`): no route's
  observed API calls change versus the lane base; summary quoted verbatim
- `git diff --check`; `make gate` with the literal `GATE OK` on the task's head

## Integration contract

The five widgets keep their public APIs; `_pages` reach them through lazy wrappers; the harness
seam makes every instrument that renders through `harness.ts` see the eager widget;
`CATEGORY_LABELS` is imported from `@/entities/expert-decision`. `W50-SHELL-FRAME` and the
judges rely on the census counts never falling below the guard's baseline.

## Failure/idempotency/security cases

- lane `gate-w50lazy`, worktree `.local/worktrees/w50-lazy`: `FOUNDATION_INSTANCE=gate-w50lazy`,
  `POSTGRES_PORT=56670`, `S3_API_PORT=60270`, `S3_CONSOLE_PORT=60271`, a lane-unique `POSTGRES_DB`
  and `S3_BUCKET`; each port checked free with `ss -ltn` before use and recorded; any further port
  the stand needs (API, health, `next start`) checked free the same way and recorded; provisioned
  with `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` and `npm --prefix web ci`; the real
  corpus attached read-only before `make gate`
- one full `make gate` on the host at a time — three Stage-B lanes run in parallel, so each asks
  the integrator for its gate slot; never edit the tree while its gate runs; `next build` is not
  run while the lane's own gate measures the tree
- owned disposable services only; `make down` and remove the lane's own volumes by exact name at
  the end
- never kill a process by pattern — only confirmed-own PIDs
- no credential, cookie or session id in evidence
- if the seam cannot take effect through `harness.ts` and the wrappers alone — so that
  `web/tests/unit/styles/screens.ts`, `rendered-language.guard.test.ts` or `vitest.config.ts`
  would have to change — stop and ask; a census that silently renders only loading states is the
  `D-88` defect
- a `try/catch` around a render is never the seam

## Rollback / feature flag

Revert the commits; the widgets load statically again. No flag, no stored data.

## Handoff

- changed files: listed in `docs/program/W50-LAZY-01.md` with `git diff --name-only <base>..<sha>`
  and `git status --porcelain -uall` empty
- commands/results: verbatim with exit status; every mutation with its red output; both route
  tables
- known limits: listed, never decided silently
- integration notes: hand back branch `agent/w50-lazy-01` at a recorded SHA
