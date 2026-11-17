/** Public API of the `run-stages-dialog` widget: «Этапы анализа раздела» of the run screen, and «Модели по этапам» before a start. */

export type { RunStagesDialogProps } from './ui/run-stages-dialog';
export { RunStagesDialog } from './ui/run-stages-dialog';
// `UIP-S05-01`: the window «Модели по этапам» that «Модели по этапам ▸» under «Запустить» opens (it replaced `PlanStagesDialog`, the run's window in plan mode).
export type { StageLayoutReading, StageModelsDialogProps, StageModelsDialogViewProps } from './ui/stage-models-dialog';
export { StageModelsDialog, StageModelsDialogView } from './ui/stage-models-dialog';
// `UIP-S05-03`: the administrator's form of the layout inside that window.
export type { StageModelsEditProps } from './ui/stage-models-edit';
export { StageModelsEdit } from './ui/stage-models-edit';
export type { StageModelsRow, StageModelsSource } from './model/stage-models-rows';
export { factOfRoles, layoutStageRows, planStageRows } from './model/stage-models-rows';
export type { ChipAlgorithm } from './model/chip-algorithms';
export { CHIP_ALGORITHMS } from './model/chip-algorithms';
