/**
 * `UI-A-06`, `UI-A-91`: the counters beside «Очередь», «База знаний» and «Заявки на регистрацию» in the side menu
 * (and `UI-A-05`'s red number of a section, which `section-navigation.test.ts` holds).
 *
 * Three layers, as `section-navigation.test.ts` reads «Разделы»: the model is pure and read as data (`menu-badges.ts`);
 * the markup is read off a static pass of the frame's navigation in its three states; and the wiring (which session
 * reads what, under which key, at which cadence, and what a loading or failed read draws) is read off a mounted frame
 * over a seeded cache. Nothing here runs an effect: a static pass is what the shell's tests are.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

import type { AppFrameSession } from '@/_app';
import { FrameNavigation, FrameNavigationView } from '@/_app/frame-navigation';
import {
  KNOWLEDGE_BASE_BADGE_LABEL, KNOWLEDGE_BASE_PROJECT_BADGE_LABEL, QUEUE_BADGE_LABEL, QUEUE_ERROR_STATES, QUEUE_ERROR_WINDOW_HOURS,
  QUEUE_ERRORS_BADGE_LABEL, QUEUE_OPEN_STATES, badgeSourceAt, badgeSourcesOf, badgeText, itemLabelWithBadges, menuBadgesOf, queueBadges,
  uncheckedBadges,
} from '@/_app/menu-badges';
import type { MenuBadges } from '@/_app/menu-badges';
import { buildNavigation } from '@/_app/navigation';
import { queryKeys } from '@/shared/api';
import type { DecisionRecordPage, ExecutionQueuePage, ExecutionQueueStateCount, RegistrationRequestPage } from '@/shared/api';
import { OPERATIONAL_LIST_POLL } from '@/entities/execution';
import { initialsOf } from '@/entities/account';
import { PendingRegistrationsTile } from '@/widgets/home-tiles';

import { newClient, renderWith, seedError } from '../screens/harness';
import { ADMIN_AND_EXPERT, ADMIN_ONLY, DEFAULT_CREDENTIAL, EXPERT, NO_ROLES } from './subjects';

const navigationState = vi.hoisted(() => ({ pathname: '/dashboard' as string | null, search: '' }));

vi.mock('next/navigation', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  usePathname: () => navigationState.pathname,
  useSearchParams: () => new URLSearchParams(navigationState.search),
}));

/** `R-150w`: a viewer reads the knowledge base and not the queue. */
const VIEWER: AppFrameSession = {
  login: 'наблюдатель@пример.испытание',
  displayLabel: 'Наблюдателева Д. Е.',
  initials: initialsOf('Наблюдателева Д. Е.'),
  roles: ['viewer'],
  isDefaultCredential: false,
  profileComplete: true,
};

const QUEUE = '/queue';
const KNOWLEDGE_BASE = '/knowledge-base';
const REGISTRATIONS = '/admin/registrations';

const overview = (counts: Partial<Record<ExecutionQueueStateCount['state'], number>>): ExecutionQueueStateCount[] =>
  (['queued', 'leased', 'running', 'retry_wait', 'succeeded', 'failed', 'cancelled', 'dead_letter'] as const).map((state) => ({
    state,
    count: counts[state] ?? 0,
  }));

const queuePage = (counts: Partial<Record<ExecutionQueueStateCount['state'], number>> | null): ExecutionQueuePage => ({
  items: [],
  page: { next_cursor: null },
  paused: false,
  ...(counts === null ? {} : { overview: overview(counts) }),
});

const knowledgePage = (total: number): DecisionRecordPage => ({ items: [], page: { next_cursor: null }, total });
const registrationPage = (pending: number): RegistrationRequestPage => ({ items: [], page: { next_cursor: null }, pending_total: pending });

// ------------------------------------------------------------------------------------------- the model

describe('which items carry a badge, and for whom the frame reads', () => {
  it('names the queue, the knowledge base and the registrations by their registry addresses, and nothing else', () => {
    expect(badgeSourceAt(QUEUE)).toBe('queue');
    expect(badgeSourceAt(KNOWLEDGE_BASE)).toBe('knowledge-base');
    expect(badgeSourceAt(REGISTRATIONS)).toBe('registrations');
    for (const other of ['/', '/projects', '/logs', '/workers', '/norms', '/analysis-settings', '/admin/users']) {
      expect(badgeSourceAt(other), other).toBeNull();
    }
  });

  it('reads exactly what the session\'s menu holds: an expert the queue and the base, an administrator the requests too, a viewer the base only', () => {
    const sources = (subject: AppFrameSession | null) => [...badgeSourcesOf(buildNavigation(subject))].sort();
    expect(sources(EXPERT)).toEqual(['knowledge-base', 'queue']);
    expect(sources(ADMIN_ONLY)).toEqual(['knowledge-base', 'queue', 'registrations']);
    expect(sources(ADMIN_AND_EXPERT)).toEqual(['knowledge-base', 'queue', 'registrations']);
    expect(sources(VIEWER)).toEqual(['knowledge-base']);
  });

  it('reads nothing for a guest, a default credential or an account with no role: they have no menu', () => {
    for (const subject of [null, DEFAULT_CREDENTIAL, NO_ROLES]) {
      expect(badgeSourcesOf(buildNavigation(subject)).size, String(subject?.login)).toBe(0);
    }
  });

  it('can fail: a menu without the row is not read for it', () => {
    expect(badgeSourcesOf({ groups: [] }).size).toBe(0);
  });
});

describe('the queue badge: the jobs that are waiting or being run', () => {
  it('sums queued, leased, running and waiting for a retry, and nothing that is over', () => {
    expect(QUEUE_OPEN_STATES).toEqual(['queued', 'leased', 'running', 'retry_wait']);
    const badges = queueBadges(overview({ queued: 3, leased: 1, running: 2, retry_wait: 1, succeeded: 500, failed: 40, cancelled: 7, dead_letter: 2 }));
    expect(badges).toEqual([{ tone: 'count', count: 7, label: `${QUEUE_BADGE_LABEL}: 7` }]);
  });

  it('is no badge at zero open jobs, whatever the finished ones add up to: the whole history makes no red mark', () => {
    expect(queueBadges(overview({ succeeded: 12, failed: 9, dead_letter: 3 }))).toEqual([]);
    expect(queueBadges(overview({}))).toEqual([]);
    expect(queueBadges(overview({ failed: 9 })).some((badge) => badge.tone === 'alert')).toBe(false);
  });

  it('is no badge, not a zero, when the page carried no overview', () => {
    expect(queueBadges(undefined)).toEqual([]);
  });
});

describe('D-331: the queue\'s red mark counts the jobs accepted in the last 24 hours that ended in an error', () => {
  const RED_LABEL = `Заданий с ошибкой за последние 24 часа`;

  it('names the window and the states in words, and a constant says how many hours', () => {
    expect(QUEUE_ERROR_WINDOW_HOURS).toBe(24);
    expect(QUEUE_ERRORS_BADGE_LABEL).toBe(RED_LABEL);
    expect(QUEUE_ERROR_STATES).toEqual(['failed', 'dead_letter']);
  });

  it('is the failed and the dead-lettered jobs of the recent overview, in the alert tone, after the open count', () => {
    const badges = queueBadges(overview({ queued: 3 }), overview({ queued: 1, succeeded: 40, failed: 2, dead_letter: 1, cancelled: 5 }));
    expect(badges.map((badge) => [badge.tone, badge.count, badge.label])).toEqual([
      ['count', 3, `${QUEUE_BADGE_LABEL}: 3`],
      ['alert', 3, `${RED_LABEL}: 3`],
    ]);
    expect(badges[1]?.title).toContain(`${RED_LABEL}: 3.`);
    expect(badges[1]?.title).toContain('«Очередь»');
  });

  it('counts only the recent overview: the whole history\'s failures are not the red mark', () => {
    // 40 failed since the beginning, none in the last day: no red mark, and the open count stays.
    const badges = queueBadges(overview({ queued: 3, failed: 40 }), overview({ succeeded: 2 }));
    expect(badges.map((badge) => badge.tone)).toEqual(['count']);
  });

  it('is its own badge: the open count may be unknown or zero while the red mark stands, and the other way round', () => {
    expect(queueBadges(undefined, overview({ failed: 2 })).map((badge) => [badge.tone, badge.count])).toEqual([['alert', 2]]);
    expect(queueBadges(overview({}), overview({ dead_letter: 1 })).map((badge) => [badge.tone, badge.count])).toEqual([['alert', 1]]);
    expect(queueBadges(overview({ running: 1 }), undefined).map((badge) => badge.tone)).toEqual(['count']);
  });

  it('is no badge for a zero, for a recent overview that is unknown, or for jobs that are merely waiting to be retried', () => {
    expect(queueBadges(overview({}), overview({ failed: 0 }))).toEqual([]);
    expect(queueBadges(overview({}), undefined)).toEqual([]);
    // `retry_wait` is a failed attempt that will run again: it is open work, not an error mark.
    expect(queueBadges(undefined, overview({ retry_wait: 4, queued: 2 }))).toEqual([]);
  });
});

describe('the figures of the other items, and the words that name them', () => {
  it('draws a count only for a figure above zero: unknown and zero are no badge', () => {
    expect(menuBadgesOf({})).toEqual({});
    expect(menuBadgesOf({ knowledgeBaseTotal: 0, pendingRegistrations: 0, queueOverview: overview({}) })).toEqual({});
    expect(menuBadgesOf({ knowledgeBaseTotal: 12, pendingRegistrations: 4 })).toEqual({
      [KNOWLEDGE_BASE]: [{ tone: 'count', count: 12, label: 'Решений по замечаниям в базе знаний: 12' }],
      [REGISTRATIONS]: [{ tone: 'count', count: 4, label: 'Заявок на регистрацию, ожидающих решения: 4' }],
    });
  });

  it('draws the section\'s red mark only for a figure above zero', () => {
    expect(uncheckedBadges(null)).toEqual([]);
    expect(uncheckedBadges(undefined)).toEqual([]);
    expect(uncheckedBadges(0)).toEqual([]);
    expect(uncheckedBadges(2)).toHaveLength(1);
    expect(uncheckedBadges(2)[0]).toMatchObject({ tone: 'alert', count: 2, label: 'Не проверено экспертом: 2' });
  });

  it('shows 99+ past two digits, and names an item with what each of its numbers counts', () => {
    expect([0, 1, 99, 100, 12345].map(badgeText)).toEqual(['0', '1', '99', '99+', '99+']);
    expect(itemLabelWithBadges('Очередь', [])).toBe('Очередь');
    expect(itemLabelWithBadges('Очередь', queueBadges(overview({ queued: 3 })))).toBe('Очередь. Задач в очереди и в работе: 3');
  });
});

// ------------------------------------------------------------------------------------------- the markup

const BADGES: MenuBadges = menuBadgesOf({
  queueOverview: overview({ queued: 2, running: 1 }),
  knowledgeBaseTotal: 140,
  pendingRegistrations: 5,
});

/** The same, with two jobs of the last day in an error: «Очередь» then carries a count and a red mark. */
const BADGES_WITH_ERRORS: MenuBadges = menuBadgesOf({
  queueOverview: overview({ queued: 2, running: 1, failed: 30 }),
  queueRecentOverview: overview({ failed: 2 }),
  knowledgeBaseTotal: 140,
  pendingRegistrations: 5,
});

function draw(badges: MenuBadges | undefined, subject: AppFrameSession | null = ADMIN_ONLY): string {
  return renderToStaticMarkup(
    createElement(FrameNavigationView, { navigation: buildNavigation(subject), pathname: '/', badges }),
  );
}

/** One of the three states of the navigation, by its marker. */
function state(markup: string, name: 'row' | 'rail' | 'stacked'): string {
  const parts = markup.split(/<div class="[^"]*" data-nav-state="/).slice(1);
  const found = parts.find((part) => part.startsWith(`${name}"`));
  if (found === undefined) throw new Error(`no ${name} state`);
  return found;
}

/** Every link of a state, its attributes and its inside. */
const linksIn = (markup: string): { readonly href: string; readonly attributes: string; readonly inside: string }[] =>
  [...markup.matchAll(/<a\b([^>]*)>(.*?)<\/a>/g)].map((m) => ({
    href: /\bhref="([^"]*)"/.exec(m[1] as string)?.[1] ?? '',
    attributes: m[1] as string,
    inside: m[2] as string,
  }));

const linkAt = (markup: string, href: string) => linksIn(markup).find((link) => link.href === href);
const pillsIn = (inside: string): string[] => [...inside.matchAll(/data-menu-badge="(\w+)">([^<]*)</g)].map((m) => `${m[1]}:${m[2]}`);

describe('the badges in the menu, in all three of its states', () => {
  it('stand at the right end of the item\'s link in the bar and in the stacked menu, with a name that says what they count', () => {
    const markup = draw(BADGES);
    for (const name of ['row', 'stacked'] as const) {
      const queue = linkAt(state(markup, name), QUEUE);
      expect(queue, `${name} queue`).toBeDefined();
      expect(queue?.attributes).toContain('aria-label="Очередь. Задач в очереди и в работе: 3"');
      expect(pillsIn(queue?.inside ?? '')).toEqual(['count:3']);
      expect(queue?.inside).toContain('title="Задач в очереди и в работе: 3"');
      // The pill follows the name, after the icon.
      expect((queue?.inside ?? '').indexOf('Очередь')).toBeLessThan((queue?.inside ?? '').indexOf('data-menu-badge'));

      const base = linkAt(state(markup, name), KNOWLEDGE_BASE);
      expect(base?.attributes).toContain('aria-label="База знаний. Решений по замечаниям в базе знаний: 140"');
      expect(pillsIn(base?.inside ?? '')).toEqual(['count:99+']);
      expect(base?.inside).toContain('title="Решений по замечаниям в базе знаний: 140"');

      const requests = linkAt(state(markup, name), REGISTRATIONS);
      expect(requests?.attributes).toContain('aria-label="Заявки на регистрацию. Заявок на регистрацию, ожидающих решения: 5"');
      expect(pillsIn(requests?.inside ?? '')).toEqual(['count:5']);
    }
  });

  it('ride the corner of the glyph in the compact rail, which carries the words in the link\'s name', () => {
    const rail = state(draw(BADGES), 'rail');
    const queue = linkAt(rail, QUEUE);
    expect(queue?.attributes).toContain('aria-label="Очередь. Задач в очереди и в работе: 3"');
    expect(pillsIn(queue?.inside ?? '')).toEqual(['count:3']);
    expect(queue?.inside).toMatch(/aria-hidden="true"><span[^>]*data-menu-badge="count">3</);
    expect(pillsIn(linkAt(rail, REGISTRATIONS)?.inside ?? '')).toEqual(['count:5']);
    expect(pillsIn(linkAt(rail, KNOWLEDGE_BASE)?.inside ?? '')).toEqual(['count:99+']);
  });

  it('D-331: carry the red mark beside the open count on «Очередь», in all three states, named in the link\'s name', () => {
    const markup = draw(BADGES_WITH_ERRORS);
    for (const name of ['row', 'rail', 'stacked'] as const) {
      const queue = linkAt(state(markup, name), QUEUE);
      expect(queue?.attributes, name).toContain(
        `aria-label="Очередь. Задач в очереди и в работе: 3. Заданий с ошибкой за последние 24 часа: 2"`,
      );
      expect(pillsIn(queue?.inside ?? ''), name).toEqual(['count:3', 'alert:2']);
      expect(queue?.inside, name).toContain('title="Заданий с ошибкой за последние 24 часа: 2.');
    }
    // The other items keep their one count and no red mark.
    expect(pillsIn(linkAt(state(markup, 'row'), KNOWLEDGE_BASE)?.inside ?? '')).toEqual(['count:99+']);
    expect(pillsIn(linkAt(state(markup, 'row'), REGISTRATIONS)?.inside ?? '')).toEqual(['count:5']);
    // Without the recent overview the red mark is gone and the count is as it was.
    expect(pillsIn(linkAt(state(draw(BADGES), 'row'), QUEUE)?.inside ?? '')).toEqual(['count:3']);
  });

  it('leave an item with no figure as the plain link it was, and the other items as they were', () => {
    const only = menuBadgesOf({ pendingRegistrations: 5 });
    for (const name of ['row', 'rail', 'stacked'] as const) {
      const markup = state(draw(only), name);
      const queue = linkAt(markup, QUEUE);
      expect(queue?.attributes, name).not.toContain('aria-label="Очередь.');
      expect(pillsIn(queue?.inside ?? ''), name).toEqual([]);
      expect(pillsIn(linkAt(markup, REGISTRATIONS)?.inside ?? ''), name).toEqual(['count:5']);
    }
    const norms = linkAt(state(draw(only), 'row'), '/norms');
    expect(norms?.attributes).not.toContain('aria-label');
    expect(draw({})).not.toContain('data-menu-badge');
  });

  it('draw a group that holds a badged item in the very markup the shared Disclosure draws for links', () => {
    // The group's list is the fork `BadgedLinks`; with no figure yet it must be indistinguishable from the original.
    expect(draw({})).toBe(draw(undefined));
    expect(draw({}, EXPERT)).toBe(draw(undefined, EXPERT));
    expect(draw({}, VIEWER)).toBe(draw(undefined, VIEWER));
  });

  it('are not drawn for a session whose menu does not hold the item', () => {
    const markup = draw(BADGES, VIEWER);
    expect(linkAt(state(markup, 'row'), QUEUE)).toBeUndefined();
    expect(linkAt(state(markup, 'row'), REGISTRATIONS)).toBeUndefined();
    expect(pillsIn(linkAt(state(markup, 'row'), KNOWLEDGE_BASE)?.inside ?? '')).toEqual(['count:99+']);
    expect(draw(BADGES, EXPERT)).not.toContain(REGISTRATIONS);
  });

  it('keep the item\'s current mark', () => {
    const current = renderToStaticMarkup(
      createElement(FrameNavigationView, { navigation: buildNavigation(ADMIN_ONLY), pathname: QUEUE, badges: BADGES }),
    );
    for (const name of ['row', 'rail', 'stacked'] as const) {
      expect(linkAt(state(current, name), QUEUE)?.attributes, name).toContain('aria-current="page"');
      expect(linkAt(state(current, name), KNOWLEDGE_BASE)?.attributes, name).not.toContain('aria-current');
    }
  });
});

// ------------------------------------------------------------------------------------------- the wiring

const KB_KEY = queryKeys.findings.journal({ limit: 1 });
const PENDING_KEY = queryKeys.registrations.list({ status: 'pending', limit: 1 });
const QUEUE_KEY = queryKeys.execution.queueCount('all');
const RECENT_QUEUE_KEY = queryKeys.execution.queueCount('last-day');

function frame(client: QueryClient, subject: AppFrameSession | null): string {
  navigationState.pathname = '/dashboard';
  navigationState.search = '';
  return renderWith(client, createElement(FrameNavigation, { navigation: buildNavigation(subject), offersSections: false }));
}

function seeded(): QueryClient {
  const client = newClient();
  client.setQueryData(QUEUE_KEY, queuePage({ queued: 2, running: 1, failed: 30 }));
  // Nothing failed in the last day, whatever the whole history holds.
  client.setQueryData(RECENT_QUEUE_KEY, queuePage({ succeeded: 4 }));
  client.setQueryData(KB_KEY, knowledgePage(140));
  client.setQueryData(PENDING_KEY, registrationPage(5));
  return client;
}

/** Each read the frame filed: its key and whether it may ask the server. */
function readsOf(client: QueryClient): { key: string; enabled: boolean }[] {
  return client
    .getQueryCache()
    .getAll()
    .map((query) => ({ key: String(query.queryKey[0]) + '/' + String(query.queryKey[1]), enabled: (query.options as { enabled?: unknown }).enabled !== false }))
    .sort((a, b) => a.key.localeCompare(b.key));
}

describe('the frame reads the counters from the cache entries of the screens they lead to', () => {
  it('draws all three for an administrator from the queue\'s overview, the base\'s total and the pending requests', () => {
    const markup = frame(seeded(), ADMIN_ONLY);
    const row = state(markup, 'row');
    expect(pillsIn(linkAt(row, QUEUE)?.inside ?? '')).toEqual(['count:3']);
    expect(pillsIn(linkAt(row, KNOWLEDGE_BASE)?.inside ?? '')).toEqual(['count:99+']);
    expect(pillsIn(linkAt(row, REGISTRATIONS)?.inside ?? '')).toEqual(['count:5']);
    // The 30 failed jobs of the whole history make no red mark: only the jobs of the last day do (`D-331`), and none failed in it.
    expect(markup).not.toContain('data-menu-badge="alert"');
    expect(pillsIn(linkAt(state(markup, 'rail'), QUEUE)?.inside ?? '')).toEqual(['count:3']);
    expect(pillsIn(linkAt(state(markup, 'stacked'), REGISTRATIONS)?.inside ?? '')).toEqual(['count:5']);
  });

  it('shares the pending requests with the home page\'s tile: one cache entry, one figure', () => {
    const client = seeded();
    const tile = renderWith(client, createElement(PendingRegistrationsTile, { href: null }));
    expect(tile).toContain('data-pending-total="5"');
    client.setQueryData(PENDING_KEY, registrationPage(8));
    expect(renderWith(client, createElement(PendingRegistrationsTile, { href: null }))).toContain('data-pending-total="8"');
    expect(pillsIn(linkAt(state(frame(client, ADMIN_ONLY), 'row'), REGISTRATIONS)?.inside ?? '')).toEqual(['count:8']);
  });

  it('asks only for what the menu holds: the queue is closed to a viewer and the requests to all but an administrator', () => {
    const viewer = seeded();
    const markup = frame(viewer, VIEWER);
    expect(pillsIn(linkAt(state(markup, 'row'), KNOWLEDGE_BASE)?.inside ?? '')).toEqual(['count:99+']);
    expect(markup).not.toContain(QUEUE);
    // The entries another screen left in the cache are not read for a menu that does not hold the item.
    expect(markup).not.toContain('Задач в очереди');
    expect(markup).not.toContain('Заявок на регистрацию');
    const unasked = (client: QueryClient) => readsOf(client).filter((read) => !read.enabled).map((read) => read.key);
    // The queue is read twice (the whole history, the last day), and neither is asked for a viewer.
    expect(unasked(viewer)).toEqual(['execution/queue-count', 'execution/queue-count', 'registrations/list']);

    const expert = seeded();
    frame(expert, EXPERT);
    expect(unasked(expert)).toEqual(['registrations/list']);

    const admin = seeded();
    frame(admin, ADMIN_ONLY);
    expect(unasked(admin)).toEqual([]);
  });

  it('files no read, and draws no badge, for a guest, a default credential and an account with no role', () => {
    for (const subject of [null, DEFAULT_CREDENTIAL, NO_ROLES]) {
      const client = newClient();
      const markup = frame(client, subject);
      expect(markup, String(subject?.login)).not.toContain('data-menu-badge');
      expect(client.getQueryCache().getAll(), String(subject?.login)).toHaveLength(0);
    }
  });

  it('files the four reads under their keys, once each: the two queue counters, the base\'s «Все» chip entry, the tile\'s entry', () => {
    const client = newClient();
    frame(client, ADMIN_ONLY);
    const reads = client.getQueryCache().getAll().map((query) => query.queryHash).sort();
    expect(reads).toEqual(
      [QUEUE_KEY, RECENT_QUEUE_KEY, KB_KEY, PENDING_KEY].map((key) => client.defaultQueryOptions({ queryKey: [...key] }).queryHash).sort(),
    );
  });

  it('D-350: the queue counters are not the queue screen\'s page, so the menu cannot fill that key with a one-row page', () => {
    expect(JSON.stringify(QUEUE_KEY)).not.toBe(JSON.stringify(queryKeys.execution.queue()));
    expect(JSON.stringify(RECENT_QUEUE_KEY)).not.toBe(JSON.stringify(QUEUE_KEY));
    // Both stay under `execution`, which every command on the queue invalidates.
    expect(QUEUE_KEY.slice(0, 1)).toEqual(queryKeys.execution.all());
    expect(RECENT_QUEUE_KEY.slice(0, 1)).toEqual(queryKeys.execution.all());
    const client = newClient();
    frame(client, ADMIN_ONLY);
    expect(client.getQueryCache().find({ queryKey: [...queryKeys.execution.queue()] })).toBeUndefined();
  });

  it('D-350, D-331: asks the queue for one row twice, the second time from 24 hours back, and the instant is not in the key', async () => {
    const client = newClient();
    frame(client, ADMIN_ONLY);
    const asked: URL[] = [];
    vi.stubGlobal('fetch', async (input: RequestInfo | URL) => {
      asked.push(new URL(String(input), 'http://web.test'));
      return new Response(JSON.stringify(queuePage({ failed: 1 })), { status: 200, headers: { 'content-type': 'application/json' } });
    });
    const before = Date.now();
    try {
      for (const key of [QUEUE_KEY, RECENT_QUEUE_KEY]) {
        const query = client.getQueryCache().find({ queryKey: [...key] });
        await (query?.options.queryFn as (() => Promise<unknown>) | undefined)?.();
      }
    } finally {
      vi.unstubAllGlobals();
    }
    const after = Date.now();
    expect(asked).toHaveLength(2);
    const [all, recent] = asked as [URL, URL];
    for (const url of [all, recent]) {
      expect(url.pathname).toMatch(/\/execution\/queue$/);
      expect(url.searchParams.get('limit')).toBe('1');
      expect(url.searchParams.has('cursor')).toBe(false);
      expect(url.searchParams.has('state')).toBe(false);
    }
    expect(all.searchParams.has('created_from')).toBe(false);
    const from = Date.parse(recent.searchParams.get('created_from') ?? '');
    expect(Number.isNaN(from)).toBe(false);
    expect(from).toBeGreaterThanOrEqual(before - QUEUE_ERROR_WINDOW_HOURS * 3_600_000);
    expect(from).toBeLessThanOrEqual(after - QUEUE_ERROR_WINDOW_HOURS * 3_600_000);
    // The instant is not part of the key, so the cache holds one entry however long the page stays open.
    expect(JSON.stringify(RECENT_QUEUE_KEY)).not.toMatch(/\d{4}-\d\d-\d\d/);
    expect(recent.searchParams.get('created_to')).toBeNull();
  });

  it('D-331: draws the red mark from the last day\'s overview alone, beside the count, and drops it when that read failed', () => {
    const client = seeded();
    client.setQueryData(RECENT_QUEUE_KEY, queuePage({ failed: 2, dead_letter: 1, succeeded: 9 }));
    const markup = frame(client, ADMIN_ONLY);
    for (const name of ['row', 'rail', 'stacked'] as const) {
      expect(pillsIn(linkAt(state(markup, name), QUEUE)?.inside ?? ''), name).toEqual(['count:3', 'alert:3']);
    }
    client.getQueryCache().find({ queryKey: [...RECENT_QUEUE_KEY] })?.setState({ status: 'error', error: new Error('нет связи'), errorUpdatedAt: Date.now() + 1, fetchStatus: 'idle' });
    const row = state(frame(client, ADMIN_ONLY), 'row');
    expect(pillsIn(linkAt(row, QUEUE)?.inside ?? '')).toEqual(['count:3']);
    // And the other way: the whole-history read failing leaves the red mark.
    const other = seeded();
    other.setQueryData(RECENT_QUEUE_KEY, queuePage({ failed: 2 }));
    other.getQueryCache().find({ queryKey: [...QUEUE_KEY] })?.setState({ status: 'error', error: new Error('нет связи'), errorUpdatedAt: Date.now() + 1, fetchStatus: 'idle' });
    expect(pillsIn(linkAt(state(frame(other, ADMIN_ONLY), 'row'), QUEUE)?.inside ?? '')).toEqual(['alert:2']);
  });

  it('D-362: the base\'s counter is the decision journal\'s total, under the key of the screen\'s «Все» chip', () => {
    const client = newClient();
    frame(client, ADMIN_ONLY);
    const probe = client.getQueryCache().find({ queryKey: [...KB_KEY] });
    expect(probe).toBeDefined();
    // The knowledge base screen reads its chips with `limit: 1` under `findings.journal`; the menu shares that entry.
    expect(KB_KEY).toEqual(queryKeys.findings.journal({ limit: 1 }));
    expect(client.getQueryCache().find({ queryKey: [...queryKeys.findings.knowledgeBase({ limit: 1 })] })).toBeUndefined();
  });

  it('follows the operational-list cadence of polling.ts on every read, which the queue screen\'s own read already does', () => {
    const client = newClient();
    frame(client, ADMIN_ONLY);
    for (const query of client.getQueryCache().getAll()) {
      const options = query.options as { refetchInterval?: unknown; refetchIntervalInBackground?: unknown };
      expect(options.refetchInterval, String(query.queryKey)).toBe(OPERATIONAL_LIST_POLL.refetchInterval);
      expect(options.refetchIntervalInBackground, String(query.queryKey)).toBe(false);
    }
  });

  it('draws nothing while a read is loading: not a zero, not a mark', () => {
    const markup = frame(newClient(), ADMIN_ONLY);
    expect(markup).not.toContain('data-menu-badge');
    expect(markup).not.toContain('aria-label="Очередь.');
    expect(markup).not.toMatch(/>0</);
  });

  it('draws nothing for a read that failed, with or without an earlier answer: that number is not what the server says now', () => {
    const none = newClient();
    seedError(none, QUEUE_KEY, new Error('нет связи'));
    seedError(none, KB_KEY, new Error('нет связи'));
    seedError(none, PENDING_KEY, new Error('нет связи'));
    expect(frame(none, ADMIN_ONLY)).not.toContain('data-menu-badge');

    const kept = seeded();
    for (const key of [QUEUE_KEY, RECENT_QUEUE_KEY, KB_KEY, PENDING_KEY]) {
      kept.getQueryCache().find({ queryKey: [...key] })?.setState({ status: 'error', error: new Error('нет связи'), errorUpdatedAt: Date.now() + 1, fetchStatus: 'idle' });
    }
    const markup = frame(kept, ADMIN_ONLY);
    expect(markup).not.toContain('data-menu-badge');
    expect(markup).not.toContain('aria-label="Очередь.');
  });

  it('can fail: one read failing hides its own badge and leaves the others', () => {
    const client = seeded();
    client.getQueryCache().find({ queryKey: [...QUEUE_KEY] })?.setState({ status: 'error', error: new Error('нет связи'), errorUpdatedAt: Date.now() + 1, fetchStatus: 'idle' });
    const row = state(frame(client, ADMIN_ONLY), 'row');
    expect(pillsIn(linkAt(row, QUEUE)?.inside ?? '')).toEqual([]);
    expect(pillsIn(linkAt(row, REGISTRATIONS)?.inside ?? '')).toEqual(['count:5']);
  });

  it('draws nothing from a queue page that carries no overview, and nothing for a count of zero', () => {
    const client = seeded();
    client.setQueryData(QUEUE_KEY, queuePage(null));
    client.setQueryData(KB_KEY, knowledgePage(0));
    client.setQueryData(PENDING_KEY, registrationPage(0));
    expect(frame(client, ADMIN_ONLY)).not.toContain('data-menu-badge');
  });

  it('reads nothing, and does not fail, where there is no query client: the bare frame of the shell\'s own tests', () => {
    navigationState.pathname = '/dashboard';
    navigationState.search = '';
    const markup = renderToStaticMarkup(createElement(FrameNavigation, { navigation: buildNavigation(ADMIN_ONLY), offersSections: false }));
    expect(markup).toContain('Очередь');
    expect(markup).not.toContain('data-menu-badge');
    // And with a client that holds nothing, the same links.
    const client = new QueryClient();
    const withClient = renderToStaticMarkup(
      createElement(QueryClientProvider, { client }, createElement(FrameNavigation, { navigation: buildNavigation(ADMIN_ONLY), offersSections: false })),
    );
    expect(withClient).toContain('Очередь');
  });
});

// ------------------------------------------------------------------------------------------- the project of the address (R-150c)

const PROJECT = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const OTHER_PROJECT = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8C';
const PROJECT_KB_KEY = queryKeys.findings.journal({ project_uid: PROJECT, limit: 1 });
const OTHER_KB_KEY = queryKeys.findings.journal({ project_uid: OTHER_PROJECT, limit: 1 });

function frameAt(client: QueryClient, subject: AppFrameSession | null, pathname: string, search = ''): string {
  navigationState.pathname = pathname;
  navigationState.search = search;
  try {
    return renderWith(client, createElement(FrameNavigation, { navigation: buildNavigation(subject), offersSections: false }));
  } finally {
    navigationState.pathname = '/dashboard';
    navigationState.search = '';
  }
}

/**
 * The link to `address`, with or without the `?project=` the frame carries onto it (`R-150c`), whatever the project is
 * spelled as. A missing link is an error, not an empty answer: «no badge» must never pass because the link was not found.
 */
const linkTo = (markup: string, address: string) => {
  const link = linksIn(markup).find((found) => found.href === address || found.href.startsWith(`${address}?project=`));
  if (link === undefined) throw new Error(`no link to ${address} in the markup`);
  return link;
};

const kbPills = (markup: string, which: 'row' | 'rail' | 'stacked' = 'row'): string[] =>
  pillsIn(linkTo(state(markup, which), KNOWLEDGE_BASE).inside);

describe('«База знаний» counts the decisions on findings of the project the address names, as the screen behind it opens on', () => {
  it('says what it counts: the project\'s decisions when a project is chosen, the installation\'s otherwise', () => {
    const all = menuBadgesOf({ knowledgeBaseTotal: 12 })[KNOWLEDGE_BASE]?.[0];
    expect(all?.label).toBe(`${KNOWLEDGE_BASE_BADGE_LABEL}: 12`);
    expect(all?.label).toBe('Решений по замечаниям в базе знаний: 12');
    const scoped = menuBadgesOf({ knowledgeBaseTotal: 12, knowledgeBaseOfProject: true })[KNOWLEDGE_BASE]?.[0];
    expect(scoped?.label).toBe(`${KNOWLEDGE_BASE_PROJECT_BADGE_LABEL}: 12`);
    expect(scoped?.label).toBe('Решений по замечаниям в базе знаний выбранного проекта: 12');
    expect(scoped?.count).toBe(12);
    expect(menuBadgesOf({ knowledgeBaseTotal: 0, knowledgeBaseOfProject: true })).toEqual({});
  });

  it('reads the project\'s own total on an optional screen with ?project=, in the bar, the rail and the stacked menu', () => {
    const client = seeded();
    client.setQueryData(PROJECT_KB_KEY, knowledgePage(12));
    const markup = frameAt(client, ADMIN_ONLY, '/dashboard', `project=${PROJECT}`);
    for (const which of ['row', 'rail', 'stacked'] as const) expect(kbPills(markup, which), which).toEqual(['count:12']);
    expect(state(markup, 'row')).toContain('Решений по замечаниям в базе знаний выбранного проекта: 12');
    // The installation's 140 is not shown beside a project.
    expect(markup).not.toContain('99+');
  });

  it('reads the project of the path on a required screen, where the link to the base carries it', () => {
    const client = seeded();
    client.setQueryData(PROJECT_KB_KEY, knowledgePage(7));
    const markup = frameAt(client, EXPERT, `/projects/${PROJECT}`);
    expect(kbPills(markup)).toEqual(['count:7']);
    expect(linkAt(state(markup, 'row'), `${KNOWLEDGE_BASE}?project=${PROJECT}`)).toBeDefined();
  });

  it('reads the installation\'s total with no project in the address, on a global screen too, and keeps the old key', () => {
    const client = seeded();
    client.setQueryData(PROJECT_KB_KEY, knowledgePage(12));
    expect(kbPills(frameAt(client, ADMIN_ONLY, '/dashboard'))).toEqual(['count:99+']);
    expect(state(frameAt(client, ADMIN_ONLY, '/dashboard'), 'row')).toContain('Решений по замечаниям в базе знаний: 140');
    // A global screen ignores ?project= for its own data, and the base is not the global screen's: it follows the address.
    expect(kbPills(frameAt(client, ADMIN_ONLY, '/queue', `project=${PROJECT}`))).toEqual(['count:12']);
    const bare = newClient();
    frameAt(bare, ADMIN_ONLY, '/dashboard');
    expect(bare.getQueryCache().find({ queryKey: [...KB_KEY] })).toBeDefined();
  });

  it('never shows another project\'s total while this project\'s is loading: no figure, not the old one', () => {
    const client = seeded();
    client.setQueryData(PROJECT_KB_KEY, knowledgePage(12));
    expect(kbPills(frameAt(client, ADMIN_ONLY, '/dashboard', `project=${OTHER_PROJECT}`))).toEqual([]);
    // And it asked under the other project's key, once, enabled: the project is in the key.
    const filed = client.getQueryCache().find({ queryKey: [...OTHER_KB_KEY] });
    expect(filed).toBeDefined();
    expect((filed?.options as { enabled?: unknown }).enabled).not.toBe(false);
  });

  it('draws nothing when the project\'s read failed, and leaves the other counters', () => {
    const client = seeded();
    client.setQueryData(PROJECT_KB_KEY, knowledgePage(12));
    client.getQueryCache().find({ queryKey: [...PROJECT_KB_KEY] })?.setState({ status: 'error', error: new Error('нет связи'), errorUpdatedAt: Date.now() + 1, fetchStatus: 'idle' });
    const markup = frameAt(client, ADMIN_ONLY, '/dashboard', `project=${PROJECT}`);
    expect(kbPills(markup)).toEqual([]);
    expect(pillsIn(linkTo(state(markup, 'row'), REGISTRATIONS).inside)).toEqual(['count:5']);
  });

  it('is not asked about a project the address spells as no uid, and draws no figure for it', () => {
    const client = seeded();
    const markup = frameAt(client, ADMIN_ONLY, '/dashboard', 'project=не-проект');
    expect(kbPills(markup)).toEqual([]);
    const probe = client.getQueryCache().find({ queryKey: [...KB_KEY] });
    expect((probe?.options as { enabled?: unknown }).enabled).toBe(false);
  });

  it('does not ask for it at all for a session whose menu has no such item', () => {
    const client = newClient();
    const markup = frameAt(client, NO_ROLES, '/dashboard', `project=${PROJECT}`);
    expect(markup).not.toContain('data-menu-badge');
    expect(client.getQueryCache().getAll()).toHaveLength(0);
  });
});
