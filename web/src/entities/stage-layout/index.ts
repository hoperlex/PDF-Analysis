/**
 * Public API of the `stage-layout` entity (`HOSTS-WEB-01`, ADR-0028): the reads of «Модели по этапам», the words, and the pure
 * rules that turn the layout into the table, the sets and the checks of a draft.
 *
 * `RUN-START-ONE-01` and `RUN-SCREEN-01` (wave 2) read the layout only through the generated client and this entity.
 * Nothing here writes. The commands are in `features/manage-stage-layout`.
 */

export {
  modelCatalogueKey, modelCatalogueQueryOptions, stageLayoutKey, stageLayoutQueryOptions, useModelCatalogue,
  useStageModelLayout,
} from './api/use-stage-layout';
export { layoutFailure, layoutRefusalSentence } from './model/failure';
export type { NamedKit } from './model/kits';
export {
  DEFAULT_ANSWER_TOKENS, DEFAULT_TIMEOUT_SECONDS, NAMED_KITS, cellKeyOf, effortsOf, isNamedKit, kitCells, kitIsOffered,
  kitModelIds, pairIsInCatalogue,
} from './model/kits';
export type { CellReading, TableRow } from './model/table';
export { cellText, layoutTable, rowCells, rowOfStageKey } from './model/table';
export {
  ADVANCED_SUMMARY, CANCEL_LABEL, EDIT_LABEL, ENSEMBLE_NOTE, HISTORY_EMPTY, HISTORY_TITLE, JOURNAL_EMPTY, JOURNAL_TITLE,
  KIT_LEGEND, LAYOUT_OFF_NOTE, LAYOUT_ON_NOTE, NOT_ON_SERVERS, NOT_ON_SERVERS_HINT, NO_AVAILABLE_MODELS, NO_LAYOUT,
  NO_LAYOUT_ADMIN, ROW_EFFORT_LABEL, ROW_MODEL_LABEL, SAVE_LABEL, STAGE_EFFORT_LABELS, STAGE_KIT_LABELS,
  STAGE_MODELS_TITLE, STAGE_ROLE_LABELS, STAGE_ROW_LABELS, SWITCH_HINT, SWITCH_LABEL, SWITCH_NEEDS_REVISION,
  TIMEOUT_LABEL, TOKENS_LABEL,
} from './model/vocabulary';
