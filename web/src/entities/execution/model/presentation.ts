import type { ExecutionJournalEntry, ExecutionQueueItem, ExecutionQueueStateCount, Role, RunState } from '@/shared/api';
import { ERROR_CODE_VALUES, RUN_STATE_VALUES } from '@/shared/api';
import { STATE_LABELS } from '@/shared/ui';
import { terminalReasonNote } from '@/entities/audit-run';

import type { ExecutionQueueState, ExecutionQueueStateGroup } from '../api/use-execution';

export type ExecutionAction = 'cancel' | 'reaudit' | 'priority' | 'pause' | 'intake' | 'connections';

/** A visible control is only a hint; the server still checks every write. */
export function canExecute(roles: readonly Role[], action: ExecutionAction): boolean {
  return action === 'priority' || action === 'pause' || action === 'intake' || action === 'connections'
    ? roles.includes('admin')
    : roles.includes('admin') || roles.includes('expert');
}

/**
 * Whether the top strip reads the pause state (the queue's and the vectors'): the roles the queue is open to. A viewer reads
 * neither (`R-150w`); the server refuses it, and this keeps the strip from asking.
 */
export function canSeePause(roles: readonly Role[]): boolean {
  return roles.includes('admin') || roles.includes('expert');
}

export function canCancel(item: ExecutionQueueItem): boolean {
  return ['queued', 'leased', 'running', 'retry_wait'].includes(item.state);
}

export function canReaudit(item: ExecutionQueueItem): boolean {
  return ['succeeded', 'failed', 'cancelled', 'dead_letter'].includes(item.state);
}

const JOB_STATE_LABELS: Readonly<Record<ExecutionQueueState, string>> = {
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
  return Object.prototype.hasOwnProperty.call(JOB_STATE_LABELS, state)
    ? JOB_STATE_LABELS[state as ExecutionQueueState]
    : null;
}

/**
 * The states the queue's filter offers, in the order a job passes through them and then ends. Typed against
 * the contract's own set (`ExecutionQueueState`), so a state the server adds stops this file compiling
 * instead of silently going unfilterable.
 */
export const QUEUE_STATE_OPTIONS: readonly { readonly value: ExecutionQueueState; readonly label: string }[] = [
  { value: 'queued', label: JOB_STATE_LABELS.queued },
  { value: 'leased', label: JOB_STATE_LABELS.leased },
  { value: 'running', label: JOB_STATE_LABELS.running },
  { value: 'retry_wait', label: JOB_STATE_LABELS.retry_wait },
  { value: 'succeeded', label: JOB_STATE_LABELS.succeeded },
  { value: 'failed', label: JOB_STATE_LABELS.failed },
  { value: 'cancelled', label: JOB_STATE_LABELS.cancelled },
  { value: 'dead_letter', label: JOB_STATE_LABELS.dead_letter },
];

/** A group of the original's task sub-tabs («Активные», «Завершённые», «Ошибки») over this queue's states. */
export interface QueueStateGroup {
  /** The group's name on the wire: `state_group` of `listExecutionQueue` (`D-370`), which the contract types. */
  readonly key: ExecutionQueueStateGroup;
  readonly label: string;
  readonly states: readonly ExecutionQueueState[];
}

/**
 * `UI-B-51`, `UI-B-69`: the original's three sub-tabs of the dispatcher's task list, over this queue's eight job states. A job that
 * waits for a worker, holds a lease, runs or waits to retry is **active**; one that ended without a failure (done, or cancelled by a
 * person) is **completed**; one that ended in failure, or stopped after its retries, is an **error**. Every state is in exactly one
 * group (a test holds it), so the group counts add up to the queue's total.
 *
 * A group is also a filter (`D-370`, contract 1.43.0): `listExecutionQueue` takes `state_group` and lists every job in any state of
 * the group, one paged and counted list. The server holds the same three sets (`execution.public.QUEUE_STATE_GROUPS`); a test here
 * and one there hold them equal, so a group's press lists exactly the jobs its counts add up.
 */
export const QUEUE_STATE_GROUPS: readonly QueueStateGroup[] = [
  { key: 'active', label: 'Активные', states: ['queued', 'leased', 'running', 'retry_wait'] },
  { key: 'completed', label: 'Завершённые', states: ['succeeded', 'cancelled'] },
  { key: 'errors', label: 'Ошибки', states: ['failed', 'dead_letter'] },
];

/** Why a queue row ended badly: the run's reason as the sentence the run screen gives it, or the bare code. */
export interface QueueItemError {
  /** The machine value, always shown beside the sentence so a person can quote it. */
  readonly code: string;
  /** The catalog sentence for the code; `null` when this client has none, and then only the code is shown. */
  readonly sentence: string | null;
}

/**
 * What a queue row says about failure, from `error_code` (the run's `terminal_reason`). Nothing is said for a
 * row without one; a code the client has no sentence for is shown as the code alone, never as a guess.
 */
export function queueItemError(item: Pick<ExecutionQueueItem, 'error_code'>): QueueItemError | null {
  // Widened on purpose: the type says the member is a catalogue code or absent, and a server one reseal
  // ahead of this client can send what the type cannot name (see `terminalReasonNote`).
  const code: string | null | undefined = item.error_code;
  if (code === undefined || code === null || code === '') return null;
  const note = terminalReasonNote(code);
  return { code, sentence: note.kind === 'described' ? note.sentence : null };
}

/**
 * `UI-PARITY-P0M` (contract 1.28.0): the queue's line of counts, as the original's «N / M» and «N ✓ M ✗»: every state
 * that has a job, in the queue's order, after the total. Counted over the period, not the state filter, so it says what
 * each choice of the filter would list.
 */
export function queueOverviewLine(overview: readonly ExecutionQueueStateCount[] | undefined): string | null {
  if (overview === undefined) return null;
  const total = overview.reduce((sum, entry) => sum + entry.count, 0);
  if (total === 0) return 'Задач нет.';
  const parts = overview.filter((entry) => entry.count > 0).map((entry) => `${JOB_STATE_LABELS[entry.state]} ${entry.count}`);
  return `Всего ${total}: ${parts.join(' · ')}`;
}

/** The count of one state in the overview, for the filter's option; `null` when the page carries no overview. */
export function queueStateCount(overview: readonly ExecutionQueueStateCount[] | undefined, state: ExecutionQueueState): number | null {
  return overview?.find((entry) => entry.state === state)?.count ?? (overview === undefined ? null : 0);
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
  // `EXEC-PAR-WEB-01`: written once when a start names its executor (`EXEC-PAR-START-01`).
  'audit_run.executor_chosen': 'Выбран исполнитель',
  'job.created': 'Задача создана',
  'job.transition': 'Состояние задачи',
  'job.priority_changed': 'Приоритет изменён',
  'attempt.created': 'Попытка создана',
  'attempt.transition': 'Состояние попытки',
  'stage.started': 'Этап начат',
  'stage.pdf_precheck': 'Проверка PDF перед анализом',
  'stage.progress': 'Ход этапа',
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
