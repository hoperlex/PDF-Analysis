/**
 * The words of a comparison upload: the state of a batch, a set and a file, the warnings of a proposal and
 * where an order came from (`version-comparison-batch.js:4-8` status labels, `store.py:223-230` warnings).
 *
 * The ten status labels of the original's batch table are «Загрузка», «Ожидает разбора», «Разбор PDF», «Требуется
 * проверка», «Ожидает обработки», «Подготовка версий», «Сравнение версий», «Готово», «Ошибка», «Исключён». The
 * contract's set states cover eight of them; «Ожидает разбора» and «Сравнение версий» have no state of their own
 * in contract `1.10.0` (a set is `uploading` until its files are read, and the comparison after preparation lives
 * in the series, not in the set), so they are not drawn.
 */

import type {
  ComparisonProposalWarning,
  ComparisonUploadFileState,
  ComparisonUploadSetState,
  ComparisonUploadState,
  ComparisonVersionOrderSource,
} from '@/shared/api';

export const UPLOAD_STATE_LABELS: Readonly<Record<ComparisonUploadState, string>> = {
  uploading: 'передаётся',
  proposed: 'ждёт подтверждения',
  processing: 'обрабатывается',
  paused: 'на паузе после текущего проекта',
  completed: 'завершена',
  cancelled: 'удалена',
};

export const SET_STATUS_LABELS: Readonly<Record<ComparisonUploadSetState, string>> = {
  uploading: 'Загрузка',
  reading: 'Разбор PDF',
  needs_confirmation: 'Требуется проверка',
  ready: 'Ожидает обработки',
  admitting: 'Подготовка версий',
  done: 'Готово',
  failed: 'Ошибка',
  excluded: 'Исключён',
};

export const FILE_STATE_LABELS: Readonly<Record<ComparisonUploadFileState, string>> = {
  declared: 'ждёт отправки',
  uploading: 'передаётся',
  verified: 'принят',
  failed: 'ошибка',
};

export const PROPOSAL_WARNING_LABELS: Readonly<Record<ComparisonProposalWarning, string>> = {
  designations_differ: 'В файлах разные шифры.',
  order_disagrees_with_file_numbers: 'Порядок по штампам не совпадает с номерами в именах файлов.',
  duplicate_revision_number: 'У двух файлов один и тот же номер «Изм.».',
  no_stamp_found: 'Штамп не прочитан: шифр взят из имени папки или файла.',
  scan_without_text: 'В файле есть листы-сканы без текста: они сравниваются только как изображения.',
};

export const ORDER_SOURCE_LABELS: Readonly<Record<ComparisonVersionOrderSource, string>> = {
  proposal: 'предложен по штампам',
  expert: 'задан экспертом',
};

/** A set a reader can act on in each way (the contract's own edges, `CMP-INGEST-02` section 3). */
export function canConfirmSet(state: ComparisonUploadSetState): boolean {
  return state === 'needs_confirmation';
}

export function canExcludeSet(state: ComparisonUploadSetState): boolean {
  return state === 'needs_confirmation' || state === 'failed';
}

export function canRetrySet(state: ComparisonUploadSetState): boolean {
  return state === 'failed';
}

/** A batch that still holds the account's one slot: everything but a finished or deleted one. */
export function uploadIsActive(state: ComparisonUploadState): boolean {
  return state !== 'completed' && state !== 'cancelled';
}
