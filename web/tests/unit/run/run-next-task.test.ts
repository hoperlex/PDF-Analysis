/**
 * «Следующая задача» on a waiting run's page (`UI-B-70`): what the card says from the run's own reading and the queue's
 * first page, and that it says nothing the data does not carry — no scheduler recommendation, no estimate of its own start.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { Account, ExecutionQueueItem, ExecutionQueuePage, RunStatus } from '@/shared/api';
import { meQueryOptions } from '@/entities/account';
import { nextTaskPlace, nextTaskWhy, nextTaskWork, runNextTask } from '@/entities/audit-run';
import { queueQueryOptions } from '@/entities/execution';
import { RunNextTask } from '@/widgets/run-progress';

import { PROJECT_UID, RUN_ID, VERSION_UID } from '../review/fixtures';

const DOCUMENT_UID = 'doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';

/** A queued job at place `n` (the place is the dispatcher's `queue_position`); `queued: false` leaves it without one. */
function job(n: number, overrides: Partial<ExecutionQueueItem> = {}, queued = true): ExecutionQueueItem {
  return {
    available_at: '2026-11-08T10:00:00Z',
    created_at: `2026-11-08T10:0${n}:00Z`,
    document_name: `Раздел ${n}`,
    document_uid: DOCUMENT_UID,
    job_id: `job_${n}`,
    priority: 0,
    project_name: `Проект ${n}`,
    project_uid: PROJECT_UID,
    run_id: `run_other_${n}`,
    state: 'queued',
    version_ordinal: n,
    version_uid: VERSION_UID,
    ...(queued ? { queue_position: n } : {}),
    ...overrides,
  } as ExecutionQueueItem;
}

/** A job in work: it has no place in the queue, and may carry an estimated finish. */
function runningJob(n: number, overrides: Partial<ExecutionQueueItem> = {}): ExecutionQueueItem {
  return job(n, { state: 'running', ...overrides }, false);
}

function pageOf(items: ExecutionQueueItem[], overrides: Partial<ExecutionQueuePage> = {}): ExecutionQueuePage {
  return {
    items,
    paused: false,
    page: { next_cursor: null },
    overview: [{ state: 'queued', count: 3 }, { state: 'running', count: 1 }, { state: 'leased', count: 0 }, { state: 'succeeded', count: 40 }],
    ...overrides,
  } as ExecutionQueuePage;
}

const RUN = { run_id: RUN_ID, state: 'queued' } as Pick<RunStatus, 'run_id' | 'state' | 'queue_reason' | 'wait_reason' | 'waiting_since'>;
const MINE = job(3, { run_id: RUN_ID });

describe('the run’s place and the job that goes first', () => {
  it('reads the place from the dispatcher’s own position and names the first job when it is another run’s', () => {
    const task = runNextTask(RUN, pageOf([job(1), job(2), MINE, runningJob(4)]));
    expect(task).toMatchObject({ position: 3, ahead: 2, isNext: false, read: 'whole' });
    expect(task.next?.run_id).toBe('run_other_1');
    expect(nextTaskPlace(task)).toBe('№ 3 в очереди. Впереди в очереди: 2.');
  });

  it('says the run is first, and names no other job, when its job heads the queue', () => {
    const task = runNextTask(RUN, pageOf([job(1, { run_id: RUN_ID }), job(2)]));
    expect(task).toMatchObject({ position: 1, ahead: 0, isNext: true, next: null });
    expect(nextTaskPlace(task)).toContain('первая в очереди');
  });

  it('says it cannot place the run when the first page does not list it, and that the page is a first page', () => {
    const partial = runNextTask(RUN, pageOf([job(1), job(2)], { page: { next_cursor: 'c1' } } as never));
    expect(partial).toMatchObject({ position: null, ahead: null, read: 'partial' });
    expect(nextTaskPlace(partial)).toContain('нет на первой странице очереди');
    const whole = runNextTask(RUN, pageOf([job(1)]));
    expect(nextTaskPlace(whole)).toContain('нет в очереди на момент чтения');
  });

  it('says nothing about a place when the queue was not read', () => {
    const task = runNextTask(RUN, undefined);
    expect(task).toMatchObject({ position: null, paused: null, inWork: null, queued: null, finishing: null, read: 'none' });
    expect(nextTaskPlace(task)).toBeNull();
    expect(nextTaskWork(task)).toBeNull();
  });
});

describe('why the run waits', () => {
  it('uses the run’s own reason in words, and since when, never one it was not given', () => {
    const task = runNextTask({ ...RUN, queue_reason: 'executor_at_capacity', waiting_since: '2026-11-08T10:00:00Z' }, undefined);
    expect(nextTaskWhy(task)).toEqual(['В очереди: исполнитель занят. Ждёт с 2026-11-08 10:00:00 UTC.']);
  });

  it('adds the pause and the jobs in front when the queue says them', () => {
    const task = runNextTask({ ...RUN, wait_reason: 'runner_offline' }, pageOf([job(1), MINE], { paused: true }));
    expect(nextTaskWhy(task)).toEqual([
      'Очередь на паузе: пока её не возобновят, ни одна задача не уходит в работу.',
      'В очереди: раннер не в сети.',
      'Впереди стоят другие задачи: сначала уходят они.',
    ]);
  });

  it('says the server named no reason when nothing explains the wait', () => {
    expect(nextTaskWhy(runNextTask(RUN, pageOf([job(1, { run_id: RUN_ID })])))).toEqual(['Сервер не назвал причину ожидания.']);
  });

  it('ignores a reason this screen has no word for', () => {
    expect(nextTaskWhy(runNextTask({ ...RUN, queue_reason: 'something_new' as never }, undefined))).toEqual(['Сервер не назвал причину ожидания.']);
  });
});

describe('what is in work', () => {
  it('counts the jobs leased and running from the overview and takes the nearest estimate from the running jobs only', () => {
    const items = [
      job(1), MINE,
      runningJob(5, { estimated_finish_at: '2026-11-08T12:30:00Z' }),
      runningJob(6, { estimated_finish_at: '2026-11-08T11:15:00Z' }),
      runningJob(7),
    ];
    const task = runNextTask(RUN, pageOf(items));
    expect(task.inWork).toBe(1);
    expect(task.queued).toBe(3);
    expect(task.finishing?.run_id).toBe('run_other_6');
    expect(nextTaskWork(task)).toBe('В работе: 1 · ожидают: 3 · ближайшее завершение по оценке: 2026-11-08 11:15:00 UTC');
  });

  it('gives no estimate of its own start and none for a queued job’s finish', () => {
    const task = runNextTask(RUN, pageOf([job(1, { estimated_finish_at: '2026-11-08T11:00:00Z' }), MINE]));
    expect(task.finishing).toBeNull();
    expect(nextTaskWork(task)).not.toContain('завершение');
  });
});

describe('the card', () => {
  function card(roles: string[] | null, page: ExecutionQueuePage | null, status: Partial<RunStatus> = {}): string {
    const client = new QueryClient();
    if (roles !== null) client.setQueryData(meQueryOptions().queryKey, { roles } as unknown as Account);
    if (page !== null) client.setQueryData(queueQueryOptions().queryKey, page);
    return renderToStaticMarkup(createElement(
      QueryClientProvider, { client }, createElement(RunNextTask, { status: { ...RUN, ...status } as RunStatus }),
    ));
  }

  it('shows the place, the first job with a link to its run, the reason and the figures for an expert', () => {
    const markup = card(['expert'], pageOf([job(1), job(2), MINE]), { queue_reason: 'executor_at_capacity' });
    expect(markup).toContain('data-run-next-task="whole"');
    expect(markup).toContain('№ 3 в очереди. Впереди в очереди: 2.');
    expect(markup).toContain('Проект 1 · Раздел 1 · версия 1');
    expect(markup).toContain(`/projects/${PROJECT_UID}/runs/run_other_1`);
    expect(markup).toContain('В очереди: исполнитель занят.');
    expect(markup).toContain('В работе: 1 · ожидают: 3');
    expect(markup).toContain('Открыть всю очередь');
  });

  it('keeps the run’s own reason and reads no queue for a session the queue is closed to', () => {
    const markup = card(['viewer'], pageOf([job(1), MINE]), { queue_reason: 'runner_offline' });
    expect(markup).toContain('data-run-next-task="none"');
    expect(markup).toContain('В очереди: раннер не в сети.');
    expect(markup).not.toContain('Открыть всю очередь');
    expect(markup).not.toContain('Эта задача');
  });

  it('draws the run’s own part and nothing about the queue while the account is not known', () => {
    const markup = card(null, null);
    expect(markup).toContain('Сервер не назвал причину ожидания.');
    expect(markup).not.toContain('Открыть всю очередь');
  });
});
