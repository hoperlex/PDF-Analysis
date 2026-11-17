/**
 * The frame's navigation, as data — `W50-PLAN.md` §3.1 and §3.5, owner ruling `R-66`.
 *
 * **Nothing here decides what a screen is or who may open it.** The rows, their labels, their
 * groups and their order are the screen registry's (`@/shared/config`), and whether a session
 * may open a row is `screenDecision`'s — the function `requireScreen` asks before it renders
 * the screen. The menu offers exactly the rows whose answer is `open`, so it cannot offer a
 * screen the guard would refuse, nor hide one the guard would open. This module adds only
 * what the registry has no column for: the names of the groups and their order in the bar, and
 * the one item that is not a row but a choice between two (`ProjectEntry`, `R-153h`). The order of «Работа» is `UIP-G-07`'s:
 * «Главная», «Дашборд», the project entry, then the rest of the registry's rows.
 *
 * Hiding a row is presentation. The guard and the API refuse on their own evidence; a stale
 * subject shows a menu its holder cannot use and nothing more.
 */

import { looksLikeProjectUid } from '@/entities/project';
import type { ScreenDecisionSubject, ScreenEntry, ScreenGroup } from '@/shared/config';
import { HOME_SCREEN, SCREEN_REGISTRY, screenAt, screenDecision, screenMatching } from '@/shared/config';
import { routes } from '@/shared/lib';

/** The groups the bar shows as disclosures, in `R-66`'s order. */
export const MENU_GROUPS = ['work', 'knowledge', 'system', 'admin'] as const satisfies readonly ScreenGroup[];
export type MenuGroup = (typeof MENU_GROUPS)[number];

/** Each group's name in the bar. */
export const MENU_GROUP_LABELS: Readonly<Record<MenuGroup, string>> = {
  work: 'Работа',
  knowledge: 'Знания',
  system: 'Система',
  admin: 'Администрирование',
};

/** One link in the menu: a registry row's address and label, and, for a templated row, which one. */
export interface NavigationItem {
  readonly address: string;
  readonly label: string;
  /**
   * The registry address the item stands for, when `address` is a concrete address of a templated row
   * (`/projects/prj_…` of `/projects/[project_uid]`): the shape {@link currentScreen} reports for the page, so the item
   * is marked current on it. Absent: `address` is itself the registry address.
   */
  readonly screen?: string | undefined;
}

/** A group the session may open at least one row of. A group with none is not in the list. */
export interface NavigationGroup {
  readonly group: MenuGroup;
  readonly label: string;
  readonly items: readonly [NavigationItem, ...NavigationItem[]];
}

/**
 * An item of «Работа» (`R-153h`, `UIP-G-07`), which is not one row but one of two, chosen by the object the address names:
 * «Объект» when one is current, «Объекты» when none is («Все объекты»). The registry holds both screens with
 * `inMenu: false` (`R-150b` moved the list into the top strip's selector, which stays), so the menu does not read them
 * as rows; it offers them through this entry, third in the group ({@link PROJECT_ENTRY_PLACE}). Each field is the
 * screen's label when the session may open it ({@link screenDecision}), `null` when it may not — the entry never offers a
 * screen the guard would refuse.
 */
export interface ProjectEntry {
  /** «Объекты», the list at `/projects`; the item when no object is current. */
  readonly list: string | null;
  /** «Объект», the current object's page at `/projects/{uid}`; the item when an object is current. */
  readonly project: string | null;
}

/**
 * What the bar offers one session. Plain data, so the server can hand it to a client island. `projectEntry` is absent
 * when the session may open neither screen; the project it depends on is the address's, known only in the browser, so
 * {@link withProjectEntry} turns it into an item there.
 */
export interface Navigation {
  readonly groups: readonly NavigationGroup[];
  readonly projectEntry?: ProjectEntry | undefined;
}

/** A menu row that is not a concrete address. A defect in the registry, not a state. */
export class MenuAddressError extends Error {
  constructor(address: string) {
    super(`navigation: the menu row ${address} is a template, not an address a link can carry`);
    this.name = 'MenuAddressError';
  }
}

function itemOf(screen: ScreenEntry): NavigationItem {
  if (screen.address.includes('[')) throw new MenuAddressError(screen.address);
  return { address: screen.address, label: screen.label };
}

/**
 * The menu for `subject` (or a guest, `null`): the registry's `inMenu` rows whose
 * {@link screenDecision} is `open`, grouped in
 * {@link MENU_GROUPS} order, each group's rows in registry order.
 * «Главная» is the registry's first row of «Работа» (`UIP-G-07`); the brand link in `AppFrame` leads home too.
 *
 * A guest, a session on its default credential and one with an incomplete profile open no
 * `session` row, so they get an empty menu — the account menu is how the latter two leave
 * that state. A row in a group the bar does not show (`account`, `hidden`) is never offered.
 * `R-80`: «Главная» is the one product row an account with no role may open, and a menu of «Главная» alone is no
 * product navigation, so the row is offered only beside another one; that account gets the empty menu it always had.
 *
 * The result also carries the {@link ProjectEntry} — «Объект» or «Объекты», third in «Работа» — which the browser
 * resolves against the object the address names ({@link withProjectEntry}).
 */
export function buildNavigation(
  subject: ScreenDecisionSubject | null,
  registry: readonly ScreenEntry[] = SCREEN_REGISTRY,
): Navigation {
  const decided = registry.filter((screen) => screen.inMenu && screenDecision(screen, subject) === 'open');
  const open = decided.some((screen) => screen.address !== HOME_SCREEN) ? decided : [];
  const groups: NavigationGroup[] = [];
  for (const group of MENU_GROUPS) {
    const [first, ...rest] = open.filter((screen) => screen.group === group).map(itemOf);
    if (first !== undefined) groups.push({ group, label: MENU_GROUP_LABELS[group], items: [first, ...rest] });
  }
  const projectEntry = projectEntryOf(subject, registry);
  return projectEntry === undefined ? { groups } : { groups, projectEntry };
}

/** The label of the screen at `address` when `subject` may open it, else `null`. */
function labelWhenOpen(screen: ScreenEntry | undefined, subject: ScreenDecisionSubject | null): string | null {
  return screen !== undefined && screenDecision(screen, subject) === 'open' ? screen.label : null;
}

/**
 * The {@link ProjectEntry} for `subject`: what the registry and {@link screenDecision} say of the project list and of a
 * project's page, the latter found by a concrete address of its shape. `undefined` when neither is open to the session
 * (a guest, a default credential, an incomplete profile, an account with no role).
 */
export function projectEntryOf(
  subject: ScreenDecisionSubject | null,
  registry: readonly ScreenEntry[] = SCREEN_REGISTRY,
): ProjectEntry | undefined {
  const list = labelWhenOpen(screenAt(routes.projects(), registry), subject);
  const project = labelWhenOpen(screenMatching(routes.project('project'), registry), subject);
  return list === null && project === null ? undefined : { list, project };
}

/**
 * The item `entry` stands for when the address names `projectUid` (`R-153h`): «Объект», linking to that object's page,
 * for an object the address spells as one; «Объекты», linking to the list, when it names none. A value that is not an
 * object's uid names no object the menu could open — the page itself says so, as it does for the «Разделы» group — so
 * the list is offered. `null` when the session may not open the screen the case calls for.
 */
export function projectEntryItem(
  entry: ProjectEntry | undefined,
  projectUid: string | null,
  registry: readonly ScreenEntry[] = SCREEN_REGISTRY,
): NavigationItem | null {
  if (entry === undefined) return null;
  if (projectUid !== null && looksLikeProjectUid(projectUid)) {
    const screen = screenMatching(routes.project(projectUid), registry);
    return entry.project === null || screen === undefined
      ? null
      : { address: routes.project(projectUid), label: entry.project, screen: screen.address };
  }
  return entry.list === null ? null : { address: routes.projects(), label: entry.list };
}

/**
 * Where the project entry stands in «Работа» (`UIP-G-07`): after the two leading rows, «Главная» and «Дашборд», and before the
 * original's screens. The place is a count, not an address, because `_app` writes no address by hand; the navigation tests
 * hold the two leading rows to the registry, so a registry that moves them reddens a case instead of moving the entry.
 */
export const PROJECT_ENTRY_PLACE = 2;

/**
 * `navigation` with its {@link ProjectEntry} drawn as an item: the third of «Работа», behind «Главная» and «Дашборд»
 * ({@link PROJECT_ENTRY_PLACE}). The group is made when the session has no other row in it. Pure, and the same navigation
 * for the bar, the compact rail and the stacked menu, which all draw `groups`.
 */
export function withProjectEntry(
  navigation: Navigation,
  projectUid: string | null,
  registry: readonly ScreenEntry[] = SCREEN_REGISTRY,
): Navigation {
  const item = projectEntryItem(navigation.projectEntry, projectUid, registry);
  if (item === null) return navigation;
  const work = navigation.groups.find((group) => group.group === 'work');
  const rows = work?.items ?? [];
  const placed: NavigationGroup = {
    group: 'work',
    label: MENU_GROUP_LABELS.work,
    items: [...rows.slice(0, PROJECT_ENTRY_PLACE), item, ...rows.slice(PROJECT_ENTRY_PLACE)] as [NavigationItem, ...NavigationItem[]],
  };
  return { ...navigation, groups: work === undefined ? [placed, ...navigation.groups] : navigation.groups.map((group) => (group === work ? placed : group)) };
}

/** Whether `item` is the page being shown: its registry address, or the shape of its templated one, is the current screen's. */
export function itemIsCurrent(item: NavigationItem, current: CurrentScreen | null): boolean {
  return current !== null && current.address === (item.screen ?? item.address);
}

/**
 * Whether the frame offers the project selector (`R-150b`) to `subject`: exactly when the
 * session may open the project list, the screen the selector's «Новый проект» and «Все проекты»
 * lead to and whose read it shows. A guest, a default credential, an incomplete profile and an
 * account with no role get no selector, as they get no menu, so the selector never offers a
 * list the API would refuse.
 */
export function offersProjectSwitcher(
  subject: ScreenDecisionSubject | null,
  registry: readonly ScreenEntry[] = SCREEN_REGISTRY,
): boolean {
  const screen = screenAt(routes.projects(), registry);
  return screen !== undefined && screenDecision(screen, subject) === 'open';
}

/**
 * Whether the side menu offers the current project's «Разделы» (`UI-A-04`): exactly when the session may open the
 * section page those items lead to, and so may read the counts beside them. The page is a registry row with a
 * template address, so it is found by a concrete address of its shape. A guest, a default credential, an
 * incomplete profile and an account with no role get no group, as they get no menu.
 */
export function offersSectionNavigation(
  subject: ScreenDecisionSubject | null,
  registry: readonly ScreenEntry[] = SCREEN_REGISTRY,
): boolean {
  const screen = screenMatching(routes.projectSection('project', 'section'), registry);
  return screen !== undefined && screenDecision(screen, subject) === 'open';
}

/**
 * Whether the top strip shows the queue's pause state (`R-151f`): exactly when the «Очередь» screen is
 * open to this session, so `viewer` (`R-150w`) and a guest never read it.
 */
export function offersPauseStatus(
  subject: ScreenDecisionSubject | null,
  registry: readonly ScreenEntry[] = SCREEN_REGISTRY,
): boolean {
  const screen = screenAt(routes.queue(), registry);
  return screen !== undefined && screenDecision(screen, subject) === 'open';
}

/** The screen being shown, as the menu marks it: its registry address and its group. */
export interface CurrentScreen {
  readonly address: string;
  readonly group: ScreenGroup;
}

/**
 * Which registry row the browser's `pathname` is showing, matched against the registry's
 * address shapes — so `/projects/prj_…/runs/run_…` marks `Работа` current although no menu
 * item is that run. `null` for an address the registry does not have (and for no pathname).
 */
export function currentScreen(
  pathname: string | null,
  registry: readonly ScreenEntry[] = SCREEN_REGISTRY,
): CurrentScreen | null {
  if (pathname === null) return null;
  const screen = screenMatching(pathname, registry);
  return screen === undefined ? null : { address: screen.address, group: screen.group };
}
