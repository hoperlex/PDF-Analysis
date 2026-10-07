/**
 * The frame's navigation (`W50-SHELL-FRAME`, `W50-PLAN.md` §3.1/§3.5, owner ruling `R-66`):
 * built from the registry only, filtered by `screenDecision`, grouped and ordered as `R-66`
 * orders it, with the current group and item marked.
 */

import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { MENU_GROUPS, MENU_GROUP_LABELS, MenuAddressError, buildNavigation, currentScreen } from '@/_app/navigation';
import type { Navigation } from '@/_app/navigation';
import { FrameNavigationView } from '@/_app/frame-navigation';
import type { ScreenEntry } from '@/shared/config';
import { SCREEN_REGISTRY } from '@/shared/config';

import {
  ADMIN_AND_EXPERT,
  ADMIN_ONLY,
  DEFAULT_CREDENTIAL,
  EXPERT,
  INCOMPLETE_PROFILE,
  NO_ROLES,
  UNKNOWN_ROLE,
} from './subjects';

/** The menu as plain text: `Главная`, then `Группа: пункт, пункт`. */
function outline(navigation: Navigation): string[] {
  return [
    ...(navigation.home === null ? [] : [`${navigation.home.label} ${navigation.home.address}`]),
    ...navigation.groups.map(
      (group) => `${group.label}: ${group.items.map((item) => `${item.label} ${item.address}`).join(', ')}`,
    ),
  ];
}

/** `R-66`, written out by hand from the ruling — never derived from the registry it checks. */
const R66 = [
  'Главная /',
  'Работа: Проекты /projects, Дашборд /dashboard, Оптимизация разделов /section-optimisation',
  'Знания: База знаний /knowledge-base, Блоки /blocks, Нормы /norms',
  'Система: Журнал выполнения /logs, Исполнители /workers, Настройки анализа /analysis-settings, Очередь /queue',
];
const ADMIN_MENU = 'Администрирование: Пользователи /admin/users, Заявки на регистрацию /admin/registrations';

describe('the live registry gives exactly R-66', () => {
  it('to a complete expert: Главная, then Работа, Знания, Система, in that order and with those items', () => {
    expect(outline(buildNavigation(EXPERT))).toEqual(R66);
  });

  it('keeps the R-66 groups for a complete session without admin', () => {
    for (const who of [NO_ROLES, UNKNOWN_ROLE]) {
      expect(outline(buildNavigation(who)), who.displayLabel).toEqual(R66);
    }
  });

  it('adds the two administrator links last only for a complete admin', () => {
    for (const who of [ADMIN_AND_EXPERT, ADMIN_ONLY]) {
      expect(outline(buildNavigation(who)), who.displayLabel).toEqual([...R66, ADMIN_MENU]);
    }
    expect(outline(buildNavigation(EXPERT))).toEqual(R66);
  });

  it('never offers /optimisation: it left the menu and stays a hidden, reachable screen', () => {
    const offered = buildNavigation(ADMIN_AND_EXPERT).groups.flatMap((group) => group.items.map((item) => item.address));
    expect(offered).not.toContain('/optimisation');
    expect(SCREEN_REGISTRY.find((screen) => screen.address === '/optimisation')).toMatchObject({
      group: 'hidden',
      inMenu: false,
    });
  });

  it('can fail: /optimisation back in the menu, or an R-66 stub gone from its group, is not R-66', () => {
    const withOptimisation = SCREEN_REGISTRY.map((screen) =>
      screen.address === '/optimisation' ? { ...screen, group: 'work' as const, inMenu: true } : screen,
    );
    expect(outline(buildNavigation(EXPERT, withOptimisation))).not.toEqual(R66);
    for (const stub of ['/section-optimisation', '/norms', '/analysis-settings', '/queue']) {
      const without = SCREEN_REGISTRY.filter((screen) => screen.address !== stub);
      expect(outline(buildNavigation(EXPERT, without)), stub).not.toEqual(R66);
    }
  });

  it('offers no row of a group the bar does not show', () => {
    for (const screen of SCREEN_REGISTRY.filter((entry) => entry.inMenu)) {
      expect(['home', ...MENU_GROUPS], screen.address).toContain(screen.group);
      expect(screen.address, 'a menu row is an address a link can carry').not.toContain('[');
    }
  });
});

describe('a session that may open no session screen sees no group', () => {
  it('a guest', () => {
    expect(buildNavigation(null)).toEqual({ home: null, groups: [] });
  });

  it('a default credential, and an incomplete profile — whose account menu is how they move on', () => {
    expect(buildNavigation(DEFAULT_CREDENTIAL)).toEqual({ home: null, groups: [] });
    expect(buildNavigation(INCOMPLETE_PROFILE)).toEqual({ home: null, groups: [] });
  });

  it('renders no navigation landmark at all for an empty menu', () => {
    const markup = renderToStaticMarkup(
      createElement(FrameNavigationView, { navigation: buildNavigation(null), pathname: '/login' }),
    );
    expect(markup).toBe('');
  });
});

/** A reduced fixture keeps the one-row synthetic role control from W50. */
const WITH_ADMIN_ROW: readonly ScreenEntry[] = [
  ...SCREEN_REGISTRY.filter((screen) => screen.group !== 'admin'),
  {
    address: '/admin/registrations',
    label: 'Заявки на регистрацию',
    group: 'admin',
    access: 'session',
    roles: ['admin'],
    inMenu: true,
  },
];

describe('a group with no row the session may open is absent', () => {
  it('the administration group, for a session without admin — roles [] included', () => {
    for (const who of [EXPERT, NO_ROLES, UNKNOWN_ROLE]) {
      const groups = buildNavigation(who, WITH_ADMIN_ROW).groups.map((group) => group.group);
      expect(groups, who.displayLabel).not.toContain('admin');
      expect(groups, who.displayLabel).toEqual(['work', 'knowledge', 'system']);
    }
  });

  it('is present, last, for a session holding admin', () => {
    for (const who of [ADMIN_ONLY, ADMIN_AND_EXPERT]) {
      const last = buildNavigation(who, WITH_ADMIN_ROW).groups.at(-1);
      expect(last, who.displayLabel).toEqual({
        group: 'admin',
        label: MENU_GROUP_LABELS.admin,
        items: [{ address: '/admin/registrations', label: 'Заявки на регистрацию' }],
      });
    }
  });

  it('and a group whose only rows are role-gated disappears whole, not as an empty heading', () => {
    const onlyGated = WITH_ADMIN_ROW.map((screen) =>
      screen.group === 'system' ? { ...screen, roles: ['admin'] as const } : screen,
    );
    expect(buildNavigation(EXPERT, onlyGated).groups.map((group) => group.group)).toEqual(['work', 'knowledge']);
    const markup = renderToStaticMarkup(
      createElement(FrameNavigationView, { navigation: buildNavigation(EXPERT, onlyGated), pathname: null }),
    );
    expect(markup).not.toContain('>Система<');
    expect(markup).not.toContain('>Администрирование<');
  });

  it('refuses a menu row that is a template rather than an address', () => {
    const template: readonly ScreenEntry[] = [
      { address: '/projects/[project_uid]', label: 'Проект', group: 'work', access: 'session', roles: 'any', inMenu: true },
    ];
    expect(() => buildNavigation(EXPERT, template)).toThrow(MenuAddressError);
  });
});

describe('the current group and item', () => {
  it('matches the registry address shape, so a page under a project marks Работа', () => {
    expect(currentScreen('/projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/runs/run_01J9ZQ8K7NHVXW3T2R5M6P4Q8B')).toEqual({
      address: '/projects/[project_uid]/runs/[run_id]',
      group: 'work',
    });
    expect(currentScreen('/blocks')).toEqual({ address: '/blocks', group: 'knowledge' });
    expect(currentScreen('/no-such-screen')).toBeNull();
    expect(currentScreen(null)).toBeNull();
  });

  const draw = (pathname: string | null): string =>
    renderToStaticMarkup(createElement(FrameNavigationView, { navigation: buildNavigation(EXPERT), pathname }));

  /** The text of every button carrying `aria-current="true"`, in document order. */
  const currentButtons = (markup: string): string[] =>
    [...markup.matchAll(/<button\b([^>]*)>([^<]*)<\/button>/g)]
      .filter((m) => /\baria-current="true"/.test(m[1] as string))
      .map((m) => m[2] as string);

  /** The `href` of every link carrying `aria-current="page"`, whatever the attribute order. */
  const currentLinks = (markup: string): string[] =>
    [...markup.matchAll(/<a\b([^>]*)>/g)]
      .map((m) => m[1] as string)
      .filter((attributes) => /\baria-current="page"/.test(attributes))
      .map((attributes) => /\bhref="([^"]*)"/.exec(attributes)?.[1] ?? '');

  it('marks the group button aria-current="true" and the item aria-current="page", in both states', () => {
    // Each twice: once in the one-row state and once in the stacked one, whose «Меню» says a
    // page inside it is current.
    const markup = draw('/blocks');
    expect(currentButtons(markup)).toEqual(['Знания', 'Меню', 'Знания']);
    expect(currentLinks(markup)).toEqual(['/blocks', '/blocks']);
  });

  it('marks the group but no item on a page the menu does not list', () => {
    const markup = draw('/projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B');
    expect(currentButtons(markup)).toEqual(['Работа', 'Меню', 'Работа']);
    expect(currentLinks(markup)).toEqual([]);
  });

  it('marks Главная as the page, and nothing on an unregistered address or without a pathname', () => {
    expect(currentLinks(draw('/'))).toEqual(['/', '/']);
    expect(currentButtons(draw('/'))).toEqual(['Меню']);
    for (const pathname of ['/no-such-screen', null]) {
      const markup = draw(pathname);
      expect(markup).not.toContain('aria-current');
    }
  });
});
