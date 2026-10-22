/**
 * Refusals of the connection commands, worded (`EXEC-HTTP-01`).
 *
 * The catalogue's codes are few, so the connection commands refuse through the safe detail
 * keys the catalogue already allows: `validation_failed` names a `field` and a `constraint`,
 * `conflict` a `conflict_reason`, `dependency_unavailable` a `dependency`. The values are a
 * closed set the executors context chooses; each has a Russian sentence here, and a value this
 * table does not know falls back to the code's own catalogue sentence — never to the English
 * message of the server.
 */

import { ApiError } from '@/shared/api';
import { executionFailure } from '@/entities/execution';
import type { ExecutionFailure } from '@/entities/execution';

const FIELD_LABELS: Readonly<Record<string, string>> = {
  display_name: 'Название',
  kind: 'Вид подключения',
  base_url: 'Адрес',
  api_flavour: 'Формат запросов',
  transport: 'Способ связи',
  pin_id: 'Модель',
  gateway_model: 'Имя модели на шлюзе',
  billing: 'Тарификация',
  timeout_seconds: 'Время ожидания',
  max_parallel_calls: 'Параллельных вызовов',
  ssh_host: 'Узел SSH',
  ssh_port: 'Порт SSH',
  ssh_user: 'Пользователь SSH',
  ssh_profile: 'Профиль команды',
  host_key: 'Отпечаток узла',
  pull_client: 'Клиент',
  answer_deadline_seconds: 'Срок ответа',
  max_claimed_tasks: 'Заданий в работе',
  purpose: 'Назначение ключа',
  value: 'Ключ',
  work_kind: 'Вид работы',
  primary_connection_id: 'Основное подключение',
  standby_connection_id: 'Резервное подключение',
};

const CONSTRAINT_SENTENCES: Readonly<Record<string, string>> = {
  base_url_invalid:
    'нужен адрес вида https://узел или https://узел:порт без параметров, пробелов и логина с паролем.',
  host_key_invalid: 'отпечаток узла не разобран: нужна строка открытого ключа из known_hosts.',
  purpose_not_for_kind: 'этот вид подключения не хранит ключ такого назначения.',
  model_not_pinned: 'эта модель не закреплена в замке провайдера, выберите модель из списка.',
  enum: 'значение вне допустимого набора.',
  field_required_for_kind: 'для этого вида подключения поле обязательно.',
  field_not_for_kind: 'это поле не относится к выбранному виду и способу связи.',
  pattern: 'значение не подходит по написанию.',
  standby_equals_primary: 'резервное подключение должно отличаться от основного.',
  kind_not_routable: 'подключение этого вида не может обслуживать выбранную работу.',
  kind_not_served: 'подключения этого вида пока не обслуживаются.',
  probe_not_ok: 'у подключения нет успешной проверки на текущем ключе.',
  min: 'значение меньше допустимого.',
  max: 'значение больше допустимого.',
  required: 'поле нужно заполнить.',
};

const CONFLICT_SENTENCES: Readonly<Record<string, string>> = {
  connection_archived: 'Подключение в архиве, команда не выполнена.',
  no_revision: 'У подключения ещё нет настроек: сначала сохраните их.',
  connection_routed: 'Подключение назначено на работу. Сначала уберите его из назначений.',
};

const DEPENDENCY_SENTENCES: Readonly<Record<string, string>> = {
  secrets_public_key_missing:
    'На стенде не задан открытый ключ для запечатывания секретов, поэтому ключ ввести нельзя. Это вопрос к тому, кто разворачивал стенд.',
};

function stringDetail(error: ApiError, key: string): string | null {
  const value = error.details[key];
  return typeof value === 'string' ? value : null;
}

/** The sentence for a refusal this screen knows how to explain; `null` for any other. */
export function connectionRefusalSentence(error: ApiError): string | null {
  if (error.errorCode === 'validation_failed') {
    const constraint = stringDetail(error, 'constraint');
    if (constraint === null) return null;
    const sentence = CONSTRAINT_SENTENCES[constraint];
    if (sentence === undefined) return null;
    const field = stringDetail(error, 'field');
    const label = field === null ? undefined : FIELD_LABELS[field];
    return label === undefined ? sentence.charAt(0).toUpperCase() + sentence.slice(1) : `${label}: ${sentence}`;
  }
  if (error.errorCode === 'conflict') {
    const reason = stringDetail(error, 'conflict_reason');
    return reason === null ? null : (CONFLICT_SENTENCES[reason] ?? null);
  }
  if (error.errorCode === 'dependency_unavailable') {
    const dependency = stringDetail(error, 'dependency');
    return dependency === null ? null : (DEPENDENCY_SENTENCES[dependency] ?? null);
  }
  return null;
}

/**
 * The failure of a connection read or command. An unknown outcome keeps the shared
 * sentence (nothing may be said about what the server did); every definite refusal gets the
 * specific sentence when this table has one.
 */
export function connectionFailure(error: unknown, write: boolean): ExecutionFailure {
  const base = executionFailure(error, write);
  if (!(error instanceof ApiError)) return base;
  const sentence = connectionRefusalSentence(error);
  if (sentence === null) return base;
  // A 503 on a write is an unknown outcome in general (the shared rule), but a missing
  // dependency the server names before it writes anything is a definite refusal: nothing was
  // done, and saying "outcome unknown" would send the person to repeat a command that cannot work.
  if (base.kind === 'unknown_outcome' && error.errorCode !== 'dependency_unavailable') return base;
  return { ...base, kind: base.kind === 'unknown_outcome' ? 'refusal' : base.kind, detail: sentence };
}
