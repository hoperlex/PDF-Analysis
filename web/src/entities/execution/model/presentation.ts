import type { ExecutionJournalEntry, ExecutionQueueItem, Role, RunState } from '@/shared/api';
import { ERROR_CODE_VALUES, RUN_STATE_VALUES } from '@/shared/api';
import { STATE_LABELS } from '@/shared/ui';

export type ExecutionAction = 'cancel' | 'reaudit' | 'priority' | 'pause';

/** A visible control is only a hint; the server still checks every write. */
export function canExecute(roles: readonly Role[], action: ExecutionAction): boolean {
  return action === 'priority' || action === 'pause'
    ? roles.includes('admin')
    : roles.includes('admin') || roles.includes('expert');
}

export function canCancel(item: ExecutionQueueItem): boolean {
  return ['queued', 'leased', 'running', 'retry_wait'].includes(item.state);
}

export function canReaudit(item: ExecutionQueueItem): boolean {
  return ['succeeded', 'failed', 'cancelled', 'dead_letter'].includes(item.state);
}

const JOB_STATE_LABELS: Readonly<Record<string, string>> = {
  queued: 'Ожидает',
  leased: 'Назначена',
  running: 'Выполняется',
  retry_wait: 'Ожидает повтора',
  succeeded: 'Завершена',
  failed: 'Ошибка',
  cancelled: 'Отменена',
  dead_letter: 'Остановлена после повторов',
};

export function jobStateLabel(state: string): string | null {
  return JOB_STATE_LABELS[state] ?? null;
}

export function queueAgeLabel(createdAt: string, asOf: number | null): string {
  if (asOf === null) return '—';
  const started = Date.parse(createdAt);
  if (!Number.isFinite(started)) return '—';
  const minutes = Math.max(0, Math.floor((asOf - started) / 60_000));
  if (minutes < 1) return 'Меньше минуты';
  if (minutes < 60) return `${minutes} мин`;
  return `${Math.floor(minutes / 60)} ч ${minutes % 60} мин`;
}

const EVENT_LABELS: Readonly<Record<string, string>> = {
  'audit_run.created': 'Прогон создан',
  'audit_run.transition': 'Состояние прогона',
  'job.created': 'Задача создана',
  'job.transition': 'Состояние задачи',
  'job.priority_changed': 'Приоритет изменён',
  'attempt.created': 'Попытка создана',
  'attempt.transition': 'Состояние попытки',
  'stage.started': 'Этап начат',
  'stage.finished': 'Этап завершён',
  'provider.prepared': 'Вызов подготовлен',
  'provider.response_received': 'Ответ получен',
  'provider.not_processed': 'Вызов не обработан',
  'provider.outcome_unknown': 'Исход вызова неизвестен',
  'provider.completed': 'Вызов завершён',
};

/**
 * Render a closed projection of the sealed journal. A new server field, even one in
 * payload, cannot become visible merely because it was added to an API response.
 */
export function visibleJournal(entry: ExecutionJournalEntry): {
  event: string;
  state: string | null;
  code: string | null;
} {
  const payload = entry.payload;
  const rawState = payload.to_state ?? payload.state;
  const state = entry.aggregate_type === 'AuditRun' &&
    typeof rawState === 'string' && (RUN_STATE_VALUES as readonly string[]).includes(rawState)
    ? STATE_LABELS[rawState as RunState]
    : typeof rawState === 'string' ? jobStateLabel(rawState) : null;
  const code = typeof payload.error_code === 'string' &&
    (ERROR_CODE_VALUES as readonly string[]).includes(payload.error_code)
    ? payload.error_code : null;
  return { event: EVENT_LABELS[entry.event_type] ?? 'Другое событие выполнения', state, code };
}
