/**
 * `UIP-S15-05` — the tab «Задачи» of «Диспетчер»: «Активные», «Завершённые» and «Ошибки» with their counts, a table under them, the
 * period of the completed ones in the reader's local time, a link to the queue and the pages by cursor. Read only. Every rule has a
 * case that fails when it is broken: a period sent for a group that has none, a count of the wrong group, a control of the queue
 * that is drawn here, a read sent for a role that must not.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { Role } from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import { QUEUE_STATE_GROUPS, queueItemError } from '@/entities/execution';
import { DEFAULT_TASKS_PERIOD, TASKS_PERIODS, tasksPeriodRange } from '@/entities/executor-host';
import type { TasksPeriod } from '@/entities/executor-host';
import { ExecutorHostTasks } from '@/widgets/executor-hosts';
import type { ExecutorHostTasksProps } from '@/widgets/executor-hosts';

import { newClient, renderScreen, seedError } from '../screens/harness';
import { JOB_DONE, JOB_FAILED, JOB_QUEUED, JOB_RUNNING, queuePage, seedQueue } from './hosts-fixtures';

/** The moment the tab is opened at, and of the reads: 21 minutes after the running job began. */
const NOW = new Date('2026-11-09T11:06:00Z');
const READ_AT = NOW.getTime();

function seeded(props: Omit<ExecutorHostTasksProps, 'roles'> & { roles?: Role[]; period?: TasksPeriod } = {}): string {
  const { roles = ['expert'], period = 'today', ...rest } = props;
  const client = newClient();
  const at = { updatedAt: READ_AT };
  // The counts of the three groups: the whole queue, no filter.
  seedQueue(client, queuePage([]), {}, at);
  seedQueue(client, queuePage([JOB_RUNNING, JOB_QUEUED]), { stateGroup: 'active' }, at);
  seedQueue(client, queuePage([JOB_DONE]), { stateGroup: 'completed', ...tasksPeriodRange(period, NOW) }, at);
  seedQueue(client, queuePage([JOB_FAILED]), { stateGroup: 'errors' }, at);
  return renderScreen(client, createElement(ExecutorHostTasks, { roles, now: NOW, initialPeriod: period, ...rest }));
}

const text = (markup: string): string => markup.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');

describe('the period, in the reader\'s local time', () => {
  it('is «Сегодня», «Неделя» and «Месяц», and opens on today', () => {
    expect(TASKS_PERIODS.map((period) => period.label)).toEqual(['Сегодня', 'Неделя', 'Месяц']);
    expect(DEFAULT_TASKS_PERIOD).toBe('today');
  });

  it('runs from a local midnight to the next one: today, the last seven days, the last thirty', () => {
    // The zone is pinned to UTC for the suite, so the edges are UTC midnights here.
    expect(tasksPeriodRange('today', NOW)).toEqual({ createdFrom: '2026-11-09T00:00:00.000Z', createdTo: '2026-11-10T00:00:00.000Z' });
    expect(tasksPeriodRange('week', NOW).createdFrom).toBe('2026-11-03T00:00:00.000Z');
    expect(tasksPeriodRange('month', NOW).createdFrom).toBe('2026-10-11T00:00:00.000Z');
    expect(tasksPeriodRange('month', NOW).createdTo).toBe('2026-11-10T00:00:00.000Z');
  });

  it('can fail: the edges are the reader\'s midnights, not UTC\'s', () => {
    const was = process.env.TZ;
    try {
      // 01:00 on the 18th in Yekaterinburg (UTC+5) is still the 17th in UTC.
      process.env.TZ = 'Asia/Yekaterinburg';
      const range = tasksPeriodRange('today', new Date('2026-11-17T20:00:00Z'));
      expect(range).toEqual({ createdFrom: '2026-11-17T19:00:00.000Z', createdTo: '2026-11-18T19:00:00.000Z' });
      expect(tasksPeriodRange('week', new Date('2026-11-17T20:00:00Z')).createdFrom).toBe('2026-11-11T19:00:00.000Z');
    } finally {
      if (was === undefined) delete process.env.TZ;
      else process.env.TZ = was;
    }
  });

  it('holds across the end of a month and of a year', () => {
    expect(tasksPeriodRange('week', new Date('2026-01-03T10:00:00Z')).createdFrom).toBe('2025-12-28T00:00:00.000Z');
    expect(tasksPeriodRange('today', new Date('2026-12-31T23:59:00Z')).createdTo).toBe('2027-01-01T00:00:00.000Z');
  });
});

describe('the three groups', () => {
  it('are the names and the states of the queue\'s own groups, each with its count from the queue\'s overview', () => {
    const markup = seeded();
    expect(QUEUE_STATE_GROUPS.map((group) => group.label)).toEqual(['Активные', 'Завершённые', 'Ошибки']);
    // Three queued, one leased, two running, one waiting to retry; five done and one cancelled; two failed and one stopped.
    expect(text(markup)).toContain('Активные 7 Завершённые 6 Ошибки 3');
    expect(markup).toContain('data-tasks-group="active"');
    expect(markup).toMatch(/aria-pressed="true"[^>]*data-tasks-group="active"/);
  });

  it('draw the counts as the whole queue\'s, whatever the period of the list', () => {
    // «Завершённые» is six whatever period is chosen: the list narrows, the count does not.
    for (const period of ['today', 'week', 'month'] as const) {
      expect(text(seeded({ initialGroup: 'completed', period })), period).toContain('Завершённые 6');
    }
  });

  it('say only the name while the queue\'s overview is not read', () => {
    const client = newClient();
    seedQueue(client, queuePage([JOB_RUNNING]), { stateGroup: 'active' }, { updatedAt: READ_AT });
    const markup = renderScreen(client, createElement(ExecutorHostTasks, { roles: ['expert'], now: NOW }));
    expect(text(markup)).toContain('Активные Завершённые Ошибки');
    expect(markup).toContain('data-tasks-count=""');
  });

  it('read the list of the open group only, under the filter of that group', () => {
    // Only the key of «Активные» is seeded: the other groups are not what is on screen.
    const client = newClient();
    seedQueue(client, queuePage([JOB_RUNNING]), { stateGroup: 'active' }, { updatedAt: READ_AT });
    const active = renderScreen(client, createElement(ExecutorHostTasks, { roles: ['expert'], now: NOW }));
    expect(active).toContain('data-task-object');
    const errors = renderScreen(client, createElement(ExecutorHostTasks, { roles: ['expert'], now: NOW, initialGroup: 'errors' }));
    expect(errors).not.toContain('data-task-object');
    expect(errors).toContain('Загрузка');
  });
});

describe('the table', () => {
  it('names the document as a link with its object under it, the state, when it began and how long', () => {
    const markup = seeded();
    for (const header of ['Документ', 'Состояние', 'Начата', 'Длительность']) expect(markup).toContain(`>${header}<`);
    expect(markup).toContain('href="/projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8A/documents/doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8A"');
    expect(markup).toContain('Планы этажей</a>');
    expect(markup).toContain('data-task-object="true">Жилой дом<');
    expect(markup).toContain('data-job-state="running"');
    expect(markup).toContain('Выполняется');
    expect(markup).toContain('09.11.2026 10:45');
    expect(markup).toContain('21 мин');
  });

  it('says a dash for the start and the length of a job that has not begun', () => {
    const markup = seeded();
    const row = markup.slice(markup.indexOf(`data-row-key="${JOB_QUEUED.job_id}"`));
    const cells = text(row.slice(0, row.indexOf('</tr>')));
    expect(cells).toContain('Разрезы');
    expect(cells).toContain('Ожидает');
    expect(cells).toMatch(/— —\s*$/);
  });

  it('measures a finished job from its start to its end, not to now', () => {
    const markup = seeded({ initialGroup: 'completed' });
    expect(markup).toContain('data-job-state="succeeded"');
    expect(markup).toContain('09.11.2026 09:00');
    expect(markup).toContain('30 мин');
    expect(markup).not.toContain('2 ч');
  });

  it('adds the reason to the errors, in the sentence of the run\'s note and the code when there is no sentence', () => {
    const markup = seeded({ initialGroup: 'errors' });
    expect(markup).toContain('>Причина<');
    expect(markup).toContain('data-job-state="failed"');
    const error = queueItemError(JOB_FAILED);
    expect(error).not.toBeNull();
    expect(markup).toContain(error?.sentence ?? `<code>${error?.code}</code>`);
    expect(markup).toContain('10 мин');
    for (const group of ['active', 'completed'] as const) expect(seeded({ initialGroup: group }), group).not.toContain('>Причина<');
  });

  it('has no server and no mode column, and none of the queue\'s controls', () => {
    for (const group of ['active', 'completed', 'errors'] as const) {
      const markup = seeded({ initialGroup: group });
      for (const absent of ['>Сервер<', '>Режим<', 'Отменить', 'Повторный аудит', 'Приоритет', 'Переместить', 'type="number"']) {
        expect(markup, `${group} ${absent}`).not.toContain(absent);
      }
    }
  });

  it('says an empty group in a sentence of its own', () => {
    const empty = (group: 'active' | 'completed' | 'errors'): string => {
      const client = newClient();
      seedQueue(client, queuePage([]), {}, { updatedAt: READ_AT });
      seedQueue(client, queuePage([]), group === 'completed' ? { stateGroup: group, ...tasksPeriodRange('today', NOW) } : { stateGroup: group }, { updatedAt: READ_AT });
      return renderScreen(client, createElement(ExecutorHostTasks, { roles: ['expert'], now: NOW, initialGroup: group }));
    };
    expect(empty('active')).toContain('Активных задач нет');
    expect(empty('completed')).toContain('Завершённых задач за этот период нет');
    expect(empty('errors')).toContain('Задач с ошибкой нет');
    expect(empty('errors')).not.toContain('<table');
  });
});

describe('the period of the completed ones', () => {
  it('is offered under «Завершённые» only, with the chosen one pressed', () => {
    const completed = seeded({ initialGroup: 'completed', period: 'week' });
    for (const period of ['today', 'week', 'month']) expect(completed).toContain(`data-tasks-period="${period}"`);
    expect(completed).toMatch(/aria-pressed="true"[^>]*data-tasks-period="week"/);
    expect(completed).toContain('>Сегодня<');
    expect(completed).toContain('>Неделя<');
    expect(completed).toContain('>Месяц<');
    for (const group of ['active', 'errors'] as const) expect(seeded({ initialGroup: group }), group).not.toContain('data-tasks-period');
  });

  it('is part of the filter the completed ones are read under, and of no other group\'s', () => {
    // The list of «Завершённые» is seeded under the range of «Неделя» only: «Сегодня» reads another key, and is still loading.
    const client = newClient();
    seedQueue(client, queuePage([]), {}, { updatedAt: READ_AT });
    seedQueue(client, queuePage([JOB_DONE]), { stateGroup: 'completed', ...tasksPeriodRange('week', NOW) }, { updatedAt: READ_AT });
    const week = renderScreen(client, createElement(ExecutorHostTasks, { roles: ['expert'], now: NOW, initialGroup: 'completed', initialPeriod: 'week' }));
    const today = renderScreen(client, createElement(ExecutorHostTasks, { roles: ['expert'], now: NOW, initialGroup: 'completed', initialPeriod: 'today' }));
    expect(week).toContain('data-job-state="succeeded"');
    expect(today).not.toContain('data-job-state="succeeded"');
    // The key of a group with no period carries none, and no two periods share a key.
    const keys = TASKS_PERIODS.map((period) => JSON.stringify(queryKeys.execution.queue(undefined, { stateGroup: 'completed', ...tasksPeriodRange(period.value, NOW) })));
    expect(new Set(keys).size).toBe(3);
    expect(JSON.stringify(queryKeys.execution.queue(undefined, { stateGroup: 'active' }))).not.toContain('createdFrom":"');
  });
});

describe('«Открыть очередь» and the pages', () => {
  it('leads to the queue, where the jobs are cancelled and put in order', () => {
    const markup = seeded();
    expect(markup).toContain('data-tasks-open-queue');
    expect(markup).toContain('href="/queue"');
    expect(markup).toContain('Открыть очередь');
  });

  it('go by cursor: «Далее» is on when the server named a next page and «Назад» is off on the first', () => {
    const client = newClient();
    seedQueue(client, queuePage([]), {}, { updatedAt: READ_AT });
    seedQueue(client, queuePage([JOB_RUNNING], { page: { next_cursor: 'c2' } }), { stateGroup: 'active' }, { updatedAt: READ_AT });
    const more = renderScreen(client, createElement(ExecutorHostTasks, { roles: ['expert'], now: NOW }));
    const button = (markup: string, mark: string): string => new RegExp(`<button[^>]*${mark}[^>]*>`).exec(markup)?.[0] ?? '';
    expect(button(more, 'data-tasks-previous')).toContain('disabled=""');
    expect(button(more, 'data-tasks-next')).not.toContain('disabled');
    expect(more).toContain('Далее');
    expect(button(seeded(), 'data-tasks-next')).toContain('disabled=""');
  });

  it('read the next page under the cursor, and the cursor is in the key', () => {
    const first = JSON.stringify(queryKeys.execution.queue(undefined, { stateGroup: 'active' }));
    const second = JSON.stringify(queryKeys.execution.queue('c2', { stateGroup: 'active' }));
    expect(second).not.toBe(first);
  });
});

describe('the roles and the failures', () => {
  it('draws a viewer nothing but the refusal, even from a cache that holds the queue', () => {
    for (const roles of [['viewer'], []] as Role[][]) {
      const markup = seeded({ roles });
      expect(markup).not.toContain('data-tasks-group');
      expect(markup).not.toContain('data-task-object');
      expect(markup).toContain('Задачи недоступны');
    }
  });

  it('draws the same tab to an expert and to an administrator', () => {
    for (const roles of [['expert'], ['admin']] as Role[][]) expect(seeded({ roles }), roles.join()).toContain('data-task-object');
  });

  it('says a failed read in words, with a retry, and does not pass the old page off as current', () => {
    const client = newClient();
    seedQueue(client, queuePage([]), {}, { updatedAt: READ_AT });
    seedError(client, queryKeys.execution.queue(undefined, { stateGroup: 'active' }), new ApiError(503, {
      contract_version: '1.58.0', error_code: 'dependency_unavailable', message: 'x', correlation_id: 'cid-tasks-1', retryable: true, details: {},
    }, null));
    const markup = renderScreen(client, createElement(ExecutorHostTasks, { roles: ['expert'], now: NOW }));
    expect(markup).toContain('data-tasks-read-failure');
    expect(markup).toContain('Задачи не прочитаны');
    expect(markup).not.toContain('data-task-object');
  });
});
