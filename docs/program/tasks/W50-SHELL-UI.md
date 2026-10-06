# Task W50-SHELL-UI — disclosure, menu and avatar primitives with fourteen avatar token pairs

## Outcome

`web/src/shared/ui/` exports `Disclosure` (the APG disclosure pattern), `Menu` (the APG menu
button pattern) and `Avatar` (initials on a circle whose colour is hashed from the account's
e-mail), and `globals.css` declares fourteen avatar token pairs `--am-avatar-NN` in both themes;
a new test enumerates all 14 × 2 values and holds the text to 4.5:1 and the circle to 3:1 against
the page background in each theme. No new dependency.

## Depends on

- `W50-REGISTRY-01` merged into `integration/w50` (Stage A); runs in parallel with
  `W50-HOME-01` and `W50-LAZY-01` on disjoint paths

## Frozen inputs

- API contract: 27 paths / 34 operations / 77 schemas — frozen; W50 makes no contract change
- error catalog: 23 codes; domain candidate revision 9, 29 opaque identities — frozen
- migration head: `0015_accounts_roles_registration` — frozen
- code base: the commit that carries `docs/program/W50-FREEZE-01.md` on `integration/w50` (published to `origin/dev`); lane base:
  `<integration/w50 commit merging W50-REGISTRY-01>` (named by the integrator in the dispatch message)
- controlling plan: `docs/program/dispatch/W50-PLAN.md` at the freeze commit, as amended by owner
  ruling `R-66` (`R-66` changes navigation groups, not these primitives)
- dependency set: `web/package.json` and `web/package-lock.json` as at the freeze, sealed by
  `web/FRONTEND_LOCK.json` — frozen
- rulings: `R-57` (generated avatar, no upload), `R-33` (3:1 for non-text; this task adds a
  dedicated check in its spirit, it does not claim `R-33` already covers the avatar)

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `web/src/app/globals.css` — the avatar palette `--am-avatar-01` … `--am-avatar-14` (background and text per pair) in `:root`, in `@media (prefers-color-scheme: dark)` `:root:not([data-theme='light'])` and in `:root[data-theme='dark']`
- enumerator_owner: `W50-SHELL-UI` (the only W50 writer of `globals.css`)
- totality_query: the new avatar test reads every `--am-avatar-NN` declaration out of `globals.css` (not out of a list in the test), asserts exactly the indices 01…14 with a background and a text value in each of the three blocks, that the two dark blocks agree, and that the avatar hash's modulus equals the number of indices found

## Captured premise evidence

- premise: `shared/ui` has no disclosure, menu or avatar primitive and no `web/tests/unit/ui` directory exists

### P-01 — the primitives this task adds do not exist

- captured_at: 2026-10-06
- command: `git ls-tree -r --name-only ead639f web/src/shared/ui`
- captured_output:
  ```text
  web/src/shared/ui/icon.tsx
  web/src/shared/ui/index.ts
  web/src/shared/ui/page-shell.tsx
  web/src/shared/ui/route-placeholder.tsx
  web/src/shared/ui/run-state-badge.tsx
  web/src/shared/ui/stage-label.ts
  web/src/shared/ui/stage-status-badge.tsx
  web/src/shared/ui/states.tsx
  ```
- interpretation: measured on `ead639f`; `W50-REGISTRY-01` does not write `shared/ui/**`, so the
  lane re-measures the same eight files at its base.

### P-02 — the test directory this task creates

- captured_at: 2026-10-06
- command: `git ls-tree -d --name-only ead639f web/tests/unit/`
- captured_output:
  ```text
  web/tests/unit/api
  web/tests/unit/decisions
  web/tests/unit/export
  web/tests/unit/lib
  web/tests/unit/projects
  web/tests/unit/qa_w49
  web/tests/unit/review
  web/tests/unit/run
  web/tests/unit/screens
  web/tests/unit/session
  web/tests/unit/styles
  web/tests/unit/widgets
  ```
- interpretation: no `web/tests/unit/ui`; the frontend runs in `environment: 'node'`
  (`web/vitest.config.ts`) with no DOM library, so keyboard behaviour is tested through pure
  functions the primitives call, not through a simulated DOM.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/dispatch/W50-PLAN.md`
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

From `W50-PLAN.md` §4 Stage B, `SHELL-UI allowed paths`, verbatim:

- `web/src/shared/ui/**`
- `web/src/app/globals.css`
- `web/tests/unit/styles/**`
- `web/tests/unit/ui/**` (new)
- `docs/program/W50-SHELL-UI.md`

## Forbidden hotspots

- every path not listed above; `contracts/**`; `web/src/shared/api/**`; migrations; `src/**`;
  root locks, `web/package.json`, `web/package-lock.json`, `web/FRONTEND_LOCK.json`;
  `web/src/_app/**` (including the composition root `providers.tsx`); `web/src/app/**` except
  `globals.css`; `web/src/_pages/**`, `web/src/widgets/**`, `web/src/entities/**`,
  `web/src/features/**`; `web/src/shared/config/**`; `tests/e2e/**`; refs, tags, deployment and
  secrets; `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`
- `shared/ui` may not import any layer above `shared` (FSD; `eslint-boundary.guard.test.ts`): the
  avatar takes `initials` and the colour key as props and does not import `entities/account`

## Non-goals

- no navigation, no account menu content, no frame change (`W50-SHELL-FRAME`): this task ships
  the primitives, not their use
- no theme change beyond the avatar tokens and the primitives' own rules; no avatar upload
  (`R-57`); no new dependency, no i18n library

## Deliverables

- `Disclosure`: a real `<button type="button" aria-expanded aria-controls>` that opens a list of
  links (the APG disclosure pattern, not `role="menu"`, because the items are links); closed by
  default; Escape closes and returns focus to the button
- `Menu`: the APG menu button pattern — trigger `<button aria-haspopup="menu" aria-expanded
  aria-controls>`, `role="menu"` list of `role="menuitem"` items (a link item or a form-submit
  item, so `Выйти` can stay a POST); Enter/Space/ArrowDown open on the first item, ArrowUp on the
  last; ArrowUp/ArrowDown move, Home/End jump; Escape closes and returns focus to the trigger;
  Tab leaves and closes; a click outside closes; focus returns to the trigger after an item is
  chosen
- the keyboard and open/close logic of both as pure exported functions (state, event → state and
  focus target) that the client components call, so the node test environment can drive them;
  the client components are thin islands (`'use client'`) over that logic
- `Avatar`: a circle with the initials it is given (the session subject already carries
  `initials`, derived from `displayLabel`, `R-57`), colour index = a stable hash of the
  normalised e-mail (the subject's `login`) modulo 14, `aria-hidden` where a visible name sits
  beside it, else an accessible name; the hash is exported and documented as e-mail-keyed so a
  corrected name does not recolour the account
- `globals.css`: fourteen pairs `--am-avatar-NN` (background, text) with a light value and a dark
  value each, in the three theme blocks the file already uses; white or near-black text chosen per
  pair; the primitives' own classes (disclosure, menu, avatar), each with a rule; no `!important`,
  no new colour outside tokens
- `web/tests/unit/ui/**`: keyboard and state tests for both primitives; the avatar hash
  (deterministic; same e-mail → same index; every one of the 14 indices reachable; a renamed
  label with the same e-mail keeps its index)
- `web/tests/unit/styles/**`: the dedicated avatar palette test of the Enumerator section; census
  seeds in `web/tests/unit/styles/screens.ts` that render each primitive in each state (closed and
  open disclosure, open menu, one avatar per pair) so the contrast census and its unreached-rule
  case reach every new rule; `theme.test.ts` parity holds for the new tokens
- `shared/ui/index.ts` exports the three primitives and their prop types
- the report `docs/program/W50-SHELL-UI.md` with the six items of `AGENTS.md` §5 and the 14 × 2
  measured ratios (text, circle) as a table produced by the test, with the command

## Required tests

- mutations, each red with its output in the report:
  - a `div` (or any non-`button`) trigger in either primitive is red
  - a token pair below the text floor (4.5:1) or the circle floor (3:1 against the page
    background) in either theme is red, measured on the real `globals.css` with one value edited
  - Escape not closing (either primitive) is red; focus not returning to the trigger is red
  - `role="menu"` on the disclosure's list is red; a missing `aria-controls` is red
  - removing one `--am-avatar-NN` from one dark block is red (palette completeness)
  - an avatar hash keyed on the label instead of the e-mail is red
- `npm --prefix web test -- --run`; `npm --prefix web run lint -- --quiet`;
  `npm --prefix web run typecheck`
- `git diff --check`; `make gate` with the literal `GATE OK` on the task's head

## Integration contract

`W50-SHELL-FRAME` composes `Disclosure` for each navigation group and for the stacked «Меню»
state, `Menu` for the account menu under `Avatar`, from `@/shared/ui` only. The primitives make no
API call, hold no query and take no session object: they take labels, links, items, `initials`
and a colour key. Every class they render has a rule in `globals.css`, and every colour they use
is a token.

## Failure/idempotency/security cases

- lane `gate-w50ui`, worktree `.local/worktrees/w50-ui`: `FOUNDATION_INSTANCE=gate-w50ui`,
  `POSTGRES_PORT=56650`, `S3_API_PORT=60250`, `S3_CONSOLE_PORT=60251`, a lane-unique `POSTGRES_DB`
  and `S3_BUCKET`; each port checked free with `ss -ltn` before use and recorded; provisioned with
  `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` and `npm --prefix web ci`; the real corpus
  attached read-only before `make gate`
- one full `make gate` on the host at a time — three Stage-B lanes run in parallel, so each asks
  the integrator for its gate slot; never edit the tree while its gate runs
- owned disposable services only; `make down` and remove the lane's own volumes by exact name at
  the end
- never kill a process by pattern — only confirmed-own PIDs
- no credential, cookie or session id in evidence; avatar fixtures use invented addresses under
  `example.test`
- stop condition (`W50-PLAN.md` §7): a primitive cannot meet the contrast or keyboard requirement
  without a dependency — stop and report, do not add one
- a hash input that is empty or not an e-mail (a legacy login) still yields a valid index; the
  avatar never renders blank (the subject's `initials` is never empty)

## Rollback / feature flag

Revert the commits. No flag; nothing renders the primitives until `W50-SHELL-FRAME`, so a revert
before Stage C changes no screen.

## Handoff

- changed files: listed in `docs/program/W50-SHELL-UI.md` with `git diff --name-only <base>..<sha>`
  and `git status --porcelain -uall` empty
- commands/results: verbatim with exit status; every mutation with its red output
- known limits: listed, never decided silently (for example: focus movement and the outside-click
  listener in a real browser are exercised first by `W50-SHELL-FRAME` and `W50-QA-01`)
- integration notes: hand back branch `agent/w50-shell-ui` at a recorded SHA
