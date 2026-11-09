/**
 * Public API of the `decision-memory` entity (`D-495`, `DECISION-MEMORY-01`, contract 1.44.0).
 *
 * The expert decision memory: a copy of what an expert saw and decided, kept after the project and the document are gone
 * (`ADR-0027`). The reads, the Russian words of its closed sets and who is offered it. Nothing here writes:
 * `features/manage-decision-memory` owns the withdraw and the restore.
 */

export {
  MEMORY_CROP_STATE_LABELS,
  MEMORY_DATA_CLASS_LABELS,
  MEMORY_ORIGIN_KIND_LABELS,
  MEMORY_REASON_CODES,
  MEMORY_REASON_LABELS,
  MEMORY_STATUS_EVENT_LABELS,
  MEMORY_STATUS_LABELS,
  MEMORY_STATUS_TONES,
  MEMORY_TRAINING_USE_LABELS,
  MEMORY_VERDICT_LABELS,
} from './model/labels';
export type {
  MemoryDataClass,
  MemoryOriginKind,
  MemoryReason,
  MemoryStatus,
  MemoryStatusEventKind,
  MemoryTrainingUse,
  MemoryVerdict,
} from './model/labels';

export {
  MEMORY_DATA_CLASS_CHOICES,
  MEMORY_STATUS_CHOICES,
  MEMORY_VERDICT_CHOICES,
  NO_MEMORY_FILTERS,
  memoryFiltersNarrow,
  memoryListQuery,
} from './model/filters';
export type { MemoryDataClassChoice, MemoryFilters, MemoryStatusChoice, MemoryVerdictChoice } from './model/filters';

export { memoryAccessOf, useMemoryAccess } from './model/access';
export type { MemoryAccess } from './model/access';

export { MEMORY_PAGE_LIMIT, useDecisionMemoryCase, useDecisionMemoryCases, useDecisionMemoryStatus } from './api/use-decision-memory';
