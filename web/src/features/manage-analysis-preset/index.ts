/**
 * Public API of the `manage-analysis-preset` feature slice (`ANALYSIS-PRESETS-01`).
 *
 * The administrator's commands on a preset: save a new one, save a new version of one, and archive
 * one. The server decides who may; the controls are offered to an administrator only.
 */

export {
  useArchiveAnalysisPreset,
  useCreateAnalysisPreset,
  useReviseAnalysisPreset,
} from './model/use-manage-analysis-preset';
export { useCommandKey } from './model/use-command-key';

export { ArchivePresetControl } from './ui/archive-preset-control';
export { PresetCommandFailure } from './ui/preset-failure';
export { PresetForm } from './ui/preset-form';
export type { PresetFormProps } from './ui/preset-form';
