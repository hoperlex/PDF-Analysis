/**
 * `UIP-DEBT-02` (owner rule of 2026-11-09: what is unavailable is hidden): «Назад» and «Далее» under the queue.
 *
 * A queue that fits one page drew both, inactive. With no page before and none after there is nothing to turn, so the row is not drawn;
 * with one side open the other button stays, inactive, as it was. Held on the widget (both sides are its props, so every case can be
 * seeded) and on the page, where the cursor of the next page comes from the server's answer; each case that holds the row away is
 * paired with one that shows it can be drawn.
 */

import { createElement } from 'react';
import type { ComponentType } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

vi.mock('next/navigation', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  usePathname: () => '/queue',
  useSearchParams: () => new URLSearchParams(''),
}));

import type { ExecutionQueueItem } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { ExecutionQueue } from '@/widgets/execution-queue';
import { QueuePage } from '@/_pages/queue';
import type { QueuePageProps } from '@/_pages/queue';

import { newClient, renderScreen } from '../screens/harness';
import { QUEUE_WORK } from './queue-work';

const job = (suffix: string, state: ExecutionQueueItem['state']): ExecutionQueueItem => ({
  job_id: `job_01J9ZQ8K7NHVXW3T2R5M6P4Q8${suffix}`, run_id: `run_01J9ZQ8K7NHVXW3T2R5M6P4Q8${suffix}`, state, priority: 0,
  created_at: '2026-10-09T10:00:00Z', available_at: '2026-10-09T10:00:00Z', ...QUEUE_WORK,
});
const noop = () => undefined;

const NAV = /<nav[^>]*aria-label="Страницы очереди"/;
const BACK = /<button[^>]*disabled=""[^>]*>Назад<\/button>/;
const FORWARD = /<button[^>]*disabled=""[^>]*>Далее<\/button>/;

describe('the pages of the queue, drawn by the widget', () => {
  const widget = (onPrevious: (() => void) | null, onNext: (() => void) | null) => renderToStaticMarkup(createElement(ExecutionQueue, {
    items: [job('A', 'queued')], roles: ['expert'], asOf: Date.parse('2026-10-09T10:05:00Z'), busy: false,
    workerOf: () => ({ kind: 'pending' as const }), onCancel: noop, onReaudit: noop, onPriority: noop, onNext, onPrevious,
  }));

  it('draws no row where there is no page before and none after', () => {
    const markup = widget(null, null);
    expect(markup).not.toMatch(NAV);
    expect(markup).not.toContain('>Назад<');
    expect(markup).not.toContain('>Далее<');
    // The rows are still there: the row of pages was the only thing left out.
    expect(markup).toContain('data-queue-row="queued"');
  });

  it('draws both buttons when there is a page after, the one before inactive', () => {
    const markup = widget(null, noop);
    expect(markup).toMatch(NAV);
    expect(markup).toMatch(BACK);
    expect(markup).not.toMatch(FORWARD);
    expect(markup).toContain('>Далее<');
  });

  it('draws both buttons when there is a page before, the one after inactive', () => {
    const markup = widget(noop, null);
    expect(markup).toMatch(NAV);
    expect(markup).toMatch(FORWARD);
    expect(markup).not.toMatch(BACK);
    expect(markup).toContain('>Назад<');
  });

  it('draws both, active, in the middle of the queue', () => {
    const markup = widget(noop, noop);
    expect(markup).toMatch(NAV);
    expect(markup).not.toMatch(BACK);
    expect(markup).not.toMatch(FORWARD);
  });
});

describe('the pages of the queue, drawn by the page', () => {
  const FINISHED = [job('C', 'succeeded'), job('D', 'failed')];

  function render(items: readonly ExecutionQueueItem[], nextCursor: string | null, props: QueuePageProps = {}): string {
    const client = newClient();
    client.setQueryData(queryKeys.execution.queue(), { items, page: { next_cursor: nextCursor }, paused: false });
    client.setQueryData(queryKeys.account.me(), { roles: ['expert'] });
    return renderScreen(client, createElement(QueuePage as ComponentType<QueuePageProps>, props));
  }

  it('draws no pages for a queue that fits one page', () => {
    const markup = render([job('A', 'queued'), job('B', 'running')], null);
    expect(markup).toContain('data-queue-row="queued"');
    expect(markup).not.toMatch(NAV);
    expect(markup).not.toContain('>Назад<');
    expect(markup).not.toContain('>Далее<');
  });

  it('draws them, the way back inactive, when the server names a next page', () => {
    const markup = render([job('A', 'queued'), job('B', 'running')], 'c2');
    expect(markup).toMatch(NAV);
    expect(markup).toMatch(BACK);
    expect(markup).not.toMatch(FORWARD);
  });

  it('draws none under «Завершённые задачи скрыты» when there is no other page to go to', () => {
    const markup = render(FINISHED, null, { initiallyHidden: true });
    expect(markup).toContain('data-queue-all-hidden');
    expect(markup).toContain('Завершённые задачи скрыты');
    expect(markup).not.toContain('>Назад<');
    expect(markup).not.toContain('>Далее<');
  });

  it('keeps the way to the other pages under «Завершённые задачи скрыты» when there is one', () => {
    const markup = render(FINISHED, 'c2', { initiallyHidden: true });
    expect(markup).toContain('data-queue-all-hidden');
    expect(markup).toMatch(BACK);
    expect(markup).toMatch(/<button[^>]*>Далее<\/button>/);
    expect(markup).not.toMatch(FORWARD);
  });
});
