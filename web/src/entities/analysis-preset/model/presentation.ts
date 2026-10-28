/**
 * What a preset is, in words (`ANALYSIS-PRESETS-01`, `R-146av`).
 *
 * A preset is a name and the executor a run is started on — the one setting a run start can take.
 * There is no cost limit and no threshold in it, because nothing selects them per run, and none is
 * worded here. The executor is shown by the name an administrator gave it and the model its
 * current settings pin, read from the connection list; nothing here is an identifier, an address
 * or a key.
 *
 * **Whether a preset can start a run now is the executor's answer, not the preset's.** The rule is
 * the blocker `executorChoices` of `entities/executor-connection` computes, the same one the executor select applies; a
 * preset whose executor cannot serve is listed with the reason and cannot be chosen, and the server
 * asks the same question again when the run starts.
 */

import type { AnalysisPreset, AnalysisPresetState, ExecutorConnectionId, PresetId } from '@/shared/api';
import type { ExecutorChoice } from '@/entities/executor-connection';
import { CHOICE_BLOCKER_SENTENCES, KIND_LABELS } from '@/entities/executor-connection';

export const PRESET_STATE_LABELS: Readonly<Record<AnalysisPresetState, string>> = {
  active: 'Действует',
  archived: 'В архиве',
};

export const PRESET_OPTION_NONE = 'Без пресета';

/** The executor a preset names, among the connections the screen has read; `undefined` when absent. */
export function presetExecutor(
  preset: Pick<AnalysisPreset, 'executor_connection_id'>,
  choices: readonly ExecutorChoice[],
): ExecutorChoice | undefined {
  return choices.find((choice) => choice.connectionId === preset.executor_connection_id);
}

/** ««Основной шлюз» (HTTP API), модель «…»» — or the honest «не найден в списке». */
export function executorPhrase(choice: ExecutorChoice | undefined): string {
  if (choice === undefined) return 'исполнитель не найден в списке подключений';
  const model = choice.model === null ? '' : `, модель «${choice.model}»`;
  return `«${choice.name}» (${KIND_LABELS[choice.kind]})${model}`;
}

/** Why a preset cannot start a run now, or `null` when it can. */
export function presetBlocker(
  preset: Pick<AnalysisPreset, 'state' | 'executor_connection_id'>,
  choices: readonly ExecutorChoice[],
): string | null {
  if (preset.state === 'archived') return 'пресет в архиве';
  const choice = presetExecutor(preset, choices);
  if (choice === undefined) return 'исполнитель не найден в списке подключений';
  return choice.blocker === null ? null : `исполнитель недоступен: ${CHOICE_BLOCKER_SENTENCES[choice.blocker]}`;
}

export interface PresetChoice {
  readonly presetId: PresetId;
  readonly name: string;
  readonly revisionNo: number;
  readonly executorConnectionId: ExecutorConnectionId;
  /** The executor's phrase, for the line under the select. */
  readonly executor: string;
  /** `null` exactly when a run can be started with this preset now. */
  readonly blocker: string | null;
}

/**
 * The presets the start control offers: the active ones, in the order the list came in. An
 * archived preset is retired and is not offered at all — unless it is the one already chosen, so a
 * choice that stops being valid between choosing and starting stays visible, disabled.
 */
export function presetChoices(
  presets: readonly AnalysisPreset[],
  choices: readonly ExecutorChoice[],
  chosen: PresetId | null,
): PresetChoice[] {
  return presets
    .filter((preset) => preset.state === 'active' || preset.preset_id === chosen)
    .map((preset) => ({
      presetId: preset.preset_id,
      name: preset.name,
      revisionNo: preset.revision_no,
      executorConnectionId: preset.executor_connection_id,
      executor: executorPhrase(presetExecutor(preset, choices)),
      blocker: presetBlocker(preset, choices),
    }));
}

export function presetCanStart(choice: PresetChoice): boolean {
  return choice.blocker === null;
}

/** The text of one option of the select: the name, and why not when the preset cannot be chosen. */
export function presetOptionLabel(choice: PresetChoice): string {
  return choice.blocker === null ? choice.name : `${choice.name} — недоступно: ${choice.blocker}`;
}

/** «Исполнитель задан пресетом «…»» — the hint the executor select shows while a preset is chosen. */
export function presetFillsExecutorSentence(name: string): string {
  return `Исполнитель задан пресетом «${name}». Чтобы выбрать другого, снимите пресет.`;
}

/** True when a connection is still offered as live, so a preset may name it. */
export function connectionIsLive(choice: ExecutorChoice): boolean {
  return !choice.archived;
}
