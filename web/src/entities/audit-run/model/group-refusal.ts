/**
 * The refusals a start meets because of the executor group the person chose, or because the stand
 * routes by rules (`EXEC2-WEB-GROUPS-01`, over `startRun` and `estimateRunCost` of API 1.16.0,
 * ADR-0026 decisions 12 to 18).
 *
 * A start that names `executor_group_id` is refused before a run exists, and nothing is written:
 *
 * - `422 validation_failed`, field `executor_group_id`, constraint `conflicts_with_executor_connection_id`
 *   or `conflicts_with_preset_id`: a group was sent together with a connection or a preset, which this
 *   screen never does;
 * - `422 validation_failed`, constraint `unknown_executor_group`: the group is not one the stand knows;
 * - `422 validation_failed`, constraint `environment_source`: a run in the `environment` provider
 *   source refuses a group;
 * - `409 conflict`, `conflict_reason` `group_archived`: the group was archived between choosing and
 *   starting.
 *
 * While the routing mode is `rules`, a start that names no connection, group or preset is admitted on
 * the rule of the `text_analysis` work kind, and a kind with no rule is `503 dependency_unavailable`
 * with `details.dependency` `no_rule_for_work_kind`.
 *
 * **A chosen group is never replaced**: the stand does not start the run on another group, on a
 * connection or on the route, and neither does this wording. Every one of these is refused again until
 * the choice or the rules change, so each is presented as unsupported: no retry under the same key is
 * offered, and no sentence invites the person to fall back to anything.
 *
 * The values are read from the three safe detail keys the catalogue allows (`constraint`,
 * `conflict_reason`, `dependency`) and only under the code that carries them, so an unrelated refusal
 * that happens to share a word is not taken for one of these.
 */

import type { ApiError } from '@/shared/api';

export type GroupRefusalKind =
  | 'group_with_executor'
  | 'group_with_preset'
  | 'group_unknown'
  | 'group_environment_source'
  | 'group_archived'
  | 'no_rule_for_work_kind';

export interface GroupRefusal {
  readonly kind: GroupRefusalKind;
  readonly presentation: 'unsupported';
  readonly title: string;
  readonly detail: string;
}

/** `details.field` of a rejection of the chosen group's identifier. */
export const GROUP_FIELD = 'executor_group_id';

const NOT_REPLACED =
  'Вместо выбранной группы прогон не запускается ни на другой группе, ни на подключении, ни по назначениям.';

const REFUSALS: Readonly<Record<GroupRefusalKind, Omit<GroupRefusal, 'kind' | 'presentation'>>> = {
  group_with_executor: {
    title: 'Группа и подключение выбраны вместе.',
    detail: 'Выберите что-то одно: либо группу, либо конкретное подключение. Прогон не запущен.',
  },
  group_with_preset: {
    title: 'Группа и пресет выбраны вместе.',
    detail: 'Выберите что-то одно: либо группу, либо пресет, который сам задаёт подключение. Прогон не запущен.',
  },
  group_unknown: {
    title: 'Выбранной группы нет.',
    detail: `Возможно, её убрали, пока вы выбирали. Обновите список групп и выберите заново. Прогон не запущен. ${NOT_REPLACED}`,
  },
  group_environment_source: {
    title: 'Прогон с источником «окружение» не может идти на группу.',
    detail: `Группа выбирает подключение при отправке в работу, а прогон с источником «окружение» его не выбирает. Прогон не запущен. ${NOT_REPLACED}`,
  },
  group_archived: {
    title: 'Выбранная группа убрана в архив.',
    detail: `Архивную группу выбрать для прогона нельзя. Обновите список групп и выберите другую. Прогон не запущен. ${NOT_REPLACED}`,
  },
  no_rule_for_work_kind: {
    title: 'Для анализа текста нет правила.',
    detail:
      'Включены правила, но виду работы «Анализ текста» не назначена группа. Администратор назначает её на вкладке «Правила» экрана «Исполнители». Прогон не запущен. Вместо правила он не запускается на другом исполнителе.',
  },
};

function detail(error: ApiError, key: string): string | null {
  const value = error.details[key];
  return typeof value === 'string' ? value : null;
}

function refusal(kind: GroupRefusalKind): GroupRefusal {
  return { kind, presentation: 'unsupported', ...REFUSALS[kind] };
}

/** The refusal an error is, or `null` for any other error. */
export function groupRefusal(error: ApiError): GroupRefusal | null {
  if (error.errorCode === 'validation_failed') {
    const constraint = detail(error, 'constraint');
    if (constraint === 'environment_source') return refusal('group_environment_source');
    if (detail(error, 'field') !== GROUP_FIELD) return null;
    if (constraint === 'conflicts_with_executor_connection_id') return refusal('group_with_executor');
    if (constraint === 'conflicts_with_preset_id') return refusal('group_with_preset');
    if (constraint === 'unknown_executor_group') return refusal('group_unknown');
    return null;
  }
  if (error.errorCode === 'conflict') {
    const reason = detail(error, 'conflict_reason');
    if (reason === 'group_archived') return refusal('group_archived');
    if (reason === 'environment_source') return refusal('group_environment_source');
    return null;
  }
  if (error.errorCode === 'dependency_unavailable') {
    const dependency = detail(error, 'dependency');
    if (dependency === 'no_rule_for_work_kind') return refusal('no_rule_for_work_kind');
    if (dependency === 'environment_source') return refusal('group_environment_source');
    return null;
  }
  return null;
}
