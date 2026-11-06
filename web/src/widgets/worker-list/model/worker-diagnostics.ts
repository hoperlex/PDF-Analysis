/**
 * The text «Скопировать диагностику» puts on the clipboard for a worker (`UI-B-68`): its state, as
 * the row prints it.
 *
 * Exactly the facts the row shows -- the worker's identity, state, whether it takes new runs, its
 * slots and version, when it started and last answered, and the runs it holds. The registry carries
 * nothing else, and no token or key belongs to a worker's record, so there is nothing to leave out;
 * the function takes the worker alone, so nothing else can be added to it by accident. Pure: nothing
 * is requested.
 */

import type { ExecutionWorker } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import { workerIntakeLabel, workerStateLabel } from '@/entities/execution';

export function workerDiagnosticText(worker: ExecutionWorker): string {
  return [
    'Диагностика исполнителя',
    `Исполнитель: ${worker.worker_id}`,
    // A state outside the set is not printed as a machine value: the list refuses such a page before a row is drawn.
    `Состояние: ${workerStateLabel(worker.state) ?? 'неизвестное состояние'}`,
    `Приём: ${workerIntakeLabel(worker.intake_enabled)}`,
    `Слотов: ${worker.slots}`,
    `Версия: ${worker.version}`,
    `Запущен: ${formatInstant(worker.started_at)}`,
    `Последний сигнал: ${formatInstant(worker.heartbeat_at)}`,
    `Текущие прогоны: ${worker.current_run_ids.length === 0 ? 'нет' : worker.current_run_ids.join(', ')}`,
  ].join('\n');
}
