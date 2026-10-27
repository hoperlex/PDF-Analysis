/**
 * Public API of the `analysis-preset` entity (`ANALYSIS-PRESETS-01`, `R-146av`): the saved presets
 * of how a run starts, the words for them, and the rules that decide which can start a run now.
 *
 * Nothing here writes. The commands are in `features/manage-analysis-preset`, and the choice at
 * run start is in `features/start-run`.
 */

export { ANALYSIS_PRESETS_KEY, analysisPresetsQueryOptions, useAnalysisPresets } from './api/use-analysis-presets';
export { presetFailure, presetRefusalSentence } from './model/failure';
export type { PresetChoice } from './model/presentation';
export {
  PRESET_OPTION_NONE,
  PRESET_STATE_LABELS,
  connectionIsLive,
  executorPhrase,
  presetBlocker,
  presetCanStart,
  presetChoices,
  presetExecutor,
  presetFillsExecutorSentence,
  presetOptionLabel,
} from './model/presentation';
