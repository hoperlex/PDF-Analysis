/**
 * The two refusals a start meets because of the executor the person chose (`EXEC-PAR-WEB-01`,
 * over `EXEC-PAR-START-01`).
 *
 * A start that names `executor_connection_id` is refused before a run exists when that connection
 * cannot serve now — `503 dependency_unavailable`, `details.dependency: executor_connection` — or
 * when the id is not one the stand accepts — `422 validation_failed`, `details.field:
 * executor_connection_id`, with the `constraint` saying which. **An explicit choice is never
 * replaced**: the stand does not fall back to the standby, to another connection or to the route,
 * and neither does this wording. The failure says what happened, in the user's words, and offers
 * nothing in place of the choice; the control that shows it draws a retry under the same key when
 * the envelope says the failure is retryable, and nothing else.
 *
 * **The reason word.** `dependency_unavailable` declares only `dependency` as a safe detail key, so
 * the stand's reason (`archived`, `kind_not_served`, `not_probed`, `no_revision`) travels as the last
 * word of the screened message: «… cannot serve a run now (archived)». It is read only when the
 * message ends in one of those four words, and only to choose one of the sentences below; any other
 * message leaves the reason out. The text of the message itself is never shown (it is English) and
 * nothing else in it is read. If the catalog gains a detail key for the reason, this is the one
 * place to change.
 */

import type { ApiError } from '@/shared/api';

export type ExecutorRefusalKind = 'executor_unavailable' | 'executor_invalid';

export interface ExecutorRefusal {
  readonly kind: ExecutorRefusalKind;
  /** `unsupported` carries no retry: the same request is refused again until the choice changes. */
  readonly presentation: 'error' | 'unsupported';
  readonly title: string;
  readonly detail: string;
}

/** `details.dependency` of a refusal that names the chosen executor. */
export const EXECUTOR_DEPENDENCY = 'executor_connection';
/** `details.field` of a rejection of the chosen executor's identifier. */
export const EXECUTOR_FIELD = 'executor_connection_id';

/** Why the stand says a connection cannot serve, as a reason the person can act on. */
const UNAVAILABLE_REASONS: ReadonlyMap<string, string> = new Map([
  ['archived', 'подключение в архиве'],
  ['kind_not_served', 'этот стенд не обслуживает такой вид подключения'],
  ['not_probed', 'для текущих настроек и ключа нет успешной проверки'],
  ['no_revision', 'настройки подключения ещё не заданы'],
]);

const REASON_AT_END = new RegExp(`\\((${[...UNAVAILABLE_REASONS.keys()].join('|')})\\)\\s*$`);

/** What `details.constraint` says about a rejected identifier. */
const INVALID_CONSTRAINTS: ReadonlyMap<string, string> = new Map([
  ['unknown_connection', 'Такого исполнителя на стенде нет.'],
  ['pattern', 'Идентификатор выбранного исполнителя имеет неверный вид.'],
  ['kind_not_routable', 'Подключение такого вида не выполняет прогоны.'],
]);

const INVALID_UNSPECIFIED = 'Стенд не принял выбранного исполнителя.';

const NOT_REPLACED =
  'Вместо выбранного исполнителя прогон не запускается ни на каком другом.';

function reasonOf(message: string): string | null {
  const match = REASON_AT_END.exec(message);
  const word = match?.[1];
  return word === undefined ? null : (UNAVAILABLE_REASONS.get(word) ?? null);
}

/** The refusal an error is, or `null` for any other error. */
export function executorRefusal(error: ApiError): ExecutorRefusal | null {
  if (error.errorCode === 'dependency_unavailable' && error.details.dependency === EXECUTOR_DEPENDENCY) {
    const reason = reasonOf(error.envelope.message);
    return {
      kind: 'executor_unavailable',
      presentation: 'error',
      title: 'Выбранный исполнитель сейчас не может выполнить прогон.',
      detail:
        (reason === null ? '' : `Причина: ${reason}. `) +
        'Прогон не запущен, и ничего не применено частично. ' +
        `${NOT_REPLACED} ` +
        'Повтор использует тот же ключ идемпотентности и тот же выбор исполнителя.',
    };
  }
  if (error.errorCode === 'validation_failed' && error.details.field === EXECUTOR_FIELD) {
    const constraint = error.details.constraint;
    const known = typeof constraint === 'string' ? INVALID_CONSTRAINTS.get(constraint) : undefined;
    return {
      kind: 'executor_invalid',
      presentation: 'unsupported',
      title: 'Выбранный исполнитель не подходит для этого прогона.',
      detail:
        `${known ?? INVALID_UNSPECIFIED} Прогон не запущен. ${NOT_REPLACED} ` +
        'Повтор с тем же выбором получит тот же отказ.',
    };
  }
  return null;
}
