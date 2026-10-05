# Wave 50 — the shell: route registry, server guards, redirects, lazy loading, grouped navigation, home, account menu

**Status:** planned; dispatchable after `W49-INT-CLOSE` and `W50-FREEZE-01`.
**Controlling rulings:** `R-55`, `R-57`, `R-60` (provisional numbers).
**Exit:** every screen is behind one route registry; the frame has grouped navigation, a real
home page and the account menu; on `origin/dev` with literal `GATE OK`. No contract change.

## 1. Objective

One declarative registry decides what the menu shows, which screens a guest, a default
credential, an expert or an administrator may open, and where a refused request is sent. The
frame grows a home page, grouped dropdown navigation and an account menu under a generated
avatar. Heavy client widgets load lazily behind typed loading and error boundaries. All of it
without a new dependency and without touching the API.

## 2. Entry conditions

| Condition | Evidence |
| --- | --- |
| `W49-INT-CLOSE` done; session subject carries `roles`, `displayLabel`, `initials` | `origin/dev`; `web/src/app/bff/session/store.ts` |
| generated client exposes `getMe`, `listRegistrations` | `web/src/shared/api/generated/operations.gen.ts` |
| frontend baseline green | `npm --prefix web test -- --run` count recorded by the freeze |

## 3. Design decisions bound by this plan

### 3.1 Route registry — `web/src/shared/config/routes.ts`

One array of entries `{ address, label, group, access, roles, inMenu }`:

- `address` is the Next address with dynamic segments (`/projects/[project_uid]`);
- `access ∈ {'public', 'open-to-default-credential', 'session'}`;
- `roles ∈ {'any', 'expert', 'admin'}` (a screen that needs both lists both);
- `group ∈ {'home', 'work', 'knowledge', 'system', 'admin', 'account', 'hidden'}`;
- the registry is the **only** list of screens: a test derives the set of `page.tsx` addresses
  from `web/src/app` (the walker in `web/tests/unit/screens/route-screens.ts`) and asserts it
  equals the registry's addresses — both directions.

Groups (P-11, accepted as proposed): Главная `/`; **Работа** — Проекты `/projects`, Дашборд `/dashboard`;
**Знания** — База знаний `/knowledge-base`, Блоки `/blocks`; **Система** — Оптимизация
`/optimisation`, Журнал выполнения `/logs`, Исполнители `/workers`; **Администрирование** —
rows are added by W51; the group renders only when it has rows the session may open.

### 3.2 Server guard — `requireScreen(address)` in `web/src/app/bff/session/screen-lock.ts`

Replaces `requireAChangedPassword()` in every `page.tsx`; the old function is removed.
Order of decisions, each a redirect or a render, never a thrown framework error:

1. no session and `access !== 'public'` → `redirect('/login?next=<validated>')`;
2. session on a default credential or with `profileComplete === false`, and the screen is not
   `open-to-default-credential` → the change/completion screen (`/account/password`, or
   `/account` when only the profile is incomplete);
3. session lacking a required role → `redirect('/403')`;
4. a session visiting `/login` → `redirect('/')`.

`next` validation: a string that starts with exactly one `/`, is not `//…` or `/\…`, has no
scheme, is at most 512 characters, and whose path matches a registry address shape; anything
else is dropped, never echoed. `search` and `hash` are preserved (the `technic` return-after-login
loses them; this one does not).

Why not middleware: the register lives in this Node process's memory and on its volume
(`R-47`/`R-51`); middleware runs in another runtime and cannot read the session. Why not the
layout: a server layout does not know which address it renders. The call-per-route plus the
registry completeness test is what makes "no unregistered screen opens" a property of the
application (the existing argument in `screen-lock.ts`).

### 3.3 Redirect and error screens

- `/403` — a registered screen, Russian, inside the frame, with the required role named from the
  registry; `app/not-found.tsx` stays and gets the frame.
- `app/error.tsx` and per-segment `loading.tsx` (`projects`, `projects/[project_uid]`,
  `dashboard`, `knowledge-base`, `admin` reserved for W51): typed states from `shared/ui/states`.
- Nothing renders a raw error message or an English framework string.

### 3.4 Lazy loading — `W50-LAZY-01`

`next/dynamic` with a `loading` state for the heavy client widgets: `widgets/evidence-viewer`,
`widgets/stage-comparison`, `widgets/run-progress`, `widgets/knowledge-base`,
`widgets/dashboard`. SSR stays on for everything the cold-load test measures. A guard asserts no
`_pages/**` module imports those five widgets statically.

### 3.5 Frame, navigation, account menu — `W50-SHELL-01`

- The frame (`web/src/_app/app-frame.tsx`) stays a server component; the dropdowns and the
  account menu are client islands under `web/src/_app/`.
- Primitives in `web/src/shared/ui/`: `Dropdown` (trigger is a `<button aria-haspopup="menu"
  aria-expanded>`; Escape, Arrow keys, Home/End, Tab leaves, click outside closes, focus returns
  to the trigger), `Avatar` (initials from `displayLabel`; colour = one of fourteen tokens
  `--am-avatar-01…14` chosen by a hash of the **e-mail**, white text, every pair passes the
  existing contrast test), `MenuGroup`.
- Navigation: groups of §3.1 filtered by the session's roles; the current group and item carry
  `aria-current`; below 780 px the groups render as a single stacked list behind one «Меню»
  button — no horizontal overflow.
- Account menu, top right: avatar trigger; header with `displayLabel`, e-mail and the role labels
  (Эксперт, Администратор); items Профиль `/account`, Сменить пароль `/account/password`, Выйти
  (POST to `/bff/v1/session/end`, unchanged). A guest sees one «Вход» link. The footer sentence
  «Один проверяющий, без разделения доступа…» is replaced; the guard
  `screen-claims-about-the-system.guard.test.ts` is updated to the new truthful sentence.
- `entities/account/**`: the `getMe` consumer, `displayLabel`/`initials` helpers, Russian role
  labels, query key `account.me`. W51 consumes it.
- No new dependency. `globals.css` is edited by this task only.

### 3.6 Home page — `W50-HOME-01`

`app/page.tsx` stops redirecting. The home page greets by `displayLabel`, lists the five most
recent projects (`listProjects`), shows the dashboard summary tile the frozen contract already
provides, and, for an `admin` session, a «Заявки на регистрацию» tile with `pending_total` from
`listRegistrations` linking to `/admin/registrations` (a W51 screen; the link renders only when
the registry has that row — until then the tile shows the count without a link). Projects moves
to the «Работа» group as its first item.

## 4. Tasks

### `W50-FREEZE-01`
Base SHA; frontend baseline counts by file; task files; ports; provisional ruling numbers replaced by the recorded ones.

### `W50-REGISTRY-01` — Stage A, alone
- **Allowed paths:** `web/src/shared/config/routes.ts`, `web/src/shared/config/index.ts`,
  `web/src/app/bff/session/screen-lock.ts`, every `web/src/app/**/page.tsx` (the guard call swap
  and nothing else), `web/src/app/403/**`, `web/src/app/not-found.tsx`, `web/src/app/error.tsx`,
  `web/src/app/**/loading.tsx` (empty typed placeholders; LAZY fills them),
  `web/src/_pages/forbidden/**`, `web/tests/unit/screens/route-screens.ts`,
  `web/tests/guards/default-credential-screens.guard.test.ts` → `screen-guard.guard.test.ts`,
  `web/tests/guards/route-registry.guard.test.ts` (new), `web/tests/unit/session/**`,
  `docs/program/W50-REGISTRY-01.md`.
- **Deliverables:** §3.1–§3.3; `app/page.tsx` becomes a registered placeholder page
  (`RoutePlaceholder`) that HOME replaces.
- **Required tests and mutations:** a `page.tsx` without `requireScreen` is red naming its
  address; a registry row without a page is red; a page without a row is red; `next=//evil.example`,
  `next=https://evil.example`, `next=/\evil`, `next=` of 513 chars are dropped; `next=/projects?x=1#y`
  survives sign-in; an expert on `/403` sees the role name; a signed-in visit to `/login`
  redirects; `npm --prefix web test -- --run`; lint; typecheck.

### `W50-SHELL-01`, `W50-HOME-01`, `W50-LAZY-01` — Stage B, parallel, disjoint
- **SHELL allowed paths:** `web/src/_app/**` except `providers.tsx`, `web/src/shared/ui/**`,
  `web/src/entities/account/**`, `web/src/app/globals.css`, `web/src/app/layout.tsx`
  (passing the full subject), `web/tests/unit/styles/**`, `web/tests/unit/widgets/**`,
  `web/tests/guards/screen-claims-about-the-system.guard.test.ts`,
  `web/tests/guards/rendered-language.guard.test.ts` (fixtures only), `docs/program/W50-SHELL-01.md`.
- **HOME allowed paths:** `web/src/app/page.tsx`, `web/src/_pages/home/**`,
  `web/src/widgets/home-*/**`, `web/tests/unit/screens/home.test.ts`, `docs/program/W50-HOME-01.md`.
- **LAZY allowed paths:** `web/src/_pages/**` except `home` and `sign-in`, the `loading.tsx`
  files REGISTRY created, `web/tests/unit/screens/cold-load.test.ts`,
  `web/tests/guards/lazy-boundary.guard.test.ts` (new), `docs/program/W50-LAZY-01.md`.
- **Required mutations:** SHELL — a `div` trigger instead of a `button` is red; a palette token
  below the contrast floor is red; the menu rendered for `roles: []` shows no admin group; the
  account header for a 200-character name does not widen the frame at 780 px. HOME — the admin
  tile is absent for an expert-only session; an unknown role label is a typed fault. LAZY — a
  static import of a lazy widget in `_pages/**` is red; the cold-load numbers do not regress.

### `W50-QA-01`
New files under `web/tests/unit/qa_w51/**` only: keyboard paths through both dropdowns; focus
return; Escape; outside click; guest redirect for every registered `session` screen; `admin`
screens absent for an expert; 780 × 900 overflow for every menu state.

### `W50-JUDGE-X`, `W50-JUDGE-Y`
- X: black-box in a built stand — open-redirect attempts; direct navigation to each role-gated
  address with the other role; default credential bypass attempts; keyboard-only operation of the
  whole shell; console errors; 780 px with hostile names.
- Y: FSD boundaries (`eslint-boundary.guard.test.ts`), the registry as the single source
  (`rg -n "href=" web/src/_app` shows no address outside the registry), no `fetch` outside
  `shared/api`, lazy boundaries do not disable SSR for measured screens, `globals.css` has a
  rule for every new class (`styling-layer.test.ts`), no new dependency, lock bytes unchanged.

### `W50-FIX`, `W50-INT-CLOSE`
Standard; `CURRENT_STATE.md` live section; `origin/dev`; stop.

## 5. Integration order

1. `W50-FREEZE-01`.
2. Stage A: `W50-REGISTRY-01`.
3. Stage B: `W50-SHELL-01` ∥ `W50-HOME-01` ∥ `W50-LAZY-01` from the Stage-A SHA.
4. Merge SHELL, HOME, LAZY in that order; `W50-QA-01`; judges; cross-examination.
5. `W50-FIX`; `W50-INT-CLOSE`.

## 6. Ownership matrix

| Hotspot / path family | Owner | Parallel writer |
| --- | --- | --- |
| `contracts/**`, migrations, backend, root locks | frozen | none |
| `web/src/shared/config/routes.ts`, `screen-lock.ts`, every `page.tsx` guard call | `W50-REGISTRY-01` (Stage A) | none |
| `web/src/_app/**`, `shared/ui/**`, `globals.css`, `layout.tsx`, `entities/account/**` | `W50-SHELL-01` | HOME, LAZY on disjoint paths |
| `web/src/_app/providers.tsx` (composition root) | frozen | none |
| `app/page.tsx`, `_pages/home/**`, `widgets/home-*/**` | `W50-HOME-01` | SHELL, LAZY |
| `_pages/**` (not home, not sign-in), `loading.tsx` bodies | `W50-LAZY-01` | SHELL, HOME |
| `web/package.json`, `web/package-lock.json` | frozen | none |
| `CURRENT_STATE.md`, `origin/dev` | `W50-INT-CLOSE` | none |

## 7. Stop conditions

`W48-PLAN.md` §14, plus: a screen needs a contract the W49 reseal did not provide; a primitive
cannot meet the contrast or keyboard requirement without a dependency; lazy loading changes a
measured cold-load number for the worse; `next` validation cannot be made exact for an address
shape.

## 8. Non-goals

No new API; no registration/admin screens (W51); no avatar upload; no i18n library; no theme
change beyond the avatar tokens; no change to `providers.tsx`.
