import Link from 'next/link';

import type { ExecutionQueueItem, Role, RunId } from '@/shared/api';
import { formatInstant, routes } from '@/shared/lib';
import {
  RunWorkerLine, canCancel, canExecute, canReaudit, jobHoldsLease, jobStateLabel, queueAgeLabel, queueItemError,
} from '@/entities/execution';
import type { RunWorker } from '@/entities/execution';
import { QueueItemWaiting } from '@/entities/audit-run';
import { EmptyState, ErrorState } from '@/shared/ui';

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

export function ExecutionQueue({
  items, roles, asOf, busy, filtered = false, workerOf, onCancel, onReaudit, onPriority, onNext, onPrevious,
}: ExecutionQueueProps) {
  if (items.some((item) => jobStateLabel(item.state) === null)) {
    return <ErrorState title="Неизвестное состояние задачи" detail="Очередь содержит состояние вне набора, который умеет показывать это приложение." />;
  }
  if (items.length === 0 && onPrevious === null) {
    return filtered
      ? <EmptyState title="Задач в этом состоянии нет" detail="Выберите другое состояние или покажите все задачи." />
      : <EmptyState title="Очередь пуста" detail="Принятые прогоны появятся здесь." />;
  }
  return (
    <section aria-label="Задачи выполнения" className={styles.list}>
      {items.length === 0 ? <EmptyState title="На этой странице задач нет" detail="Вернитесь к предыдущей странице." /> : null}
      <ol>
        {items.map((item) => {
          const error = queueItemError(item);
          return (
          <li key={item.job_id} className={styles.row}>
            <div className={styles.heading}>
              <strong>{jobStateLabel(item.state)}</strong>
              <span>Приоритет: {item.priority}</span>
            </div>
            {/* `UI-PARITY-QUEUE-A`: what the job executes, read from the server and never from a screen's memory. */}
            <p className={styles.work} data-queue-work>
              <Link href={routes.project(item.project_uid)}>{item.project_name}</Link>
              {' · '}
              <Link href={routes.document(item.project_uid, item.document_uid)}>{item.document_name}</Link>
              {' · '}
              <Link href={routes.version(item.project_uid, item.version_uid)}>{`Версия ${item.version_ordinal}`}</Link>
            </p>
            <p className={styles.identity}>
              Прогон <a href={routes.logs(item.run_id)}><code>{item.run_id}</code></a>
              {' · '}
              <Link href={routes.run(item.project_uid, item.run_id)}>Открыть прогон</Link>
            </p>
            <p className={styles.identity}>Задача <code>{item.job_id}</code></p>
            <QueueItemWaiting item={item} />
            {jobHoldsLease(item.state) ? <div className={styles.identity}><RunWorkerLine worker={workerOf(item.run_id)} /></div> : null}
            <p>Принята: <time dateTime={item.created_at}>{formatInstant(item.created_at)}</time></p>
            <p>Возраст: {queueAgeLabel(item.created_at, asOf)}</p>
            <p>Доступна: <time dateTime={item.available_at}>{formatInstant(item.available_at)}</time></p>
            <p data-queue-started>
              Начат: {item.started_at === undefined
                ? '—'
                : <time dateTime={item.started_at}>{formatInstant(item.started_at)}</time>}
            </p>
            <p data-queue-finished>
              Завершён: {item.finished_at === undefined
                ? '—'
                : <time dateTime={item.finished_at}>{formatInstant(item.finished_at)}</time>}
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
            <div className={styles.actions}>
              {canExecute(roles, 'cancel') && canCancel(item) ? (
                <button className="am-button am-button--quiet" type="button" disabled={busy} onClick={() => onCancel(item)}>Отменить прогон</button>
              ) : null}
              {canExecute(roles, 'reaudit') && canReaudit(item) ? (
                <button className="am-button am-button--quiet" type="button" disabled={busy} onClick={() => onReaudit(item)}>Повторный аудит</button>
              ) : null}
              {canExecute(roles, 'priority') && item.state === 'queued' ? (
                <form onSubmit={(event) => {
                  event.preventDefault();
                  const value = Number(new FormData(event.currentTarget).get('priority'));
                  if (Number.isInteger(value) && value >= -100 && value <= 100) onPriority(item, value);
                }}>
                  <label>Приоритет
                    <input name="priority" type="number" min="-100" max="100" step="1" defaultValue={item.priority} required />
                  </label>
                  <button className="am-button am-button--quiet" type="submit" disabled={busy}>Изменить</button>
                </form>
              ) : null}
            </div>
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
