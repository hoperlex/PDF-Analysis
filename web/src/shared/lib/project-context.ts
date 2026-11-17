/**
 * The project (the «объект») the user works in, read from the address, or, when the address names none, taken from the
 * account's last choice (`R-150c`, `UI-PARITY-01` «Project context», `UIP-G-06`, owner ruling Г7-B).
 *
 * **The address is the only source of an explicit choice.** No store, no cookie, no copy in client state: a reload, a pasted
 * link and Back/Forward all restore the project from the address alone. What the address does not say, the server's
 * answer fills in: `getMe` carries `last_project_uid`, the object the account chose last in the list (`setMyLastProject`);
 * there is no hidden state of the browser tab. These helpers are the one place that knows how it is spelled. They are pure
 * functions over a pathname, a query string and the account's answer; they do not navigate and they do not fetch.
 *
 * ## The order of what wins (`resolveProjectContext`)
 *
 *   1. the path, `/projects/[project_uid]…` (a `required` screen);
 *   2. `?project=<project_uid>`;
 *   3. `?project=all`, the explicit choice «Все объекты»;
 *   4. the account's `last_project_uid`, on an `optional` screen only;
 *   5. nothing: «Все объекты».
 *
 * «Все объекты» is written `?project=all` ({@link ALL_PROJECTS_PARAM}). The absence of the parameter is no longer «все
 * объекты»: it is «the object the account chose last», and where there is none, «все объекты». `all` can never be a
 * project's uid (those are `prj_…`), and the explicit choice is not sent to the server (`setMyLastProject` has no body
 * for it), so it lives in the address only.
 *
 * ## The three classes
 *
 * Each registered screen carries a `projectScope` in the screen registry
 * (`web/src/shared/config/screen-registry.ts`):
 *
 *   - `required`: the project is in the path (`/projects/[project_uid]…`). It is always there; a
 *     `?project=` beside it is redundant, and where the two disagree **the path wins**.
 *   - `optional`: the screen follows the project the header chose, carried in `?project=`.
 *     Without it the screen shows the account's last object, and «Все объекты» where there is none (a comparison asks to
 *     choose one).
 *   - `global`: the screen is not about one project. It ignores `?project=` and the account's last choice, but the frame
 *     carries the address's project on, so a chosen project survives a visit to «Очередь» and back.
 *
 * An address no registry row matches (a 404, a typo) has no class: nothing reads a project from it
 * and nothing is added to links that lead to it.
 *
 * ## Why these helpers and not a generic query-string helper
 *
 * Each has a rule of its own: which source wins, which parameters die with a project change, which
 * targets must not receive the parameter. They are not a general `getParam`/`setParam`.
 *
 * The identity is opaque: a project uid is never parsed or validated here beyond "present and not
 * empty". Whether it names a real project is the screen's question (unknown project on a required
 * screen is an explicit not-found there).
 */

import type { ScreenEntry } from '@/shared/config';
import { SCREEN_REGISTRY, screenMatching } from '@/shared/config';

/** The query parameter that carries the project on `optional` and `global` screens. */
export const PROJECT_PARAM = 'project';

/**
 * The value of `?project=` that is the explicit choice «Все объекты» (`UIP-G-06`). It beats the account's last object, which
 * the absence of the parameter does not. A project uid is `prj_…`, so it never reads as this.
 */
export const ALL_PROJECTS_PARAM = 'all';

/**
 * The parameters that only mean something inside one project. A project change removes them: a
 * `section`, `version`, `pair`, `set`, `run`, `cursor` or `tab` of one project names nothing in
 * another, and carrying it over would open the new project on a stale selection.
 */
export const PROJECT_DEPENDENT_PARAMS = ['section', 'version', 'pair', 'set', 'run', 'cursor', 'tab'] as const;

/** The path segment of the project in a registry address. */
const PROJECT_SEGMENT = '[project_uid]';

/** The class of a screen, as the registry states it. */
export type ProjectScope = NonNullable<ScreenEntry['projectScope']>;

/**
 * Where the project came from: the path, a `?project=<uid>`, the explicit `?project=all` (no project, chosen), the account's
 * last object (`resolveProjectContext` only; an address alone never says it), or nowhere.
 */
export type ProjectSource = 'path' | 'query' | 'all' | 'remembered' | 'none';

export interface ProjectContext {
  /** The project's uid; `null` for «Все объекты», chosen (`source` `all`) or not (`none`). */
  readonly projectUid: string | null;
  readonly source: ProjectSource;
}

/** What these helpers need of a query string: both `URLSearchParams` and Next's read-only one have it. */
export type SearchParamsLike = Pick<URLSearchParams, 'get' | 'toString'>;

const NO_PROJECT: ProjectContext = { projectUid: null, source: 'none' };
const ALL_CHOSEN: ProjectContext = { projectUid: null, source: 'all' };

/** The registry row of `pathname` (no query, no fragment), with its class checked to be stated. */
function rowOf(
  pathname: string,
  registry: readonly ScreenEntry[],
): (ScreenEntry & { readonly projectScope: ProjectScope }) | undefined {
  const row = screenMatching(pathname, registry);
  if (row === undefined) return undefined;
  if (row.projectScope === undefined) {
    // Every row of the live registry states it (a type and a guard test). A registry that does not
    // is a defect to surface, not a screen to treat as `global`.
    throw new Error(`The screen registry row ${row.address} has no projectScope.`);
  }
  return { ...row, projectScope: row.projectScope };
}

/** The project uid in the path of a `required` row, from the position of `[project_uid]` in its address. */
function pathProjectUid(pathname: string, row: ScreenEntry): string {
  const at = row.address.split('/').indexOf(PROJECT_SEGMENT);
  const uid = at === -1 ? undefined : pathname.split('/')[at];
  if (uid === undefined || uid === '') {
    throw new Error(`The required-project screen ${row.address} has no ${PROJECT_SEGMENT} segment.`);
  }
  return uid;
}

/** The raw `?project=` of a query string: a uid, {@link ALL_PROJECTS_PARAM}, or `null`; an empty one names none. */
function queryProjectUid(searchParams: SearchParamsLike): string | null {
  const value = searchParams.get(PROJECT_PARAM);
  return value === null || value === '' ? null : value;
}

/** True for an address inside this application: one `/`, not `//host` and not `/\host`. */
function isApplicationPath(href: string): boolean {
  return href.startsWith('/') && !href.startsWith('//') && !href.startsWith('/\\');
}

/**
 * The class of the screen `pathname` addresses, or `null` when no registry row matches it.
 *
 * @param pathname the path only, without query or fragment.
 */
export function projectScopeOf(
  pathname: string,
  registry: readonly ScreenEntry[] = SCREEN_REGISTRY,
): ProjectScope | null {
  return rowOf(pathname, registry)?.projectScope ?? null;
}

/**
 * The project an address names, and where it came from. The address alone: the account's last object is
 * {@link resolveProjectContext}'s.
 *
 *   - on a `required` screen, the path's `project_uid` (`'path'`), whatever `?project=` says;
 *   - on an `optional` or `global` screen, the non-empty `?project=<uid>` (`'query'`) — a `global`
 *     screen ignores it for its own content but the frame still reads it, to carry it on;
 *   - `?project=all` is the explicit «Все объекты»: no project, and `'all'`, so that it can be told from an address that
 *     says nothing;
 *   - otherwise nothing (`'none'`): no parameter, an empty one, or an address with no class.
 *
 * @param pathname the path only, without query or fragment.
 */
export function readProjectContext(
  pathname: string,
  searchParams: SearchParamsLike,
  registry: readonly ScreenEntry[] = SCREEN_REGISTRY,
): ProjectContext {
  const row = rowOf(pathname, registry);
  if (row === undefined) return NO_PROJECT;
  if (row.projectScope === 'required') return { projectUid: pathProjectUid(pathname, row), source: 'path' };
  const fromQuery = queryProjectUid(searchParams);
  if (fromQuery === null) return NO_PROJECT;
  return fromQuery === ALL_PROJECTS_PARAM ? ALL_CHOSEN : { projectUid: fromQuery, source: 'query' };
}

/**
 * The project a screen works in: what the address names, and where it names none, the account's last object.
 *
 * `remembered` is `last_project_uid` of `getMe`: a uid, or `null`/`undefined` for «no last object» and «not known (yet)».
 * It is read only on an `optional` screen, the ones that follow the object; a `global` screen and an address with no class
 * keep what the address says. The order is {@link readProjectContext}'s (path, `?project=<uid>`, `?project=all`), then the
 * remembered object (`'remembered'`), then nothing.
 *
 * @param pathname the path only, without query or fragment.
 */
export function resolveProjectContext(
  pathname: string,
  searchParams: SearchParamsLike,
  remembered: string | null | undefined,
  registry: readonly ScreenEntry[] = SCREEN_REGISTRY,
): ProjectContext {
  const fromAddress = readProjectContext(pathname, searchParams, registry);
  if (fromAddress.source !== 'none') return fromAddress;
  if (remembered === null || remembered === undefined || remembered === '') return fromAddress;
  return projectScopeOf(pathname, registry) === 'optional' ? { projectUid: remembered, source: 'remembered' } : fromAddress;
}

/**
 * The query string an address should have: a copy of `searchParams` in which the path wins and a
 * project is spelled one way.
 *
 *   - on a `required` screen `?project=` is dropped: the path already says it, and when the two
 *     differ the query must not contradict it;
 *   - elsewhere an empty `?project=` is dropped (no project is the absence of the parameter) and a
 *     repeated one keeps the first value, as {@link readProjectContext} reads it;
 *   - an address with no class is returned unchanged.
 *
 * Every other parameter keeps its value and its order. The caller compares the result's `toString()`
 * with the current query to decide whether to rewrite the address.
 *
 * @param pathname the path only, without query or fragment.
 */
export function canonicalProjectParams(
  pathname: string,
  searchParams: SearchParamsLike,
  registry: readonly ScreenEntry[] = SCREEN_REGISTRY,
): URLSearchParams {
  const params = new URLSearchParams(searchParams.toString());
  const scope = projectScopeOf(pathname, registry);
  if (scope === null) return params;
  if (scope === 'required') {
    params.delete(PROJECT_PARAM);
    return params;
  }
  const first = params.get(PROJECT_PARAM);
  if (first === '') params.delete(PROJECT_PARAM);
  else if (first !== null && params.getAll(PROJECT_PARAM).length > 1) params.set(PROJECT_PARAM, first);
  return params;
}

/**
 * `href` with the project carried onto it: for a link the frame draws, so choosing a project
 * outlives a click.
 *
 *   - an `optional` or `global` target gets `?project=<projectUid>` (replacing one it already had),
 *     and keeps the rest of its query and its fragment;
 *   - a `required` target is returned unchanged — its project is in its path, and a second copy
 *     could only disagree with it;
 *   - `projectUid` {@link ALL_PROJECTS_PARAM} carries the explicit «Все объекты» the same way, as `?project=all`;
 *   - `projectUid` `null` (or empty), no project, removes `?project=` from an `optional` or
 *     `global` target;
 *   - an `href` that is not a registered address of this application (another origin, a typo,
 *     a relative path) is returned unchanged.
 */
export function withProjectParam(
  href: string,
  projectUid: string | null,
  registry: readonly ScreenEntry[] = SCREEN_REGISTRY,
): string {
  if (!isApplicationPath(href)) return href;
  const fragmentAt = href.indexOf('#');
  const beforeFragment = fragmentAt === -1 ? href : href.slice(0, fragmentAt);
  const fragment = fragmentAt === -1 ? '' : href.slice(fragmentAt);
  const queryAt = beforeFragment.indexOf('?');
  const pathname = queryAt === -1 ? beforeFragment : beforeFragment.slice(0, queryAt);
  const query = queryAt === -1 ? '' : beforeFragment.slice(queryAt + 1);

  const scope = projectScopeOf(pathname, registry);
  if (scope === null || scope === 'required') return href;

  const params = new URLSearchParams(query);
  if (projectUid === null || projectUid === '') {
    if (!params.has(PROJECT_PARAM)) return href;
    params.delete(PROJECT_PARAM);
  } else {
    if (params.getAll(PROJECT_PARAM).length === 1 && params.get(PROJECT_PARAM) === projectUid) return href;
    params.set(PROJECT_PARAM, projectUid);
  }
  const encoded = params.toString();
  return `${pathname}${encoded === '' ? '' : `?${encoded}`}${fragment}`;
}

/**
 * The query string after the user chooses `newProjectUid` in the header, on an `optional` or
 * `global` screen: the new project is set, and every parameter that only meant something inside the
 * old one ({@link PROJECT_DEPENDENT_PARAMS}) is removed. `null` (or empty) is «Все объекты», and it is a choice like any
 * other: `?project=all` ({@link ALL_PROJECTS_PARAM}), not the absence of the parameter, which would let the account's last
 * object come back (`UIP-G-06`).
 *
 * Choosing what the address already says changes nothing — the user keeps their selection. The dependent parameters go
 * with a change of project, and only then: `effectiveProjectUid` is the project the screen is on when the address says
 * none (the account's last object), so choosing that very object writes it into the address and keeps the rest; left out,
 * it is read from the address (`?project=<uid>`, or `null` for `all` and for none). Every other parameter is kept. On a
 * `required` screen the header navigates to the chosen project's page instead; that is a path, not a query, and not this
 * function.
 */
export function switchProject(
  searchParams: SearchParamsLike,
  newProjectUid: string | null,
  effectiveProjectUid?: string | null,
): URLSearchParams {
  const params = new URLSearchParams(searchParams.toString());
  const wanted = newProjectUid === null || newProjectUid === '' ? ALL_PROJECTS_PARAM : newProjectUid;
  const current = queryProjectUid(params);
  if (current === wanted) return params;
  const before = effectiveProjectUid !== undefined ? effectiveProjectUid : current === ALL_PROJECTS_PARAM ? null : current;
  const after = wanted === ALL_PROJECTS_PARAM ? null : wanted;
  params.set(PROJECT_PARAM, wanted);
  if (before !== after) for (const dependent of PROJECT_DEPENDENT_PARAMS) params.delete(dependent);
  return params;
}
