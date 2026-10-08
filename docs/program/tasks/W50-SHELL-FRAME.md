# Task W50-SHELL-FRAME — grouped navigation from the registry, the account menu, a truthful footer

## Outcome

The frame (`web/src/_app/app-frame.tsx`, still a server component) renders the navigation groups
of the screen registry as amended by `R-66` — Главная; «Работа», «Знания», «Система»;
«Администрирование» only when the session may open one of its rows — filtered by the session's
roles, with `aria-current` on the current group and item, fitting one row at 780 px or collapsing
into one stacked list behind a «Меню» disclosure; an account menu under a generated avatar at the
top right (header: `displayLabel`, e-mail, role labels; Профиль, Сменить пароль, Выйти); a guest
sees one «Вход» link; the footer no longer says there is no separation of access. No hard-coded
address remains in `web/src/_app`.

## Depends on

- `W50-SHELL-UI`, `W50-HOME-01`, `W50-LAZY-01` merged into `integration/w50` (Stage C)

## Frozen inputs

- API contract: 27 paths / 34 operations / 77 schemas — frozen; W50 makes no contract change
- error catalog: 23 codes; domain candidate revision 9, 29 opaque identities — frozen
- migration head: `0015_accounts_roles_registration` — frozen
- code base: the commit that carries `docs/program/W50-FREEZE-01.md` on `integration/w50` (published to `origin/dev`); lane base:
  `<integration/w50 commit merging W50-LAZY-01>` (named by the integrator in the dispatch message)
- controlling plan: `docs/program/dispatch/W50-PLAN.md` at the freeze commit, as amended by owner
  ruling `R-66`
- owner ruling `R-66` (navigation amendment A-6), which this menu renders:
  - **Работа** = Проекты `/projects`, Дашборд `/dashboard`, «Оптимизация разделов»
    `/section-optimisation` (stub);
  - **Знания** = База знаний `/knowledge-base`, Блоки `/blocks`, «Нормы» `/norms` (stub);
  - **Система** = Журнал выполнения `/logs`, Исполнители `/workers`, «Настройки анализа»
    `/analysis-settings` (stub), «Очередь» `/queue` (stub);
  - `/optimisation` is not in any menu group; it stays registered and reachable in group `hidden`
    until W59
- from earlier W50 lanes: the registry and `requireScreen` (`W50-REGISTRY-01`); `Disclosure`,
  `Menu`, `Avatar` and the avatar tokens (`W50-SHELL-UI`); `entities/account` role labels
  (`W50-REGISTRY-01`)
- session subject: `login` (the e-mail once the profile is complete; a legacy login before),
  `displayLabel`, `initials`, `roles`, `isDefaultCredential`, `profileComplete` — there is no
  separate e-mail field; "e-mail" in `W50-PLAN.md` §3.5 is the subject's `login`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the frame hard-codes its addresses and carries a footer sentence that W49 made false

### P-01 — the hard-coded addresses this task removes

- captured_at: 2026-10-06
- command: `git grep -n 'href="/' ead639f -- web/src/_app`
- captured_output:
  ```text
  ead639f:web/src/_app/app-frame.tsx:50:        <Link className="am-app__brand" href="/projects">
  ead639f:web/src/_app/app-frame.tsx:69:        <Link className="am-app__nav" href="/knowledge-base">
  ead639f:web/src/_app/app-frame.tsx:82:        <Link className="am-app__nav" href="/account/password">
  ead639f:web/src/_app/app-frame.tsx:118:        <Link className="am-app__nav" href="/blocks">
  ead639f:web/src/_app/app-frame.tsx:121:        <Link className="am-app__nav" href="/optimisation">
  ead639f:web/src/_app/app-frame.tsx:124:        <Link className="am-app__nav" href="/logs">
  ead639f:web/src/_app/app-frame.tsx:127:        <Link className="am-app__nav" href="/workers">
  ead639f:web/src/_app/app-frame.tsx:136:        <Link className="am-app__nav" href="/dashboard">
  ead639f:web/src/_app/app-frame.tsx:142:         * This was an unconditional `<Link href="/login">Вход</Link>`: a signed-in reviewer
  ead639f:web/src/_app/app-frame.tsx:157:          <Link className="am-app__signin" href="/login">
  ```
- interpretation: measured on `ead639f`; no Stage A or B lane writes `_app/**`, so the lane
  re-measures the same lines at its base. Line 142 is a comment. After this task every `href`
  rendered by `_app` comes from the registry.

### P-02 — the footer sentence

- captured_at: 2026-10-06
- command: `git grep -n 'Один проверяющий' ead639f -- web/src`
- captured_output:
  ```text
  ead639f:web/src/_app/app-frame.tsx:205:        Альфа-версия. Один проверяющий, без разделения доступа между учётными записями.
  ```
- interpretation: false since W49 (`R-55`, `R-60`: a role set separates what an account may do).

## Historical evidence

- correction_mode: none
- source_record: `docs/program/dispatch/W50-PLAN.md`
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

From `W50-PLAN.md` §4 Stage C `W50-SHELL-FRAME`, verbatim:

- `web/src/_app/**` except `providers.tsx`
- `web/src/app/layout.tsx` (passing the full subject)
- `web/tests/unit/shell/**` (new)
- `web/tests/guards/screen-claims-about-the-system.guard.test.ts`
- `web/tests/guards/rendered-language.guard.test.ts` (fixtures, and — granted at the `W50-REGISTRY-01` merge — adding `web/src/app/error.tsx` to the hand-written list of boundaries it renders, beside `not-found`)
- `docs/program/W50-SHELL-FRAME.md`

Granted by the integrator at the freeze (Stage C; `W50-SHELL-UI` is already merged, so no
parallel writer), each only for what the frame change makes false, measured at `ead639f`:

- `web/tests/unit/screens/forms-and-pages.test.ts` lines 185–232 (`describe('the application
  frame')`: the guest frame's `href="/projects"`, the `{ login }` session fixture, the footer
  phrase «разделения доступа между учётными записями»)
- `web/tests/unit/styles/screens.ts` lines 201, 210–213, 235–236 (the census' `AppFrame`
  fixtures pass `session: { login }`; the menu-open states need census seeds)
- `web/tests/guards/prepared-sections.guard.test.ts` lines 248–255 (the navigation case renders
  the guest frame and requires `/optimisation`, `/logs`, `/workers`, `/knowledge-base` and
  `/account/password` among its links; under `R-66` `/optimisation` leaves the menu and a guest
  sees only «Вход») — the case keeps its meaning for a signed-in session

Granted by the integrator at the Stage-B merges (2026-10-07): `web/tests/unit/screens/route-screens.ts`
— only an additional `/` seed rendered for a session holding `admin` (with a project list), so
the rendered-language guard and the census reach the home page's administrator tile and its
recent-projects branch; one mutation that drops the seed turns the guard's coverage check red.

Granted by the integrator by message during Stage C (2026-10-07), recorded here before the merge:

- **Q1 — one access predicate.** `web/src/shared/config/screen-registry.ts`: add the pure
  `screenDecision(screen, subject | null): 'open' | 'sign-in' | 'change-password' |
  'complete-profile' | 'forbidden'` (`enforceScreen`'s decisions 1–4 in their order; an unknown
  role matches no row); export it from `web/src/shared/config/index.ts`; in
  `web/src/app/bff/session/screen-lock.ts` `enforceScreen` calls it and maps each decision to its
  existing redirect, decision 5 stays there. No behaviour change: `screen-guard.guard.test.ts`
  stays green unedited; one mutation (a reordered decision) turns it red. The frame keeps rows
  whose decision is `'open'`; `web/tests/unit/shell/**` drives the function, with a fixture
  registry holding an admin-only row and an assertion on the live registry's role-gated set.
- **Q2.** Grants are read by content; line numbers measured at `ead639f` drifted.
  `prepared-sections.guard.test.ts`: only the navigation case changes (a signed-in session,
  `/optimisation` dropped, the four stubs included); the `SECTIONS` rows stay.
- **Q3 — option A.** `route-screens.ts`: the `home-admin` seed (roles `['admin','expert']`) and
  `derivedScreens()` yielding every seed of an address in `SEEDS` order;
  `rendered-language.guard.test.ts`: the loaded cache state seeds the two home keys (a 5-project
  page; a pending page with `pending_total` 2) and one new case asserts some rendered state carries
  `data-home-tile="registrations"` and `data-recent-project-count="5"`, with its can-fail; the
  mutation "drop `home-admin`" turns it red; the report gives the census delta.
- **Q4 — option 1.** `screen-set.guard.test.ts`: only the assertion that counted one screen per
  address becomes `new Set(screens.map((s) => s.address)).size` against the same expected count;
  the unique-names check stays; one can-fail (an address's seeds dropped); the report states that
  the relationship moved from "exactly one screen per address" to "every non-excused address
  rendered at least once, names unique".

## Forbidden hotspots

- every path not listed above; `web/src/_app/providers.tsx` (composition root);
  `web/src/app/globals.css` (`W50-SHELL-UI` only — the frame's layout rules go in a CSS module
  under `web/src/_app/`, imported by the component that uses it); `web/src/shared/**` (the
  registry and the primitives are consumed, not edited); `web/src/app/**` except `layout.tsx`;
  `web/src/_pages/**`, `web/src/widgets/**`, `web/src/entities/**`, `web/src/features/**`;
  `contracts/**`; migrations; `src/**`; root locks, `web/package.json`, `web/package-lock.json`,
  `web/FRONTEND_LOCK.json`; `tests/e2e/**`; refs, tags, deployment and secrets;
  `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`
- `tests/e2e/pc01/journey/prove_the_width_assertion_can_fail.mjs` relies on `.am-app__bar`
    declaring `flex-wrap: wrap;` in `globals.css`; keep that selector and declaration or stop

## Non-goals

- no new screen, no registry row, no change to `requireScreen` (`W50-REGISTRY-01`'s)
- no primitive or token change (`W50-SHELL-UI`'s); no global CSS
- no avatar upload; no theme change; no `providers.tsx` change; no new dependency
- no `/admin/*` row (W51); the administration group renders nothing in W50

## Deliverables

- `layout.tsx` passes the full subject (or `null`) to `AppFrame`; the frame still reads no cookie
  itself and stays a server component; the disclosures and the account menu are client islands
  under `web/src/_app/`
- navigation built from the registry only: rows with `inMenu: true`, grouped as `R-66` orders
  them, filtered to the rows the session may open (access level and roles, the same predicate
  `requireScreen` uses — one function, not a copy); a group with no openable row is absent;
  `aria-current` on the current group and item (the current address read in a client island,
  matched against registry address shapes); at the 780 px floor the groups fit one row or collapse
  into one stacked list behind a «Меню» disclosure — both states tested, neither overflowing
- a session on a default credential or with an incomplete profile sees no navigation group it
  cannot open (so, in W50, none) and still sees the account menu
- account menu, top right: `Avatar` trigger (initials from the subject; colour key the subject's
  `login`); header with `displayLabel`, the e-mail (`login`) and the role labels from
  `entities/account` (Эксперт, Администратор; an unknown role is a typed fault); items Профиль
  `/account`, Сменить пароль `/account/password`, Выйти (POST to `/bff/v1/session/end`, unchanged);
  a guest sees one «Вход» link and no menu
- the brand link goes to `/`; every `href` in `_app` comes from the registry
- the footer sentence «Альфа-версия. Один проверяющий, без разделения доступа между учётными
  записями.» replaced by a sentence that is true of W49's role set, proposed in the report with
  its evidence; `screen-claims-about-the-system.guard.test.ts` extended so a rendered sentence
  that denies roles or separation of access is red while the contract declares `Role`
  (derived from `components.schemas.Role`, not a literal), with the old footer and the old
  `/projects` subtitle among its red controls
- `rendered-language.guard.test.ts` fixtures (lines 1049 and 1056–1060 at `ead639f`) move to the
  full subject: guest, expert-only, admin, default credential, incomplete profile, menu open
- the frame makes **no API call from the browser**: it renders from the subject the layout passes;
  a `getMe` from the frame would add an undeclared call to every route of the live journey
- `web/tests/unit/shell/**`: navigation, filtering, account menu, guest state
- the report `docs/program/W50-SHELL-FRAME.md` with the six items of `AGENTS.md` §5

## Required tests

- mutations, each red with its output in the report:
  - the menu rendered for `roles: []` shows no admin group
  - a group with no openable row is absent — W50 has no role-gated row, so this case runs the
    menu builder against a fixture registry with an `admin` row and an `admin`-only group, and a
    second case asserts the live registry's menu equals `R-66`'s groups and order exactly
  - `/optimisation` in the menu is red; a missing `R-66` stub in its group is red
  - the account header for a 66-character label and a 254-character e-mail does not widen the
    frame at 780 px; the stacked state has no horizontal overflow — asserted on markup and CSS in
    `web/tests/unit/shell/**`, and measured in a browser on the lane stand at 780 × 900 with an
    existing instrument unchanged (`tests/e2e/pc01/journey/look.mjs`, `width.mjs`),
    `scrollWidth <= innerWidth` quoted for each menu state
  - a literal `href="/…"` in `_app` is red; `Выйти` as a link (GET) is red; a `div` trigger is red
  - the old footer sentence is red in the extended claims guard
- `rg -n "href=" web/src/_app` output quoted: no address outside the registry
- `npm --prefix web test -- --run`; `npm --prefix web run lint -- --quiet`;
  `npm --prefix web run typecheck`; `npm --prefix web run build` (route table quoted)
- the live journey on the lane stand (`npm --prefix web run e2e:pc01 -- --phase all`), signed in
  as a complete-profile account with a changed password: every route at 780 × 900 without
  overflow, no undeclared call; summary quoted verbatim
- keyboard-only pass in a real browser on the lane stand: Tab to each group, open/close with
  Enter/Space/Escape, the account menu with arrows/Home/End/Escape, focus back on the trigger,
  outside click closes — recorded step by step
- `git diff --check`; `make gate` with the literal `GATE OK` on the task's head

## Integration contract

`AppFrame` takes the subject (or `null`) and renders the registry's menu for it; nothing else in
the tree decides which screens the menu shows. The frame makes no browser-side API call. The
footer and the claims guard state only what W49's contract makes true.

## Failure/idempotency/security cases

- lane `gate-w50frame`, worktree `.local/worktrees/w50-frame`: `FOUNDATION_INSTANCE=gate-w50frame`,
  `POSTGRES_PORT=56680`, `S3_API_PORT=60280`, `S3_CONSOLE_PORT=60281`, a lane-unique `POSTGRES_DB`
  and `S3_BUCKET`; each port checked free with `ss -ltn` before use and recorded; any further port
  the stand needs (API, health, `next start`) checked free the same way and recorded; provisioned
  with `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` and `npm --prefix web ci`; the real
  corpus attached read-only before `make gate`
- one full `make gate` on the host at a time; never edit the tree while its gate runs
- owned disposable services only; `make down` and remove the lane's own volumes by exact name at
  the end
- never kill a process by pattern — only confirmed-own PIDs
- no credential, cookie, session id or real e-mail in evidence; the 254-character e-mail is an
  invented address under `example.test`
- the menu hides what a session cannot open, and that is presentation only: the guard and the API
  still refuse on their own evidence; a stale subject shows a menu its holder cannot use and
  nothing more
- the subject is rendered as text, never as HTML; a hostile `displayLabel` cannot inject markup
- a frame change that needs a path outside the allowed paths above is a stop, not an edit

## Rollback / feature flag

Revert the commits; the frame returns to the Stage-B frame (hard-coded links, footer). No flag, no
stored data.

## Handoff

- changed files: listed in `docs/program/W50-SHELL-FRAME.md` with
  `git diff --name-only <base>..<sha>` and `git status --porcelain -uall` empty
- commands/results: verbatim with exit status; every mutation with its red output; the browser
  readings and the keyboard pass
- known limits: listed, never decided silently — at least the footer wording (a product sentence
  the owner may want to word) and what the header shows for `roles: []`
- integration notes: hand back branch `agent/w50-shell-frame` at a recorded SHA
