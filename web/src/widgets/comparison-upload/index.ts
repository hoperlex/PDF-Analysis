/**
 * Public API of the `comparison-upload` widget (`CMP-VC-UI-01`): the dialogs «Загрузка проекта и версий» and «Загрузка
 * нескольких проектов» over the comparison upload operations of `CMP-SEAL-C0` — declare the files, send them in parts that can
 * be stopped and continued, read the proposal, confirm each set — and the pieces under them (the transfer, the matching of
 * files to declarations, the set editor).
 */

export type { UploadDialogProps, UploadDialogViewProps, UploadMode } from './ui/upload-dialog';
export {
  BATCH_SWITCH,
  BATCH_TITLE,
  PICK_HINT,
  PROPOSAL_NOTE,
  REPICK_NOTE,
  SINGLE_TITLE,
  UploadDialog,
  UploadDialogView,
  ZIP_NOTE,
} from './ui/upload-dialog';
export type { SetEditorProps } from './ui/set-editor';
export { SetEditor } from './ui/set-editor';
export type { FlowPhase, Progress, UploadFlow } from './ui/use-upload-flow';
export { useUploadFlow } from './ui/use-upload-flow';
export type { SetDraft } from './model/confirm';
export {
  awaitingConfirmation,
  confirmationOf,
  draftOf,
  moveFile,
  proposedConfirmation,
  proposedFiles,
  relabel,
} from './model/confirm';
export type { Group, PickedFile, PrecheckProblem } from './model/files';
export {
  MAX_BATCH_BYTES,
  MAX_FILES,
  MAX_FILE_BYTES,
  MAX_SETS,
  PART_SIZE_BYTES,
  PRECHECK_SENTENCES,
  declaredName,
  groupOf,
  groupsOf,
  isPdfName,
  partCount,
  pickFiles,
  precheck,
} from './model/files';
export { hex, sha256Hex } from './model/hash';
export type { Declared, Local, Matching } from './model/matching';
export { matchFiles } from './model/matching';
export type { TransferEvents, TransferFile, TransferOutcome, TransferPorts } from './model/transfer';
export { KeyBook, RETRYABLE_FILE_REASONS, isRetryableFailure, needsTransfer, transferFiles } from './model/transfer';
