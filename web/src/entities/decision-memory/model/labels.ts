/**
 * The Russian words of the decision memory (`D-495`, `DECISION-MEMORY-01`).
 *
 * Each table is keyed by the contract's closed set, so a value the contract adds does not compile until it has a word. The
 * contract values stay on `data-*` attributes of the markup that draws them; the reader sees Russian.
 */

import type {
  DecisionMemoryCaseSummary,
  DecisionMemoryDecision,
  DecisionMemoryStatus,
  DecisionMemoryStatusChangeRequest,
  DecisionMemoryStatusEvent,
} from '@/shared/api';

export type MemoryStatus = DecisionMemoryCaseSummary['status'];
export type MemoryDataClass = DecisionMemoryCaseSummary['data_class'];
export type MemoryVerdict = NonNullable<DecisionMemoryCaseSummary['current_verdict']>;
export type MemoryReason = DecisionMemoryStatusChangeRequest['reason_code'];
export type MemoryOriginKind = DecisionMemoryDecision['origin_kind'];
export type MemoryStatusEventKind = DecisionMemoryStatusEvent['kind'];
export type MemoryTrainingUse = DecisionMemoryStatus['training_use'];

/** «Состояние»: where a case stands. A withdrawn case stays in the memory and leaves hints, prompts and exports. */
export const MEMORY_STATUS_LABELS: Readonly<Record<MemoryStatus, string>> = {
  active: 'Действует',
  withdrawn: 'Отозвано',
  forgotten: 'Забыто',
};

/** The badge tone of a standing (the global `.am-badge--*` set). */
export const MEMORY_STATUS_TONES: Readonly<Record<MemoryStatus, 'ok' | 'degraded' | 'inert'>> = {
  active: 'ok',
  withdrawn: 'degraded',
  forgotten: 'inert',
};

/** «Данные»: whether the case was captured from test or from real documents (fixed at capture). */
export const MEMORY_DATA_CLASS_LABELS: Readonly<Record<MemoryDataClass, string>> = {
  test: 'Тестовые',
  real: 'Реальные',
};

export const MEMORY_TRAINING_USE_LABELS: Readonly<Record<MemoryTrainingUse, string>> = {
  off: 'выключено',
  on: 'включено',
};

/** The closed reasons of a withdraw or a restore, in the order the contract lists them. No free text: it would be kept for ever. */
export const MEMORY_REASON_CODES: readonly MemoryReason[] = [
  'capture_defect',
  'wrong_decision',
  'client_request',
  'test_data',
  'other',
];

export const MEMORY_REASON_LABELS: Readonly<Record<MemoryReason, string>> = {
  capture_defect: 'Дефект захвата',
  wrong_decision: 'Ошибочное решение',
  client_request: 'Просьба клиента',
  test_data: 'Тестовые данные',
  other: 'Другая причина',
};

export const MEMORY_VERDICT_LABELS: Readonly<Record<MemoryVerdict, string>> = {
  accepted: 'Принято',
  rejected: 'Отклонено',
};

export const MEMORY_ORIGIN_KIND_LABELS: Readonly<Record<MemoryOriginKind, string>> = {
  direct: 'решено на находке',
  carried: 'перенесено из прошлой версии',
  imported: 'загружено из книги решений',
};

export const MEMORY_STATUS_EVENT_LABELS: Readonly<Record<MemoryStatusEventKind, string>> = {
  withdraw: 'Отозвано',
  restore: 'Возвращено',
  forget: 'Содержимое забыто',
};

/** «Кадры»: whether the case references crop images (the images themselves are not served yet). */
export const MEMORY_CROP_STATE_LABELS: Readonly<Record<DecisionMemoryCaseSummary['crop_state'], string>> = {
  referenced: 'есть',
  none_available: 'нет',
};
