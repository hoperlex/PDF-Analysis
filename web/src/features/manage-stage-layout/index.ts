/**
 * Public API of the `manage-stage-layout` feature slice (`HOSTS-WEB-01`, ADR-0028).
 *
 * The administrator's commands on the layout of models over the analysis stages: save a new revision (the form «Изменить» with
 * the segments «Только Claude · Только Codex · Свой набор», a model and an effort for each row but the blocks, which is one scheme of a
 * closed list of three, «Сравнение версий» under «Свой набор» only, and «Дополнительно») and the
 * switch «Модели по этапам: включены» with its journal. The server's catalogue decides what may be chosen; the form offers
 * only that.
 */

export {
  chooseKit, draftChanged, draftProblem, draftRequest, initialDraft, modelOptions, offeredBlockSchemes, offeredKits,
  setBlockScheme, setCellEffort, setCellLimit, setCellModel, setComparisonEffort, setComparisonLimit, setComparisonModel,
} from './model/draft';
export type { LayoutDraft } from './model/draft';
export { useReviseStageModelLayout, useSetStageModelLayoutEnabled } from './model/use-manage-stage-layout';
export { LayoutEditor, LayoutEditorView } from './ui/layout-editor';
export { LayoutSwitch, LayoutSwitchView } from './ui/layout-switch';
