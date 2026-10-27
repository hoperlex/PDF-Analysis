/**
 * The refusals a start meets because of the preset the person chose (`ANALYSIS-PRESETS-01`).
 *
 * A start that carries `preset_id` is refused before a run exists when the preset is not known —
 * `422 validation_failed`, `details.field: preset_id`, `constraint: unknown_preset` — or is in the
 * archive — `409 conflict`, `details.conflict_reason: preset_archived` — or when it came together
 * with an executor — `422`, `constraint: conflicts_with_executor_connection_id`, which this
 * screen never sends. **A chosen preset is never replaced**: the stand does not start the run on the
 * route, on another preset or on the preset's older version, and neither does this wording. The
 * refusal of the preset's own executor (it cannot serve now) is the executor's refusal, worded by
 * `./executor-refusal.ts`, because to the stand it is exactly that.
 *
 * Every one of these is refused again until the choice changes, so each is presented as
 * unsupported: no retry under the same key is offered.
 */

import type { ApiError } from '@/shared/api';

export type PresetRefusalKind = 'preset_unknown' | 'preset_archived' | 'preset_with_executor';

export interface PresetRefusal {
  readonly kind: PresetRefusalKind;
  readonly presentation: 'unsupported';
  readonly title: string;
  readonly detail: string;
}

/** `details.field` of a rejection of the chosen preset's identifier. */
export const PRESET_FIELD = 'preset_id';

const NOT_REPLACED = 'Вместо выбранного пресета прогон не запускается ни с каким другим и ни на каком исполнителе по умолчанию.';

/** The refusal an error is, or `null` for any other error. */
export function presetRefusal(error: ApiError): PresetRefusal | null {
  if (error.errorCode === 'validation_failed' && error.details.field === PRESET_FIELD) {
    const constraint = error.details.constraint;
    if (constraint === 'conflicts_with_executor_connection_id') {
      return {
        kind: 'preset_with_executor',
        presentation: 'unsupported',
        title: 'Пресет и исполнитель выбраны вместе.',
        detail: 'Выберите что-то одно: пресет сам задаёт исполнителя. Прогон не запущен.',
      };
    }
    return {
      kind: 'preset_unknown',
      presentation: 'unsupported',
      title: 'Выбранного пресета нет.',
      detail: `Возможно, его убрали, пока вы выбирали. Обновите список пресетов и выберите заново. Прогон не запущен. ${NOT_REPLACED}`,
    };
  }
  if (error.errorCode === 'conflict' && error.details.conflict_reason === 'preset_archived') {
    return {
      kind: 'preset_archived',
      presentation: 'unsupported',
      title: 'Выбранный пресет убран в архив.',
      detail: `Архивный пресет выбрать для прогона нельзя. Обновите список пресетов и выберите другой. Прогон не запущен. ${NOT_REPLACED}`,
    };
  }
  return null;
}
