/**
 * `W50-QA-01`, the `R-66` item — the navigation amendment as the owner ruled it, on the merged
 * frame.
 *
 * `OWNER_RULINGS_2026-09-17.md` §3.22: **Работа** — Проекты `/projects`, Дашборд `/dashboard`,
 * «Оптимизация разделов» `/section-optimisation` (stub); **Знания** — База знаний
 * `/knowledge-base`, Блоки `/blocks`, «Нормы» `/norms` (stub); **Система** — Журнал выполнения
 * `/logs`, Исполнители `/workers`, «Настройки анализа» `/analysis-settings` (stub), «Очередь»
 * `/queue` (stub); `/optimisation` leaves the menu and stays a registered, reachable screen
 * (group `hidden`). Each stub is `RoutePlaceholder`, says it is not implemented, shows no digit
 * and invents no data; access `session`, roles `any`.
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

import { readFileSync } from 'node:fs';
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
import { RoutePlaceholder } from '@/shared/ui';

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
      ['/projects', 'Проекты'],
      ['/dashboard', 'Дашборд'],
      ['/section-optimisation', 'Оптимизация разделов'],
    ],
  },
  {
    group: 'Знания',
    items: [
      ['/knowledge-base', 'База знаний'],
      ['/blocks', 'Блоки'],
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

/** The four stubs of `R-66`, each with the group the ruling puts it in. */
const STUBS: readonly { readonly address: string; readonly label: string; readonly group: string }[] = [
  { address: '/section-optimisation', label: 'Оптимизация разделов', group: 'work' },
  { address: '/norms', label: 'Нормы', group: 'knowledge' },
  { address: '/analysis-settings', label: 'Настройки анализа', group: 'system' },
  { address: '/queue', label: 'Очередь', group: 'system' },
];

const COMPLETE: SessionAccount = {
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
  const links = [...html.matchAll(/<a [^>]*href="([^"]+)"[^>]*>([^<]*)<\/a>/g)].map(
    (m) => [m[1] as string, m[2] as string] as [string, string],
  );
  return { groups, links };
}

const RULED_LINKS: [string, string][] = [['/', 'Главная'], ...RULING.flatMap((g) => g.items.map(([a, l]) => [a, l] as [string, string]))];

// --------------------------------------------------------------------------------- the menu

describe('R-66: the menu’s groups and items equal the ruling’s, in order', () => {
  it('as data: non-admin sessions see exactly the R-66 groups and their order', () => {
    for (const roles of [['expert'], []] as const) {
      const navigation = buildNavigation({ roles, isDefaultCredential: false, profileComplete: true });
      expect(navigation.home, `roles [${roles.join(',')}]`).toEqual({ address: '/', label: 'Главная' });
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
  it('is registered: group hidden, not in the menu, session/any', () => {
    expect(screenAt('/optimisation')).toMatchObject({ group: 'hidden', inMenu: false, access: 'session', roles: 'any' });
  });

  it('is absent from every group, as data and in the rendered frame', () => {
    for (const roles of [['expert'], ['admin', 'expert'], []] as const) {
      const navigation = buildNavigation({ roles, isDefaultCredential: false, profileComplete: true });
      const offered = navigation.groups.flatMap((group) => group.items.map((item) => item.address));
      expect(offered).not.toContain('/optimisation');
    }
    expect(renderFrame(frameSession())).not.toContain('href="/optimisation"');
  });

  it('a complete-profile session opens it: the guard returns and the route renders its screen', async () => {
    forgetEverySession();
    jar.value = openSession({ ...COMPLETE, roles: [] }, 'qa-credential', 3600);
    const { default: OptimisationRoute } = await import('@/app/optimisation/page');
    const element = await OptimisationRoute({ params: Promise.resolve({}), searchParams: Promise.resolve({}) });
    expect(isValidElement(element) && element.type === OptimisationPage).toBe(true);
  });
});

// -------------------------------------------------------------------------------- the stubs

const fetchSpy = vi.fn(async () => {
  throw new Error('a stub made a network call');
});

describe('R-66: each of the four stubs is an honest RoutePlaceholder', () => {
  beforeEach(() => {
    forgetEverySession();
    jar.value = openSession(COMPLETE, 'qa-credential', 3600);
    fetchSpy.mockClear();
    vi.stubGlobal('fetch', fetchSpy);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  for (const stub of STUBS) {
    describe(stub.address, () => {
      it('is registered session / any, in the ruled group, in the menu, under the ruled label', () => {
        expect(screenAt(stub.address)).toEqual({
          address: stub.address,
          label: stub.label,
          group: stub.group,
          access: 'session',
          roles: 'any',
          inMenu: true,
        });
      });

      it('renders RoutePlaceholder for its own address, says it is not implemented, shows no digit, calls nothing', async () => {
        const module = (await import(/* @vite-ignore */ join(WEB_ROOT, 'src', 'app', stub.address.slice(1), 'page.tsx'))) as {
          default: (props: unknown) => Promise<ReactElement>;
        };
        const routed = await module.default({ params: Promise.resolve({}), searchParams: Promise.resolve({}) });
        // The route renders a page component, and that component renders RoutePlaceholder itself.
        const page = (routed.type as (props: object) => ReactElement)(routed.props as object);
        expect(page.type, `${stub.address} does not render RoutePlaceholder`).toBe(RoutePlaceholder);
        expect((page.props as { route?: unknown }).route).toBe(stub.address);

        const client = newClient();
        const markup = renderScreen(client, routed);
        const text = [...markup.matchAll(/>([^<>]+)</g)].map((m) => (m[1] ?? '').trim()).filter(Boolean).join(' ');
        expect(markup).toContain(`data-route="${stub.address}"`);
        // It says it is not implemented: the placeholder's own two sentences.
        expect(text).toContain('Раздел пока недоступен');
        expect(text).toContain('Этот раздел ещё не готов.');
        expect(text).toContain(stub.label);
        // No digit anywhere the reader sees.
        expect(text.match(/\d/g), `${stub.address} shows a digit: ${text}`).toBeNull();
        // It invents no data: no request made, no query opened, no list or table drawn.
        expect(fetchSpy).not.toHaveBeenCalled();
        expect(client.getQueryCache().getAll()).toEqual([]);
        expect(markup).not.toMatch(/<(table|ul|ol|li|dl)\b/);
      });

      it('its source asks nothing of the API', () => {
        const pageModule = readFileSync(
          join(WEB_ROOT, 'src', '_pages', stub.address.slice(1), 'ui', `${stub.address.slice(1)}-page.tsx`),
          'utf8',
        );
        expect(pageModule).not.toMatch(/from '@\/shared\/api|useQuery|fetch\(/);
      });

      it('a guest is sent to sign in, carrying it in next', async () => {
        jar.value = null;
        const module = (await import(/* @vite-ignore */ join(WEB_ROOT, 'src', 'app', stub.address.slice(1), 'page.tsx'))) as {
          default: (props: unknown) => Promise<unknown>;
        };
        let location: string | null = null;
        try {
          await module.default({ params: Promise.resolve({}), searchParams: Promise.resolve({ from: 'menu' }) });
        } catch (thrown) {
          location = String((thrown as { digest?: unknown }).digest ?? '').split(';')[2] ?? null;
        }
        expect(location).toBe(`/login?next=${encodeURIComponent(`${stub.address}?from=menu`)}`);
      });
    });
  }

  it('the four are exactly the ruling’s stubs among the menu rows (no fifth placeholder hides in the menu)', () => {
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

  it('a complete profile with an empty role set: the whole ruled menu, and the account menu', () => {
    const markup = renderFrame(frameSession({ roles: [] }));
    expect(readMenu(region(markup, 'data-nav-state="row"')).links).toEqual(RULED_LINKS);
    expect(markup).toContain('Роли не назначены.');
  });

  it('the account menu’s items: Профиль, Сменить пароль, and Выйти as a POST', () => {
    const markup = renderFrame(frameSession());
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
