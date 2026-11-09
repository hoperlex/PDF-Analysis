/**
 * `R-153h` (owner, 2026-11-09): the first item of «Работа» is «Проект» when the address names one project and «Проекты»
 * when it names none («Все проекты») — the user's road to those screens had been unclear since `R-150b` took the list
 * out of the menu rows.
 *
 * The item is not a registry row (both screens stay `inMenu: false`, which the registry guards hold): it is the
 * navigation's `projectEntry`, decided by `screenDecision` for the session and turned into an item by
 * `withProjectEntry` for the project the address names. These cases read the decision as data (`projectEntryOf`,
 * `projectEntryItem`, `withProjectEntry`), the markup off a static pass of the navigation in all three of its states
 * (the bar, the compact rail and the stacked «Меню»), and the wiring (the project from the path or from `?project=`)
 * off a mounted frame, the way `section-navigation.test.ts` reads the «Разделы» group.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

import { FrameNavigation, FrameNavigationView } from '@/_app/frame-navigation';
import { buildNavigation, itemIsCurrent, projectEntryItem, projectEntryOf, withProjectEntry } from '@/_app/navigation';
import type { Navigation } from '@/_app/navigation';
import type { ScreenEntry } from '@/shared/config';
import { SCREEN_REGISTRY } from '@/shared/config';
import { routes } from '@/shared/lib';

import { newClient, renderWith } from '../screens/harness';
import { ADMIN_ONLY, DEFAULT_CREDENTIAL, EXPERT, INCOMPLETE_PROFILE, NO_ROLES } from './subjects';

const navigationState = vi.hoisted(() => ({ pathname: null as string | null, search: '' }));

vi.mock('next/navigation', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  usePathname: () => navigationState.pathname,
  useSearchParams: () => new URLSearchParams(navigationState.search),
}));

const PROJECT = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const OTHER = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8C';
const VIEWER = { ...EXPERT, roles: ['viewer'] };
const BOTH = { list: 'Проекты', project: 'Проект' };

// ------------------------------------------------------------------------------------------------- reading

interface Link {
  readonly href: string;
  readonly name: string;
  readonly current: boolean;
}

const textOf = (markup: string): string => markup.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();

/** The links of `markup` in document order: where they lead, what they are called, and whether they are the page shown. */
function linksOf(markup: string): Link[] {
  return [...markup.matchAll(/<a\b([^>]*)>(.*?)<\/a>/gs)].map((match) => {
    const attributes = match[1] as string;
    return {
      href: (/\bhref="([^"]*)"/.exec(attributes)?.[1] ?? '').replace(/&amp;/g, '&'),
      name: /\baria-label="([^"]*)"/.exec(attributes)?.[1] ?? textOf(match[2] as string),
      current: /\baria-current="page"/.test(attributes),
    };
  });
}

type StateName = 'row' | 'rail' | 'stacked';

/** The three states of one navigation, each as the part of the markup that draws it. */
function statesOf(markup: string): Record<StateName, string> {
  const rail = markup.indexOf('data-nav-state="rail"');
  const stacked = markup.indexOf('data-nav-state="stacked"');
  expect(markup.indexOf('data-nav-state="row"'), 'the bar').toBeGreaterThan(-1);
  expect(rail, 'the rail').toBeGreaterThan(-1);
  expect(stacked, 'the stacked menu').toBeGreaterThan(-1);
  return { row: markup.slice(0, rail), rail: markup.slice(rail, stacked), stacked: markup.slice(stacked) };
}

function draw(navigation: Navigation, pathname: string | null, projectUid?: string | null): string {
  return renderToStaticMarkup(createElement(FrameNavigationView, { navigation, pathname, projectUid }));
}

/** The first two links of each state: the entry and what «Работа» held first before it. */
function firstTwo(markup: string): Record<StateName, Link[]> {
  const states = statesOf(markup);
  return {
    row: linksOf(states.row).slice(0, 2),
    rail: linksOf(states.rail).slice(0, 2),
    stacked: linksOf(states.stacked).slice(0, 2),
  };
}

/** The `href` of every link marked as the page shown, in each state. */
function markedIn(markup: string): string[][] {
  return Object.values(statesOf(markup)).map((state) => linksOf(state).filter((link) => link.current).map((link) => link.href));
}

// ---------------------------------------------------------------------------------------------------- data

describe('R-153h: who is offered the entry', () => {
  it('every session that may open the project list and a project\'s page: an expert, an administrator, a viewer', () => {
    for (const who of [EXPERT, ADMIN_ONLY, VIEWER]) {
      expect(projectEntryOf(who), who.roles.join(',')).toEqual(BOTH);
      expect(buildNavigation(who).projectEntry, who.roles.join(',')).toEqual(BOTH);
    }
  });

  it('no guest, default credential, incomplete profile or account with no role — the menu stays empty for them', () => {
    for (const who of [null, DEFAULT_CREDENTIAL, INCOMPLETE_PROFILE, NO_ROLES, { ...NO_ROLES, roles: ['auditor'] }]) {
      expect(projectEntryOf(who), String(who?.login)).toBeUndefined();
      expect(buildNavigation(who), String(who?.login)).toEqual({ groups: [] });
    }
    expect(draw(buildNavigation(null), '/', null)).toBe('');
  });

  it('takes each decision from the registry, not from a role written here: a row closed to the session is not offered', () => {
    const closed = (...addresses: string[]): readonly ScreenEntry[] =>
      SCREEN_REGISTRY.map((row) => (addresses.includes(row.address) ? { ...row, roles: ['admin'] as const } : row));
    // The list closed to an expert: «Проект» stays, «Проекты» goes.
    const noList = buildNavigation(EXPERT, closed('/projects'));
    expect(noList.projectEntry).toEqual({ list: null, project: 'Проект' });
    expect(projectEntryItem(noList.projectEntry, null)).toBeNull();
    expect(projectEntryItem(noList.projectEntry, PROJECT)).toMatchObject({ label: 'Проект' });
    expect(linksOf(statesOf(draw(noList, '/', null)).row)[0]?.href).toBe('/dashboard');
    // The project page closed to an expert: «Проекты» stays, «Проект» goes — and an administrator keeps both.
    const noProject = buildNavigation(EXPERT, closed('/projects/[project_uid]'));
    expect(noProject.projectEntry).toEqual({ list: 'Проекты', project: null });
    expect(projectEntryItem(noProject.projectEntry, PROJECT)).toBeNull();
    expect(projectEntryItem(noProject.projectEntry, null)).toMatchObject({ label: 'Проекты' });
    expect(linksOf(statesOf(draw(noProject, '/dashboard', PROJECT)).row)[0]?.href).toBe(`/dashboard?project=${PROJECT}`);
    expect(buildNavigation(ADMIN_ONLY, closed('/projects')).projectEntry).toEqual(BOTH);
    // Both closed: no entry at all.
    const neither = buildNavigation(EXPERT, closed('/projects', '/projects/[project_uid]'));
    expect(neither.projectEntry).toBeUndefined();
    expect(draw(neither, '/dashboard', PROJECT)).not.toContain('href="/projects');
  });

  it('is not a registry row: both screens stay out of the menu rows, and the groups hold neither address', () => {
    for (const address of ['/projects', '/projects/[project_uid]']) {
      expect(SCREEN_REGISTRY.find((row) => row.address === address), address).toMatchObject({ inMenu: false, group: 'work' });
    }
    const offered = buildNavigation(EXPERT).groups.flatMap((group) => group.items.map((item) => item.address));
    expect(offered.filter((address) => address.startsWith('/projects'))).toEqual([]);
  });
});

describe('R-153h: the item for the project the address names', () => {
  const entry = BOTH;

  it('is «Проект», leading to that project\'s page, when a project is current', () => {
    expect(projectEntryItem(entry, PROJECT)).toEqual({
      address: routes.project(PROJECT),
      label: 'Проект',
      screen: '/projects/[project_uid]',
    });
  });

  it('is «Проекты», leading to the list, when none is — and when the value is not a project\'s uid at all', () => {
    expect(projectEntryItem(entry, null)).toEqual({ address: routes.projects(), label: 'Проекты' });
    // A value the address spells as something else names no project the menu could open; the page itself says so.
    for (const value of ['', 'не-проект', '../admin/users', 'prj_', `${PROJECT}/runs`]) {
      expect(projectEntryItem(entry, value), value).toEqual({ address: routes.projects(), label: 'Проекты' });
    }
  });

  it('is nothing for a navigation that carries no entry', () => {
    expect(projectEntryItem(undefined, PROJECT)).toBeNull();
    const bare: Navigation = { groups: [{ group: 'work', label: 'Работа', items: [{ address: '/dashboard', label: 'Дашборд' }] }] };
    expect(withProjectEntry(bare, PROJECT)).toBe(bare);
  });

  it('is the first item of «Работа», before «Дашборд», and leaves every other group as it was', () => {
    const live = buildNavigation(EXPERT);
    for (const [projectUid, first] of [
      [null, { address: '/projects', label: 'Проекты' }],
      [PROJECT, { address: `/projects/${PROJECT}`, label: 'Проект', screen: '/projects/[project_uid]' }],
    ] as const) {
      const shown = withProjectEntry(live, projectUid);
      expect(shown.groups.map((group) => group.group), String(projectUid)).toEqual(['work', 'knowledge', 'system']);
      expect(shown.groups[0]?.items.slice(0, 2), String(projectUid)).toEqual([first, { address: '/dashboard', label: 'Дашборд' }]);
      expect(shown.groups[0]?.items.slice(1), String(projectUid)).toEqual(live.groups[0]?.items);
      expect(shown.groups.slice(1), String(projectUid)).toEqual(live.groups.slice(1));
    }
    // The navigation it was given is not touched.
    expect(live.groups[0]?.items[0]).toEqual({ address: '/dashboard', label: 'Дашборд' });
  });

  it('makes the «Работа» group, first, when the session has no other row in it', () => {
    const onlyProjects = SCREEN_REGISTRY.filter((row) => row.group !== 'work' || row.address.startsWith('/projects'));
    const lone = buildNavigation(EXPERT, onlyProjects);
    expect(lone.groups.map((group) => group.group)).toEqual(['knowledge', 'system']);
    const shown = withProjectEntry(lone, null, onlyProjects);
    expect(shown.groups.map((group) => group.group)).toEqual(['work', 'knowledge', 'system']);
    expect(shown.groups[0]).toEqual({ group: 'work', label: 'Работа', items: [{ address: '/projects', label: 'Проекты' }] });
  });

  it('marks the item current on the page it leads to, by the registry shape of that page', () => {
    const item = projectEntryItem(entry, PROJECT);
    const list = projectEntryItem(entry, null);
    if (item === null || list === null) throw new Error('no item');
    expect(itemIsCurrent(item, { address: '/projects/[project_uid]', group: 'work' })).toBe(true);
    expect(itemIsCurrent(item, { address: '/projects/[project_uid]/sections/[section_code]', group: 'work' })).toBe(false);
    expect(itemIsCurrent(item, { address: '/projects', group: 'work' })).toBe(false);
    expect(itemIsCurrent(list, { address: '/projects', group: 'work' })).toBe(true);
    expect(itemIsCurrent(list, { address: '/projects/[project_uid]', group: 'work' })).toBe(false);
    expect(itemIsCurrent(list, null)).toBe(false);
  });
});

// --------------------------------------------------------------------------------------------------- markup

describe('R-153h: the entry in the bar, the compact rail and the stacked menu', () => {
  const live = buildNavigation(EXPERT);

  it('with no project: «Проекты» first, leading to the list, then «Дашборд» — in all three states', () => {
    for (const projectUid of [null, undefined]) {
      const found = firstTwo(draw(live, '/', projectUid));
      for (const [state, links] of Object.entries(found)) {
        expect(links.map((link) => [link.href, link.name]), `${state} ${String(projectUid)}`).toEqual([
          ['/projects', 'Проекты'],
          ['/dashboard', 'Дашборд'],
        ]);
      }
    }
  });

  it('with a project: «Проект» first, leading to that project, then «Дашборд» carrying the project — in all three states', () => {
    const found = firstTwo(draw(live, '/dashboard', PROJECT));
    for (const [state, links] of Object.entries(found)) {
      expect(links.map((link) => [link.href, link.name]), state).toEqual([
        [`/projects/${PROJECT}`, 'Проект'],
        [`/dashboard?project=${PROJECT}`, 'Дашборд'],
      ]);
    }
  });

  it('puts the project in the item\'s path and carries no second copy of it in the query', () => {
    const hrefs = linksOf(draw(live, '/dashboard', PROJECT)).map((link) => link.href);
    expect(hrefs.filter((href) => href.startsWith(`/projects/${PROJECT}`))).toEqual(Array(3).fill(`/projects/${PROJECT}`));
    // With none, the list takes nothing.
    expect(linksOf(draw(live, '/', null)).filter((link) => link.href.startsWith('/projects')).map((link) => link.href)).toEqual(Array(3).fill('/projects'));
  });

  it('is aria-current="page" on the project\'s page, and not on the section pages, the documents or another screen', () => {
    expect(markedIn(draw(live, `/projects/${PROJECT}`, PROJECT))).toEqual(Array(3).fill([`/projects/${PROJECT}`]));
    expect(markedIn(draw(live, `/projects/${PROJECT}/sections/AR`, PROJECT))).toEqual([[], [], []]);
    expect(markedIn(draw(live, `/projects/${PROJECT}/documents/doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B`, PROJECT))).toEqual([[], [], []]);
    expect(markedIn(draw(live, '/dashboard', PROJECT))).toEqual(Array(3).fill([`/dashboard?project=${PROJECT}`]));
  });

  it('is aria-current="page" on the list, and only there', () => {
    expect(markedIn(draw(live, '/projects', null))).toEqual(Array(3).fill(['/projects']));
    expect(markedIn(draw(live, '/dashboard', null))).toEqual(Array(3).fill(['/dashboard']));
    expect(markedIn(draw(live, '/', null))).toEqual([[], [], []]);
    // On the list with a project chosen, the item is the project's page, which is not the page shown.
    expect(markedIn(draw(live, '/projects', PROJECT))).toEqual([[], [], []]);
  });

  it('is aria-current="page" in a group that draws its list itself because an item carries a counter', () => {
    // «Очередь» carries a counter, so a group holding it hands the shared `Disclosure` its own list (`BadgedLinks`).
    const badged: Navigation = {
      ...live,
      groups: [{ group: 'work', label: 'Работа', items: [{ address: '/queue', label: 'Очередь' }] }],
    };
    const markup = renderToStaticMarkup(createElement(FrameNavigationView, { navigation: badged, pathname: `/projects/${PROJECT}`, projectUid: PROJECT, badges: {} }));
    const row = linksOf(statesOf(markup).row);
    expect(row.map((link) => [link.href, link.current])).toEqual([[`/projects/${PROJECT}`, true], [`/queue?project=${PROJECT}`, false]]);
    const list = linksOf(statesOf(renderToStaticMarkup(createElement(FrameNavigationView, { navigation: badged, pathname: '/projects', projectUid: null, badges: {} }))).row);
    expect(list.map((link) => [link.href, link.current])).toEqual([['/projects', true], ['/queue', false]]);
  });

  it('marks the «Работа» group current on the project\'s page, as it did before', () => {
    const markup = draw(live, `/projects/${PROJECT}`, PROJECT);
    expect(markup).toContain('aria-label="Работа" data-current-group="true"');
  });

  it('names the rail link by the item, so the compact rail needs no text', () => {
    const rail = statesOf(draw(live, '/dashboard', PROJECT)).rail;
    expect(rail).toMatch(/<a [^>]*aria-label="Проект"[^>]*href="\/projects\/prj_[^"]*"/);
    expect(rail).toContain('data-nav-glyph="project"');
    expect(statesOf(draw(live, '/', null)).rail).toContain('data-nav-glyph="projects"');
  });

  it('draws the glyph of the item in the bar and the stacked menu too', () => {
    const states = statesOf(draw(live, '/dashboard', PROJECT));
    expect(states.row).toContain('data-nav-glyph="project"');
    expect(states.stacked).toContain('data-nav-glyph="project"');
    expect(states.row).not.toContain('data-nav-glyph="projects"');
  });

  it('can fail: a menu told another project leads to another page, and a menu told none does not lead to a project', () => {
    expect(linksOf(draw(live, '/dashboard', PROJECT))[0]?.href).not.toEqual(linksOf(draw(live, '/dashboard', OTHER))[0]?.href);
    expect(linksOf(draw(live, '/dashboard', null))[0]?.href).not.toContain(PROJECT);
    expect(linksOf(draw(live, '/dashboard', PROJECT))[0]?.href).not.toEqual(linksOf(draw(live, '/dashboard', null))[0]?.href);
  });
});

// --------------------------------------------------------------------------------------------------- wiring

describe('R-153h: the frame reads the project from the address', () => {
  const frame = (navigation: Navigation = buildNavigation(EXPERT)): string =>
    renderWith(newClient(), createElement(FrameNavigation, { navigation }));
  /** The first link of each state of the frame as the address currently names the project. */
  const firstOfEach = (): Link[] => Object.values(statesOf(frame())).map((state) => linksOf(state)[0] as Link);

  it('on a required screen, the project of the path: «Проект», current', () => {
    navigationState.pathname = routes.project(PROJECT);
    navigationState.search = '';
    expect(firstOfEach()).toEqual(Array(3).fill({ href: `/projects/${PROJECT}`, name: 'Проект', current: true }));
  });

  it('on an optional screen, the project of ?project=: «Проект», not the page shown', () => {
    navigationState.pathname = '/dashboard';
    navigationState.search = `project=${OTHER}`;
    expect(firstOfEach()).toEqual(Array(3).fill({ href: `/projects/${OTHER}`, name: 'Проект', current: false }));
  });

  it('on the list with a project chosen, the item is that project\'s page', () => {
    navigationState.pathname = '/projects';
    navigationState.search = `project=${PROJECT}`;
    expect(firstOfEach()).toEqual(Array(3).fill({ href: `/projects/${PROJECT}`, name: 'Проект', current: false }));
  });

  it('with no project in the address, «Все проекты»: «Проекты», current on the list', () => {
    navigationState.pathname = '/projects';
    navigationState.search = '';
    expect(firstOfEach()).toEqual(Array(3).fill({ href: '/projects', name: 'Проекты', current: true }));
    navigationState.pathname = '/dashboard';
    expect(firstOfEach()).toEqual(Array(3).fill({ href: '/projects', name: 'Проекты', current: false }));
    navigationState.search = 'project=';
    expect(firstOfEach()).toEqual(Array(3).fill({ href: '/projects', name: 'Проекты', current: false }));
  });

  it('with a malformed ?project=, the list: the page itself says the value is no project', () => {
    navigationState.pathname = '/dashboard';
    navigationState.search = 'project=..%2Fadmin%2Fusers';
    expect(firstOfEach().map((link) => link.href)).toEqual(Array(3).fill('/projects?project=..%2Fadmin%2Fusers'));
  });

  it('is nothing for a session the frame offers no menu', () => {
    navigationState.pathname = '/dashboard';
    navigationState.search = '';
    expect(frame(buildNavigation(null))).toBe('');
  });
});
