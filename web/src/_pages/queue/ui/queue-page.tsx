'use client';

import { useMemo, useRef, useState } from 'react';
import Link from 'next/link';

import type { ExecutionQueueItem, RunStatus } from '@/shared/api';
import { ApiError, newIdempotencyKey } from '@/shared/api';
import { routes, useAddressState } from '@/shared/lib';
import { useMe } from '@/entities/account';
import {
  QUEUE_STATE_OPTIONS, UpdateTime, canExecute, executionFailure, jobHoldsLease, queueOverviewLine, queueStateCount,
  runWorker, useExecutionQueue,
  useWorkerLookup,
} from '@/entities/execution';
import type { ExecutionFailure, ExecutionQueueFilter } from '@/entities/execution';
import { useCancelRun } from '@/features/cancel-run';
import { useReauditCostApproval, useReauditRun } from '@/features/reaudit-run';
import { useSetJobPriority } from '@/features/set-job-priority';
import { usePauseExecution } from '@/features/pause-execution';
import { ComparisonQueueBlock, ExecutionQueue } from '@/widgets/execution-queue';
import { CostApproval, ErrorState, LoadingState, PageShell, UnsupportedState } from '@/shared/ui';
import { EMPTY_QUEUE_ADDRESS, readQueueAddress, writeQueueAddress } from '../model/address';
import type { QueueAddress } from '../model/address';
import { QUEUE_PERIOD_OPTIONS, isQueuePeriod, queuePeriodStart } from '../model/period';
import type { QueuePeriod } from '../model/period';
import styles from './queue-page.module.css';

interface RunIntent {
  readonly kind: 'cancel' | 'reaudit';
  readonly item: ExecutionQueueItem;
  readonly key: string;
}

interface PriorityIntent {
  readonly kind: 'priority';
  readonly item: ExecutionQueueItem;
  readonly priority: number;
  readonly key: string;
}

interface PauseIntent {
  readonly kind: 'pause';
  readonly paused: boolean;
  readonly key: string;
}

type Intent = RunIntent | PriorityIntent | PauseIntent;
type NewIntent =
  | { readonly kind: 'cancel' | 'reaudit'; readonly item: ExecutionQueueItem }
  | { readonly kind: 'priority'; readonly item: ExecutionQueueItem; readonly priority: number }
  | { readonly kind: 'pause'; readonly paused: boolean };

export function intentLabel(intent: Intent): string {
  switch (intent.kind) {
    case 'cancel': return `Отменить прогон ${intent.item.run_id}?`;
    case 'reaudit': return `Начать повторный аудит прогона ${intent.item.run_id}?`;
    case 'priority': return `Установить приоритет ${intent.priority} для прогона ${intent.item.run_id}?`;
    case 'pause': return intent.paused ? 'Приостановить выдачу задач?' : 'Возобновить выдачу задач?';
  }
}

export interface QueuePageProps {
  /**
   * The filter the address named, read on the server by the route, so the first read of the queue is already the filtered one.
   * Inside the app router the address itself is the source and this is what it said; a static render starts from it.
   */
  readonly initialAddress?: QueueAddress | undefined;
}

export function QueuePage({ initialAddress = EMPTY_QUEUE_ADDRESS }: QueuePageProps = {}) {
  // The state and the period are in the address (`?state=&period=`), so a link opens the queue filtered, a reload keeps the filter and
  // the side menu's «Очередь» (no query) clears it. A choice REPLACES the entry: a filter is not a place to go Back to.
  const [address, setAddress] = useAddressState(readQueueAddress, writeQueueAddress, initialAddress);
  const stateFilter = address.state;
  const filterKey = `${address.state}|${address.period}`;
  // A cursor belongs to the filter it was issued under (the server refuses it under another), so the pages walked are held with
  // the filter they were walked under and forgotten when the filter is anything else -- including a change the address made.
  const [paging, setPaging] = useState<{ readonly key: string; readonly cursors: readonly string[] }>({ key: filterKey, cursors: [] });
  const cursors = paging.key === filterKey ? paging.cursors : [];
  const setCursors = (update: readonly string[] | ((current: readonly string[]) => readonly string[])) => {
    setPaging({ key: filterKey, cursors: typeof update === 'function' ? update(cursors) : update });
  };
  // The instant the period begins at, taken when the period is chosen (or the page opened on it) and held: the filter, its cursors
  // and its cache key do not slide under a person who is reading a page.
  const periodFrom = useMemo(() => queuePeriodStart(address.period, new Date()), [address.period]);
  const period = { value: address.period, from: periodFrom };
  const [intent, setIntent] = useState<Intent | null>(null);
  const [commandFailure, setCommandFailure] = useState<ExecutionFailure | null>(null);
  const [lastRun, setLastRun] = useState<RunStatus | null>(null);
  const [completed, setCompleted] = useState(false);
  const sequence = useRef(0);
  const cursor = cursors.at(-1);
  const filter: ExecutionQueueFilter = {
    ...(stateFilter === '' ? {} : { state: stateFilter }),
    ...(period.from === undefined ? {} : { createdFrom: period.from }),
  };
  const queue = useExecutionQueue(cursor, filter);
  // `W54-WORKERS-WEB`: the worker registry is read only while a listed Job holds a Lease.
  const holdsLease = queue.data?.items.some((item) => jobHoldsLease(item.state)) ?? false;
  const workers = useWorkerLookup(holdsLease);
  const account = useMe();
  const cancel = useCancelRun();
  const reaudit = useReauditRun();
  const reauditCost = useReauditCostApproval(intent?.kind === 'reaudit' ? intent.item.run_id : null,
    intent?.kind === 'reaudit' ? intent.key : null);
  const priority = useSetJobPriority();
  const pause = usePauseExecution();
  const busy = cancel.isPending || reaudit.isPending || priority.isPending || pause.isPending;
  const roles = account.data?.roles ?? [];
  const readFailure = queue.error === null ? null : executionFailure(queue.error, false);
  const accountFailure = account.error === null ? null : executionFailure(account.error, false);
  const next = queue.data?.page.next_cursor ?? null;
  // Row ages are measured at the last successful read, so they never claim a moment the data
  // does not describe. `0` means no read has succeeded yet.
  const asOf = queue.dataUpdatedAt > 0 ? queue.dataUpdatedAt : null;
  const costFailure = reauditCost.error === null ? null : executionFailure(reauditCost.error, false);

  function chooseState(next: string) {
    const known = QUEUE_STATE_OPTIONS.find((option) => option.value === next);
    setAddress({ state: known === undefined ? '' : known.value, period: address.period }, 'replace');
  }

  function choosePeriod(chosen: string) {
    const value: QueuePeriod = isQueuePeriod(chosen) ? chosen : 'all';
    setAddress({ state: address.state, period: value }, 'replace');
  }

  function select(nextIntent: NewIntent) {
    sequence.current += 1;
    setIntent({ ...nextIntent, key: newIdempotencyKey() });
    setCommandFailure(null);
    setCompleted(false);
    setLastRun(null);
  }

  async function execute(chosen: Intent) {
    const mine = sequence.current;
    try {
      let run: RunStatus | null = null;
      switch (chosen.kind) {
        case 'cancel': run = await cancel.mutateAsync({ runId: chosen.item.run_id, idempotencyKey: chosen.key }); break;
        case 'reaudit': {
          if (reauditCost.consent === undefined || reauditCost.pending) return;
          run = await reaudit.mutateAsync({ runId: chosen.item.run_id,
            idempotencyKey: reauditCost.idempotencyKey, costConsent: reauditCost.consent });
          break;
        }
        case 'priority': await priority.mutateAsync({
          jobId: chosen.item.job_id, priority: chosen.priority,
          idempotencyKey: chosen.key,
        }); break;
        case 'pause': await pause.mutateAsync({ paused: chosen.paused, idempotencyKey: chosen.key }); break;
      }
      if (mine !== sequence.current) return;
      setLastRun(run);
      setCommandFailure(null);
      setCompleted(true);
      setIntent(null);
      setCursors([]);
    } catch (error) {
      if (mine !== sequence.current) return;
      if (chosen.kind === 'reaudit' && error instanceof ApiError && error.details?.conflict_reason === 'run_cost_estimate_stale') {
        reauditCost.clear();
        setCommandFailure({ kind: 'conflict', detail: 'Оценка стоимости устарела. Получите новую оценку и подтвердите лимит снова.', correlationId: error.correlationId });
        setCompleted(false);
        return;
      }
      setCommandFailure(executionFailure(error, true));
      setCompleted(false);
    }
  }

  return (
    <PageShell
      title="Очередь"
      subtitle="Устойчивые задачи прогонов. Данные обновляются автоматически, пока вкладка открыта, и по запросу."
      actions={(
        <>
          {/* The original's «+ Добавить проекты»: work enters the queue from a project's documents, so the way there is one click. */}
          <Link href={routes.projects()} title="Выберите проект и запустите аудит его документов" data-queue-add>+ Добавить проекты</Link>
          <button className="am-button am-button--quiet" type="button" onClick={() => { void queue.refetch(); if (holdsLease) void workers.refetch(); }}>Обновить</button>
        </>
      )}
    >
      <UpdateTime dataUpdatedAt={queue.dataUpdatedAt} failed={queue.isError} />
      <div className={styles.toolbar}>
        <label>
          Состояние задачи{' '}
          <select
            name="queue-state"
            data-queue-state-filter
            value={stateFilter}
            onChange={(event) => chooseState(event.currentTarget.value)}
          >
            <option value="">Все состояния</option>
            {QUEUE_STATE_OPTIONS.map((option) => {
              // `UI-PARITY-P0M`: each state with its count, so the filter says what it would list.
              const count = queueStateCount(queue.data?.overview, option.value);
              return <option key={option.value} value={option.value}>{count === null ? option.label : `${option.label} (${count})`}</option>;
            })}
          </select>
        </label>
        <label>
          Период{' '}
          <select name="queue-period" data-queue-period-filter value={period.value} onChange={(event) => choosePeriod(event.currentTarget.value)}>
            {QUEUE_PERIOD_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        {queueOverviewLine(queue.data?.overview) === null ? null : (
          <span className="am-note" data-queue-overview>{queueOverviewLine(queue.data?.overview)}</span>
        )}
        {account.data !== undefined && canExecute(roles, 'pause') && queue.data !== undefined ? (
          <button
            type="button"
            className="am-button am-button--quiet am-button--small"
            disabled={busy}
            onClick={() => select({ kind: 'pause', paused: !queue.data.paused })}
          >
            {queue.data.paused ? 'Возобновить выдачу' : 'Приостановить выдачу'}
          </button>
        ) : null}
      </div>
      {queue.data?.paused === true ? <p role="status" className="am-note" data-execution-paused>Выдача задач приостановлена.</p> : null}
      {account.isPending ? <LoadingState what="права на управление очередью" /> : null}
      {accountFailure !== null ? (
        <div data-execution-account-failure={accountFailure.kind}>
          <p role="status" className="am-note" data-execution-controls-withheld>Очередь показана без команд: права не прочитаны.</p>
          <ErrorState title="Права не прочитаны" detail={accountFailure.detail} correlationId={accountFailure.correlationId} onRetry={() => void account.refetch()} />
        </div>
      ) : null}
      {queue.isPending ? <LoadingState what="очередь" /> : null}
      {/*
        * A failed read with no data is «не открылась». A failed read after a successful one keeps
        * the last page on screen under the stale line (`UpdateTime`), because a periodic read
        * that blinked must not erase the queue; the failure is still said, never swallowed.
        */}
      {readFailure !== null ? <div data-execution-read-failure={readFailure.kind}><ErrorState title={queue.data === undefined ? 'Очередь не открылась' : 'Очередь не обновилась'} detail={readFailure.detail} correlationId={readFailure.correlationId} onRetry={() => void queue.refetch()} /></div> : null}
      {/*
        * `C-27`: every complete account may read the queue, so its rows do not wait for
        * `getMe`. Until the roles are read — or when that read fails — `roles` is empty and
        * the widget draws no command; the server refuses a command by role anyway.
        */}
      {queue.data !== undefined ? (
        <div className={styles.panel}>
          <ExecutionQueue
            items={queue.data.items}
            roles={roles}
            asOf={asOf}
            busy={busy}
            filtered={stateFilter !== '' || period.from !== undefined}
            workerOf={(runId) => runWorker(workers.data, workers.error !== null, runId)}
            onCancel={(item) => select({ kind: 'cancel', item })}
            onReaudit={(item) => select({ kind: 'reaudit', item })}
            onPriority={(item, value) => select({ kind: 'priority', item, priority: value })}
            onPrevious={cursors.length === 0 ? null : () => setCursors((current) => current.slice(0, -1))}
            onNext={next === null ? null : () => setCursors((current) => [...current, next])}
          />
        </div>
      ) : null}
      <div className={styles.panel}>
        <ComparisonQueueBlock />
      </div>
      {intent !== null ? (
        <section className={styles.intent} role="group" aria-label="Подтверждение команды выполнения" data-execution-intent={intent.kind}>
          <p>{intentLabel(intent)}</p>
          {intent.kind === 'reaudit' ? <>
            <p className="am-note">Повторный аудит требует новой оценки и согласия. Исполнителя и текущие параметры определяет сервер по исходному прогону.</p>
            {reauditCost.pending ? <LoadingState what="стоимость повторного аудита" /> : null}
            {costFailure === null ? null : <ErrorState title="Стоимость повторного аудита не оценена" detail={costFailure.detail} correlationId={costFailure.correlationId} />}
            {reauditCost.estimate === null ? null : <CostApproval estimate={reauditCost.estimate} ceiling={reauditCost.ceiling}
              approved={reauditCost.approved} disabled={busy || reauditCost.pending}
              onCeilingChange={reauditCost.setCeiling} onApprovedChange={reauditCost.setApproved} />}
            <button type="button" className="am-button am-button--quiet" disabled={busy || reauditCost.pending}
              onClick={() => { setCommandFailure(null); reauditCost.refresh(); }}>Обновить оценку стоимости</button>
          </> : null}
          <button type="button" className="am-button" disabled={busy || (intent.kind === 'reaudit' && (reauditCost.pending || reauditCost.consent === undefined)) || (commandFailure !== null && commandFailure.kind !== 'unknown_outcome')} onClick={() => void execute(intent)}>
            {commandFailure?.kind === 'unknown_outcome' ? 'Повторить с тем же ключом' : 'Подтвердить'}
          </button>{' '}
          <button type="button" className="am-button am-button--quiet" disabled={busy} onClick={() => { sequence.current += 1; setIntent(null); setCommandFailure(null); }}>Отмена</button>
        </section>
      ) : null}
      {commandFailure !== null ? (
        <div data-execution-action-failure={commandFailure.kind}>
          {commandFailure.kind === 'permission' || commandFailure.kind === 'transition' || commandFailure.kind === 'conflict' ? (
            <UnsupportedState title="Команда отклонена" detail={commandFailure.kind === 'transition' && intent?.kind === 'cancel' ? 'Текущее состояние сохранено. Отмена на этапе проверки недоступна.' : commandFailure.detail} />
          ) : (
            <ErrorState title={commandFailure.kind === 'unknown_outcome' ? 'Исход команды неизвестен' : 'Команда не выполнена'} detail={commandFailure.detail} correlationId={commandFailure.correlationId} />
          )}
          {['permission', 'transition', 'conflict'].includes(commandFailure.kind) &&
          commandFailure.correlationId !== null
            ? <p>Идентификатор корреляции <code>{commandFailure.correlationId}</code></p>
            : null}
        </div>
      ) : null}
      {completed ? <p role="status" className="am-note">Команда выполнена.</p> : null}
      {lastRun !== null ? <p><Link href={routes.run(lastRun.project_uid, lastRun.run_id)}>Открыть прогон {lastRun.run_id}</Link></p> : null}
    </PageShell>
  );
}
