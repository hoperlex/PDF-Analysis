/**
 * `UIP-S15-04` — the tab «Обзор» of «Диспетчер»: the strip of five numbers and the servers in a short form. The numbers are a pure
 * function of plain values (`overviewFigures`); the queue's three come from the queue's own overview, summed by the widget, and
 * «Ошибки» is `live_failure_count`, the number on the red badge of the menu's «Очередь». Every rule has a case that fails when it
 * is broken: a number read from the wrong field, a dash that becomes a zero, a block the stand has no data for that is drawn.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ExecutionQueueStateCount, Role } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { routes } from '@/shared/lib';
import { OVERVIEW_LABELS, OVERVIEW_QUEUE_NOT_READ, UNKNOWN_FIGURE, executorHostsKey, overviewFigures } from '@/entities/executor-host';
import { ExecutorHostsOverview, HostCompact, HostsOverviewView } from '@/widgets/executor-hosts';
import { menuBadgesOf } from '@/_app/menu-badges';

import { newClient, renderScreen } from '../screens/harness';
import {
  HOST_LIST, QUEUE_OVERVIEW, SERVER_BUSY, SERVER_ONLINE, SERVER_OFFLINE, queuePage, seedHosts, seedQueue,
} from './hosts-fixtures';

const noop = (): void => undefined;
const NOW = Date.parse('2026-11-09T11:06:00Z');

function view(queue: { overview: readonly ExecutionQueueStateCount[] | undefined; liveFailures: number | undefined } | null, list = HOST_LIST): string {
  return renderScreen(newClient(), createElement(HostsOverviewView, { list, queue, asOf: NOW, onShowServers: noop }));
}

const figure = (markup: string, key: string): string => {
  const at = markup.indexOf(`data-overview-figure="${key}"`);
  expect(at, key).toBeGreaterThan(-1);
  return markup.slice(markup.lastIndexOf('<li', at), markup.indexOf('</li>', at)).replace(/<[^>]+>/g, '').trim();
};

describe('the five numbers', () => {
  const input = { online: 2, total: 3, slotsFree: 3, slotsTotal: 7, running: 3, queued: 4, failures: 2 };

  it('are «На связи N из M», «Выполняется», «В очереди», «Ошибки» and «Свободно мест N из M», in that order', () => {
    const figures = overviewFigures(input);
    expect(figures.map((item) => [item.label, item.value])).toEqual([
      ['На связи', '2 из 3'], ['Выполняется', '3'], ['В очереди', '4'], ['Ошибки', '2'], ['Свободно мест', '3 из 7'],
    ]);
    expect(figures.map((item) => item.label)).toEqual(Object.values(OVERVIEW_LABELS));
  });

  it('keep the two numbers of the servers and say a dash, never a zero, for the three of a queue that is not read', () => {
    const figures = overviewFigures({ ...input, running: null, queued: null, failures: null });
    expect(figures.map((item) => item.value)).toEqual(['2 из 3', UNKNOWN_FIGURE, UNKNOWN_FIGURE, UNKNOWN_FIGURE, '3 из 7']);
    expect(UNKNOWN_FIGURE).toBe('—');
    // A real zero is a zero.
    expect(overviewFigures({ ...input, running: 0, queued: 0, failures: 0 }).map((item) => item.value).slice(1, 4)).toEqual(['0', '0', '0']);
  });

  it('warn on «Ошибки» only when there is an error', () => {
    expect(overviewFigures(input).filter((item) => item.warning).map((item) => item.key)).toEqual(['errors']);
    expect(overviewFigures({ ...input, failures: 0 }).some((item) => item.warning)).toBe(false);
    expect(overviewFigures({ ...input, failures: null }).some((item) => item.warning)).toBe(false);
  });
});

describe('the strip of a read list and a read queue', () => {
  const queue = { overview: QUEUE_OVERVIEW, liveFailures: 2 };

  it('reads «Выполняется» as running and leased, «В очереди» as queued and waiting to retry, and the servers from the list', () => {
    const markup = view(queue);
    expect(figure(markup, 'online')).toBe('На связи 3 из 4');
    expect(figure(markup, 'running')).toBe('Выполняется 3');
    expect(figure(markup, 'queued')).toBe('В очереди 4');
    expect(figure(markup, 'slots')).toBe('Свободно мест 3 из 7');
  });

  it('can fail: «Ошибки» is the live failures, not the failed and the stopped jobs counted from the overview', () => {
    // The overview holds two failed and one stopped (3); the server says two nothing has answered.
    expect(figure(view(queue), 'errors')).toBe('Ошибки 2');
    expect(figure(view({ overview: QUEUE_OVERVIEW, liveFailures: 0 }), 'errors')).toBe('Ошибки 0');
  });

  it('shows the same number as the red badge of the menu\'s «Очередь», and the open jobs of its count badge', () => {
    const badges = menuBadgesOf({ queueOverview: QUEUE_OVERVIEW, queueLiveFailures: 2 })[routes.queue()] ?? [];
    expect(badges.find((badge) => badge.tone === 'alert')?.count).toBe(2);
    expect(badges.find((badge) => badge.tone === 'count')?.count).toBe(3 + 4);
    expect(figure(view(queue), 'errors')).toContain(String(badges.find((badge) => badge.tone === 'alert')?.count));
  });

  it('says a dash for the three numbers of the queue when it is not read, says why, and keeps the numbers of the servers', () => {
    const markup = view(null);
    for (const key of ['running', 'queued', 'errors']) expect(figure(markup, key), key).toContain('—');
    expect(figure(markup, 'online')).toBe('На связи 3 из 4');
    expect(figure(markup, 'slots')).toBe('Свободно мест 3 из 7');
    expect(markup).toContain('data-overview-queue-failure');
    expect(markup).toContain(OVERVIEW_QUEUE_NOT_READ);
    expect(view(queue)).not.toContain('data-overview-queue-failure');
  });

  it('says a dash while the queue is on its way, without calling it a failure', () => {
    const markup = view({ overview: undefined, liveFailures: undefined });
    for (const key of ['running', 'queued', 'errors']) expect(figure(markup, key), key).toContain('—');
    expect(markup).not.toContain('data-overview-queue-failure');
  });

  it('leads to «Серверы» by «Все серверы →»', () => {
    const markup = view(queue);
    expect(markup).toContain('data-overview-all-servers');
    expect(markup).toContain('Все серверы →');
  });

  it('draws no block the stand has no data for: no next task, no projects to check, no attention, no done today', () => {
    const markup = view(queue);
    for (const absent of ['Следующая задача', 'Проекты для проверки', 'Требует внимания', 'Завершено сегодня', 'Рекомендация', 'Scheduler', 'WS', 'Реальные данные']) {
      expect(markup, absent).not.toContain(absent);
    }
    expect(markup).not.toMatch(/CPU|RAM|GPU|VRAM|лимит|остаток|телеметри/i);
  });

  it('says there are no servers and still leads to «Серверы»', () => {
    const markup = view(queue, { items: [], online: 0, slots_free: 0, slots_total: 0, total: 0 });
    expect(markup).toContain('Серверов пока нет.');
    expect(markup).not.toContain('data-overview-hosts');
    expect(markup).toContain('data-overview-all-servers');
  });
});

describe('a server in its short form', () => {
  const card = (host = SERVER_ONLINE): string => renderScreen(newClient(), createElement(HostCompact, { host, asOf: NOW }));

  it('says the state, the load and what it does now, and no model and no control', () => {
    const markup = card();
    expect(markup).toContain('data-host-compact');
    expect(markup).toContain('основной');
    expect(markup).toContain('>на связи<');
    expect(markup).toContain('data-host-load="2/3"');
    expect(markup).toContain('Сейчас:');
    expect(markup).toContain('Анализ блоков · 21 мин');
    expect(markup).not.toContain('data-host-model');
    expect(markup).not.toContain('<button');
    expect(markup).not.toContain('role="switch"');
    expect(markup).not.toContain('Использовать');
  });

  it('is grey with its own sentence for a server with no contact, and draws nothing under «Сейчас» for a free one', () => {
    const grey = card(SERVER_OFFLINE);
    expect(grey).toContain('data-host-tone="offline"');
    expect(grey).toContain('data-host-no-contact');
    expect(grey).not.toContain('data-host-load');
    expect(card(SERVER_BUSY)).not.toContain('data-host-now');
  });

  it('draws the cards of the list under the strip, one for each server', () => {
    const markup = view({ overview: QUEUE_OVERVIEW, liveFailures: 2 });
    expect(markup.match(/data-host-compact=/g)).toHaveLength(4);
  });
});

describe('the tab as a role meets it', () => {
  const tab = (roles: Role[], seed = true): string => {
    const client = newClient();
    if (seed) {
      seedHosts(client);
      seedQueue(client, queuePage([]));
    }
    return renderScreen(client, createElement(ExecutorHostsOverview, { roles, onShowServers: noop }));
  };

  it('draws the strip and the cards to an expert and to an administrator', () => {
    for (const roles of [['expert'], ['admin']] as Role[][]) {
      const markup = tab(roles);
      expect(markup, roles.join()).toContain('data-hosts-overview');
      expect(figure(markup, 'running')).toBe('Выполняется 3');
      expect(markup.match(/data-host-compact=/g)).toHaveLength(4);
    }
  });

  it('draws a viewer nothing but the refusal, even from a cache that holds the data', () => {
    for (const roles of [['viewer'], []] as Role[][]) {
      const markup = tab(roles);
      expect(markup).not.toContain('data-overview-figure');
      expect(markup).not.toContain('data-host-compact');
      expect(markup).toContain('Обзор недоступен');
    }
  });

  it('builds the read of the servers and of the queue for the roles that may, and builds none for a viewer', () => {
    // A render builds the queries it would read, whether or not the cache holds an answer: the keys it names are what it asks for.
    const asked = (roles: Role[]): string[] => {
      const client = newClient();
      renderScreen(client, createElement(ExecutorHostsOverview, { roles, onShowServers: noop }));
      return client.getQueryCache().getAll().map((query) => JSON.stringify(query.queryKey));
    };
    const hosts = JSON.stringify(executorHostsKey());
    const queue = JSON.stringify(queryKeys.execution.queue());
    for (const roles of [['expert'], ['admin']] as Role[][]) expect(asked(roles), roles.join()).toEqual([hosts, queue]);
    for (const roles of [['viewer'], []] as Role[][]) expect(asked(roles), roles.join()).toEqual([]);
  });
});
