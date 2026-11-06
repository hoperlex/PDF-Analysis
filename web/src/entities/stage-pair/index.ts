/** Public API of the stage-pair catalog. */
export { STAGE_PAIR_KEYS, useStagePairs, useStagePairSuggestions, useConfirmStagePair, useSetStagePairCompleteness } from './model/catalog';
export { completenessLabel, suggestionReason } from './model/words';
export type { StageDocumentName, StageDocumentNames } from './model/documents';
export { documentCaption, namesOf, useStageDocumentNames } from './model/documents';
