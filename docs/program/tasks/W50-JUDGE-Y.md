# Task W50-JUDGE-Y — judge of the shell wave, architecture entry point

## Outcome

A report-only, author-independent verdict on the merged W50 candidate, from the architecture
and the guards.

## Depends on

- `W50-QA-01`

## Frozen inputs

- API contract: 27 paths / 34 operations / 77 schemas — frozen; W50 makes no contract change
- error catalog: 23 codes; domain candidate revision 9, 29 opaque identities — frozen
- migration head: `0015_accounts_roles_registration` — frozen
- code base: the commit that carries `docs/program/W50-FREEZE-01.md` on `integration/w50` (published to `origin/dev`); subject: the merged W50 candidate
  `<integration/w50 commit after W50-QA-01>` (named by the integrator in the dispatch message)
- controlling plan: `docs/program/dispatch/W50-PLAN.md` at the freeze commit, as amended by owner
  ruling `R-66` (Работа = Проекты, Дашборд, «Оптимизация разделов» `/section-optimisation`;
  Знания = База знаний, Блоки, «Нормы» `/norms`; Система = Журнал выполнения, Исполнители,
  «Настройки анализа» `/analysis-settings`, «Очередь» `/queue`; `/optimisation` in no menu
  group, registered `hidden` and reachable; the four stubs honest `RoutePlaceholder`s, access
  `session`, roles `any`)
- the lazy baseline: the `next build` route table recorded by `W50-FREEZE-01`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the dependency set and its lock are sealed at the W49 closure, and W50 may not move them

### P-01 — the lock bytes the subject must keep

- captured_at: 2026-10-06
- command: `git ls-tree ead639f web/package.json web/package-lock.json web/FRONTEND_LOCK.json`
- captured_output:
  ```text
  100644 blob 14fc4b48026640a195f8dd1e66a09a6ff7251666	web/FRONTEND_LOCK.json
  100644 blob 3b986e543b1be7fc654d94aee17963382f664143	web/package-lock.json
  100644 blob 3ea4aede04af84823821e115f8312c545faec30e	web/package.json
  ```
- interpretation: measured on `ead639f`; the freeze is documentation only, so the subject's blobs
  must be these three. The judge re-measures on the subject and reads only this task file and the
  subject SHA before its own pass.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/dispatch/W50-PLAN.md`
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/reviews/W50-JUDGE-Y.md`

## Forbidden hotspots

- every other tracked path, every ref, tag and deployment action

## Non-goals

- no repair, merge, ruling or register edit

## Deliverables

- architecture entry point:
  - FSD boundaries hold (`web/tests/guards/eslint-boundary.guard.test.ts`), and a deliberate
    upward import in a copy is red
  - the registry is the single source: `rg -n "href=" web/src/_app` shows no address outside it;
    the registry's addresses, the `page.tsx` set, `tests/e2e/pc01/journey/manifest.json` and the
    seeds of `web/tests/unit/screens/route-screens.ts` are one set, and each guard over them is red
    on a one-row drift
  - every `page.tsx` calls `requireScreen` with its own `params`/`searchParams`, and
    `requireAChangedPassword` no longer exists
  - no `fetch` outside `shared/api` (`transport-boundary.guard.test.ts`)
  - the eager seam renders every one of the five lazy widgets in the contrast census and the
    language guards; the census' screen and pair counts are not below the baseline
  - `globals.css` has a rule for every new class (`web/tests/unit/styles/styling-layer.test.ts`);
    the fourteen avatar pairs are complete in both themes and each clears its floors
  - no new dependency; `web/package.json`, `web/package-lock.json` and `web/FRONTEND_LOCK.json`
    byte-identical to P-01; `providers.tsx` unchanged; `contracts/**` unchanged
  - the `next build` route table did not regress against the freeze baseline, route by route
  - `AGENTS.md` §4 on the new code: no business logic in UI components beyond presentation, no
    silent fallback (an unknown role is a typed fault), no identity by display string (the avatar
    colour is keyed on the e-mail, not the label), no deep import into another slice
  - `R-66` in the code: the registry's groups, items and order; `/optimisation` registered
    `hidden` with `inMenu: false`; the four stubs registered `session`/`any` and rendered by
    `RoutePlaceholder`
  - every guard the wave added is shown able to fail; prose the wave touched in `docs/` and in
    comments states what the code now does
- findings (path, line, consequence, reproduction) classed release-blocking /
  must-fix-before-merge / register; mutation results; untested questions; verdict
- cross-examination with `W50-JUDGE-X` after both black-box passes, under `W48-JUDGES.md`

## Required tests

- every probe restored; final `git diff --name-only <subject>..HEAD` names only the report

## Integration contract

The integrator opens `W50-FIX` only for upheld release-blocking findings.

## Failure/idempotency/security cases

- lane `gate-w50jy`, worktree `.local/worktrees/w50-jy`: `FOUNDATION_INSTANCE=gate-w50jy`,
  `POSTGRES_PORT=56710`, `S3_API_PORT=60310`, `S3_CONSOLE_PORT=60311`, a lane-unique `POSTGRES_DB`
  and `S3_BUCKET`; each port checked free with `ss -ltn` before use and recorded; any further
  port checked free the same way and recorded
- one full `make gate` on the host at a time if the judge runs one; never edit the tree while a
  gate or `next build` measures it; never measure during a subagent fan-out
- owned disposable services only; `make down` and remove the lane's own volumes by exact name at
  the end
- never kill a process by pattern — only confirmed-own PIDs
- no credential, cookie value, session id or token in evidence

## Rollback / feature flag

Report-only; revert the report commit.

## Handoff

- changed files: listed in `docs/program/reviews/W50-JUDGE-Y.md` with
  `git diff --name-only <subject>..<sha>`
- commands/results: verbatim with exit status; every mutation with its red output
- known limits: listed, never decided silently
- integration notes: hand back branch `agent/w50-judge-y` at a recorded SHA
