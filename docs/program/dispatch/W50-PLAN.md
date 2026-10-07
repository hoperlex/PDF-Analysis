# Wave 50 — the shell: screen registry, server guards, redirects, lazy loading, grouped navigation, home, account menu

**Status:** planned; dispatchable after `W49-INT-CLOSE` and `W50-FREEZE-01`.
**Controlling rulings:** `R-55`, `R-57`, `R-60` (provisional numbers). Navigation groups: poll
P-11 (`IDENTITY-WAVES.md` §3.1).
**Roles:** lanes, QA, judges and FIX are the executor's; freeze, merges, the final gate and
publication are the integrator's (`IDENTITY-WAVES.md` §8).
**Exit:** every screen is behind one registry; the frame has grouped navigation, a real home page
and the account menu; on `origin/dev` with literal `GATE OK`. No contract change.

## 1. Objective

One declarative registry decides what the menu shows, which screens a guest, a default
credential, an incomplete profile, an expert or an administrator may open, and where a refused
request is sent. The frame grows a home page, grouped disclosure navigation and an account menu
under a generated avatar. Heavy client widgets load lazily behind typed loading and error
boundaries without the test instruments losing sight of them. No new dependency, no API change.

## 2. Entry conditions

| Condition | Evidence |
| --- | --- |
| `W49-INT-CLOSE` done; session subject carries `roles`, `displayLabel`, `initials`, `profileComplete` | `origin/dev`; `web/src/app/bff/session/store.ts` |
| generated client exposes `getMe`, `listRegistrations` | `web/src/shared/api/generated/operations.gen.ts` |
| frontend baseline | `npm --prefix web test -- --run` counts by file, and the `next build` route table (first-load JS per route), both recorded by the freeze |

## 3. Design decisions bound by this plan

### 3.1 Screen registry — `web/src/shared/config/screen-registry.ts`

Named "screen registry" because `web/src/shared/lib/routes.ts` already exists and builds
addresses from identities; the registry imports it and does not replace it.

One array of entries `{ address, label, group, access, roles, inMenu }`:

- `address` is the Next address with dynamic segments (`/projects/[project_uid]`);
- `access` is one of three nested levels: `public` — anyone, session or not;
  `open-to-default-credential` — a session is required, but one still on its seeded or reset
  password, or with an incomplete profile, may open it; `session` — a session with a changed
  password, a complete profile and the roles below;
- `roles ∈ {'any', 'expert', 'admin'}` (any-of, as the API's register);
- `group ∈ {'home', 'work', 'knowledge', 'system', 'admin', 'account', 'hidden'}`;
- the registry is the **only** list of screens: a test derives the set of `page.tsx` addresses
  from `web/src/app` (the walker in `web/tests/unit/screens/route-screens.ts`) and asserts it
  equals the registry's addresses, both directions; `tests/e2e/pc01/journey/manifest.json`
  (which `test_pc01_journey_conformance.py` compares with `web/src/app`) lists the same set.

Groups (P-11 as amended by `R-66` at `W50-FREEZE-01`): Главная `/`; **Работа** — Проекты
`/projects`, Дашборд `/dashboard`, «Оптимизация разделов» `/section-optimisation` (stub);
**Знания** — База знаний `/knowledge-base`, Блоки `/blocks`, «Нормы» `/norms` (stub);
**Система** — Журнал выполнения `/logs`, Исполнители `/workers`, «Настройки анализа»
`/analysis-settings` (stub), «Очередь» `/queue` (stub); `/optimisation` is registered in group
`hidden` until W59; **Администрирование** — rows are added by W51; the group renders only when it
has rows the session may open. The four stubs and their wording are `W50-REGISTRY-01`'s
(`R-66`).

### 3.2 Server guard — `requireScreen(address, { params, searchParams })`

Lives in `web/src/app/bff/session/screen-lock.ts`, replaces `requireAChangedPassword()` in every
`page.tsx`; the old function is removed. Each `page.tsx` passes its own `params` and
`searchParams` so the guard can rebuild the concrete address it is protecting. Decisions, in
order, each a redirect or a normal return, never a thrown framework error:

1. no session and `access !== 'public'` → `redirect('/login?next=<validated>')`, where `next` is
   the concrete path plus its query string. **The fragment never reaches the server and is not
   preserved**; the plan says so instead of promising it.
2. session on a default credential and the screen is not `open-to-default-credential` →
   `/account/password`;
3. session with `profileComplete === false` and the screen is not `open-to-default-credential` →
   `/account` (the W51 completion screen; until W51 lands, `/account` is a registered
   placeholder that says what is missing);
4. session lacking a required role → `redirect('/403?from=<validated>')`; the `/403` screen names
   the role the registry requires for `from`;
5. a session visiting `/login` → `redirect('/')`.

After a successful sign-in the browser lands on `/`, not `/projects`: `AFTER_SIGN_IN` in the BFF
handler, the mirror constant in `features/sign-in/model/exchange.ts` and `session.lands_on` in
`tests/e2e/pc01/journey/manifest.json` move together in `W50-REGISTRY-01`.

`next`/`from` validation (one function, unit-tested): a string that starts with exactly one `/`,
is not `//…` or `/\…`, has no scheme, is at most 512 characters, and whose path matches a
registry address shape; anything else is dropped, never echoed. The sign-in form carries the
validated `next` in a hidden field, and the BFF's after-sign-in redirect uses it after validating
it again; both are this wave's `W50-REGISTRY-01` (the BFF handler and the form are in its paths).

Why not middleware: the register lives in this Node process's memory and on its volume
(`R-47`/`R-51`); middleware runs in another runtime and cannot read the session. Why not the
layout: a server layout does not know which address it renders. The call-per-route plus the
registry completeness test is what makes "no unregistered screen opens" a property of the
application (the existing argument in `screen-lock.ts`). No redirect cycle exists: `/login`,
`/account/password` and `/account` are `open-to-default-credential` or `public`, and `/` is
`session`.

### 3.3 Redirect and error screens

- `/403` — a registered `public` screen, Russian, inside the frame; `app/not-found.tsx` stays
  and gets the frame.
- `app/error.tsx` and per-segment `loading.tsx` (`projects`, `projects/[project_uid]`,
  `dashboard`, `knowledge-base`; `admin` is W51's): typed states from `shared/ui/states`.
- Nothing renders a raw error message or an English framework string.

### 3.4 Lazy loading — `W50-LAZY-01`

`next/dynamic` with a `loading` state for the heavy client widgets: `widgets/evidence-viewer`,
`widgets/stage-comparison`, `widgets/run-progress`, `widgets/knowledge-base`,
`widgets/dashboard`. Two things must both hold, and each has a check:

- **the bundle really splits:** the `next build` route table's first-load JS per route is
  recorded before and after in the report, and no measured route gets worse; *(amended by the
  owner's direct poll of 2026-10-07: the five target routes' first-load JS falls, and no other
  route grows by more than the measured fixed cost of the async-chunk runtime — at most 1.5 kB
  gzip per route on this toolchain — with the exact-byte table in the report. Any `import()`
  adds webpack's chunk-id map to the runtime every route loads, so "no route grows" was
  unsatisfiable by any lazy loading; `W50-LAZY-01` measured −25 / −10 / −8 / −2 kB on the heavy
  routes against +0.7 … +1.4 kB elsewhere.)*
- **the instruments keep seeing the widgets:** the screen harness
  (`web/tests/unit/screens/harness.ts`, `renderToStaticMarkup`), the contrast census and the
  language guards render `_pages` synchronously, where a dynamic import yields only its
  `loading` state. The task defines one seam through which those instruments render the eager
  widget (for example, each lazy wrapper module also exports the eager component and the harness
  resolves it), and a guard asserts the census' screen and pair counts did not decrease.

`CATEGORY_LABELS`, which `_pages/knowledge-base` imports from the widget today, moves to the
`expert-decision` entity so the page keeps no static import of a lazy widget; a guard asserts no
`_pages/**` module imports those five widgets statically. The sentence «Одна учётная запись…
Ролей нет» in `_pages/projects` is removed here, because this task owns `_pages/**`.

### 3.5 Frame, navigation, account menu — `W50-SHELL-UI` then `W50-SHELL-FRAME`

- The frame (`web/src/_app/app-frame.tsx`) stays a server component; the disclosures and the
  account menu are client islands under `web/src/_app/`.
- Primitives in `web/src/shared/ui/` (`SHELL-UI`): `Disclosure` for navigation groups (a
  `<button aria-expanded aria-controls>` opening a list of links — the APG disclosure pattern,
  not `role="menu"`, because the items are links); `Menu` for the account menu (the APG menu
  button pattern: `aria-haspopup="menu"`, Escape, Arrow keys, Home/End, Tab leaves, click outside
  closes, focus returns to the trigger); `Avatar` (initials from `displayLabel`; colour from a
  hash of the **e-mail**, so a corrected name does not recolour the account; **fourteen token
  pairs** `--am-avatar-NN` with a light-theme and a dark-theme value each, white or near-black
  text chosen per pair). The existing contrast census measures only pairs a seeded screen
  happens to render, so `SHELL-UI` adds a dedicated test that enumerates all 14 × 2 token values
  and asserts the text contrast floor and **3:1 of the circle against the page background in both
  themes** — a new check in the spirit of `R-33`, not a claim that `R-33` already covers it.
- Navigation (`SHELL-FRAME`): groups of §3.1 filtered by the session's roles; the current group
  and item carry `aria-current`; at the 780 px floor the groups either fit in one row or collapse
  into one stacked list behind a «Меню» disclosure — both states are tested and neither overflows
  horizontally.
- Account menu, top right: avatar trigger; header with `displayLabel`, e-mail and the role labels
  (Эксперт, Администратор); items Профиль `/account`, Сменить пароль `/account/password`, Выйти
  (POST to `/bff/v1/session/end`, unchanged). A guest sees one «Вход» link. The footer sentence
  «Один проверяющий, без разделения доступа…» is replaced, and
  `screen-claims-about-the-system.guard.test.ts` is updated to the new truthful sentence.
- No new dependency. `globals.css` is edited by `SHELL-UI` only.

### 3.6 Account entity and home page

- `web/src/entities/account/**` (built in Stage A by `W50-REGISTRY-01` so that both HOME and
  FRAME can consume it): the `getMe` consumer, `displayLabel`/`initials` helpers, Russian role
  labels, query key `account.me`. An unknown role value is a typed fault.
- `app/page.tsx` stops redirecting (`W50-HOME-01`). The home page greets by `displayLabel`,
  lists the five most recent projects (`listProjects`), shows the dashboard summary tile the
  frozen contract already provides, and, for an `admin` session, a «Заявки на регистрацию» tile
  with `pending_total` from `listRegistrations`; the tile links to `/admin/registrations` only
  once that row exists in the registry (W51). Projects moves to the «Работа» group as its first
  item.

## 4. Tasks

Each task lists `Depends on`; standard forms are in `IDENTITY-WAVES.md` §10.

### `W50-FREEZE-01` (integrator)
Depends on: `W49-INT-CLOSE`. Standard form; records the `next build` route table as the lazy
baseline.

### `W50-REGISTRY-01` — Stage A, alone (executor)
- **Depends on:** `W50-FREEZE-01`.
- **Allowed paths:** `web/src/shared/config/screen-registry.ts`, `web/src/shared/config/index.ts`,
  `web/src/app/bff/session/screen-lock.ts`, `web/src/app/bff/v1/[...path]/route.ts` (the
  after-sign-in redirect only), every `web/src/app/**/page.tsx` (the guard call with the page's
  `params`/`searchParams`, nothing else), `web/src/app/403/**`, `web/src/app/not-found.tsx`,
  `web/src/app/error.tsx`, `web/src/app/**/loading.tsx` (empty typed placeholders; LAZY fills
  them), `web/src/_pages/forbidden/**`, `web/src/_pages/account/**` (the placeholder of §3.2
  step 3), `web/src/app/account/page.tsx` (new placeholder route), `web/src/features/sign-in/**`
  and `web/src/_pages/sign-in/**` (the hidden `next` field), `web/src/entities/account/**`,
  `web/src/_pages/home/**` (placeholder module exporting `HomePage`; HOME replaces its content
  and keeps the named export and its props), `tests/e2e/pc01/journey/manifest.json`,
  `web/src/shared/api/query-keys.ts`, `web/docs/PC01_UI_SEAM.md` (§6 only),
  `web/tests/unit/api/configuration-and-cache-keys.test.ts`,
  `web/tests/contract/narrow-sets.contract.test.ts`,
  `web/tests/guards/query-key-shape.guard.test.ts` (the query namespaces `account`, `users`,
  `registrations` are a closed set checked against `PC01_UI_SEAM.md` §6 and a unit literal —
  they enter once, here, so no later lane touches them), `web/tests/unit/screens/route-screens.ts`,
  `web/tests/guards/default-credential-screens.guard.test.ts` → `screen-guard.guard.test.ts`,
  `web/tests/guards/screen-registry.guard.test.ts` (new), `web/tests/unit/session/**`,
  `web/tests/unit/entities/account.test.ts` (new), `docs/program/W50-REGISTRY-01.md`.
- **Deliverables:** §3.1–§3.3 and §3.6's entity; `app/page.tsx` becomes a registered
  `session` placeholder (`RoutePlaceholder`) rendered from `_pages/home`, and the `root-redirect`
  opt-out seed in `route-screens.ts` becomes an ordinary seed, so HOME later changes content
  only; the three query namespaces and their key factories.
- **Required tests and mutations:** a `page.tsx` without `requireScreen` is red naming its
  address; a registry row without a page is red; a page without a row is red; a page missing
  from `manifest.json` is red (`test_pc01_journey_conformance.py`); `next=//evil.example`,
  `next=https://evil.example`, `next=/\evil`, a 513-character `next`, and `next=/nowhere` are
  dropped; `next=/projects?x=1` survives sign-in with its query; an expert on `/403?from=/admin/users`
  sees «Администратор»; a signed-in visit to `/login` redirects; the five decisions of §3.2 each
  have a test; `npm --prefix web test -- --run`; lint; typecheck.

### Stage B — `W50-SHELL-UI` ∥ `W50-HOME-01` ∥ `W50-LAZY-01` (executor; disjoint paths)
- **Depends on:** `W50-REGISTRY-01` (all three).
- **SHELL-UI allowed paths:** `web/src/shared/ui/**`, `web/src/app/globals.css`,
  `web/tests/unit/styles/**`, `web/tests/unit/ui/**` (new), `docs/program/W50-SHELL-UI.md`.
  Deliverables: the primitives and tokens of §3.5. Mutations: a `div` trigger is red; a token
  pair below the contrast floor in either theme is red; Escape not closing is red.
- **HOME allowed paths:** `web/src/app/page.tsx`, `web/src/_pages/home/**`,
  `web/src/widgets/home-*/**`, `web/tests/unit/screens/home.test.ts`, `docs/program/W50-HOME-01.md`.
  Mutations: the admin tile is absent for an expert-only session; an unknown role label is a
  typed fault; a maximum-length `displayLabel` (66 characters) does not widen the page at 780 px.
- **LAZY allowed paths:** `web/src/_pages/**` except `home`, `sign-in`, `account`, `forbidden`;
  the `loading.tsx` files REGISTRY created; `web/src/widgets/knowledge-base/**` and
  `web/src/entities/expert-decision/**` (only to move `CATEGORY_LABELS`);
  `web/tests/unit/screens/cold-load.test.ts`, `web/tests/unit/screens/harness.ts` (the eager
  seam), `web/tests/guards/lazy-boundary.guard.test.ts` (new), `docs/program/W50-LAZY-01.md`.
  Mutations: a static import of a lazy widget in `_pages/**` is red; a census screen or pair
  count lower than the baseline is red; the report carries the route table before and after.

### Stage C — `W50-SHELL-FRAME` (executor)
- **Depends on:** `W50-SHELL-UI`, `W50-HOME-01`, `W50-LAZY-01` merged.
- **Allowed paths:** `web/src/_app/**` except `providers.tsx`, `web/src/app/layout.tsx` (passing
  the full subject), `web/tests/unit/shell/**` (new),
  `web/tests/guards/screen-claims-about-the-system.guard.test.ts`,
  `web/tests/guards/rendered-language.guard.test.ts` (fixtures only), `docs/program/W50-SHELL-FRAME.md`.
- **Deliverables:** navigation, account menu, footer sentence of §3.5.
- **Mutations:** the menu rendered for `roles: []` shows no admin group; a group with no
  openable row is absent; the account header for a 66-character label and a 254-character e-mail
  does not widen the frame at 780 px; the stacked state has no horizontal overflow.

### `W50-QA-01` (executor, fresh context)
Depends on: `W50-SHELL-FRAME`. Standard form, files under `web/tests/unit/qa_w50/**`: keyboard
paths through both primitives; focus return; Escape; outside click; guest redirect for every
registered `session` screen with its `next`; `admin` screens absent for an expert; 780 × 900
overflow for every menu state; the `/403` screen for every role-gated row.

### `W50-JUDGE-X`, `W50-JUDGE-Y` (executor, fresh contexts)
- X: black-box in a built stand — open-redirect attempts; direct navigation to each role-gated
  address with the other role; default-credential and incomplete-profile bypass attempts;
  keyboard-only operation of the whole shell; console errors; 780 px with maximum-length labels.
- Y: FSD boundaries (`eslint-boundary.guard.test.ts`), the registry as the single source
  (`rg -n "href=" web/src/_app` shows no address outside it), no `fetch` outside `shared/api`,
  the eager seam renders every lazy widget in the census, `globals.css` has a rule for every new
  class (`styling-layer.test.ts`), no new dependency, lock bytes unchanged, the route table did
  not regress.

### `W50-FIX` (executor), `W50-INT-CLOSE` (integrator)
Standard forms.

### Grants widened at `W50-FREEZE-01`

The task files are the grants. At the freeze the integrator widened four of them beyond §4, each
for a file the task's own change makes false (measured at `ead639f`): `W50-REGISTRY-01` gets the
four `R-66` stub routes and their `_pages` modules, the `PC01_UI_SEAM.md` §2 `/` row, and the
release-acceptance files that pin sixteen routes and `/` → `/projects`
(`verify-acceptance.mjs`, `test_alpha_acceptance_command.py`, `manual-alpha-check.sh`,
`ALPHA_PUBLIC_ACCEPTANCE.md`, the `redden*` manifests); `W50-HOME-01` gets the `root` and
`sign-in` `expects_api` entries of the journey manifest; `W50-SHELL-FRAME` gets three test files
that pin the old frame; `W50-QA-01` gets `tests/e2e/pc01/qa_w50/**`. The `next build` route table
`W50-LAZY-01` compares against is measured on its own base (the Stage-A merge), with the freeze's
reading quoted where one exists.

### Integrator rulings at the `W50-REGISTRY-01` merge (2026-10-06)

`W50-REGISTRY-01` (merged at the commit after `8e9706b`) handed back seven questions:

1. **A guest must get a real redirect, not a 200 with a redirect in the stream.** The segment
   `loading.tsx` files above guarded pages turn `requireScreen`'s redirect into a streamed
   `NEXT_REDIRECT` with status 200. `W50-LAZY-01` deletes the four segment `loading.tsx` files
   (`app/projects`, `app/projects/[project_uid]`, `app/dashboard`, `app/knowledge-base`), keeps
   typed loading states inside `_pages/**` around the lazy widgets, adds to its new
   `lazy-boundary.guard.test.ts` a rule that no `loading.tsx` sits at or above a `page.tsx` whose
   registry access is not `public`, and records on its lane stand, for every registered
   `session` screen, that a guest gets `307` with `Location: /login?next=…`.
2. The error boundary's texts are covered by `screen-guard.guard.test.ts`; adding `error.tsx` to
   `rendered-language.guard.test.ts`'s hand-written list is granted to `W50-SHELL-FRAME`, which
   already owns that file's fixtures in Stage C.
3. The registry keeps literal addresses typed by `ScreenAddress` instead of importing
   `routes.ts` (§3.1 said "imports it"): a compile-time check on every literal is accepted as
   equivalent; §3.1's sentence is read that way.
4. `next` is lost after a refused sign-in and after the forced default-password change: carried
   to W51, whose sign-in and password screens own those redirects (`W51-FREEZE-01` input).
5. Stale prose outside the grant (`routes.ts:30`, `journey.mjs:304`, the journey README, the
   legacy `openSession` docstring in `store.ts`, `$comment` and root's `listProjects` in the
   `redden-write` fixtures, "three" in `prepared-sections.guard.test.ts` titles): collected for
   `W50-FIX`, which gets an explicit grant for them.
6. `configuration-and-cache-keys.test.ts:224` counts decision cache keys, not namespaces: no
   change needed.
7. `UserListFilters` and `RegistrationListFilters` are not re-exported from `@/shared/api`:
   carried to W51, whose admin lanes consume them (`W51-FREEZE-01` input).

The Stage-B lane base is the commit that carries this section.

### Integrator rulings at the Stage-B merges (2026-10-07)

- `W50-HOME-01`: the journey manifest's `root` and `sign-in` declare the home page's
  `listProjects` and `getDashboardSummary`, and `listRegistrations` as `optional_api` (only an
  administrator makes it) — moved by the integrator, as the task's integration contract says.
  The rendered-language guard cannot reach the administrator tile or the recent-projects
  branches (its `/` seed is an expert's): `W50-SHELL-FRAME` adds an administrator `/` seed to
  `web/tests/unit/screens/route-screens.ts` (granted below; REGISTRY's zone is merged and free).
  The registrations link stays registry-driven and appears when W51 registers
  `/admin/registrations`.
- `W50-SHELL-UI`'s notes for the frame: the avatar's 3:1 circle check covers the page and the bar
  surfaces only — the frame places the avatar on the bar; the group at the bar's right edge
  passes `align: 'end'`; real focus, outside click and Tab-away are first exercised by the frame
  and QA in a browser; `DisclosureView`/`MenuView` stay out of the public index, and the frame
  uses the islands.

### Integrator rulings at the Stage-C merge (2026-10-07)

`W50-SHELL-FRAME` (merged at the commit after `9e8d5da`) handed back four questions:

1. **The census lost one pair** (`text|--am-accent|--am-paper|hover|-`): its only site was the
   bar's old «Выйти» button, which this task removed by design. §7's "the census shrinks" is
   about coverage lost while the element stays; here the element is gone. Accepted as an expected
   delta; the screen count rose (86 → 90). The lazy guard's `BASELINE` still reads below the
   merged counts and is raised in `W50-FIX`.
2. **The footer** «Альфа-версия. Изменять данные может эксперт, управлять учётными записями —
   администратор.» — confirmed by the owner's direct poll the same day.
3. The account menu's item says «Сменить пароль» (an action) while the screen's title says
   «Смена пароля» (a name): both stay.
4. The account header for an empty role set says «Роли не назначены.», as the home page does:
   accepted.

Two process changes from the owner's direct polls of the same day apply from here on: `R-70`
(`AGENTS.md` §8) — light acceptance by default, the complete gate only at named points; and
Stage E runs as fresh background subagents launched by the integrator. `W50-JUDGE-Y`'s lazy
baseline is corrected: `W50-FREEZE-01` did not measure a route table, so the judge measures its
own (see that task file).

## 5. Integration order

1. `W50-FREEZE-01`.
2. Stage A: `W50-REGISTRY-01`.
3. Stage B: `W50-SHELL-UI` ∥ `W50-HOME-01` ∥ `W50-LAZY-01` from the Stage-A SHA; merge in that
   order.
4. Stage C: `W50-SHELL-FRAME`.
5. `W50-QA-01`; judges; cross-examination; `W50-FIX`.
6. `W50-INT-CLOSE`.

## 6. Ownership matrix

| Hotspot / path family | Owner | Role | Parallel writer |
| --- | --- | --- | --- |
| `contracts/**`, migrations, backend, root locks | frozen | — | none |
| `shared/config/screen-registry.ts`, `screen-lock.ts`, every `page.tsx` guard call, BFF after-sign-in redirect, sign-in form, `entities/account/**`, `_pages/home` placeholder, `manifest.json`, query namespaces (`query-keys.ts`, `PC01_UI_SEAM.md` §6, their tests) | `W50-REGISTRY-01` (Stage A) | executor | none |
| `shared/ui/**`, `globals.css`, style tests | `W50-SHELL-UI` | executor | HOME, LAZY on disjoint paths |
| `app/page.tsx`, `_pages/home/**`, `widgets/home-*/**` | `W50-HOME-01` | executor | SHELL-UI, LAZY |
| `_pages/**` (not home, sign-in, account, forbidden), `loading.tsx` bodies, `widgets/knowledge-base/**`, `entities/expert-decision/**` | `W50-LAZY-01` | executor | SHELL-UI, HOME |
| `_app/**` except `providers.tsx`, `layout.tsx` | `W50-SHELL-FRAME` (Stage C) | executor | none |
| `web/src/_app/providers.tsx` (composition root), `web/package.json`, `web/package-lock.json` | frozen | — | none |
| `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `origin/dev` | `W50-INT-CLOSE` | integrator | none |

## 7. Stop conditions

`W48-PLAN.md` §14, plus: a screen needs a contract the W49 reseal did not provide; a primitive
cannot meet the contrast or keyboard requirement without a dependency; a route's first-load JS
grows beyond the amended bound of §3.4 or the census shrinks; `next` validation cannot be made exact for an address shape;
a page needs `params` the guard cannot receive.

## 8. Non-goals

No new API; no registration/admin screens (W51); the `/account` screen is a placeholder here;
no avatar upload; no i18n library; no theme change beyond the avatar tokens; no change to
`providers.tsx`.
