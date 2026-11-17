'use client';

/**
 * The tab «Задачи» of «Диспетчер» (`UIP-S15-05`, `Г12-B`, `Г4-B`, `Г1-C`): the queue's jobs in three groups, «Активные», «Завершённые»
 * and «Ошибки», each with its count, and under them a table.
 *
 * ```
 * [Активные 3] [Завершённые 6] [Ошибки 3]                        Открыть очередь
 * (для «Завершённых»:  Сегодня · Неделя · Месяц)
 * Документ              Состояние     Начата            Длительность   Причина
 * Планы этажей          Выполняется   09.11.2026 10:45  21 мин
 * Жилой дом
 * ```
 *
 * The names and the states of the three groups are `QUEUE_STATE_GROUPS` of `execution`, the counts the queue's overview, the list
 * `listExecutionQueue` with `state_group` (and, for «Завершённых», the period `[created_from, created_to)` in the reader's local
 * time). Read only: a job is cancelled or put elsewhere in the order on the screen «Очередь», to which the link leads. Nothing of
 * the queue widget is copied or imported; the two read the same entity. No server and no mode are drawn: the queue has neither.
 * No panel of a task with stages, models or technical information (`Г12-B`).
 *
 * The pages go by cursor. A cursor belongs to the filter it was issued under, so the pages walked are held with that filter and
 * start again when the group or the period changes. Nothing is read for a viewer (`R-150w`).
 */

import Link from 'next/link';
import { useMemo, useState } from 'react';

import type { ExecutionQueueItem, ExecutionQueueStateCount, Role } from '@/shared/api';
import {
  JobStateBadge,
  QUEUE_STATE_GROUPS,
  UpdateTime,
  executionFailure,
  queueAgeLabel,
  queueItemError,
  queueStateCount,
  useExecutionQueue,
} from '@/entities/execution';
import type { ExecutionQueueFilter, ExecutionQueueStateGroup } from '@/entities/execution';
import { DEFAULT_TASKS_PERIOD, TASKS_PERIODS, mayReadHosts, tasksPeriodRange } from '@/entities/executor-host';
import type { TasksPeriod } from '@/entities/executor-host';
import { formatInstant, routes } from '@/shared/lib';
import { EmptyState, ErrorState, LoadingState, Table, UnsupportedState } from '@/shared/ui';
import type { TableColumn } from '@/shared/ui';

import styles from './executor-hosts.module.css';

const EMPTY_TITLES: Readonly<Record<ExecutionQueueStateGroup, string>> = {
  active: 'Активных задач нет',
  completed: 'Завершённых задач за этот период нет',
  errors: 'Задач с ошибкой нет',
};

/** The jobs of one group counted from the queue's overview; `null` when there is no overview to count from. */
function groupCount(overview: readonly ExecutionQueueStateCount[] | undefined, states: readonly ExecutionQueueStateCount['state'][]): number | null {
  let sum = 0;
  for (const state of states) {
    const one = queueStateCount(overview, state);
    if (one === null) return null;
    sum += one;
  }
  return sum;
}

/** «21 мин» of a job: since it began, to its end or, while it runs, to the last read. A job that has not begun has none. */
function durationOf(item: ExecutionQueueItem, asOf: number | null): string {
  if (item.started_at === undefined) return '—';
  if (item.finished_at === undefined) return queueAgeLabel(item.started_at, asOf);
  const end = Date.parse(item.finished_at);
  return queueAgeLabel(item.started_at, Number.isFinite(end) ? end : null);
}

function columnsOf(group: ExecutionQueueStateGroup, asOf: number | null): readonly TableColumn<ExecutionQueueItem>[] {
  const columns: TableColumn<ExecutionQueueItem>[] = [
    {
      key: 'document',
      header: 'Документ',
      cell: (item) => (
        <>
          <Link href={routes.document(item.project_uid, item.document_uid)}>{item.document_name}</Link>
          <span className={styles.taskObject} data-task-object>{item.project_name}</span>
        </>
      ),
    },
    { key: 'state', header: 'Состояние', cell: (item) => <JobStateBadge state={item.state} /> },
    {
      key: 'started',
      header: 'Начата',
      cell: (item) => (item.started_at === undefined ? '—' : <time dateTime={item.started_at}>{formatInstant(item.started_at)}</time>),
    },
    { key: 'duration', header: 'Длительность', cell: (item) => durationOf(item, asOf) },
  ];
  if (group === 'errors') {
    columns.push({
      key: 'reason',
      header: 'Причина',
      cell: (item) => {
        const error = queueItemError(item);
        if (error === null) return '—';
        // A code this client has no sentence for is shown as the code alone, never as a guess.
        return error.sentence ?? <code>{error.code}</code>;
      },
    });
  }
  return columns;
}

export interface ExecutorHostTasksProps {
  readonly roles: readonly Role[];
  /** Test seams: the group and the period the tab opens on, and the moment the period is counted from. */
  readonly initialGroup?: ExecutionQueueStateGroup | undefined;
  readonly initialPeriod?: TasksPeriod | undefined;
  readonly now?: Date | undefined;
}

export function ExecutorHostTasks({ roles, initialGroup, initialPeriod, now }: ExecutorHostTasksProps) {
  if (!mayReadHosts(roles)) {
    return <UnsupportedState title="Задачи недоступны" detail="Задачи показываются экспертам и администраторам." />;
  }
  return <TasksReads initialGroup={initialGroup ?? 'active'} initialPeriod={initialPeriod ?? DEFAULT_TASKS_PERIOD} now={now} />;
}

interface TasksReadsProps {
  readonly initialGroup: ExecutionQueueStateGroup;
  readonly initialPeriod: TasksPeriod;
  readonly now: Date | undefined;
}

/** The reads of the tab; mounted only for a role that may read the queue, so the viewer sends none. */
function TasksReads({ initialGroup, initialPeriod, now }: TasksReadsProps) {
  const [group, setGroup] = useState<ExecutionQueueStateGroup>(initialGroup);
  const [period, setPeriod] = useState<TasksPeriod>(initialPeriod);
  // The range of a period is taken when it is chosen (or the tab opened on it) and held: the filter, its cursors and its key do not slide.
  const range = useMemo(() => tasksPeriodRange(period, now ?? new Date()), [period, now]);
  const filter: ExecutionQueueFilter = group === 'completed' ? { stateGroup: group, ...range } : { stateGroup: group };
  const filterKey = `${group}|${group === 'completed' ? period : ''}`;
  const [paging, setPaging] = useState<{ readonly key: string; readonly cursors: readonly string[] }>({ key: filterKey, cursors: [] });
  const cursors = paging.key === filterKey ? paging.cursors : [];
  const setCursors = (update: (current: readonly string[]) => readonly string[]) => setPaging({ key: filterKey, cursors: update(cursors) });

  const list = useExecutionQueue(cursors.at(-1), filter);
  // The counts of the three groups are the whole queue's, whatever the period of the list below.
  const counts = useExecutionQueue();
  const failure = list.error === null ? null : executionFailure(list.error, false);
  const next = list.data?.page.next_cursor ?? null;
  const asOf = list.dataUpdatedAt > 0 ? list.dataUpdatedAt : null;
  const overview = counts.isError ? undefined : counts.data?.overview;

  return (
    <div className={styles.panel} data-hosts-tasks>
      <div className={styles.tasksBar}>
        <div role="group" aria-label="Задачи по состоянию" className={styles.tasksGroups} data-tasks-groups={group}>
          {QUEUE_STATE_GROUPS.map((entry) => {
            const count = groupCount(overview, entry.states);
            return (
              <button
                key={entry.key}
                type="button"
                className={entry.key === group ? 'am-button am-button--small' : 'am-button am-button--quiet am-button--small'}
                aria-pressed={entry.key === group}
                data-tasks-group={entry.key}
                data-tasks-count={count ?? ''}
                onClick={() => setGroup(entry.key)}
              >
                {count === null ? entry.label : `${entry.label} ${count}`}
              </button>
            );
          })}
        </div>
        <Link className="am-button am-button--quiet am-button--small" href={routes.queue()} data-tasks-open-queue>Открыть очередь</Link>
      </div>
      {group === 'completed' ? (
        <div role="group" aria-label="Период" className={styles.tasksPeriods} data-tasks-periods={period}>
          {TASKS_PERIODS.map((entry) => (
            <button
              key={entry.value}
              type="button"
              className={entry.value === period ? 'am-button am-button--small' : 'am-button am-button--quiet am-button--small'}
              aria-pressed={entry.value === period}
              data-tasks-period={entry.value}
              onClick={() => setPeriod(entry.value)}
            >
              {entry.label}
            </button>
          ))}
        </div>
      ) : null}
      <UpdateTime dataUpdatedAt={list.dataUpdatedAt} failed={list.isError} />
      {list.isPending ? <LoadingState what="задачи" /> : null}
      {failure === null ? null : (
        <div data-tasks-read-failure={failure.kind}>
          <ErrorState
            title={list.data === undefined ? 'Задачи не прочитаны' : 'Задачи не обновились'}
            detail={failure.detail}
            correlationId={failure.correlationId}
            onRetry={() => void list.refetch()}
          />
        </div>
      )}
      {list.data === undefined ? null : list.data.items.length === 0 && cursors.length === 0 ? (
        <EmptyState title={EMPTY_TITLES[group]} />
      ) : (
        <>
          <Table
            columns={columnsOf(group, asOf)}
            rows={list.data.items}
            rowKey={(item) => item.job_id}
          />
          <nav aria-label="Страницы задач" className={styles.tasksPages}>
            <button type="button" className="am-button am-button--quiet" disabled={cursors.length === 0} data-tasks-previous onClick={() => setCursors((current) => current.slice(0, -1))}>Назад</button>
            <button type="button" className="am-button am-button--quiet" disabled={next === null} data-tasks-next onClick={() => { if (next !== null) setCursors((current) => [...current, next]); }}>Далее</button>
          </nav>
        </>
      )}
    </div>
  );
}
