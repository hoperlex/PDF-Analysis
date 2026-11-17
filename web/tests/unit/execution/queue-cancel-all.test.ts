/**
 * `UIP-S13-04`: «Отменить очередь (N)».
 *
 * Held here, each with a case that shows it can fail:
 *
 *   - the button is drawn for a number the server said, and only to the roles that may cancel a run;
 *   - the jobs it cancels are the ones a cancel can reach, every page of them, each run once;
 *   - one command for each run, each under a key of its own, one after another; a run sent again goes under the key it had;
 *   - the result is the honest sum «Отменено N из M», every run that is not cancelled with its reason, and nothing is rolled back;
 *   - no sentence of the sweep holds a run's number.
 */

import { createElement } from 'react';
import type { ComponentType } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { ExecutionQueueItem, ExecutionQueuePage, ExecutionQueueStateCount } from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import { QueuePage } from '@/_pages/queue';
import type { QueuePageProps } from '@/_pages/queue';
import {
  cancelRefusal, cancelSummary, cancellableCount, cancellableJobs, readActiveJobs, sweepCancel, workName,
} from '@/_pages/queue/model/cancel-queue';
import type { CancelOutcome } from '@/_pages/queue/model/cancel-queue';
import { CancelQueuePanel } from '@/_pages/queue/ui/cancel-queue';
import type { CancelQueue } from '@/_pages/queue/ui/use-cancel-queue';
import { executionFailure } from '@/entities/execution';

import { newClient, renderScreen } from '../screens/harness';
import { QUEUE_WORK } from './queue-work';

const job = (suffix: string, state: ExecutionQueueItem['state'] = 'queued', over: Partial<ExecutionQueueItem> = {}): ExecutionQueueItem => ({
  job_id: `job_01J9ZQ8K7NHVXW3T2R5M6P4Q8${suffix}`, run_id: `run_01J9ZQ8K7NHVXW3T2R5M6P4Q8${suffix}`, state, priority: 0,
  created_at: '2026-10-09T10:00:00Z', available_at: '2026-10-09T10:00:00Z', ...QUEUE_WORK, document_name: `Документ ${suffix}`, ...over,
});

const envelope = (code: 'permission_denied' | 'state_transition_not_allowed' | 'conflict' | 'dependency_unavailable') => ({
  contract_version: '1.59.0', error_code: code, message: 'Безопасный отказ.', correlation_id: 'cid-cancel-all', retryable: false,
}) as const;

const OVERVIEW: readonly ExecutionQueueStateCount[] = [
  { state: 'queued', count: 3 }, { state: 'leased', count: 1 }, { state: 'running', count: 2 }, { state: 'retry_wait', count: 1 },
  { state: 'succeeded', count: 12 }, { state: 'failed', count: 2 }, { state: 'cancelled', count: 1 }, { state: 'dead_letter', count: 1 },
];

describe('the number on the button', () => {
  it('is the overview\'s count of the jobs that are not finished, and nothing for a page with no overview', () => {
    expect(cancellableCount(OVERVIEW)).toBe(7);
    expect(cancellableCount(OVERVIEW.map((entry) => ({ ...entry, count: 0 })))).toBe(0);
    expect(cancellableCount(undefined)).toBe(0);
  });

  describe('on the page', () => {
    function render(roles: readonly string[], overview: readonly ExecutionQueueStateCount[] | null = OVERVIEW): string {
      const client = newClient();
      client.setQueryData(queryKeys.execution.queue(), {
        items: [job('A')], page: { next_cursor: null }, paused: false, ...(overview === null ? {} : { overview }),
      });
      client.setQueryData(queryKeys.account.me(), { roles });
      return renderScreen(client, createElement(QueuePage as ComponentType<QueuePageProps>));
    }

    it('is drawn for the roles that may cancel a run, with the number', () => {
      for (const roles of [['expert'], ['admin'], ['expert', 'admin']]) {
        expect(render(roles), roles.join()).toMatch(/<button[^>]*data-queue-cancel-all="7"[^>]*>Отменить очередь \(7\)<\/button>/);
      }
    });

    it('is not drawn for a role that may not, for an empty queue, or without an overview', () => {
      expect(render(['viewer'])).not.toContain('data-queue-cancel-all');
      expect(render([])).not.toContain('data-queue-cancel-all');
      expect(render(['expert'], OVERVIEW.map((entry) => ({ ...entry, count: entry.state === 'succeeded' ? 5 : 0 })))).not.toContain('data-queue-cancel-all');
      expect(render(['expert'], null)).not.toContain('data-queue-cancel-all');
    });
  });
});

describe('the jobs it cancels', () => {
  it('are the ones a cancel can reach, each run once', () => {
    const items = [job('A', 'queued'), job('B', 'leased'), job('C', 'running'), job('D', 'retry_wait'), job('E', 'succeeded'), job('F', 'failed'),
      job('G', 'cancelled'), job('H', 'dead_letter'), job('A', 'queued')];
    expect(cancellableJobs(items).map((item) => item.state)).toEqual(['queued', 'leased', 'running', 'retry_wait']);
  });

  it('are read page after page under the cursor each page names, and a cursor named twice ends the read with an error', async () => {
    const pages: Record<string, ExecutionQueuePage> = {
      first: { items: [job('A'), job('B')], page: { next_cursor: 'c2' }, paused: false },
      c2: { items: [job('C')], page: { next_cursor: 'c3' }, paused: false },
      c3: { items: [job('D')], page: { next_cursor: null }, paused: false },
    };
    const asked: (string | undefined)[] = [];
    const read = await readActiveJobs(async (cursor) => { asked.push(cursor); return pages[cursor ?? 'first']!; });
    expect(read.map((item) => item.document_name)).toEqual(['Документ A', 'Документ B', 'Документ C', 'Документ D']);
    expect(asked).toEqual([undefined, 'c2', 'c3']);
    const loop: Record<string, ExecutionQueuePage> = {
      first: { items: [job('A')], page: { next_cursor: 'c2' }, paused: false },
      c2: { items: [job('B')], page: { next_cursor: 'c2' }, paused: false },
    };
    await expect(readActiveJobs(async (cursor) => loop[cursor ?? 'first']!)).rejects.toThrow('one cursor twice');
  });
});

describe('the sweep', () => {
  const jobs = [job('A'), job('B', 'running'), job('C', 'leased')];

  function options() {
    let n = 0;
    return { keys: new Map<string, string>(), newKey: () => `ik-${++n}`, stopped: () => false };
  }

  it('sends one command for each run, each under a key of its own, one after another', async () => {
    const seen: [string, string][] = [];
    let running = 0;
    let overlap = 0;
    const outcomes = await sweepCancel(jobs, async (item, key) => {
      running += 1;
      overlap = Math.max(overlap, running);
      seen.push([item.run_id, key]);
      await Promise.resolve();
      running -= 1;
    }, options());
    expect(outcomes.map((outcome) => outcome.kind)).toEqual(['cancelled', 'cancelled', 'cancelled']);
    expect(seen.map(([run]) => run)).toEqual(jobs.map((item) => item.run_id));
    expect(new Set(seen.map(([, key]) => key)).size).toBe(3);
    expect(overlap).toBe(1);
  });

  it('says what each came to: a refusal by its name, an unknown outcome as unknown, and goes on to the next run', async () => {
    const outcomes = await sweepCancel(jobs, async (item) => {
      if (item.job_id === jobs[0]!.job_id) return;
      if (item.job_id === jobs[1]!.job_id) throw new ApiError(409, envelope('state_transition_not_allowed'), null);
      throw new ApiError(503, envelope('dependency_unavailable'), null);
    }, options());
    expect(outcomes.map((outcome) => outcome.kind)).toEqual(['cancelled', 'refused', 'unknown']);
    const summary = cancelSummary(outcomes);
    expect(summary.sentence).toBe('Отменено 1 из 3.');
    expect(summary.rest.map((entry) => entry.reason)).toEqual(['отмена на этапе проверки недоступна', 'исход неизвестен']);
    expect(summary.rest.map((entry) => workName(entry.item))).toEqual(['«Документ B», версия 2', '«Документ C», версия 2']);
  });

  it('sends a run again under the key it had, and a stopped sweep leaves the rest unsent', async () => {
    const shared = options();
    const first: string[] = [];
    await sweepCancel([jobs[0]!], async (_item, key) => { first.push(key); throw new ApiError(503, envelope('dependency_unavailable'), null); }, shared);
    const again: string[] = [];
    await sweepCancel([jobs[0]!], async (_item, key) => { again.push(key); }, shared);
    expect(again).toEqual(first);

    const calls = { n: 0 };
    const stopped = await sweepCancel(jobs, async () => { calls.n += 1; }, { ...options(), stopped: () => calls.n >= 1 });
    expect(stopped.map((outcome) => outcome.kind)).toEqual(['cancelled', 'skipped', 'skipped']);
    expect(cancelSummary(stopped).sentence).toBe('Отменено 1 из 3.');
    expect(cancelSummary(stopped).rest.every((entry) => entry.reason.includes('не отправлена'))).toBe(true);
  });

  it('names each kind of refusal in words, and never a run\'s number', () => {
    const failure = (status: number, code: Parameters<typeof envelope>[0]) => executionFailure(new ApiError(status, envelope(code), null), true);
    expect(cancelRefusal(failure(409, 'state_transition_not_allowed'))).toBe('отмена на этапе проверки недоступна');
    expect(cancelRefusal(failure(403, 'permission_denied'))).toBe('нет прав на отмену');
    expect(cancelRefusal(failure(409, 'conflict'))).toBe('состояние задачи изменилось, отмена не принята');
    expect(cancelRefusal(failure(503, 'dependency_unavailable'))).toBe('исход неизвестен');
  });
});

describe('what the page says', () => {
  const fake = (phase: CancelQueue['phase']): CancelQueue => ({
    phase, busy: false, begin: () => {}, confirm: () => {}, dismiss: () => {}, stop: () => {}, retryUnknown: () => {},
  });
  const html = (phase: CancelQueue['phase']) => renderToStaticMarkup(createElement(CancelQueuePanel, { queue: fake(phase) }));

  it('asks once, with the number of the jobs', () => {
    const markup = html({ kind: 'ask', jobs: [job('A'), job('B'), job('C')] });
    expect(markup).toContain('data-queue-cancel-ask="3"');
    expect(markup).toContain('Будет отменено задач: 3.');
    expect(markup).toContain('>Подтвердить</button>');
    expect(markup).toContain('>Отмена</button>');
  });

  it('says how far the sweep is, and offers to stop it', () => {
    const markup = html({ kind: 'sending', total: 5, sent: 2 });
    expect(markup).toContain('Отменяю: 2 из 5');
    expect(markup).toContain('>Остановить</button>');
  });

  it('says «Отменено N из M» with the document and version of each run that is not cancelled, and its reason', () => {
    const outcomes: CancelOutcome[] = [
      { kind: 'cancelled', item: job('A') },
      { kind: 'refused', item: job('B', 'running'), reason: 'отмена на этапе проверки недоступна' },
      { kind: 'unknown', item: job('C'), reason: 'исход неизвестен' },
    ];
    const markup = html({ kind: 'done', outcomes });
    expect(markup).toContain('Отменено 1 из 3.');
    expect(markup).toContain('«Документ B», версия 2: отмена на этапе проверки недоступна.');
    expect(markup).toContain('«Документ C», версия 2: исход неизвестен.');
    expect(markup).toContain('Повторить с тем же ключом');
    expect(markup).not.toContain('run_');
    expect(markup).not.toContain('job_');
  });

  it('does not offer a repeat when no outcome is unknown, and says when there was nothing to cancel', () => {
    expect(html({ kind: 'done', outcomes: [{ kind: 'cancelled', item: job('A') }] })).not.toContain('Повторить');
    expect(html({ kind: 'done', outcomes: [] })).toContain('Отменять нечего');
    expect(html({ kind: 'idle' })).toBe('');
  });
});
