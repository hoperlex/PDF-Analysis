/**
 * «Исполнители» — the worker registry (`W54-WORKERS-WEB`, plan §3.7).
 *
 * Online and stale workers first, offline ones collapsed below them. Each row says what the
 * worker is doing: its state, whether it takes new runs, its slots and version, when it
 * started and last answered, and the runs it holds now. The intake switch is drawn only for
 * an administrator, and pressing it only asks the page to confirm; the server still checks
 * every write.
 */

import type { ExecutionWorker, Role } from '@/shared/api';
import { formatInstant, routes } from '@/shared/lib';
import {
  canExecute, groupWorkers, hasUnknownWorkerState, workerIntakeLabel, workerStateLabel,
} from '@/entities/execution';
import { EmptyState, ErrorState } from '@/shared/ui';

import styles from './worker-list.module.css';

export interface WorkerListProps {
  readonly items: readonly ExecutionWorker[];
  readonly roles: readonly Role[];
  readonly busy: boolean;
  readonly onIntake: (worker: ExecutionWorker, enabled: boolean) => void;
  readonly onNext: (() => void) | null;
  readonly onPrevious: (() => void) | null;
}

function WorkerRow({
  worker, roles, busy, onIntake,
}: { readonly worker: ExecutionWorker } & Pick<WorkerListProps, 'roles' | 'busy' | 'onIntake'>) {
  return (
    <li className={styles.row} data-worker-state={worker.state} data-worker-intake={worker.intake_enabled ? 'on' : 'off'}>
      <div className={styles.heading}>
        <strong>{workerStateLabel(worker.state)}</strong>
        <span>{workerIntakeLabel(worker.intake_enabled)}</span>
      </div>
      <p className={styles.identity}>Исполнитель <code>{worker.worker_id}</code></p>
      <p>Слотов: {worker.slots}</p>
      <p className={styles.identity}>Версия: <code>{worker.version}</code></p>
      <p>Запущен: <time dateTime={worker.started_at}>{formatInstant(worker.started_at)}</time></p>
      <p>Последний сигнал: <time dateTime={worker.heartbeat_at}>{formatInstant(worker.heartbeat_at)}</time></p>
      {worker.current_run_ids.length === 0 ? (
        <p data-worker-runs="0">Текущих прогонов нет.</p>
      ) : (
        <div className={styles.identity} data-worker-runs={worker.current_run_ids.length}>
          <p>Текущие прогоны:</p>
          <ul className={styles.runs}>
            {worker.current_run_ids.map((runId) => (
              <li key={runId}><a href={routes.logs(runId)}><code>{runId}</code></a></li>
            ))}
          </ul>
        </div>
      )}
      {canExecute(roles, 'intake') ? (
        <div className={styles.actions}>
          <button
            className="am-button am-button--quiet"
            type="button"
            disabled={busy}
            onClick={() => onIntake(worker, !worker.intake_enabled)}
          >
            {worker.intake_enabled ? 'Не брать новые' : 'Разрешить'}
          </button>
        </div>
      ) : null}
    </li>
  );
}

export function WorkerList({ items, roles, busy, onIntake, onNext, onPrevious }: WorkerListProps) {
  if (hasUnknownWorkerState(items)) {
    return <ErrorState title="Неизвестное состояние исполнителя" detail="Список содержит состояние вне набора, который умеет показывать это приложение." />;
  }
  if (items.length === 0 && onPrevious === null) {
    return (
      <EmptyState
        title="Исполнителей нет"
        detail="Ни один исполнитель не зарегистрирован. Прогоны, которые выполняет само приложение, в этом списке не показываются."
      />
    );
  }
  const { active, offline } = groupWorkers(items);
  const row = (worker: ExecutionWorker) => (
    <WorkerRow key={worker.worker_id} worker={worker} roles={roles} busy={busy} onIntake={onIntake} />
  );
  return (
    <section aria-label="Исполнители" className={styles.list}>
      {items.length === 0 ? <EmptyState title="На этой странице исполнителей нет" detail="Вернитесь к предыдущей странице." /> : null}
      {items.length > 0 && active.length === 0 ? (
        <p role="status" className="am-note" data-workers-none-active>
          На этой странице нет исполнителей на связи.
        </p>
      ) : null}
      {active.length > 0 ? <ol data-worker-group="active">{active.map(row)}</ol> : null}
      {offline.length > 0 ? (
        <details className={styles.offline} data-worker-group="offline">
          <summary>Отключённые исполнители: {offline.length}</summary>
          <ol>{offline.map(row)}</ol>
        </details>
      ) : null}
      <nav aria-label="Страницы исполнителей" className={styles.actions}>
        <button type="button" className="am-button am-button--quiet" disabled={onPrevious === null} onClick={onPrevious ?? undefined}>Назад</button>
        <button type="button" className="am-button am-button--quiet" disabled={onNext === null} onClick={onNext ?? undefined}>Далее</button>
      </nav>
    </section>
  );
}
