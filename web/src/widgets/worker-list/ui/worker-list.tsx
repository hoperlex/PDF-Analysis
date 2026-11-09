/**
 * «Исполнители» — the worker registry (`W54-WORKERS-WEB`, plan §3.7).
 *
 * Online and stale workers first, offline ones collapsed below them. Each row says what the
 * worker is doing: its state, whether it takes new runs, its slots and version, when it
 * started and last answered, and the runs it holds now. The intake switch is drawn only for
 * an administrator, and pressing it only asks the page to confirm; the server still checks
 * every write. `UI-B-68`: each row carries «Скопировать диагностику», the row's facts as text for any role.
 */

import type { ExecutionWorker, Role } from '@/shared/api';
import { formatInstant, routes } from '@/shared/lib';
import {
  canExecute, groupWorkers, hasUnknownWorkerState, workerIntakeLabel, workerStateLabel,
} from '@/entities/execution';
import { EmptyState, ErrorState } from '@/shared/ui';

import { workerDiagnosticText } from '../model/worker-diagnostics';
import { CopyDiagnostics } from './copy-diagnostics';
import styles from './worker-list.module.css';

export interface WorkerListProps {
  readonly items: readonly ExecutionWorker[];
  readonly roles: readonly Role[];
  readonly busy: boolean;
  readonly onIntake: (worker: ExecutionWorker, enabled: boolean) => void;
  readonly onNext: (() => void) | null;
  readonly onPrevious: (() => void) | null;
}

/** The tone of a worker's state: the original's Online green, a silent one amber, Offline red. */
function workerTone(state: ExecutionWorker['state']): string {
  switch (state) {
    case 'online': return 'ok';
    case 'stale': return 'degraded';
    default: return 'failed';
  }
}

function WorkerRow({
  worker, roles, busy, onIntake,
}: { readonly worker: ExecutionWorker } & Pick<WorkerListProps, 'roles' | 'busy' | 'onIntake'>) {
  return (
    <li className={styles.row} data-worker-state={worker.state} data-worker-intake={worker.intake_enabled ? 'on' : 'off'}>
      {/* One line as the original's server card header: the state, what it takes, who it is, its slots and its last word. */}
      <div className={styles.line}>
        <span className={`am-badge am-badge--${workerTone(worker.state)}`}>
          <span className="am-badge__label">{workerStateLabel(worker.state)}</span>
        </span>
        <span>{workerIntakeLabel(worker.intake_enabled)}</span>
        <span className={styles.identity}>Исполнитель <code>{worker.worker_id}</code></span>
        <span>Слотов: {worker.slots}{worker.state === 'online' ? ` (занято ${worker.current_run_ids.length})` : ''}</span>
        <span className={styles.identity}>Версия: <code>{worker.version}</code></span>
        <span>Последний сигнал: <time dateTime={worker.heartbeat_at}>{formatInstant(worker.heartbeat_at)}</time></span>
        <span className={styles.quiet}>Запущен: <time dateTime={worker.started_at}>{formatInstant(worker.started_at)}</time></span>
      </div>
      <div className={styles.line}>
        {worker.current_run_ids.length === 0 ? (
          <span data-worker-runs="0">Текущих прогонов нет.</span>
        ) : (
          <span className={styles.identity} data-worker-runs={worker.current_run_ids.length}>
            Текущие прогоны:{' '}
            {worker.current_run_ids.map((runId, index) => (
              <span key={runId}>{index === 0 ? '' : ', '}<a href={routes.logs(runId)}><code>{runId}</code></a></span>
            ))}
          </span>
        )}
        {/* `UI-B-68`: the row's facts as text for a message to whoever looks after the worker; any role may copy what it reads. */}
        <span className={styles.end}>
          <CopyDiagnostics text={workerDiagnosticText(worker)} />
          {canExecute(roles, 'intake') ? (
            <button
              className="am-button am-button--quiet am-button--small"
              type="button"
              disabled={busy}
              onClick={() => onIntake(worker, !worker.intake_enabled)}
            >
              {worker.intake_enabled ? 'Не брать новые' : 'Разрешить'}
            </button>
          ) : null}
        </span>
      </div>
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
