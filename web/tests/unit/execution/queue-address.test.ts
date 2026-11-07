/**
 * «Очередь» keeps its filter in the address (`?state=&period=`), second UX pass of 2026-11-07.
 *
 * Held here, each with a case that shows it can fail:
 *
 *   - the address is read and written as a pure pair, with the closed sets enforced: a state the contract does not have and a period
 *     the screen does not offer are dropped, never echoed, and «Все состояния» / «За всё время» are the absent parameter;
 *   - a parameter that is not this screen's is carried through a write untouched;
 *   - the page, given the address the route read on the server, makes its FIRST read already filtered: the cache holds the
 *     filtered queue entry and not the unfiltered one, so no unfiltered request precedes it;
 *   - the link «Обзор» of «Исполнители» makes (`queueStateHref`) is read back by this screen as the state it names: the widget and the
 *     page cannot import each other, so this is the place their two spellings of `state` are held to agree.
 */

import { createElement } from 'react';
import type { ComponentType } from 'react';
import { describe, expect, it } from 'vitest';

import { queryKeys } from '@/shared/api';
import { QUEUE_STATE_OPTIONS } from '@/entities/execution';
import {
  EMPTY_QUEUE_ADDRESS, QUEUE_PERIOD_PARAM, QUEUE_STATE_PARAM, QueuePage, isQueueState, readQueueAddress, writeQueueAddress,
} from '@/_pages/queue';
import type { QueuePageProps } from '@/_pages/queue';
import { queueStateHref } from '@/widgets/worker-list';

import { newClient, renderScreen } from '../screens/harness';

const read = (query: string) => readQueueAddress(new URLSearchParams(query));

describe('the queue address, read', () => {
  it('names the state and the period, and an empty address narrows nothing', () => {
    expect(read('state=failed&period=week')).toEqual({ state: 'failed', period: 'week' });
    expect(read('')).toEqual(EMPTY_QUEUE_ADDRESS);
    expect(read('state=&period=')).toEqual(EMPTY_QUEUE_ADDRESS);
  });

  it('accepts exactly the contract’s states and the screen’s periods', () => {
    for (const option of QUEUE_STATE_OPTIONS) expect(read(`state=${option.value}`).state).toBe(option.value);
    for (const period of ['today', 'week', 'month', 'all'] as const) expect(read(`period=${period}`).period).toBe(period);
  });

  it('drops a value outside the closed sets instead of echoing it', () => {
    expect(read('state=exploded&period=forever')).toEqual(EMPTY_QUEUE_ADDRESS);
    expect(read('state=FAILED').state).toBe('');
    expect(read('state=failed%20').state).toBe('');
    expect(isQueueState('failed')).toBe(true);
    expect(isQueueState('exploded')).toBe(false);
    expect(isQueueState(undefined)).toBe(false);
  });
});

describe('the queue address, written', () => {
  it('writes the state and the period, and the absent parameter is «все»', () => {
    expect(writeQueueAddress(new URLSearchParams(''), { state: 'failed', period: 'month' }).toString()).toBe('state=failed&period=month');
    expect(writeQueueAddress(new URLSearchParams('state=failed&period=month'), EMPTY_QUEUE_ADDRESS).toString()).toBe('');
    expect(writeQueueAddress(new URLSearchParams('state=failed'), { state: '', period: 'today' }).toString()).toBe('period=today');
  });

  it('carries a parameter of another screen through', () => {
    const written = writeQueueAddress(new URLSearchParams('project=prj_X&state=queued'), { state: 'failed', period: 'all' });
    expect(written.get('project')).toBe('prj_X');
    expect(written.get(QUEUE_STATE_PARAM)).toBe('failed');
    expect(written.has(QUEUE_PERIOD_PARAM)).toBe(false);
  });

  it('round-trips every state', () => {
    for (const option of QUEUE_STATE_OPTIONS) {
      const written = writeQueueAddress(new URLSearchParams(''), { state: option.value, period: 'week' });
      expect(readQueueAddress(written)).toEqual({ state: option.value, period: 'week' });
    }
  });
});

describe('the page opened on an address', () => {
  const EMPTY_PAGE = { items: [], page: { next_cursor: null }, paused: false };

  it('reads the filtered queue first, and never the unfiltered one', () => {
    const client = newClient();
    client.setQueryData(queryKeys.execution.queue(undefined, { state: 'failed' }), EMPTY_PAGE);
    const markup = renderScreen(client, createElement(QueuePage as ComponentType<QueuePageProps>, { initialAddress: { state: 'failed', period: 'all' } }));
    const keys = client.getQueryCache().getAll().map((query) => JSON.stringify(query.queryKey));
    expect(keys).toContain(JSON.stringify(queryKeys.execution.queue(undefined, { state: 'failed' })));
    expect(keys).not.toContain(JSON.stringify(queryKeys.execution.queue(undefined, {})));
    // The list says it is narrowed and the select shows the state.
    expect(markup).toMatch(/<option value="failed" selected="">/);
    expect(markup).not.toMatch(/<option value="" selected="">/);
  });

  it('can fail: with no address the unfiltered queue is the one read and «Все состояния» is chosen', () => {
    const client = newClient();
    client.setQueryData(queryKeys.execution.queue(undefined, {}), EMPTY_PAGE);
    const markup = renderScreen(client, createElement(QueuePage));
    const keys = client.getQueryCache().getAll().map((query) => JSON.stringify(query.queryKey));
    expect(keys).toContain(JSON.stringify(queryKeys.execution.queue(undefined, {})));
    expect(keys.filter((key) => key.includes('failed'))).toEqual([]);
    expect(markup).toMatch(/<option value="" selected="">/);
  });

  it('shows the period chosen by the address', () => {
    const client = newClient();
    const markup = renderScreen(client, createElement(QueuePage as ComponentType<QueuePageProps>, { initialAddress: { state: '', period: 'week' } }));
    expect(markup).toMatch(/<option value="week" selected="">/);
  });
});

describe('the links «Обзор» of «Исполнители» makes into the queue', () => {
  it('open the queue on the state they name', () => {
    for (const state of ['failed', 'dead_letter'] as const) {
      const href = queueStateHref(state);
      expect(href.startsWith('/queue?')).toBe(true);
      expect(readQueueAddress(new URL(href, 'http://web.test').searchParams)).toEqual({ state, period: 'all' });
    }
  });
});
