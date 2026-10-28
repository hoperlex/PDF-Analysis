'use client';

/**
 * «Пресет» — the second way to choose how a run starts (`ANALYSIS-PRESETS-01`): a saved preset
 * fills the executor, so the person does not choose it by hand.
 *
 * The options are «Без пресета» and the active presets. A preset whose executor cannot serve now is
 * listed **disabled, with the reason** — the same rule, the same sentences, as the executor select —
 * and an archived preset is not listed unless it is the one chosen, so a choice that stops being
 * valid between choosing and starting stays visible instead of silently turning into another option.
 * While a preset is chosen the executor select shows the preset's executor and is locked; changing
 * the executor means taking the preset off.
 *
 * It is presentational: the lists are read by the control and arrive as `reading`. When the presets
 * cannot be read the select says so and keeps its default, so a start without a preset still works.
 * Nothing rendered is an identifier, an address or a key: the labels are names, versions and the
 * executor's name and model.
 */

import type { PresetId } from '@/shared/api';
import { LoadingState } from '@/shared/ui';
import type { PresetChoice } from '@/entities/analysis-preset';
import { PRESET_OPTION_NONE, presetCanStart, presetOptionLabel } from '@/entities/analysis-preset';

export type PresetListReading =
  | { readonly phase: 'loading' }
  | {
      readonly phase: 'failed';
      readonly detail: string;
      readonly correlationId: string | null;
      readonly onRetry: () => void;
    }
  | { readonly phase: 'ready'; readonly choices: readonly PresetChoice[] };

export interface PresetSelectViewProps {
  /** The DOM id the label points at. */
  readonly id: string;
  readonly reading: PresetListReading;
  /** The chosen preset, or `null` for «Без пресета». */
  readonly value: PresetId | null;
  /** True while a start is in flight: the choice is the one that was sent. */
  readonly disabled: boolean;
  readonly onChange: (next: PresetId | null) => void;
}

export function chosenPreset(optionValue: string): PresetId | null {
  return optionValue === '' ? null : optionValue;
}

export function PresetSelectView({ id, reading, value, disabled, onChange }: PresetSelectViewProps) {
  const choices = reading.phase === 'ready' ? reading.choices : [];
  const chosenGone = value !== null && !choices.some((choice) => choice.presetId === value);
  const current = choices.find((choice) => choice.presetId === value);

  return (
    <div className="am-form__field" data-preset-select>
      <label htmlFor={id}>Пресет</label>
      <select
        id={id}
        value={value ?? ''}
        disabled={disabled}
        onChange={(event) => onChange(chosenPreset(event.target.value))}
      >
        <option value="">{PRESET_OPTION_NONE}</option>
        {choices.map((choice) => (
          <option key={choice.presetId} value={choice.presetId} disabled={!presetCanStart(choice)}>
            {presetOptionLabel(choice)}
          </option>
        ))}
        {chosenGone ? (
          <option value={value} disabled>
            Выбранный пресет больше не в списке
          </option>
        ) : null}
      </select>

      {reading.phase === 'loading' ? <LoadingState what="пресеты" /> : null}

      {reading.phase === 'failed' ? (
        <>
          <p className="am-form__hint" role="status" data-preset-list-failure>
            Список пресетов не прочитан. {reading.detail} Прогон можно запустить и без пресета.
          </p>
          {reading.correlationId === null ? null : (
            <p className="am-form__hint">
              Идентификатор корреляции <code>{reading.correlationId}</code>
            </p>
          )}
          <div>
            <button type="button" className="am-button am-button--quiet am-button--small" onClick={reading.onRetry}>
              Прочитать пресеты снова
            </button>
          </div>
        </>
      ) : null}

      {reading.phase === 'ready' ? (
        <p className="am-form__hint" data-preset-hint={value === null ? 'none' : 'chosen'}>
          {value === null
            ? 'Пресет — сохранённый выбор исполнителя. Без пресета исполнителя выбирают ниже или оставляют по умолчанию.'
            : current === undefined
              ? 'Выбранного пресета больше нет в списке. Обновите страницу или снимите пресет.'
              : `Прогон пойдёт на исполнителе из пресета «${current.name}» (версия ${current.revisionNo}): ${current.executor}. Если исполнитель не сможет выполнить прогон, другой не подставляется.`}
          {choices.length === 0 ? ' Сохранённых пресетов пока нет.' : ''}
        </p>
      ) : null}
    </div>
  );
}
