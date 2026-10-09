import type { ExecutionQueueItem, Role } from '@/shared/api';
import { formatInstant, routes } from '@/shared/lib';
import { canCancel, canExecute, canReaudit, jobStateLabel, queueAgeLabel } from '@/entities/execution';
import { EmptyState, ErrorState } from '@/shared/ui';

import styles from './execution-queue.module.css';

export interface ExecutionQueueProps {
  readonly items: readonly ExecutionQueueItem[];
  readonly roles: readonly Role[];
  readonly asOf: number | null;
  readonly busy: boolean;
  readonly onCancel: (item: ExecutionQueueItem) => void;
  readonly onReaudit: (item: ExecutionQueueItem) => void;
  readonly onPriority: (item: ExecutionQueueItem, priority: number) => void;
  readonly onNext: (() => void) | null;
  readonly onPrevious: (() => void) | null;
}

export function ExecutionQueue({
  items, roles, asOf, busy, onCancel, onReaudit, onPriority, onNext, onPrevious,
}: ExecutionQueueProps) {
  if (items.some((item) => jobStateLabel(item.state) === null)) {
    return <ErrorState title="Неизвестное состояние задачи" detail="Очередь содержит состояние вне набора, который умеет показывать это приложение." />;
  }
  if (items.length === 0 && onPrevious === null) {
    return <EmptyState title="Очередь пуста" detail="Принятые прогоны появятся здесь." />;
  }
  return (
    <section aria-label="Задачи выполнения" className={styles.list}>
      {items.length === 0 ? <EmptyState title="На этой странице задач нет" detail="Вернитесь к предыдущей странице." /> : null}
      <ol>
        {items.map((item) => (
          <li key={item.job_id} className={styles.row}>
            <div className={styles.heading}>
              <strong>{jobStateLabel(item.state)}</strong>
              <span>Приоритет: {item.priority}</span>
            </div>
            <p className={styles.identity}>Прогон <a href={routes.logs(item.run_id)}><code>{item.run_id}</code></a></p>
            <p className={styles.identity}>Задача <code>{item.job_id}</code></p>
            <p>Принята: <time dateTime={item.created_at}>{formatInstant(item.created_at)}</time></p>
            <p>Возраст: {queueAgeLabel(item.created_at, asOf)}</p>
            <p>Доступна: <time dateTime={item.available_at}>{formatInstant(item.available_at)}</time></p>
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
        ))}
      </ol>
      <nav aria-label="Страницы очереди" className={styles.actions}>
        <button type="button" className="am-button am-button--quiet" disabled={onPrevious === null} onClick={onPrevious ?? undefined}>Назад</button>
        <button type="button" className="am-button am-button--quiet" disabled={onNext === null} onClick={onNext ?? undefined}>Далее</button>
      </nav>
    </section>
  );
}
