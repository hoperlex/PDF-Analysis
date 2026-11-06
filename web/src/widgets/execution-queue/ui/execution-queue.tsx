import Link from 'next/link';

import type { ExecutionQueueItem, Role, RunId } from '@/shared/api';
import { formatInstant, routes } from '@/shared/lib';
import {
  JobStateBadge, RunWorkerLine, canCancel, canExecute, canReaudit, jobHoldsLease, jobStateLabel, queueAgeLabel, queueItemError,
} from '@/entities/execution';
import type { RunWorker } from '@/entities/execution';
import { QueueItemWaiting } from '@/entities/audit-run';
import { EmptyState, ErrorState } from '@/shared/ui';

import { queueTiming } from '../model/timing';

import styles from './execution-queue.module.css';

export interface ExecutionQueueProps {
  readonly items: readonly ExecutionQueueItem[];
  readonly roles: readonly Role[];
  readonly asOf: number | null;
  readonly busy: boolean;
  /**
   * True while a state filter narrows the list. An empty answer then says that no job matches, not that
   * the queue is empty.
   */
  readonly filtered?: boolean;
  /**
   * Who holds a run (`W54-WORKERS-WEB`), asked only for a row whose Job holds a Lease
   * (`leased`, `running`); a queued or finished Job has no worker to name.
   */
  readonly workerOf: (runId: RunId) => RunWorker;
  readonly onCancel: (item: ExecutionQueueItem) => void;
  readonly onReaudit: (item: ExecutionQueueItem) => void;
  readonly onPriority: (item: ExecutionQueueItem, priority: number) => void;
  readonly onNext: (() => void) | null;
  readonly onPrevious: (() => void) | null;
}

/**
 * The original's queue line «ЧЧ:ММ → ЧЧ:ММ · длительность» (UTC, like every instant here). A job that never started and
 * never finished prints nothing: its place and age say the rest. The exact instants are in the tooltips.
 */
function QueueTimingLine({ item, asOf }: { readonly item: ExecutionQueueItem; readonly asOf: number | null }) {
  const timing = queueTiming(item, asOf);
  if (timing === null) return null;
  return (
    <span className={styles.timing} data-queue-timing={timing.duration ?? ''}>
      {item.started_at === undefined
        ? '—'
        : <time dateTime={item.started_at} title={`Начат: ${formatInstant(item.started_at)}`} data-queue-started>{timing.start}</time>}
      {' → '}
      {item.finished_at === undefined
        ? <span data-queue-finished="">…</span>
        : <time dateTime={item.finished_at} title={`Завершён: ${formatInstant(item.finished_at)}`} data-queue-finished>{timing.end}</time>}
      {' UTC'}
      {timing.duration === null ? null : ` · ${timing.duration}`}
    </span>
  );
}

export function ExecutionQueue({
  items, roles, asOf, busy, filtered = false, workerOf, onCancel, onReaudit, onPriority, onNext, onPrevious,
}: ExecutionQueueProps) {
  if (items.some((item) => jobStateLabel(item.state) === null)) {
    return <ErrorState title="Неизвестное состояние задачи" detail="Очередь содержит состояние вне набора, который умеет показывать это приложение." />;
  }
  if (items.length === 0 && onPrevious === null) {
    return filtered
      ? <EmptyState title="Задач в этом состоянии нет" detail="Выберите другое состояние или период, либо покажите все задачи." />
      : <EmptyState title="Очередь пуста" detail="Принятые прогоны появятся здесь." />;
  }
  return (
    <section aria-label="Задачи выполнения" className={styles.list}>
      {items.length === 0 ? <EmptyState title="На этой странице задач нет" detail="Вернитесь к предыдущей странице." /> : null}
      <ol>
        {items.map((item) => {
          const error = queueItemError(item);
          const mayCancel = canExecute(roles, 'cancel') && canCancel(item);
          const mayReaudit = canExecute(roles, 'reaudit') && canReaudit(item);
          const mayPrioritise = canExecute(roles, 'priority') && item.state === 'queued';
          return (
          <li key={item.job_id} className={styles.row} data-queue-row={item.state}>
            {/* One line as the original's queue item: state, place, the work, its times; the rest of the facts under it. */}
            <div className={styles.line}>
              <JobStateBadge state={item.state} />
              {/* `UI-PARITY-P0M`: a queued job's place in the dispatcher's order, as the original numbers its queue. */}
              {item.queue_position === undefined ? null : <span data-queue-position={item.queue_position}>№ {item.queue_position} в очереди</span>}
              {/* `UI-PARITY-QUEUE-A`: what the job executes, read from the server and never from a screen's memory. */}
              <span className={styles.work} data-queue-work>
                <Link href={routes.project(item.project_uid)}>{item.project_name}</Link>
                {' · '}
                <Link href={routes.document(item.project_uid, item.document_uid)}>{item.document_name}</Link>
                {' · '}
                <Link href={routes.version(item.project_uid, item.version_uid)}>{`Версия ${item.version_ordinal}`}</Link>
              </span>
              <QueueTimingLine item={item} asOf={asOf} />
              <span className={styles.priority}>Приоритет: {item.priority}</span>
            </div>
            <QueueItemWaiting item={item} />
            {jobHoldsLease(item.state) ? <div className={styles.identity}><RunWorkerLine worker={workerOf(item.run_id)} /></div> : null}
            {/* The job's identities and times as one running line of facts, as many to a line as the panel holds. */}
            <p className={styles.facts}>
              <span className={styles.identity}>
                Прогон <a href={routes.logs(item.run_id)}><code>{item.run_id}</code></a>
                {' '}(<Link href={routes.run(item.project_uid, item.run_id)}>Открыть прогон</Link>)
              </span>
              <span className={styles.identity}>Задача <code>{item.job_id}</code></span>
              <span>Принята: <time dateTime={item.created_at}>{formatInstant(item.created_at)}</time></span>
              {/* `R-151v`: who started the run, as the original's queue says; older runs do not know. */}
              <span data-queue-started-by>Запустил: {item.started_by_label ?? 'неизвестно'}</span>
              <span>Возраст: {queueAgeLabel(item.created_at, asOf)}</span>
              {item.attempt_count === undefined ? null : <span data-queue-attempts={item.attempt_count}>Попыток: {item.attempt_count}</span>}
              <span>Доступна: <time dateTime={item.available_at}>{formatInstant(item.available_at)}</time></span>
              {item.estimated_finish_at === undefined ? null : (
                // `R-151u`: from similar past runs; never shown without enough history.
                <span data-queue-eta>
                  Ожидаемое завершение: ≈ <time dateTime={item.estimated_finish_at}>{formatInstant(item.estimated_finish_at)}</time>
                </span>
              )}
            </p>
            {error === null ? null : (
              <p role="status" data-queue-error={error.code}>
                Ошибка: <code>{error.code}</code>{error.sentence === null ? null : <> — {error.sentence}</>}
              </p>
            )}
            {item.interrupted_reason === undefined ? null : (
              <p data-queue-interrupted={item.interrupted_reason}>
                Прогон был прерван: <code>{item.interrupted_reason}</code>
              </p>
            )}
            {mayCancel || mayReaudit || mayPrioritise ? (
            <div className={styles.actions}>
              {mayCancel ? (
                <button className="am-button am-button--quiet am-button--small" type="button" disabled={busy} onClick={() => onCancel(item)}>Отменить прогон</button>
              ) : null}
              {mayReaudit ? (
                <button className="am-button am-button--quiet am-button--small" type="button" disabled={busy} onClick={() => onReaudit(item)}>Повторный аудит</button>
              ) : null}
              {mayPrioritise ? (
                <form onSubmit={(event) => {
                  event.preventDefault();
                  const value = Number(new FormData(event.currentTarget).get('priority'));
                  if (Number.isInteger(value) && value >= -100 && value <= 100) onPriority(item, value);
                }}>
                  <label>Приоритет
                    <input name="priority" type="number" min="-100" max="100" step="1" defaultValue={item.priority} required />
                  </label>
                  <button className="am-button am-button--quiet am-button--small" type="submit" disabled={busy}>Изменить</button>
                </form>
              ) : null}
            </div>
            ) : null}
          </li>
          );
        })}
      </ol>
      <nav aria-label="Страницы очереди" className={styles.actions}>
        <button type="button" className="am-button am-button--quiet" disabled={onPrevious === null} onClick={onPrevious ?? undefined}>Назад</button>
        <button type="button" className="am-button am-button--quiet" disabled={onNext === null} onClick={onNext ?? undefined}>Далее</button>
      </nav>
    </section>
  );
}
