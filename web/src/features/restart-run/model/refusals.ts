/**
 * `RUN-RESTART-01`: how a refused restart reads. One plain sentence for each typed refusal of `restartRun` (and of the cost estimate
 * of a restart, which refuses the same way), and the same sentence for a restart that failed at the executor before any paid call
 * (the new run's `terminal_detail.reason`).
 *
 * Three families, each named in the operation's own description:
 *   - `409 state_transition_not_allowed` (`requested_state` `restart`): the run is published or has not ended;
 *   - `409 conflict` with `conflict_reason` `restart_source_deleted`, `restart_source_leased`, `restart_in_progress`;
 *   - `422 analysis_input_invalid` with `details.reason`, and where it belongs to one chip `details.restart_point` or `details.stage_id`:
 *     the `restart_*` reasons, and the `source_stage_*` reasons of `startRunFromStage` for the artifacts the preparation is taken by.
 *
 * The chip is named by its short name from the stage dictionary, never by an id. A failure that is not one of these keeps its usual
 * wording (`executionFailure`), after «Перезапуск не выполнен:».
 */

import { ApiError } from '@/shared/api';
import { chipById, chipOfStage } from '@/entities/audit-run';
import { executionFailure } from '@/entities/execution';

/** The reader's advice that always works: a new run with today's settings. */
const REAUDIT = 'Чтобы выполнить с нуля, повторите прогон.';
/** For a result of the preparation that cannot be taken: the preparation computed again takes nothing. */
const FROM_PREPARATION = 'Перезапустите с «Подготовки».';

/** The source run changed between the screen and the command; thrown by the price reading before any consent is asked for. */
export class RestartSourceChanged extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'RestartSourceChanged';
  }
}

/** The chip a refusal names: `restart_point` (a chip), else the code stage or procedure id of `stage_id`. */
function chipNameOf(details: Readonly<Record<string, unknown>>): string | null {
  const point = details.restart_point;
  if (typeof point === 'string') {
    const chip = chipById(point);
    if (chip !== null) return chip.short;
  }
  const stage = details.stage_id;
  if (typeof stage === 'string') {
    const chip = chipOfStage(stage);
    if (chip !== null) return chip.short;
  }
  return null;
}

/** «этапа «Блоки»», or «этого этапа» where the refusal names none. */
const ofChip = (name: string | null): string => (name === null ? 'этого этапа' : `этапа «${name}»`);

/** The artifact reasons of the preparation, the ones `startRunFromStage` has always had; the stage is named by its chip. */
const SOURCE_STAGE_REASONS: Readonly<Record<string, (name: string | null) => string>> = {
  source_stage_not_completed: (name) =>
    `${name === null ? 'Этап' : `Этап «${name}»`} исходного прогона не завершён успешно, его результат взять нельзя. ${FROM_PREPARATION}`,
  source_stage_version_changed: (name) =>
    `Результат ${ofChip(name)} получен более старой версией этапа, чем действует сейчас; брать его нельзя. ${FROM_PREPARATION}`,
  source_stage_output_incomplete: (name) =>
    `В результате ${ofChip(name)} исходного прогона нет обязательных данных. ${FROM_PREPARATION}`,
  source_artifact_unavailable: (name) =>
    `Сохранённый результат ${ofChip(name)} исходного прогона недоступен. ${FROM_PREPARATION}`,
  source_artifact_changed: (name) =>
    `Сохранённый результат ${ofChip(name)} исходного прогона не совпадает с записанным. ${FROM_PREPARATION}`,
  source_stage_inputs_changed: (name) =>
    `Условия выполнения ${ofChip(name)} изменились с исходного прогона (допуск страниц без текстового слоя); результат взять нельзя. ${FROM_PREPARATION}`,
};

/** The `restart_*` reasons of `422 analysis_input_invalid`, each with the sentence for the chip it names. */
const RESTART_REASONS: Readonly<Record<string, (name: string | null) => string>> = {
  restart_source_not_stage_layout: () =>
    `Прогон запущен без раскладки моделей по этапам, поэтому его готовые ответы взять нельзя. ${REAUDIT}`,
  restart_source_not_v2: () =>
    `Прогон выполнен другой версией полного анализа, его готовые ответы взять нельзя. ${REAUDIT}`,
  restart_settings_differ: () =>
    `Настройки прогона отличаются от тех, что подошли бы перезапуску, поэтому его ответы не повторить. ${REAUDIT}`,
  restart_text_not_reusable: () =>
    'Результат этапа «Текст» исходного прогона взять нельзя: он неполный или получен другой версией этапа. Перезапустите с «Текста».',
  restart_reply_missing: (name) =>
    `Для ${ofChip(name)} в исходном прогоне не сохранён ответ модели, поэтому взять его нельзя. Перезапустите с ${name === null ? 'этого этапа' : `«${name}»`}.`,
  restart_request_changed: (name) =>
    name === 'Нормы'
      ? 'Поиск норм дал другой результат, чем в исходном прогоне, и ответ модели к нему не подошёл. Перезапустите с «Норм».'
      : `Запрос к модели для ${ofChip(name)} стал другим, чем в исходном прогоне, и сохранённый ответ не подошёл. Перезапустите с ${name === null ? 'этого этапа' : `«${name}»`}.`,
};

/** Every reason this file has a sentence for, for the test that holds them to the contract. */
export const RESTART_REFUSAL_REASONS: readonly string[] = [...Object.keys(RESTART_REASONS), ...Object.keys(SOURCE_STAGE_REASONS)];

/** `restart_source_deleted`, `restart_source_leased`, `restart_in_progress`: the conflicts of `409 conflict`. */
const CONFLICTS: Readonly<Record<string, string>> = {
  restart_source_deleted: 'Этот прогон уже удалён, перезапустить его нельзя.',
  restart_source_leased: 'Прогон ещё не остановился: его работа не закончена. Подождите немного и повторите.',
  restart_in_progress: 'Перезапуск этого прогона уже идёт. Дождитесь его результата или остановите его.',
};

export const RESTART_CONFLICT_REASONS: readonly string[] = Object.keys(CONFLICTS);

/**
 * The sentence for a reason of `422 analysis_input_invalid` (a refusal, or the `terminal_detail` of a restart that failed at the executor),
 * or `null` for a reason this file does not know. `details` is the refusal's `details` or the run's `terminal_detail`.
 */
export function restartReasonSentence(details: Readonly<Record<string, unknown>>): string | null {
  const reason = details.reason;
  if (typeof reason !== 'string') return null;
  const name = chipNameOf(details);
  const say = RESTART_REASONS[reason];
  if (say !== undefined) return say(name);
  const artifact = SOURCE_STAGE_REASONS[reason];
  return artifact === undefined ? null : artifact(name);
}

const NOT_ENDED: ReadonlySet<string> = new Set(['created', 'queued', 'running', 'validating']);

/** `409 state_transition_not_allowed` for a restart: a published run is re-audited; a run that has not ended is stopped first. */
function transitionSentence(details: Readonly<Record<string, unknown>>): string | null {
  if (details.requested_state !== 'restart') return null;
  const current = details.current_state;
  if (current === 'published') return 'Опубликованный прогон не перезапускается: его можно повторить целиком.';
  if (typeof current === 'string' && NOT_ENDED.has(current)) return 'Прогон ещё не завершился. Сначала остановите его.';
  return 'Прогон в этом состоянии перезапустить нельзя.';
}

/**
 * The sentence for a refused restart, or `null` when the failure is anything else (the caller then says what it always says).
 * Nothing was written: no run was created and the source stays as it was.
 */
export function restartRefusal(error: unknown): string | null {
  if (error instanceof RestartSourceChanged) return error.message;
  if (!(error instanceof ApiError)) return null;
  const details = error.details;
  switch (error.errorCode) {
    case 'state_transition_not_allowed':
      return transitionSentence(details);
    case 'conflict': {
      const reason = details.conflict_reason;
      return typeof reason === 'string' ? (CONFLICTS[reason] ?? null) : null;
    }
    case 'analysis_input_invalid':
      return restartReasonSentence(details);
    default:
      return null;
  }
}

/** The sentence a screen shows for a failed read of the price or a failed command. */
export function restartFailureText(error: unknown, write: boolean): string {
  return restartRefusal(error) ?? `Перезапуск не выполнен: ${executionFailure(error, write).detail}`;
}
