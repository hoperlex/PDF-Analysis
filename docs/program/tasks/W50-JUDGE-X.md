# Task W50-JUDGE-X — judge of the shell wave, attacker and user entry point

## Outcome

A report-only, author-independent verdict on the merged W50 candidate, from a black-box pass
against a built stand.

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

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: before W50 the sign-in landing is a constant, so `next` is a new redirect input this wave adds

### P-01 — the sign-in landing at the W49 closure

- captured_at: 2026-10-06
- command: `git grep -n "AFTER_SIGN_IN" ead639f -- web/src`
- captured_output:
  ```text
  ead639f:web/src/app/bff/v1/[...path]/route.ts:227:const AFTER_SIGN_IN = '/projects';
  ead639f:web/src/app/bff/v1/[...path]/route.ts:706:    account.isDefaultCredential ? CHANGE_PASSWORD_SCREEN : AFTER_SIGN_IN,
  ```
- interpretation: measured on `ead639f`, before the wave; the judge measures the subject itself.
  The judge reads only this task file and the subject SHA before its own pass.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/dispatch/W50-PLAN.md`
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/reviews/W50-JUDGE-X.md`

## Forbidden hotspots

- every other tracked path, every ref, tag and deployment action; the public alpha stand is never
  driven

## Non-goals

- no repair, merge, ruling or register edit

## Deliverables

- black-box pass in a stand built from the subject (`npm --prefix web run build` and `next start`,
  not `next dev`; the subject's API under the worktree venv; a disposable database and bucket):
  - open-redirect attempts through `next` and `from`: `//host`, `/\host`, schemes, encoded
    slashes and backslashes, over-length values, unregistered paths, CR/LF, a valid path with a
    hostile query, through the guard's redirect, the sign-in form's hidden field and the BFF's
    after-sign-in redirect, with and without a session; whether an invalid value is ever echoed
  - direct navigation to each role-gated address with the other role (measure the registry's
    role-gated set first and report it), and to every registered address as a guest, on a default
    credential and with an incomplete profile: every answer a redirect to where `W50-PLAN.md`
    §3.2 says, never a rendered screen, a framework error or a cycle
  - default-credential and incomplete-profile bypass attempts: typed addresses, `next` pointing
    past the lock, prefetch, the BFF directly, a stale cookie after a password change
  - keyboard-only operation of the whole shell: every navigation group, the stacked «Меню»
    state, the account menu (arrows, Home/End, Escape, Tab, focus return), sign-out by keyboard
  - console errors and uncaught exceptions on every registered route, signed in and as a guest
  - 780 px with maximum-length labels: a 66-character `displayLabel`, a 254-character e-mail, the
    longest group label, every menu state, `scrollWidth <= innerWidth`
  - `R-66` as a user meets it: the menu's groups and items and their order; `/optimisation`
    absent from the menu yet opening by address; the four stubs saying they are not implemented,
    with no number and no invented data
- findings (path, line, consequence, reproduction) classed release-blocking /
  must-fix-before-merge / register; mutation or probe results; untested questions; verdict
- cross-examination with `W50-JUDGE-Y` after both black-box passes, under `W48-JUDGES.md`

## Required tests

- every probe restored; final `git diff --name-only <subject>..HEAD` names only the report

## Integration contract

The integrator opens `W50-FIX` only for upheld release-blocking findings.

## Failure/idempotency/security cases

- lane `gate-w50jx`, worktree `.local/worktrees/w50-jx`: `FOUNDATION_INSTANCE=gate-w50jx`,
  `POSTGRES_PORT=56700`, `S3_API_PORT=60300`, `S3_CONSOLE_PORT=60301`, a lane-unique `POSTGRES_DB`
  and `S3_BUCKET`; each port checked free with `ss -ltn` before use and recorded; the stand's API,
  health and web ports checked free the same way immediately before use and recorded in the report
- one full `make gate` on the host at a time if the judge runs one; never edit the tree while a
  gate measures it
- owned disposable services only; `make down` and remove the lane's own volumes by exact name at
  the end
- never kill a process by pattern — only confirmed-own PIDs
- no credential, cookie value, session id, token or `docker compose config` output in evidence;
  the stand's accounts and passwords are invented and disposable and never written into the report

## Rollback / feature flag

Report-only; revert the report commit.

## Handoff

- changed files: listed in `docs/program/reviews/W50-JUDGE-X.md` with
  `git diff --name-only <subject>..<sha>`
- commands/results: verbatim with exit status; every probe with its output
- known limits: listed, never decided silently
- integration notes: hand back branch `agent/w50-judge-x` at a recorded SHA
