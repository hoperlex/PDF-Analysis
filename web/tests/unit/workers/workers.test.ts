/**
 * `W54-WORKERS-WEB` — the «Исполнители» screen and the worker named on the queue.
 *
 * Plan §3.7: the registry lists online and stale workers first and offline ones collapsed;
 * an administrator, and only an administrator, sees the intake switch; any role reads the
 * list (`R-80`); the reads are never stale (`C-26`'s rule); the empty and failed states say
 * what they are, in Russian.
 */

import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ExecutionQueueItem, ExecutionWorker, ExecutionWorkerPage, Role } from '@/shared/api';
import { ApiError, TransportError, queryKeys } from '@/shared/api';
import {
  WORKER_LOOKUP_LIMIT, WORKER_PAGE_LIMIT, canExecute, groupWorkers, hasUnknownWorkerState,
  jobHoldsLease, runHoldsLease, runWorker, workerIntakeLabel, workerStateLabel,
  workersQueryOptions,
} from '@/entities/execution';
import { ExecutionQueue } from '@/widgets/execution-queue';
import { WorkerList } from '@/widgets/worker-list';
import { QueuePage } from '@/_pages/queue/ui/queue-page';
import { WorkersPage, intakeIntentLabel } from '@/_pages/workers/ui/workers-page';

import { newClient, renderScreen, seedError } from '../screens/harness';

const RUN_ID = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const OTHER_RUN = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8G';
const noop = () => {};

function worker(over: Partial<ExecutionWorker> = {}): ExecutionWorker {
  return {
    worker_id: 'wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8A',
    state: 'online',
    intake_enabled: true,
    slots: 1,
    version: '0.5.0',
    started_at: '2026-10-12T10:00:00Z',
    heartbeat_at: '2026-10-12T10:05:00Z',
    current_run_ids: [],
    ...over,
  };
}

const ONLINE = worker({ current_run_ids: [RUN_ID] });
const STALE = worker({ worker_id: 'wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', state: 'stale', intake_enabled: false });
const OFFLINE = worker({ worker_id: 'wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8C', state: 'offline' });
/** The server's order: newest start first, which here puts the offline worker first. */
const REGISTRY: readonly ExecutionWorker[] = [OFFLINE, ONLINE, STALE];

function page(items: readonly ExecutionWorker[], next: string | null = null): ExecutionWorkerPage {
  return { items: [...items], page: { next_cursor: next } };
}

function list(roles: Role[], items: readonly ExecutionWorker[] = REGISTRY, onPrevious: (() => void) | null = null): string {
  return renderToStaticMarkup(createElement(WorkerList, {
    items, roles, busy: false, onIntake: noop, onNext: null, onPrevious,
  }));
}

function envelope(code: 'permission_denied' | 'dependency_unavailable') {
  return {
    contract_version: '1.10.0', error_code: code,
    message: 'Безопасный отказ.', correlation_id: 'cid-workers-1', retryable: false,
  } as const;
}

describe('worker presentation', () => {
  it('names each sealed state in Russian and refuses a value outside the set', () => {
    expect(workerStateLabel('online')).toBe('На связи');
    expect(workerStateLabel('stale')).toBe('Не отвечает');
    expect(workerStateLabel('offline')).toBe('Отключён');
    expect(workerStateLabel('draining')).toBeNull();
    expect(hasUnknownWorkerState([worker({ state: 'draining' as ExecutionWorker['state'] })])).toBe(true);
    expect(hasUnknownWorkerState(REGISTRY)).toBe(false);
    expect(workerIntakeLabel(true)).toBe('Берёт новые прогоны');
    expect(workerIntakeLabel(false)).toBe('Не берёт новые прогоны');
  });

  it('puts online and stale workers above offline ones, keeping the server order in each', () => {
    const groups = groupWorkers(REGISTRY);
    expect(groups.active.map((w) => w.worker_id)).toEqual([ONLINE.worker_id, STALE.worker_id]);
    expect(groups.offline.map((w) => w.worker_id)).toEqual([OFFLINE.worker_id]);
  });

  it('gives the intake switch to an administrator only', () => {
    expect(canExecute([], 'intake')).toBe(false);
    expect(canExecute(['expert'], 'intake')).toBe(false);
    expect(canExecute(['admin'], 'intake')).toBe(true);
    expect(canExecute(['expert', 'admin'], 'intake')).toBe(true);
  });

  it('names the worker of the stopping or allowing intent', () => {
    expect(intakeIntentLabel({ worker: ONLINE, enabled: false, key: 'ik' })).toContain(ONLINE.worker_id);
    expect(intakeIntentLabel({ worker: ONLINE, enabled: false, key: 'ik' })).toContain('Запретить');
    expect(intakeIntentLabel({ worker: STALE, enabled: true, key: 'ik' })).toContain(STALE.worker_id);
    expect(intakeIntentLabel({ worker: STALE, enabled: true, key: 'ik' })).toContain('Разрешить');
  });
});

describe('worker reads', () => {
  it('are never stale, refresh on focus and live in the execution namespace', () => {
    const options = workersQueryOptions();
    expect(options.staleTime).toBe(0);
    expect(options.refetchOnWindowFocus).toBe('always');
    expect(options.queryKey[0]).toBe('execution');
    expect(options.queryKey).toEqual(queryKeys.execution.workers(undefined, WORKER_PAGE_LIMIT));
    expect(workersQueryOptions('a').queryKey).not.toEqual(workersQueryOptions('b').queryKey);
  });

  it('read a separate, larger first page to name a run worker, and only when asked', () => {
    const lookup = workersQueryOptions(undefined, WORKER_LOOKUP_LIMIT, false);
    expect(WORKER_LOOKUP_LIMIT).toBe(200);
    expect(lookup.enabled).toBe(false);
    expect(lookup.staleTime).toBe(0);
    expect(lookup.queryKey).not.toEqual(workersQueryOptions().queryKey);
  });

  it('say who holds a run, and never call an incomplete read "no worker"', () => {
    expect(runWorker(page(REGISTRY), false, RUN_ID)).toEqual({ kind: 'held', workerId: ONLINE.worker_id });
    expect(runWorker(page(REGISTRY), false, OTHER_RUN)).toEqual({ kind: 'unheld' });
    expect(runWorker(page(REGISTRY, 'next-page'), false, OTHER_RUN)).toEqual({ kind: 'beyond' });
    expect(runWorker(undefined, true, RUN_ID)).toEqual({ kind: 'unreadable' });
    expect(runWorker(undefined, false, RUN_ID)).toEqual({ kind: 'pending' });
  });

  it('are asked only in the states where a Lease is held', () => {
    expect(['leased', 'running'].filter(jobHoldsLease)).toEqual(['leased', 'running']);
    expect(['queued', 'retry_wait', 'succeeded', 'failed'].some(jobHoldsLease)).toBe(false);
    expect(['running', 'validating'].filter(runHoldsLease)).toEqual(['running', 'validating']);
    expect(['created', 'queued', 'published', 'partial', 'failed', 'cancelled'].some(runHoldsLease)).toBe(false);
  });
});

describe('the worker list', () => {
  it('lists online and stale above the collapsed offline group', () => {
    const markup = list(['expert']);
    const online = markup.indexOf(ONLINE.worker_id);
    const stale = markup.indexOf(STALE.worker_id);
    const offline = markup.indexOf(OFFLINE.worker_id);
    expect(online).toBeGreaterThan(-1);
    expect(stale).toBeGreaterThan(online);
    expect(offline).toBeGreaterThan(stale);
    expect(markup).toMatch(/<details[^>]*data-worker-group="offline"/);
    expect(markup.indexOf('<details')).toBeLessThan(offline);
    expect(markup.indexOf('<details')).toBeGreaterThan(stale);
    expect(markup).toContain('Отключённые исполнители: 1');
  });

  it('shows state, intake, slots, version, times and current runs', () => {
    const markup = list(['expert']);
    for (const text of ['На связи', 'Не отвечает', 'Отключён', 'Берёт новые прогоны',
      'Не берёт новые прогоны', 'Слотов: 1', '0.5.0', 'Последний сигнал', 'Текущих прогонов нет.']) {
      expect(markup).toContain(text);
    }
    expect(markup).toContain(`href="/logs?run_id=${RUN_ID}"`);
  });

  it('draws the switch for an administrator only, worded by the current intake', () => {
    expect(list([])).not.toContain('Не брать новые');
    expect(list(['expert'])).not.toContain('Не брать новые');
    expect(list(['expert'])).not.toContain('>Разрешить<');
    const admin = list(['admin']);
    expect(admin.match(/>Не брать новые</g)?.length).toBe(2);
    expect(admin.match(/>Разрешить</g)?.length).toBe(1);
  });

  it('says when no worker is registered, and when none on the page is on line', () => {
    const empty = list(['admin'], []);
    expect(empty).toContain('Исполнителей нет');
    expect(empty).toContain('само приложение');
    expect(list(['admin'], [], noop)).toContain('На этой странице исполнителей нет');
    expect(list(['admin'], [OFFLINE])).toContain('data-workers-none-active');
    expect(list(['admin'])).not.toContain('data-workers-none-active');
  });

  it('refuses to render a state outside the sealed set', () => {
    const markup = list(['admin'], [worker({ state: 'draining' as ExecutionWorker['state'] })]);
    expect(markup).toContain('Неизвестное состояние исполнителя');
    expect(markup).not.toContain('wrk_');
  });
});

describe('the «Исполнители» page', () => {
  function seeded(roles: Role[] | 'failed', workers: ExecutionWorkerPage | 'failed' = page(REGISTRY)) {
    const client = newClient();
    if (workers === 'failed') {
      seedError(client, queryKeys.execution.workers(undefined, WORKER_PAGE_LIMIT), new ApiError(503, envelope('dependency_unavailable'), null));
    } else {
      client.setQueryData(queryKeys.execution.workers(undefined, WORKER_PAGE_LIMIT), workers);
    }
    if (roles === 'failed') seedError(client, queryKeys.account.me(), new TransportError('connection closed'));
    else client.setQueryData(queryKeys.account.me(), { roles });
    return renderScreen(client, createElement(WorkersPage));
  }

  it('is no longer the placeholder', () => {
    const markup = seeded(['expert']);
    expect(markup).not.toContain('data-route="/workers"');
    expect(markup).not.toContain('в альфе');
    expect(markup).toContain('Исполнители');
    expect(markup).toContain('>Обновить</button>');
  });

  it('gives an administrator the switch and an expert the list alone', () => {
    expect(seeded(['admin'])).toContain('Не брать новые');
    const expert = seeded(['expert']);
    expect(expert).toContain(ONLINE.worker_id);
    expect(expert).not.toContain('Не брать новые');
  });

  it('renders the rows without any switch when getMe fails, and says why', () => {
    const markup = seeded('failed');
    expect(markup).toContain(ONLINE.worker_id);
    expect(markup).toContain('data-workers-controls-withheld');
    expect(markup).toContain('Исполнители показаны без команд: права не прочитаны.');
    expect(markup).not.toContain('Не брать новые');
  });

  it('says the registry was not read instead of showing an empty list', () => {
    const markup = seeded(['admin'], 'failed');
    expect(markup).toContain('data-workers-read-failure="refusal"');
    expect(markup).toContain('Исполнители не прочитаны');
    expect(markup).toContain('cid-workers-1');
    expect(markup).not.toContain('Исполнителей нет');
  });

  it('opens no confirmation until a switch is pressed', () => {
    expect(seeded(['admin'])).not.toContain('Подтвердить');
  });
});

describe('the queue names the worker holding a run', () => {
  const running: ExecutionQueueItem = {
    job_id: 'job_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', run_id: RUN_ID, state: 'running', priority: 0,
    created_at: '2026-10-12T10:00:00Z', available_at: '2026-10-12T10:00:00Z',
  };

  function queue(item: ExecutionQueueItem, workers?: ExecutionWorkerPage | 'failed'): string {
    const client = newClient();
    client.setQueryData(queryKeys.execution.queue(), { items: [item], page: { next_cursor: null }, paused: false });
    client.setQueryData(queryKeys.account.me(), { roles: ['expert'] });
    const key = queryKeys.execution.workers(undefined, WORKER_LOOKUP_LIMIT);
    if (workers === 'failed') seedError(client, key, new TransportError('connection closed'));
    else if (workers !== undefined) client.setQueryData(key, workers);
    return renderScreen(client, createElement(QueuePage));
  }

  it('names it, linked to «Исполнители», for a running Job', () => {
    const markup = queue(running, page(REGISTRY));
    expect(markup).toContain('data-run-worker="held"');
    expect(markup).toContain(ONLINE.worker_id);
    expect(markup).toContain('href="/workers"');
  });

  it('says so when no registered worker holds it, or the registry was not read', () => {
    expect(queue({ ...running, run_id: OTHER_RUN }, page(REGISTRY))).toContain('data-run-worker="unheld"');
    expect(queue(running, 'failed')).toContain('data-run-worker="unreadable"');
    expect(queue(running)).toContain('data-run-worker="pending"');
  });

  it('asks nothing about a Job that holds no Lease', () => {
    const markup = queue({ ...running, state: 'queued' }, page(REGISTRY));
    expect(markup).not.toContain('data-run-worker');
    expect(renderToStaticMarkup(createElement(ExecutionQueue, {
      items: [{ ...running, state: 'succeeded' }], roles: [], asOf: null, busy: false,
      workerOf: () => { throw new Error('asked about a run no worker holds'); },
      onCancel: noop, onReaudit: noop, onPriority: noop, onNext: null, onPrevious: null,
    }))).not.toContain('data-run-worker');
  });
});
