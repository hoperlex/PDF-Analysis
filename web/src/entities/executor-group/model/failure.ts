/**
 * Refusals of the group, rule and routing-mode commands, worded (`EXEC2-WEB-GROUPS-01`,
 * ADR-0026 decision 18).
 *
 * EXEC-2 adds no error code. A refusal reaches the browser through the catalogue's existing codes
 * and their existing safe detail keys: `validation_failed` names a `field` and a `constraint`,
 * `conflict` a `conflict_reason`, `dependency_unavailable` a `dependency`. Each value the group
 * commands choose has a Russian sentence here, and a value this table does not know falls back to
 * the code's own catalogue sentence, never to the English message of the server.
 *
 * An unknown outcome keeps the shared sentence: nothing may be said about what the server did.
 * Every definite refusal gets the specific sentence, and none of them offers a way around it.
 */

import { ApiError } from '@/shared/api';
import { executionFailure } from '@/entities/execution';
import type { ExecutionFailure } from '@/entities/execution';

import { GROUP_MEMBERS_MAX, GROUP_MEMBERS_MIN } from './vocabulary';

const FIELD_LABELS: Readonly<Record<string, string>> = {
  display_name: 'Название',
  pin_id: 'Модель',
  gateway_model: 'Имя модели на шлюзе',
  billing: 'Тарификация',
  members: 'Состав',
  strategy: 'Порядок выбора',
  preview_digest: 'Предложение перехода',
  mapping: 'Соответствие видов работы группам',
  work_kind: 'Вид работы',
  group_revision_id: 'Версия группы',
  executor_group_id: 'Группа исполнителей',
};

const CONSTRAINT_SENTENCES: Readonly<Record<string, string>> = {
  // `createExecutorGroup` and `reviseExecutorGroup`: the members (decision 10).
  unknown_executor_connection: 'в составе есть подключение, которого на стенде нет.',
  member_revision_not_of_connection:
    'версия настроек не принадлежит подключению; обновите страницу и выберите состав заново.',
  member_repeated: 'одно подключение указано в составе дважды.',
  tie_break_order_repeated: 'порядок выбора при равной загрузке повторяется.',
  member_kind_not_served: 'подключение такого вида пока не обслуживается.',
  // The group is homogeneous: the three fields every member must share.
  member_pin_mismatch:
    'у одного из подключений закреплена другая модель. В группе все подключения закреплены на одной модели.',
  member_model_mismatch:
    'у одного из подключений другое имя модели на шлюзе. В группе оно у всех подключений одно.',
  member_billing_mismatch:
    'у одного из подключений другая тарификация. Смешанные группы не принимаются.',
  model_not_pinned: 'эта модель не закреплена в замке провайдера, выберите модель из списка.',
  // The cut-over (decision 17).
  preview_digest_required: 'подтверждение должно нести сверку предложения. Откройте предложение заново.',
  mapping_required: 'не указано, какие виды работы переводятся. Откройте предложение заново.',
  mapping_not_accepted: 'для возврата к основным и резервным подключениям соответствие не передаётся.',
  mapping_entry_not_ready: 'в соответствии есть вид работы, который перенести нельзя. Откройте предложение заново.',
  mapping_work_kind_repeated: 'вид работы указан в соответствии дважды.',
  // The start of a run with a group (kept here so a command can show it too).
  conflicts_with_executor_connection_id: 'группу нельзя выбрать вместе с подключением.',
  conflicts_with_preset_id: 'группу нельзя выбрать вместе с пресетом.',
  unknown_executor_group: 'такой группы на стенде нет.',
  environment_source: 'прогон с источником «окружение» не может идти на группу.',
  enum: 'значение вне допустимого набора.',
  required: 'поле нужно заполнить.',
  max_length: 'значение длиннее допустимого.',
  pattern: 'значение не подходит по написанию.',
  min: 'значение меньше допустимого.',
  max: 'значение больше допустимого.',
};

/**
 * A constraint whose wording depends on the field it refused. `range` is the case: on `members` it
 * is the size of the group.
 */
const FIELD_CONSTRAINT_SENTENCES: Readonly<Record<string, string>> = {
  'members/range': `в группе должно быть от ${GROUP_MEMBERS_MIN} до ${GROUP_MEMBERS_MAX} подключений.`,
};

const CONFLICT_SENTENCES: Readonly<Record<string, string>> = {
  connection_archived: 'Подключение из состава в архиве. Уберите его из состава.',
  group_archived: 'Группа в архиве: её нельзя ни изменить, ни назначить правилом, ни выбрать для прогона.',
  group_name_in_use: 'Группа с таким названием уже есть среди действующих. Выберите другое название.',
  group_routed:
    'Группу нельзя убрать в архив, пока правило направляет на неё работу. Сначала назначьте виду работы другую группу.',
  routing_mode_rules:
    'Включены правила: основное и резервное подключения не меняются. Сначала вернитесь к основным и резервным подключениям.',
  routing_mode_unchanged: 'Режим уже такой, как вы выбрали. Обновите страницу.',
  preview_stale:
    'Предложение устарело: назначения изменились после того, как вы его открыли. Откройте предложение заново и подтвердите ещё раз.',
};

const DEPENDENCY_SENTENCES: Readonly<Record<string, string>> = {
  no_rule_for_work_kind:
    'Включены правила, но для этого вида работы правила нет. Назначьте ему группу на вкладке «Правила».',
};

function stringDetail(error: ApiError, key: string): string | null {
  const value = error.details[key];
  return typeof value === 'string' ? value : null;
}

/** The sentence for a refusal this table can explain; `null` for any other. */
export function groupRefusalSentence(error: ApiError): string | null {
  if (error.errorCode === 'validation_failed') {
    const constraint = stringDetail(error, 'constraint');
    if (constraint === null) return null;
    const field = stringDetail(error, 'field');
    const sentence = (field === null ? undefined : FIELD_CONSTRAINT_SENTENCES[`${field}/${constraint}`])
      ?? CONSTRAINT_SENTENCES[constraint];
    if (sentence === undefined) return null;
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
 * The failure of a group read or command. An unknown outcome keeps the shared sentence; every
 * definite refusal gets the specific one. A missing dependency the server names before it writes
 * anything is a definite refusal even though it is a 503: nothing was done, and calling the
 * outcome unknown would send the person to repeat a command that cannot work.
 */
export function groupFailure(error: unknown, write: boolean): ExecutionFailure {
  const base = executionFailure(error, write);
  if (!(error instanceof ApiError)) return base;
  const sentence = groupRefusalSentence(error);
  if (sentence === null) return base;
  if (base.kind === 'unknown_outcome' && error.errorCode !== 'dependency_unavailable') return base;
  return { ...base, kind: base.kind === 'unknown_outcome' ? 'refusal' : base.kind, detail: sentence };
}
