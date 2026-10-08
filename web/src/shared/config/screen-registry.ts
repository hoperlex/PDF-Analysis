/**
 * The screen registry — `W50-PLAN.md` §3.1, as owner ruling `R-66` amends its groups.
 *
 * **The only list of screens this application has.** One row per address `web/src/app`
 * serves, and nothing else decides what a screen is called, which navigation group it sits
 * in, whether it is in the menu, and who may open it. Three things hold it to the tree, so a
 * screen cannot be added, removed or renamed in one place only:
 *
 *   - `web/tests/guards/screen-registry.guard.test.ts` derives the set of `page.tsx`
 *     addresses from `web/src/app` and asserts it equals this registry's, both directions;
 *   - `tests/e2e/test_pc01_journey_conformance.py` asserts the journey manifest walks the
 *     same set;
 *   - `web/tests/guards/screen-set.guard.test.ts` asserts every address has a rendering seed.
 *
 * Named *screen* registry because `web/src/shared/lib/routes.ts` already exists and is a
 * different thing: it builds the **concrete** address of one project, run or version from
 * its identities. This module lists the **templates** (`/projects/[project_uid]`) and says
 * who may open each; it does not build links and does not replace `routes`.
 *
 * ## Access, in three nested levels
 *
 *   `public`                      anyone, with or without a session;
 *   `open-to-default-credential`  a session is required, but one still on its seeded or reset
 *                                 password, or with an incomplete profile, may open it — the
 *                                 screens that get such a session out of that state;
 *   `session`                     a session with a changed password, a complete profile and
 *                                 one of the row's `roles`.
 *
 * The guard that reads this is `requireScreen` in `web/src/app/bff/session/screen-lock.ts`,
 * called by every route file. **None of it authorises anything:** the API refuses every
 * operation on its own evidence (`auditmanager.api.security`); this decides where a browser
 * is *sent*.
 *
 * ## The `next` and `from` addresses
 *
 * A guest sent to sign in carries the address it asked for in `next`; a session sent to
 * `/403` carries it in `from`. Both are read back from a query string the browser controls,
 * so both pass one validator here — {@link safeReturnPath} — before anything uses them: in
 * the sign-in form's hidden field, in the BFF's after-sign-in redirect, and on the `/403`
 * screen. A value that fails it is dropped and never echoed.
 */

import type { Role } from '@/shared/api/generated/types.gen';

/** The three access levels, most open first. */
export const SCREEN_ACCESS_LEVELS = ['public', 'open-to-default-credential', 'session'] as const;
export type ScreenAccess = (typeof SCREEN_ACCESS_LEVELS)[number];

/**
 * The navigation groups (`W50-PLAN.md` §3.1, `R-66`). A group with no row the session may
 * open does not render.
 */
export const SCREEN_GROUPS = ['home', 'work', 'knowledge', 'system', 'admin', 'account', 'hidden'] as const;
export type ScreenGroup = (typeof SCREEN_GROUPS)[number];

/**
 * Who may open a `session` screen: `'any'` account, or any one of the listed roles (any-of,
 * as the API's own register reads a role set). A list is never empty.
 */
export type ScreenRoles = 'any' | readonly [Role, ...Role[]];

export interface ScreenEntry {
  /** The Next address, dynamic segments as their directory names: `/projects/[project_uid]`. */
  readonly address: string;
  /** What the screen is called, in Russian, in the menu and wherever it is named. */
  readonly label: string;
  readonly group: ScreenGroup;
  readonly access: ScreenAccess;
  readonly roles: ScreenRoles;
  /** Whether the navigation menu offers it. A screen under a project is reached from it. */
  readonly inMenu: boolean;
}

/**
 * Every screen, in menu order within each group.
 *
 * `R-66`: **Работа** — Проекты, Дашборд, «Оптимизация разделов»; **Знания** — База знаний,
 * Блоки, «Нормы»; **Система** — Журнал выполнения, Исполнители, «Настройки анализа»,
 * «Очередь». `/optimisation` left the menu and stays a registered, reachable screen in
 * `hidden` until project optimisation becomes a project tab. The four new sections are
 * honest stubs, `session`/`any`.
 *
 * The screens under a project are in `work` with `inMenu: false`: they belong to the group
 * the navigation marks current while one of them is open, and they are reached from a
 * project, never from the menu.
 */
export const SCREEN_REGISTRY = [
  { address: '/', label: 'Главная', group: 'home', access: 'session', roles: 'any', inMenu: true },

  { address: '/projects', label: 'Проекты', group: 'work', access: 'session', roles: 'any', inMenu: true },
  { address: '/dashboard', label: 'Дашборд', group: 'work', access: 'session', roles: 'any', inMenu: true },
  {
    address: '/section-optimisation',
    label: 'Оптимизация разделов',
    group: 'work',
    access: 'session',
    roles: 'any',
    inMenu: true,
  },
  {
    address: '/projects/[project_uid]',
    label: 'Проект',
    group: 'work',
    access: 'session',
    roles: 'any',
    inMenu: false,
  },
  {
    address: '/projects/[project_uid]/documents/[document_uid]',
    label: 'Документ',
    group: 'work',
    access: 'session',
    roles: 'any',
    inMenu: false,
  },
  {
    address: '/projects/[project_uid]/versions/[version_uid]',
    label: 'Версия документа',
    group: 'work',
    access: 'session',
    roles: 'any',
    inMenu: false,
  },
  {
    address: '/projects/[project_uid]/versions/[version_uid]/comparison',
    label: 'Сравнение прогонов',
    group: 'work',
    access: 'session',
    roles: 'any',
    inMenu: false,
  },
  {
    address: '/projects/[project_uid]/runs/[run_id]',
    label: 'Прогон',
    group: 'work',
    access: 'session',
    roles: 'any',
    inMenu: false,
  },
  {
    address: '/projects/[project_uid]/runs/[run_id]/review',
    label: 'Разбор находок',
    group: 'work',
    access: 'session',
    roles: 'any',
    inMenu: false,
  },

  {
    address: '/knowledge-base',
    label: 'База знаний',
    group: 'knowledge',
    access: 'session',
    roles: 'any',
    inMenu: true,
  },
  { address: '/blocks', label: 'Блоки', group: 'knowledge', access: 'session', roles: 'any', inMenu: true },
  { address: '/norms', label: 'Нормы', group: 'knowledge', access: 'session', roles: 'any', inMenu: true },

  {
    address: '/logs',
    label: 'Журнал выполнения',
    group: 'system',
    access: 'session',
    roles: 'any',
    inMenu: true,
  },
  { address: '/workers', label: 'Исполнители', group: 'system', access: 'session', roles: 'any', inMenu: true },
  {
    address: '/analysis-settings',
    label: 'Настройки анализа',
    group: 'system',
    access: 'session',
    roles: 'any',
    inMenu: true,
  },
  { address: '/queue', label: 'Очередь', group: 'system', access: 'session', roles: 'any', inMenu: true },

  {
    address: '/optimisation',
    label: 'Оптимизация',
    group: 'hidden',
    access: 'session',
    roles: 'any',
    inMenu: false,
  },

  {
    address: '/admin/users',
    label: 'Пользователи',
    group: 'admin',
    access: 'session',
    roles: ['admin'],
    inMenu: true,
  },
  {
    address: '/admin/users/[user_uid]',
    label: 'Пользователь',
    group: 'admin',
    access: 'session',
    roles: ['admin'],
    inMenu: false,
  },
  {
    address: '/admin/registrations',
    label: 'Заявки на регистрацию',
    group: 'admin',
    access: 'session',
    roles: ['admin'],
    inMenu: true,
  },

  { address: '/login', label: 'Вход', group: 'account', access: 'public', roles: 'any', inMenu: false },
  { address: '/register', label: 'Регистрация', group: 'account', access: 'public', roles: 'any', inMenu: false },
  {
    address: '/register/submitted',
    label: 'Заявка на регистрацию',
    group: 'account',
    access: 'public',
    roles: 'any',
    inMenu: false,
  },
  {
    address: '/account',
    label: 'Профиль',
    group: 'account',
    access: 'open-to-default-credential',
    roles: 'any',
    inMenu: false,
  },
  {
    address: '/account/password',
    label: 'Смена пароля',
    group: 'account',
    access: 'open-to-default-credential',
    roles: 'any',
    inMenu: false,
  },

  { address: '/403', label: 'Доступ закрыт', group: 'hidden', access: 'public', roles: 'any', inMenu: false },
] as const satisfies readonly ScreenEntry[];

/** The registered addresses, as a type: a route file cannot name an address that is not here. */
export type ScreenAddress = (typeof SCREEN_REGISTRY)[number]['address'];

/** The access level of one registered address, as a type. */
export type ScreenAccessOf<A extends ScreenAddress> = Extract<
  (typeof SCREEN_REGISTRY)[number],
  { readonly address: A }
>['access'];

/** The addresses the guard's redirects land on. Each is a row above. */
export const HOME_SCREEN = '/' satisfies ScreenAddress;
export const SIGN_IN_SCREEN = '/login' satisfies ScreenAddress;
export const CHANGE_PASSWORD_SCREEN = '/account/password' satisfies ScreenAddress;
export const PROFILE_SCREEN = '/account' satisfies ScreenAddress;
export const FORBIDDEN_SCREEN = '/403' satisfies ScreenAddress;

/** The query parameters the guard's redirects carry the asked-for address in. */
export const NEXT_PARAM = 'next';
export const FROM_PARAM = 'from';

// ---------------------------------------------------------------- who may open a screen

/**
 * What a session is, as far as opening a screen goes: its roles and the two states that keep
 * it out of `session` screens. A role this tier does not know is a plain string here, so it
 * reaches {@link screenDecision} and matches no row instead of being dropped on the way.
 */
export interface ScreenDecisionSubject {
  readonly roles: readonly string[];
  readonly isDefaultCredential: boolean;
  readonly profileComplete: boolean;
}

/**
 * What happens when `subject` (or a guest, `null`) asks for `screen`: it opens, or the
 * browser is sent to sign in, to change a default password, to complete the profile, or to
 * `/403`.
 */
export type ScreenDecision = 'open' | 'sign-in' | 'change-password' | 'complete-profile' | 'forbidden';

/**
 * **The one answer to "may this session open this screen".** `requireScreen` maps each
 * answer to its redirect (`web/src/app/bff/session/screen-lock.ts`), and the frame's
 * navigation offers exactly the rows whose answer is `open` — one function, so the menu
 * cannot offer a screen the guard refuses, or hide one it opens (`W50-SHELL-FRAME`; the
 * integrator's grant of 2026-10-07 moved it here out of `enforceScreen`, unchanged).
 *
 * In order, and the order is the behaviour:
 *
 *   1. a guest opens only `public` screens, and is sent to sign in from any other;
 *   2. `R-50`: a default credential opens no `session` screen — only the ones that change it;
 *   3. `R-59`: nor does an incomplete profile — only the ones that complete it;
 *   4. a `session` screen with roles needs any one of them; a role value this tier does not
 *      know matches no row, so it is refused like a missing one and never read as `any`.
 *
 * It decides where a browser is *sent* and what a menu *offers*; it authorises nothing. The
 * API refuses every operation on its own evidence.
 */
export function screenDecision(screen: ScreenEntry, subject: ScreenDecisionSubject | null): ScreenDecision {
  if (subject === null) return screen.access === 'public' ? 'open' : 'sign-in';
  if (screen.access === 'session') {
    if (subject.isDefaultCredential) return 'change-password';
    if (!subject.profileComplete) return 'complete-profile';
    if (screen.roles !== 'any' && !screen.roles.some((role) => subject.roles.includes(role))) return 'forbidden';
  }
  return 'open';
}

/** The registry row for an address, or `undefined` for one that is not registered. */
export function screenAt(
  address: string,
  registry: readonly ScreenEntry[] = SCREEN_REGISTRY,
): ScreenEntry | undefined {
  return registry.find((screen) => screen.address === address);
}

// ------------------------------------------------------------------- the return address

/** The longest `next`/`from` this application carries. Anything longer is dropped. */
export const RETURN_PATH_MAX_LENGTH = 512;

/**
 * What one dynamic segment's value may be: RFC 3986 unreserved characters, and not a
 * segment made only of dots.
 *
 * Every identity this application addresses is `<prefix>_<ULID>`, so this is wider than any
 * real value and narrower than anything that could change where a browser goes: no `/`, no
 * `\`, no `%` (so no encoded separator), no `:` and no `.`/`..`.
 */
const SEGMENT_VALUE = /^(?!\.+$)[A-Za-z0-9._~-]+$/;

/**
 * What a query string may hold: RFC 3986 query characters, with every `%` the start of a
 * complete escape. No space, no control character, no `#`, no `\`, nothing outside ASCII —
 * so the value is safe to put in a `Location` header and in an attribute exactly as it is.
 */
const QUERY = /^(?:[A-Za-z0-9\-._~!$&'()*+,;=:@/?]|%[0-9A-Fa-f]{2})*$/;

/** True when `path` (no query) has the shape of `template` (a registry address). */
function pathMatches(path: string, template: string): boolean {
  const asked = path.split('/');
  const shape = template.split('/');
  if (asked.length !== shape.length) return false;
  return shape.every((part, index) => {
    const value = asked[index] as string;
    return /^\[[^\]]+\]$/.test(part) ? SEGMENT_VALUE.test(value) : value === part;
  });
}

/** The registry row whose address shape `path` (no query) has, if any. */
export function screenMatching(
  path: string,
  registry: readonly ScreenEntry[] = SCREEN_REGISTRY,
): ScreenEntry | undefined {
  return registry.find((screen) => pathMatches(path, screen.address));
}

/**
 * The one validator for `next` and `from` (`W50-PLAN.md` §3.2). Returns the value when it is
 * a same-application address and `null` for anything else — the caller drops a `null`, and
 * never echoes what it was given.
 *
 * A value passes when it is a string of at most {@link RETURN_PATH_MAX_LENGTH} characters
 * that starts with exactly one `/` (so not `//host…`, which a browser reads as another
 * origin, and not `/\host…`, which some browsers read the same way), carries no scheme, and
 * whose path — everything before the first `?` — has the shape of a registered address; the
 * query, if any, must be made of query characters only.
 *
 * **The fragment is not preserved.** A browser never sends the part after `#` to the
 * server, so the guard that builds `next` never sees it, and a value carrying a `#` did not
 * come from the guard: it is dropped whole rather than trimmed.
 */
export function safeReturnPath(
  candidate: unknown,
  registry: readonly ScreenEntry[] = SCREEN_REGISTRY,
): string | null {
  if (typeof candidate !== 'string') return null;
  if (candidate.length === 0 || candidate.length > RETURN_PATH_MAX_LENGTH) return null;
  if (!candidate.startsWith('/')) return null;
  // Two independent layers refuse `//host` and `/\host`: this line, and the shape check
  // below — an empty segment or a backslash never matches a registered segment. Either alone
  // suffices, so removing one changes no answer; removing both is red in
  // `web/tests/unit/session/return-path.test.ts` (`W50-REGISTRY-01` report, mutation M05g).
  if (candidate.startsWith('//') || candidate.startsWith('/\\')) return null;
  const queryAt = candidate.indexOf('?');
  const path = queryAt === -1 ? candidate : candidate.slice(0, queryAt);
  const query = queryAt === -1 ? '' : candidate.slice(queryAt + 1);
  // No scheme: a path that matches a registered shape has no `:` in it, and the query is
  // checked character by character. Said here so it is not mistaken for an omission.
  if (screenMatching(path, registry) === undefined) return null;
  if (!QUERY.test(query)) return null;
  return candidate;
}

/** The values Next hands a route file: `params` and `searchParams`, each a promise. */
export type RouteParams = Readonly<Record<string, string | string[] | undefined>>;

/**
 * The concrete address a route file is serving, rebuilt from its template, its `params` and
 * its `searchParams`: `/projects/[project_uid]` with `{project_uid: 'prj_…'}` and `{x: '1'}`
 * is `/projects/prj_…?x=1`. `null` when a segment has no single value.
 *
 * The query is re-encoded by `URLSearchParams`, so what comes out is made of query
 * characters whatever the browser sent; {@link safeReturnPath} still has the last word.
 */
export function concreteAddress(
  template: string,
  params: RouteParams,
  searchParams: RouteParams,
): string | null {
  let missing = false;
  const path = template.replace(/\[([^\]]+)\]/g, (_, name: string) => {
    const value = params[name];
    if (typeof value !== 'string' || value.length === 0) {
      missing = true;
      return '';
    }
    return value;
  });
  if (missing) return null;
  const query = new URLSearchParams();
  for (const [name, value] of Object.entries(searchParams)) {
    if (value === undefined) continue;
    for (const one of Array.isArray(value) ? value : [value]) query.append(name, one);
  }
  const encoded = query.toString();
  return encoded.length === 0 ? path : `${path}?${encoded}`;
}

/**
 * The roles the screen at `from` requires, for the `/403` screen to name — or `null` when
 * `from` is not a valid return address, or names a screen that requires no role.
 *
 * Takes the registry as a parameter so the case `W50` cannot reach with its own rows — a
 * role-gated screen; `R-60` gives none of W50's screens a role — is testable against a
 * registry that has one.
 */
export function requiredRolesFor(
  from: unknown,
  registry: readonly ScreenEntry[] = SCREEN_REGISTRY,
): readonly Role[] | null {
  const valid = safeReturnPath(from, registry);
  if (valid === null) return null;
  const queryAt = valid.indexOf('?');
  const screen = screenMatching(queryAt === -1 ? valid : valid.slice(0, queryAt), registry);
  if (screen === undefined || screen.roles === 'any') return null;
  return screen.roles;
}
