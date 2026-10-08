/**
 * The frame's navigation, as data — `W50-PLAN.md` §3.1 and §3.5, owner ruling `R-66`.
 *
 * **Nothing here decides what a screen is or who may open it.** The rows, their labels, their
 * groups and their order are the screen registry's (`@/shared/config`), and whether a session
 * may open a row is `screenDecision`'s — the function `requireScreen` asks before it renders
 * the screen. The menu offers exactly the rows whose answer is `open`, so it cannot offer a
 * screen the guard would refuse, nor hide one the guard would open. This module adds only
 * what the registry has no column for: the names of the groups and their order in the bar.
 *
 * Hiding a row is presentation. The guard and the API refuse on their own evidence; a stale
 * subject shows a menu its holder cannot use and nothing more.
 */

import type { ScreenDecisionSubject, ScreenEntry, ScreenGroup } from '@/shared/config';
import { SCREEN_REGISTRY, screenDecision, screenMatching } from '@/shared/config';

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

/** One link in the menu: a registry row's address and label, nothing else. */
export interface NavigationItem {
  readonly address: string;
  readonly label: string;
}

/** A group the session may open at least one row of. A group with none is not in the list. */
export interface NavigationGroup {
  readonly group: MenuGroup;
  readonly label: string;
  readonly items: readonly [NavigationItem, ...NavigationItem[]];
}

/** What the bar offers one session. Plain data, so the server can hand it to a client island. */
export interface Navigation {
  /** `Главная`, when the session may open it. */
  readonly home: NavigationItem | null;
  readonly groups: readonly NavigationGroup[];
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
 * {@link screenDecision} is `open`, `Главная` on its own and the rest grouped in
 * {@link MENU_GROUPS} order, each group's rows in registry order.
 *
 * A guest, a session on its default credential and one with an incomplete profile open no
 * `session` row, so they get an empty menu — the account menu is how the latter two leave
 * that state. A row in a group the bar does not show (`account`, `hidden`) is never offered.
 */
export function buildNavigation(
  subject: ScreenDecisionSubject | null,
  registry: readonly ScreenEntry[] = SCREEN_REGISTRY,
): Navigation {
  const open = registry.filter((screen) => screen.inMenu && screenDecision(screen, subject) === 'open');
  const home = open.find((screen) => screen.group === 'home');
  const groups: NavigationGroup[] = [];
  for (const group of MENU_GROUPS) {
    const [first, ...rest] = open.filter((screen) => screen.group === group).map(itemOf);
    if (first !== undefined) groups.push({ group, label: MENU_GROUP_LABELS[group], items: [first, ...rest] });
  }
  return { home: home === undefined ? null : itemOf(home), groups };
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
