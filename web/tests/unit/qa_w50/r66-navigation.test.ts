/**
 * `W50-QA-01`, the `R-66` item — the navigation amendment as the owner ruled it, on the merged
 * frame.
 *
 * `OWNER_RULINGS_2026-09-17.md` §3.22: **Работа** — Проекты `/projects`, Дашборд `/dashboard`,
 * «Оптимизация разделов» `/section-optimisation`; **Знания** — База знаний
 * `/knowledge-base`, Блоки `/blocks`, «Нормы» `/norms` (stub); **Система** — Журнал выполнения
 * `/logs`, Исполнители `/workers`, «Настройки анализа» `/analysis-settings` (stub), «Очередь»
 * `/queue`; `/optimisation` leaves the menu and stays a registered, reachable screen
 * (group `hidden`). W53 built `/logs` and `/queue`, `W55A-WEB-NORMS` built `/norms`,
 * `W59-ANALYSIS-SETTINGS-01` built `/analysis-settings` and `W63-SECTION-FORM7-01` built
 * `/section-optimisation`: no R-66 stub is left. Access remains `session`, roles `any-role`, and
 * every graduated screen keeps its ruled place in the menu, asserted by `RULING` below and by
 * the cases that follow it.
 *
 * **`R-150b` (`UI-PARITY-01` wave 1, 2026-11-05) amends it:** «Проекты» left the menu. The
 * project list is chosen from the «Проекты ▾» selector in the frame's top strip
 * (`widgets/project-switcher`), which replaces that item of the order; `/projects` stays a
 * registered, reachable screen (`inMenu: false`). `RULING` below is the R-66 order **without** it,
 * and the `R-150b` cases after the menu cases hold the replacement.
 *
 * **`R-153h` (owner, 2026-11-09) brings the list back, but not as a row:** the first item of «Работа» is «Проект»
 * when the address names a project and «Проекты» when it names none, drawn from the navigation's `projectEntry`
 * (`web/tests/unit/shell/project-entry.test.ts` holds it). The frame in these cases has no router, so it names no
 * project: its first item is «Проекты», `/projects`. The registry still holds `/projects` with `inMenu: false`, and
 * the data cases below (`buildNavigation`'s groups) are unchanged.
 *
 * The expectation below is typed from the ruling, not read from the registry, and the menu is
 * read three ways: the data the frame builds (`buildNavigation`), and the two rendered states of
 * the real frame (`AppFrame` — the one-row bar and the stacked «Меню»), in document order.
 *
 * The menu states the frame shows each kind of visitor (guest, default credential, incomplete
 * profile, complete) are asserted here on the rendered frame too; their widths are browser
 * facts (`tests/e2e/pc01/qa_w50/width-states.mjs`).
 *
 * Written by QA from the plan, without the lane reports.
 */

import { join } from 'node:path';

import { createElement, isValidElement } from 'react';
import type { ReactElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { WEB_ROOT } from '../../guards/lib/repo';
import { newClient, renderScreen } from '../screens/harness';

import type { AppFrameSession } from '@/_app';
import { AppFrame } from '@/_app';
import { buildNavigation } from '@/_app/navigation';
import { OptimisationPage } from '@/_pages/optimisation';
import type { SessionAccount } from '@/app/bff/session/store';
import { forgetEverySession, openSession } from '@/app/bff/session/store';
import { SCREEN_REGISTRY, screenAt } from '@/shared/config';

const jar = vi.hoisted(() => ({ value: null as string | null }));

vi.mock('next/headers', () => ({
  cookies: async () => ({
    get: (name: string) => (jar.value === null ? undefined : { name, value: jar.value }),
  }),
}));

// --------------------------------------------------------------------- the ruling, typed in

const RULING: readonly { readonly group: string; readonly items: readonly (readonly [string, string])[] }[] = [
  {
    group: 'Работа',
    items: [
      // `R-150b`: ['/projects', 'Проекты'] is no longer here; the selector in the top strip took it.
      ['/dashboard', 'Дашборд'],
      ['/section-optimisation', 'Оптимизация разделов'],
      // `W61-DISPATCHER-01` (roadmap Q-2) adds «Диспетчер» at the end of «Работа».
      ['/dispatcher', 'Диспетчер'],
      // `UI-PARITY-P0P` adds «График работ» after «Диспетчер», as the original's menu has it.
      ['/schedule', 'График работ'],
      // `CMP-VC-UI-01` (plan §1.1) adds «Сравнение версий» after it.
      ['/version-comparison', 'Сравнение версий'],
      // `CMP-ACTIVATE-1030`: the owner activated the stage screen, and the menu offers it beside the version one.
      ['/stage-comparison', 'Сравнение стадий'],
    ],
  },
  {
    group: 'Знания',
    items: [
      ['/knowledge-base', 'База знаний'],
      // `R-151m`: «Блоки» left the menu; it is a tab of the version, its address a chooser out of the menu.
      ['/norms', 'Нормы'],
    ],
  },
  {
    group: 'Система',
    items: [
      ['/logs', 'Журнал выполнения'],
      ['/workers', 'Исполнители'],
      ['/analysis-settings', 'Настройки анализа'],
      ['/queue', 'Очередь'],
    ],
  },
];

const COMPLETE: SessionAccount = {
  userUid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
  login: 'qa-reviewer@qa.invalid',
  displayLabel: 'Проверка К. А.',
  initials: 'ПК',
  roles: ['expert'],
  isDefaultCredential: false,
  profileComplete: true,
};

function frameSession(changes: Partial<AppFrameSession> = {}): AppFrameSession {
  return { ...COMPLETE, ...changes };
}

function renderFrame(session: AppFrameSession | null): string {
  return renderScreen(newClient(), createElement(AppFrame, { session, children: createElement('p', null, 'содержимое') }));
}

/** The part of the markup between the element carrying `marker` and the end of that element's subtree. */
function region(markup: string, marker: string): string {
  const start = markup.indexOf(marker);
  if (start === -1) return '';
  // Walk the tags from the opening `<div` that holds the marker until its depth returns to zero.
  const open = markup.lastIndexOf('<div', start);
  let depth = 0;
  const tag = /<(\/?)div\b[^>]*>/g;
  tag.lastIndex = open;
  for (let match = tag.exec(markup); match !== null; match = tag.exec(markup)) {
    depth += match[1] === '/' ? -1 : 1;
    if (depth === 0) return markup.slice(open, match.index + match[0].length);
  }
  return markup.slice(open);
}

/** The group buttons and links of a navigation region, in document order. */
function readMenu(html: string): { readonly groups: string[]; readonly links: [string, string][] } {
  const groups = [...html.matchAll(/<button[^>]*class="am-disclosure__button"[^>]*>([^<]*)<\/button>/g)].map(
    (m) => m[1] as string,
  );
  // Every link starts with its glyph (`<span class="am-disclosure__icon"><svg>…</svg></span>`, DESIGN-REF-01-NAV), so the
  // label is the text after that span, not the text directly after the opening tag.
  const links = [
    ...html.matchAll(/<a [^>]*href="([^"]+)"[^>]*>(?:<span class="am-disclosure__icon"[^>]*>[\s\S]*?<\/span>)?([^<]*)<\/a>/g),
  ].map((m) => [m[1] as string, m[2] as string] as [string, string]);
  return { groups, links };
}

// `R-153h`: the frame renders with no router, so it names no project and its first link is the list; «Проект» replaces it
// on a project's address (`project-entry.test.ts`).
const RULED_LINKS: [string, string][] = [
  ['/projects', 'Проекты'],
  ...RULING.flatMap((g) => g.items.map(([a, l]) => [a, l] as [string, string])),
];

// --------------------------------------------------------------------------------- the menu

describe('R-66: the menu’s groups and items equal the ruling’s, in order', () => {
  it('as data: non-admin sessions see exactly the R-66 groups and their order', () => {
    // `R-80`: an empty role set has no product navigation; the brand still links home.
    for (const roles of [['expert']] as const) {
      const navigation = buildNavigation({ roles, isDefaultCredential: false, profileComplete: true });
      expect(
        navigation.groups.map((group) => ({
          group: group.label,
          items: group.items.map((item) => [item.address, item.label]),
        })),
        `roles [${roles.join(',')}]`,
      ).toEqual(RULING.map((group) => ({ group: group.group, items: group.items.map(([a, l]) => [a, l]) })));
    }
  });

  it('admins see the same R-66 prefix followed by the two W51 administrator links', () => {
    for (const roles of [['admin'], ['expert', 'admin']] as const) {
      const navigation = buildNavigation({ roles, isDefaultCredential: false, profileComplete: true });
      expect(navigation.groups.slice(0, 3).map((group) => ({
        group: group.label,
        items: group.items.map((item) => [item.address, item.label]),
      }))).toEqual(RULING.map((group) => ({ group: group.group, items: group.items.map(([a, l]) => [a, l]) })));
      expect(navigation.groups.at(-1)).toMatchObject({
        group: 'admin',
        items: [
          { address: '/admin/users', label: 'Пользователи' },
          { address: '/admin/registrations', label: 'Заявки на регистрацию' },
          { address: '/admin/auth-events', label: 'Журнал входов' },
        ],
      });
    }
  });

  it('as rendered, in the one-row bar: the same groups and links in the same order', () => {
    const markup = renderFrame(frameSession());
    const row = readMenu(region(markup, 'data-nav-state="row"'));
    expect(row.groups).toEqual(['Работа', 'Знания', 'Система']);
    expect(row.links).toEqual(RULED_LINKS);
  });

  it('as rendered, in the stacked «Меню»: «Меню», then the same groups and links in the same order', () => {
    const markup = renderFrame(frameSession());
    const stacked = readMenu(region(markup, 'data-nav-state="stacked"'));
    expect(stacked.groups).toEqual(['Меню', 'Работа', 'Знания', 'Система']);
    expect(stacked.links).toEqual(RULED_LINKS);
  });
});

describe('R-66: /optimisation is in no menu group, registered in hidden, and opens', () => {
  it('is registered: group hidden, not in the menu, session/any-role', () => {
    expect(screenAt('/optimisation')).toMatchObject({ group: 'hidden', inMenu: false, access: 'session', roles: 'any-role' });
  });

  it('is absent from every group, as data and in the rendered frame', () => {
    for (const roles of [['expert'], ['admin', 'expert'], []] as const) {
      const navigation = buildNavigation({ roles, isDefaultCredential: false, profileComplete: true });
      const offered = navigation.groups.flatMap((group) => group.items.map((item) => item.address));
      expect(offered).not.toContain('/optimisation');
    }
    expect(renderFrame(frameSession())).not.toContain('href="/optimisation"');
  });

  it('a complete session holding a role opens it: the guard returns and the route renders its screen', async () => {
    forgetEverySession();
    jar.value = openSession({ ...COMPLETE, roles: ['expert'] }, 'qa-credential', 3600);
    const { default: OptimisationRoute } = await import('@/app/optimisation/page');
    const element = await OptimisationRoute({ params: Promise.resolve({}), searchParams: Promise.resolve({}) });
    expect(isValidElement(element) && element.type === OptimisationPage).toBe(true);
  });
});

// ------------------------------------------------------------------- the graduated screens

const fetchSpy = vi.fn(async () => {
  throw new Error('a guarded route made a network call');
});

const GROUP_ID = 'arg_01M2545JSD15ETSNNV904X991K';

/** The route's element for `/analysis-settings` carrying the given query-string. */
async function analysisSettingsRoute(query: Record<string, string | string[]>): Promise<ReactElement> {
  const module = (await import(/* @vite-ignore */ join(WEB_ROOT, 'src', 'app', 'analysis-settings', 'page.tsx'))) as {
    default: (props: unknown) => Promise<ReactElement>;
  };
  return module.default({ params: Promise.resolve({}), searchParams: Promise.resolve(query) });
}

/**
 * Every read a rendered screen registered: its key, and whether it is allowed to ask the server.
 * Sorted by key, so the list pins WHICH reads exist and not the order the widgets mount in.
 */
function readsOf(client: ReturnType<typeof newClient>): { key: readonly unknown[]; enabled: boolean }[] {
  return client
    .getQueryCache()
    .getAll()
    // `enabled` is an observer option the cache keeps on the query; its type does not say so.
    .map((query) => ({ key: query.queryKey, enabled: (query.options as { enabled?: unknown }).enabled !== false }))
    .sort((a, b) => JSON.stringify(a.key).localeCompare(JSON.stringify(b.key)));
}

describe('R-66: the stubs have graduated, and each keeps its ruled row and place', () => {
  beforeEach(() => {
    forgetEverySession();
    jar.value = openSession(COMPLETE, 'qa-credential', 3600);
    fetchSpy.mockClear();
    vi.stubGlobal('fetch', fetchSpy);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('/norms graduated (W55A-WEB-NORMS): its ruled row and place are kept, and it reads the snapshot list', async () => {
    expect(screenAt('/norms')).toEqual({
      address: '/norms',
      label: 'Нормы',
      group: 'knowledge',
      access: 'session',
      roles: 'any-role',
      inMenu: true,
      projectScope: 'global',
    });
    const module = (await import(/* @vite-ignore */ join(WEB_ROOT, 'src', 'app', 'norms', 'page.tsx'))) as {
      default: (props: unknown) => Promise<ReactElement>;
    };
    const routed = await module.default({ params: Promise.resolve({}), searchParams: Promise.resolve({}) });
    const client = newClient();
    const markup = renderScreen(client, routed);
    expect(markup).not.toContain('Раздел пока недоступен');
    expect(markup).not.toContain('data-route="/norms"');
    // It asks the server which snapshot is current, and searches nothing until asked to.
    expect(client.getQueryCache().getAll().map((query) => query.queryKey[1])).toEqual(['snapshots']);
  });

  it('/analysis-settings graduated (W59-ANALYSIS-SETTINGS-01): its ruled row and place are kept, and it reads the profile registry, the group review and the pack status', async () => {
    expect(screenAt('/analysis-settings')).toEqual({
      address: '/analysis-settings',
      label: 'Настройки анализа',
      group: 'system',
      access: 'session',
      roles: 'any-role',
      inMenu: true,
      projectScope: 'global',
    });
    const routed = await analysisSettingsRoute({});
    const client = newClient();
    const markup = renderScreen(client, routed);
    expect(markup).not.toContain('Раздел пока недоступен');
    expect(markup).not.toContain('data-route="/analysis-settings"');
    // Exactly these reads, each under its own key: the registry, the AR v3 beta group review
    // (`AR-V3-BETA-GROUP-REVIEW-SCREEN-01`) and the installed-pack status
    // (`AR-V3-BETA-PACK-STATUS-WEB-01`). The section «Пресеты запуска» (`ANALYSIS-PRESETS-01`) moved to
    // `/workers/advanced` (`HOSTS-WEB-01b`), so the account, the presets and the connection list are no
    // longer read here: a read that came back with the section reddens this list.
    // With no `group_id` in the address the review has no
    // group to ask about: its query is registered under the empty address and DISABLED, so the
    // screen asks the server nothing about any group; the pack status is always read, because
    // it names no group. An extra read, or a lost one, reddens this list.
    expect(readsOf(client)).toEqual([
      { key: ['analysis', 'profiles'], enabled: true },
      { key: ['runs', 'ar-v3-group-review', ''], enabled: false },
      { key: ['runs', 'ar-v3-pack-status'], enabled: true },
    ]);
  });

  it('/analysis-settings with a valid group_id: the group review read is ENABLED for exactly that group', async () => {
    const routed = await analysisSettingsRoute({ group_id: GROUP_ID });
    const client = newClient();
    renderScreen(client, routed);
    expect(readsOf(client)).toEqual([
      { key: ['analysis', 'profiles'], enabled: true },
      { key: ['runs', 'ar-v3-group-review', GROUP_ID], enabled: true },
      { key: ['runs', 'ar-v3-pack-status'], enabled: true },
    ]);
  });

  it('/analysis-settings with a malformed group_id: the route answers not-found and reads nothing', async () => {
    for (const bad of ['arg_bad', GROUP_ID.toLowerCase(), [GROUP_ID, GROUP_ID]]) {
      let digest: string | null = null;
      try {
        await analysisSettingsRoute({ group_id: bad });
      } catch (thrown) {
        digest = String((thrown as { digest?: unknown }).digest ?? '');
      }
      expect(digest, JSON.stringify(bad)).toBe('NEXT_HTTP_ERROR_FALLBACK;404');
    }
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('/section-optimisation graduated (W63-SECTION-FORM7-01): its ruled row and place are kept, and it reads the AR section', async () => {
    expect(screenAt('/section-optimisation')).toEqual({
      address: '/section-optimisation',
      label: 'Оптимизация разделов',
      group: 'work',
      access: 'session',
      roles: 'any-role',
      inMenu: true,
      projectScope: 'optional',
    });
    const module = (await import(/* @vite-ignore */ join(WEB_ROOT, 'src', 'app', 'section-optimisation', 'page.tsx'))) as {
      default: (props: unknown) => Promise<ReactElement>;
    };
    const routed = await module.default({ params: Promise.resolve({}), searchParams: Promise.resolve({}) });
    const client = newClient();
    const markup = renderScreen(client, routed);
    expect(markup).not.toContain('Раздел пока недоступен');
    expect(markup).not.toContain('data-route="/section-optimisation"');
    // One read, under its own key: the analysed section, unfiltered, first page.
    const keys = client.getQueryCache().getAll().map((query) => query.queryKey);
    // Two reads, both of the AR section: the specification, and since contract 1.37.0 (lane C3, UI-PARITY-OPT-CARRYOVER)
    // the «Принято» tab's first page, whose server `total` is the number the tab shows without being opened.
    expect(keys, `the reads the screen made: ${JSON.stringify(keys)}`).toHaveLength(2);
    expect(keys[0]?.slice(0, 3)).toEqual(['optimisation', 'section-specification', 'AR']);
    expect(keys[0]?.[3]).toEqual({ projectUid: null, q: null, offset: 0, limit: 50 });
    expect(keys[1]?.slice(0, 2)).toEqual(['optimisation', 'accepted']);
    expect(keys[1]?.[2]).toMatchObject({ section_code: 'AR' });
  });

  it('/section-optimisation: a guest is sent to sign in, carrying it in next', async () => {
    jar.value = null;
    const module = (await import(/* @vite-ignore */ join(WEB_ROOT, 'src', 'app', 'section-optimisation', 'page.tsx'))) as {
      default: (props: unknown) => Promise<unknown>;
    };
    let location: string | null = null;
    try {
      await module.default({ params: Promise.resolve({}), searchParams: Promise.resolve({ from: 'menu' }) });
    } catch (thrown) {
      location = String((thrown as { digest?: unknown }).digest ?? '').split(';')[2] ?? null;
    }
    expect(location).toBe(`/login?next=${encodeURIComponent('/section-optimisation?from=menu')}`);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('all R-66 menu addresses remain registered after the stubs graduated', () => {
    const menuRows = SCREEN_REGISTRY.filter((row) => row.inMenu && !['home', 'admin'].includes(row.group)).map((row) => row.address);
    expect(menuRows.sort()).toEqual(RULING.flatMap((group) => group.items.map(([address]) => address)).sort());
  });
});

// ---------------------------------------------------------------------- the menu states

describe('the frame’s menu per kind of visitor', () => {
  it('a guest: no navigation, no account menu, one «Вход» link', () => {
    const markup = renderFrame(null);
    expect(markup).not.toContain('aria-label="Разделы"');
    expect(markup).not.toContain('aria-haspopup="menu"');
    expect([...markup.matchAll(/<a [^>]*href="\/login"[^>]*>([^<]*)<\/a>/g)].map((m) => m[1])).toEqual(['Вход']);
  });

  it('a default credential and an incomplete profile: no navigation, but the account menu to move on with', () => {
    for (const changes of [{ isDefaultCredential: true }, { profileComplete: false }]) {
      const markup = renderFrame(frameSession(changes));
      expect(markup, JSON.stringify(changes)).not.toContain('aria-label="Разделы"');
      expect(markup, JSON.stringify(changes)).toContain('aria-haspopup="menu"');
      expect(markup, JSON.stringify(changes)).not.toContain('>Вход<');
    }
  });

  it('R-80: a complete profile with an empty role set: brand and account menu, no duplicate home link', () => {
    const markup = renderFrame(frameSession({ roles: [] }));
    expect(markup).not.toContain('aria-label="Разделы"');
    // The brand is the one link home: a glyph and the «AuditManager» label, named for assistive technology.
    expect(markup).toMatch(
      /<a[^>]*aria-label="AuditManager — главная"[^>]*href="\/"[^>]*>(?:<svg[^>]*>[\s\S]*?<\/svg>)?<span[^>]*>AuditManager<\/span><\/a>/,
    );
    expect(markup.match(/<a[^>]*href="\/"/g)).toHaveLength(1);
    expect(markup).toContain('aria-haspopup="menu"');
    expect(markup).toContain('Роли не назначены.');
  });

  it('the account menu’s items: Профиль, Сменить пароль, and Выйти as a POST', () => {
    // `R-150b`: the frame holds a second menu button now, the project selector; the account menu is its own region.
    const markup = region(renderFrame(frameSession()), 'data-account-menu');
    const items = [...markup.matchAll(/<(a|button)[^>]*role="menuitem"[^>]*>([^<]*)<\/(?:a|button)>/g)].map((m) => [
      m[1],
      m[2],
    ]);
    expect(items).toEqual([
      ['a', 'Профиль'],
      ['a', 'Сменить пароль'],
      ['button', 'История версий'],
      ['button', 'Выйти'],
    ]);
    const form = /<form[^>]*>(?=<button type="submit"[^>]*role="menuitem")/.exec(markup)?.[0] ?? '';
    expect(form).toContain('method="post"');
    expect(form).toContain('action="/bff/v1/session/end"');
  });
});

// ------------------------------------------------------------------------------------ R-150b

describe('R-150b: «Проекты» left the menu rows, and the selector in the top strip took its place', () => {
  const ROLE_SETS = [['expert'], ['admin'], ['admin', 'expert']] as const;

  it('/projects is a registered, open screen that no menu offers', () => {
    expect(screenAt('/projects')).toEqual({
      address: '/projects',
      label: 'Проекты',
      group: 'work',
      access: 'session',
      roles: 'any-role',
      inMenu: false,
      projectScope: 'global',
    });
    expect(SCREEN_REGISTRY.filter((row) => row.inMenu).map((row) => row.address)).not.toContain('/projects');
  });

  it('is in no group of the data, and `R-153h` draws it only as the first item of «Работа» in all three states of the bar', () => {
    for (const roles of ROLE_SETS) {
      const navigation = buildNavigation({ roles, isDefaultCredential: false, profileComplete: true });
      const offered = navigation.groups.flatMap((group) => group.items.map((item) => item.address));
      expect(offered, roles.join(',')).not.toContain('/projects');
      expect(navigation.groups[0]?.items.map((item) => item.address)[0], roles.join(',')).toBe('/dashboard');
      const markup = renderFrame(frameSession({ roles }));
      for (const state of ['row', 'rail', 'stacked']) {
        const links = [...region(markup, `data-nav-state="${state}"`).matchAll(/<a [^>]*href="([^"]+)"/g)].map((m) => m[1]);
        expect(links.filter((href) => href === '/projects'), `${roles.join(',')} ${state}`).toHaveLength(1);
        expect(links[0], `${roles.join(',')} ${state}`).toBe('/projects');
      }
    }
  });

  it('is reached from the selector instead: «Новый проект» and «Все проекты» lead to it', () => {
    const selector = region(renderFrame(frameSession()), 'data-project-switcher');
    expect(selector).toContain('data-project-switcher');
    // The frame renders with no router, so its address is unknown and behaves like a global screen:
    // both entries are the project list.
    // «Все проекты» is the choice the address makes (it names no project), so it carries the ✓ cell of `D-363` after its words.
    expect([...selector.matchAll(/<a [^>]*role="menuitem"[^>]*href="([^"]+)"[^>]*>([^<]*)(?:<span class="am-menu__check"[^>]*>[^<]*<\/span>)?<\/a>/g)].map((m) => [m[1], m[2]])).toEqual([
      ['/projects', 'Все проекты'],
      ['/projects', 'Новый проект'],
    ]);
  });

  it('stands in the top strip, after the screen\'s own name and before the stand, theme and account controls', () => {
    const markup = renderFrame(frameSession());
    const strip = markup.slice(markup.indexOf('class="am-app__utility"'), markup.indexOf('<main'));
    const order = ['aria-label="Текущий раздел"', 'data-project-switcher', 'aria-label="Оформление"', 'data-account-menu'].map((marker) =>
      strip.indexOf(marker),
    );
    expect(order.every((at) => at >= 0), JSON.stringify(order)).toBe(true);
    expect(order).toEqual([...order].sort((a, b) => a - b));
  });

  it('is offered to exactly the sessions that may open the project list', () => {
    expect(renderFrame(null)).not.toContain('data-project-switcher');
    for (const changes of [{ isDefaultCredential: true }, { profileComplete: false }, { roles: [] }, { roles: ['auditor'] }]) {
      expect(renderFrame(frameSession(changes)), JSON.stringify(changes)).not.toContain('data-project-switcher');
    }
    for (const roles of ROLE_SETS) {
      expect(renderFrame(frameSession({ roles })), roles.join(',')).toContain('data-project-switcher');
    }
  });
});
