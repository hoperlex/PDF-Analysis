/**
 * The preset a run was started with, in words (`ANALYSIS-PRESETS-01`, over `RunStatus.preset`).
 *
 * `RunStatus.preset` is the preset version the run recorded when it started — the preset, the number
 * of the version and the name it had then, so a later rename or a new version does not change what
 * the run says. A run started without a preset — by hand, by the stand's route, or as a repeat of an
 * earlier run — carries none, and nothing is shown: the screen does not say "без пресета" about a
 * run that never had the choice.
 */

import type { RunStatus } from '@/shared/api';

export interface RunPresetLine {
  readonly name: string;
  readonly revisionNo: number;
}

/** The preset of a run, or `null` when the run has none to show. */
export function runPresetLine(run: Pick<RunStatus, 'preset'>): RunPresetLine | null {
  const preset = run.preset;
  if (preset === undefined || preset === null) return null;
  if (typeof preset.name !== 'string' || preset.name.trim() === '') return null;
  return { name: preset.name, revisionNo: preset.revision_no };
}

/** The value of a «Пресет» row: «Быстрый черновик», версия 2. */
export function runPresetValue(line: RunPresetLine): string {
  return `«${line.name}», версия ${line.revisionNo}`;
}

/** «Пресет «…», версия 2» — the sentence of a list row. */
export function runPresetSentence(line: RunPresetLine): string {
  return `Пресет ${runPresetValue(line)}`;
}
