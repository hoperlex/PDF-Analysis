/**
 * `UI-PARITY-QUEUE-A` (contract 1.18.0): a queue row says what the job executes, when it started and ended and why it
 * failed; the list is narrowed by a state; the cache key and the request carry the filter.
 */

import { QueryClient } from '@tanstack/react-query';
import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { ExecutionQueueItem } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import {
  QUEUE_STATE_OPTIONS, jobStateLabel, queueItemError, queueQueryOptions,
} from '@/entities/execution';
import { terminalReasonNote } from '@/entities/audit-run';
import { ExecutionQueue } from '@/widgets/execution-queue';
import { QueuePage } from '@/_pages/queue/ui/queue-page';

import { newClient, renderScreen } from '../screens/harness';
import { QUEUE_WORK } from './queue-work';

const RUN_ID = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const JOB_ID = 'job_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const CREATED = '2026-10-09T10:00:00Z';
const STARTED = '2026-10-09T10:01:00Z';
const FINISHED = '2026-10-09T10:09:30Z';
const noop = () => {};

const item = (overrides: Partial<ExecutionQueueItem> = {}): ExecutionQueueItem => ({
  job_id: JOB_ID, run_id: RUN_ID, state: 'queued', priority: 0, created_at: CREATED, available_at: CREATED,
  ...QUEUE_WORK, ...overrides,
});

function rows(items: readonly ExecutionQueueItem[], filtered = false): string {
  return renderToStaticMarkup(createElement(ExecutionQueue, {
    items, roles: [], asOf: Date.parse('2026-10-09T10:05:00Z'), busy: false, filtered,
    workerOf: () => ({ kind: 'pending' as const }), onCancel: noop, onReaudit: noop, onPriority: noop,
    onNext: null, onPrevious: null,
  }));
}

describe('the row names the work', () => {
  it('prints «Проект · Документ · Версия» as links to the project, the document and the version', () => {
    const markup = rows([item()]);
    expect(markup).toContain('data-queue-work');
    expect(markup).toContain(`href="/projects/${QUEUE_WORK.project_uid}"`);
    expect(markup).toContain(`href="/projects/${QUEUE_WORK.project_uid}/documents/${QUEUE_WORK.document_uid}"`);
    expect(markup).toContain(`href="/projects/${QUEUE_WORK.project_uid}/versions/${QUEUE_WORK.version_uid}"`);
    expect(markup).toContain('Школа № 7');
    expect(markup).toContain('АР, лист 3');
    expect(markup).toContain('>Версия 2<');
    expect(markup.indexOf('Школа № 7')).toBeLessThan(markup.indexOf('АР, лист 3'));
    expect(markup.indexOf('АР, лист 3')).toBeLessThan(markup.indexOf('>Версия 2<'));
  });

  it('links the run page beside the journal link it had', () => {
    const markup = rows([item()]);
    expect(markup).toContain(`href="/projects/${QUEUE_WORK.project_uid}/runs/${RUN_ID}"`);
    expect(markup).toContain('Открыть прогон');
    expect(markup).toContain(`href="/logs?run_id=${RUN_ID}"`);
  });
});

describe('the row says when the job started and ended', () => {
  it('prints no times for a job that has neither started nor finished', () => {
    const markup = rows([item()]);
    expect(markup).not.toContain('data-queue-timing');
    expect(markup).not.toContain('data-queue-started=');
  });

  it('prints the original\'s «начало → конец · длительность» line, with the exact instants in the tooltips', () => {
    const markup = rows([item({ state: 'failed', started_at: STARTED, finished_at: FINISHED })]);
    expect(markup).toContain('data-queue-timing="8 мин 30 с"');
    expect(markup).toContain(`<time dateTime="${STARTED}" title="Начат: ${formatInstant(STARTED)}" data-queue-started="true">09.10 10:01</time>`);
    expect(markup).toContain(`<time dateTime="${FINISHED}" title="Завершён: ${formatInstant(FINISHED)}" data-queue-finished="true">10:09</time>`);
    expect(markup).toContain(' UTC');
  });

  it('measures a running job to the last read and leaves its end open', () => {
    const markup = rows([item({ state: 'running', started_at: STARTED })]);
    expect(markup).toContain('data-queue-timing="4 мин"');
    expect(markup).toContain('data-queue-finished="">…</span>');
  });
});

describe('the row says why the job failed', () => {
  it('prints the sentence the run screen gives the run\'s reason, with the code beside it', () => {
    const markup = rows([item({ state: 'failed', error_code: 'analysis_failed' })]);
    const note = terminalReasonNote('analysis_failed');
    expect(note.kind).toBe('described');
    expect(markup).toContain('data-queue-error="analysis_failed"');
    expect(markup).toContain('<code>analysis_failed</code>');
    expect(markup).toContain(note.sentence.replace(/&/g, '&amp;'));
  });

  it('prints only the code for a code this client has no sentence for', () => {
    const unknown = 'a_code_from_a_newer_contract' as NonNullable<ExecutionQueueItem['error_code']>;
    expect(queueItemError({ error_code: unknown })).toEqual({ code: 'a_code_from_a_newer_contract', sentence: null });
    const markup = rows([item({ state: 'failed', error_code: unknown })]);
    expect(markup).toContain('<code>a_code_from_a_newer_contract</code>');
    expect(markup).not.toContain('У этого экрана нет описания');
  });

  it('prints nothing about an error for a job that has none', () => {
    expect(queueItemError({})).toBeNull();
    expect(rows([item({ state: 'succeeded', started_at: STARTED, finished_at: FINISHED })])).not.toContain('data-queue-error');
  });

  it('prints an interrupted reason verbatim', () => {
    const markup = rows([item({ state: 'failed', interrupted_reason: 'executor_process_ended_before_terminal' })]);
    expect(markup).toContain('data-queue-interrupted="executor_process_ended_before_terminal"');
    expect(markup).toContain('<code>executor_process_ended_before_terminal</code>');
  });
});

describe('the state filter', () => {
  it('offers every state once, labelled as the row labels it, plus «Все состояния»', () => {
    const client = newClient();
    client.setQueryData(queryKeys.execution.queue(), { items: [item()], page: { next_cursor: null }, paused: false });
    const markup = renderScreen(client, createElement(QueuePage));
    expect(markup).toContain('<select');
    expect(markup).toContain('data-queue-state-filter');
    expect(markup).toContain('<option value="" selected="">Все состояния</option>');
    expect(QUEUE_STATE_OPTIONS.map((option) => option.value)).toHaveLength(8);
    for (const option of QUEUE_STATE_OPTIONS) {
      expect(option.label).toBe(jobStateLabel(option.value));
      expect(markup).toContain(`<option value="${option.value}">${option.label}</option>`);
    }
  });

  it('says that no job matches, not that the queue is empty, when a state is chosen', () => {
    expect(rows([], true)).toContain('Задач в этом состоянии нет');
    expect(rows([], false)).toContain('Очередь пуста');
    expect(rows([], true)).not.toContain('Очередь пуста');
  });
});

describe('the cache key and the request carry the filter', () => {
  it('keys a page by its state and its period, so two filters never share a cached page', () => {
    const none = JSON.stringify(queueQueryOptions().queryKey);
    const failed = JSON.stringify(queueQueryOptions(undefined, { state: 'failed' }).queryKey);
    const running = JSON.stringify(queueQueryOptions(undefined, { state: 'running' }).queryKey);
    const period = JSON.stringify(queueQueryOptions(undefined, { createdFrom: '2026-10-01T00:00:00Z' }).queryKey);
    expect(new Set([none, failed, running, period]).size).toBe(4);
    expect(queueQueryOptions('c1', { state: 'failed' }).queryKey)
      .not.toEqual(queueQueryOptions('c2', { state: 'failed' }).queryKey);
  });

  it('keys an unfiltered page exactly as the queue was keyed before the filters existed', () => {
    const client = new QueryClient();
    client.setQueryData(queryKeys.execution.queue(), 'seeded');
    expect(client.getQueryData(queueQueryOptions().queryKey)).toBe('seeded');
    expect(client.getQueryData(queueQueryOptions(undefined, {}).queryKey)).toBe('seeded');
    client.setQueryData(queryKeys.execution.queue('c9'), 'paged');
    expect(client.getQueryData(queueQueryOptions('c9').queryKey)).toBe('paged');
  });

  it('keeps the refresh policy it had', () => {
    const options = queueQueryOptions(undefined, { state: 'failed' });
    expect(options.staleTime).toBe(0);
    expect(options.refetchOnWindowFocus).toBe('always');
    expect(options.refetchIntervalInBackground).toBe(false);
  });

  describe('on the wire', () => {
    beforeEach(() => { vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', '/bff/v1'); });
    afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); });

    async function requested(options: ReturnType<typeof queueQueryOptions>): Promise<URL> {
      let seen = '';
      vi.stubGlobal('fetch', async (input: string) => {
        seen = input;
        return new Response(JSON.stringify({ items: [], page: { next_cursor: null }, paused: false }), {
          status: 200, headers: { 'Content-Type': 'application/json' },
        });
      });
      await options.queryFn();
      return new URL(seen, 'http://web.test');
    }

    it('sends the state and the period as the contract names them, and nothing for an unset filter', async () => {
      const filtered = await requested(queueQueryOptions('cur', {
        state: 'dead_letter', createdFrom: '2026-10-01T00:00:00Z', createdTo: '2026-11-01T00:00:00Z',
      }));
      expect(filtered.pathname).toBe('/bff/v1/execution/queue');
      expect(filtered.searchParams.get('state')).toBe('dead_letter');
      expect(filtered.searchParams.get('created_from')).toBe('2026-10-01T00:00:00Z');
      expect(filtered.searchParams.get('created_to')).toBe('2026-11-01T00:00:00Z');
      expect(filtered.searchParams.get('cursor')).toBe('cur');
      const plain = await requested(queueQueryOptions());
      for (const name of ['state', 'created_from', 'created_to', 'cursor']) {
        expect(plain.searchParams.has(name), name).toBe(false);
      }
    });
  });
});
