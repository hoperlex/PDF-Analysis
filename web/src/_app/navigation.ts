/**
 * The frame's navigation, as data — `W50-PLAN.md` §3.1 and §3.5, owner ruling `R-66`.
 *
 * **Nothing here decides what a screen is or who may open it.** The rows, their labels, their
 * groups and their order are the screen registry's (`@/shared/config`), and whether a session
 * may open a row is `screenDecision`'s — the function `requireScreen` asks before it renders
 * the screen. The menu offers exactly the rows whose answer is `open`, so it cannot offer a
 * screen the guard would refuse, nor hide one the guard would open. This module adds only
 * what the registry has no column for: the names of the groups and their order in the bar, and
 * the one item that is not a row but a choice between two (`ProjectEntry`, `R-153h`).
 *
 * Hiding a row is presentation. The guard and the API refuse on their own evidence; a stale
 * subject shows a menu its holder cannot use and nothing more.
 */

import { looksLikeProjectUid } from '@/entities/project';
import type { ScreenDecisionSubject, ScreenEntry, ScreenGroup } from '@/shared/config';
import { SCREEN_REGISTRY, screenAt, screenDecision, screenMatching } from '@/shared/config';
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
 * The first item of «Работа» (`R-153h`), which is not one row but one of two, chosen by the project the address names:
 * «Проект» when one is current, «Проекты» when none is («Все проекты»). The registry holds both screens with
 * `inMenu: false` (`R-150b` moved the list into the top strip's selector, which stays), so the menu does not read them
 * as rows; it offers them through this entry. Each field is the screen's label when the session may open it
 * ({@link screenDecision}), `null` when it may not — the entry never offers a screen the guard would refuse.
 */
export interface ProjectEntry {
  /** «Проекты», the list at `/projects`; the item when no project is current. */
  readonly list: string | null;
  /** «Проект», the current project's page at `/projects/{uid}`; the item when a project is current. */
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
 * The home screen stays reachable through the brand link in `AppFrame`.
 *
 * A guest, a session on its default credential and one with an incomplete profile open no
 * `session` row, so they get an empty menu — the account menu is how the latter two leave
 * that state. A row in a group the bar does not show (`account`, `hidden`) is never offered.
 *
 * The result also carries the {@link ProjectEntry} — «Проект» or «Проекты», first in «Работа» —
 * which the browser resolves against the project the address names ({@link withProjectEntry}).
 */
export function buildNavigation(
  subject: ScreenDecisionSubject | null,
  registry: readonly ScreenEntry[] = SCREEN_REGISTRY,
): Navigation {
  const open = registry.filter((screen) => screen.inMenu && screenDecision(screen, subject) === 'open');
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
 * The item `entry` stands for when the address names `projectUid` (`R-153h`): «Проект», linking to that project's page,
 * for a project the address spells as one; «Проекты», linking to the list, when it names none. A value that is not a
 * project's uid names no project the menu could open — the page itself says so, as it does for the «Разделы» group — so
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
 * `navigation` with its {@link ProjectEntry} drawn as an item: the first of «Работа», before «Дашборд». The group is
 * made when the session has no other row in it. Pure, and the same navigation for the bar, the compact rail and the
 * stacked menu, which all draw `groups`.
 */
export function withProjectEntry(
  navigation: Navigation,
  projectUid: string | null,
  registry: readonly ScreenEntry[] = SCREEN_REGISTRY,
): Navigation {
  const item = projectEntryItem(navigation.projectEntry, projectUid, registry);
  if (item === null) return navigation;
  const work = navigation.groups.find((group) => group.group === 'work');
  const first: NavigationGroup = { group: 'work', label: MENU_GROUP_LABELS.work, items: [item, ...(work?.items ?? [])] };
  return { ...navigation, groups: work === undefined ? [first, ...navigation.groups] : navigation.groups.map((group) => (group === work ? first : group)) };
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
