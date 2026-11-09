/**
 * Public API of the `executor-host` entity (`HOSTS-WEB-01`, ADR-0028): the reads of «Серверы», the words, and the pure rules
 * that turn a `listExecutorHosts` answer into the rows, chips and summary of the screen.
 *
 * Nothing here writes. The commands are in `features/manage-executor-host`.
 */

export {
  executorHostDetailsKey, executorHostDetailsQueryOptions, executorHostsKey, executorHostsQueryOptions, mayReadHosts,
  useExecutorHostDetails, useExecutorHosts,
} from './api/use-executor-hosts';
export { hostFailure, hostRefusalSentence } from './model/failure';
export { modelLabel, modelLabels } from './model/models';
export type { HostRowReading, HostRowTone, ModelChip } from './model/rows';
export { availableModelIds, hostRowReading, liveHosts, modelChips } from './model/rows';
export {
  ACCESS_LABELS, API_MARK, API_MARK_HINT, AUTH_STATE_LABELS, CLIENT_DOCUMENTS_LINE, HOST_STATE_LABELS, MENU_DELETE,
  MENU_DETAILS, MENU_LABEL, MODEL_STATE_LABELS, NO_MODELS, PROVIDER_LABELS, SERVERS_EMPTY, SERVERS_EMPTY_ADMIN,
  SERVERS_TITLE, UNAVAILABLE_REASON_SENTENCES, USE_HINT, USE_LABEL, noContactSentence, summarySentence,
} from './model/vocabulary';
