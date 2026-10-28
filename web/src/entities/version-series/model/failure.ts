/**
 * A refusal of a comparison operation, in a reviewer's words (`CMP-SEAL-C0`, `CMP-SEAL-C1`).
 *
 * The contract adds no error code for the comparison module: every refusal rides an existing code with a
 * registered **reason** in one safe detail key — `conflict_reason` under `conflict`, `constraint` under
 * `validation_failed`, `dependency` under `dependency_unavailable`, `role` under `storage_integrity_error`
 * (`contracts/domain/v1/error-codes.json`, the notes of those four codes). `catalog-message.ts` words a
 * *code*; the reasons are the screens' words, and this file is where they live, as the preset and
 * pairing refusals keep theirs next to their entities. A reason this table does not know falls back to
 * the code's own catalogue sentence, never to the server's English.
 *
 * `dependency_unavailable` is the **normal state of a module that is not wired yet or is off**: it is not
 * a crash and not an empty list, and {@link ComparisonFailure.moduleUnavailable} lets a screen show
 * «Модуль ещё недоступен» instead of a red error.
 */

import { ApiError, failureMessage } from '@/shared/api';
import type { FailureKind } from '@/shared/api/failure-message';

/** `conflict_reason`s of the comparison modules (`error-codes.json`, `conflict` notes). */
export const COMPARISON_CONFLICT_SENTENCES: Readonly<Record<string, string>> = {
  comparison_upload_active:
    'У вас уже есть незавершённая загрузка для сравнения (на стенде их не больше двух). Завершите или удалите её, затем загрузите снова.',
  comparison_upload_state:
    'Загрузка сейчас в другом состоянии, и это действие ей не подходит: например, часть присылают после завершения, продолжают не остановленную загрузку или удаляют завершённую.',
  comparison_set_state:
    'Комплект сейчас в другом состоянии, и это действие ему не подходит. Повтор возможен только для комплекта с ошибкой, которую повтор может исправить.',
  comparison_version_order_stale:
    'Порядок версий уже изменили после того, как вы его открыли. Ничего не сохранено; порядок прочитан заново.',
  comparison_matrix_stale:
    'Сопоставление листов изменилось после того, как вы его открыли: пересобрано или правлено другим человеком. Ничего не применено; сопоставление прочитано заново, а ваши правки остались в черновике.',
  comparison_edit_none: 'Отменять нечего: в этом комплекте нет применённых правок.',
  comparison_series_active:
    'Сравнение соседних версий этого комплекта уже идёт, стоит в очереди или на паузе. Дождитесь его конца или остановите его.',
  comparison_series_state:
    'Сравнение соседних версий сейчас в другом состоянии, и это действие ему не подходит. Состояние прочитано заново.',
};

/** `constraint`s of the comparison modules (`error-codes.json`, `validation_failed` notes). */
export const COMPARISON_CONSTRAINT_SENTENCES: Readonly<Record<string, string>> = {
  comparison_files_limit: 'В одной загрузке больше 10 000 файлов. Ничего не создано.',
  comparison_sets_limit: 'Файлы образуют больше 100 комплектов. Разделите загрузку.',
  comparison_batch_bytes_limit: 'Заявленный объём загрузки больше 8 ГиБ. Ничего не создано.',
  comparison_batch_pages_limit: 'В загрузке заявлено больше 10 000 страниц. Ничего не создано.',
  comparison_project_bytes_limit:
    'Вместе с тем, что проект уже хранит для сравнения, получилось бы больше 8 ГиБ. Ничего не создано.',
  comparison_part_number: 'У этого файла не должно быть части с таким номером: размер файла требует меньше частей.',
  comparison_part_size:
    'Часть больше 16 МиБ, либо часть не последняя и короче размера части загрузки.',
  comparison_set_members:
    'В подтверждении должны быть все файлы комплекта, каждый один раз, и только они. Файл другого комплекта сюда не переносится.',
  comparison_edit_invalid:
    'Правка не подходит: лист не принадлежит версии этого комплекта, связь соединяет версию с самой собой, либо для этого вида правки не хватает данных. Ничего не применено.',
  comparison_edits_limit: 'В одной пачке больше 500 правок. Ничего не применено; примените часть правок и повторите.',
  display_name: 'Имя файла состоит из одних управляющих знаков, показать его нельзя.',
  required_together: 'Стадию и раздел указывают вместе или не указывают вовсе.',
  declared_page_count: 'Заявленное число страниц не совпало с числом страниц документа.',
  comparison_zip_unreadable: 'Это не ZIP-архив, либо его оглавление не удаётся прочитать в допустимых пределах.',
  comparison_zip_entry_count: 'В архиве больше 1 000 записей вместе с вложенным архивом.',
  comparison_zip_member_name: 'В архиве есть имя с абсолютным путём, буквой диска, обратной косой чертой или «..».',
  comparison_zip_symlink: 'В архиве есть символическая ссылка.',
  comparison_zip_encrypted_member: 'В архиве есть зашифрованный файл.',
  comparison_zip_compression_method: 'В архиве есть способ сжатия, кроме хранения без сжатия и deflate.',
  comparison_zip_duplicate_member: 'В архиве повторяется имя файла, в том числе после приведения регистра.',
  comparison_zip_member_kind: 'В архиве есть файл, который не PDF и не вложенный архив первого уровня.',
  comparison_zip_nested_depth: 'Архив вложен в архив, который сам лежит в архиве: глубже одного уровня нельзя.',
  comparison_zip_member_size: 'Один из файлов архива больше 250 МиБ.',
  comparison_zip_total_size: 'Содержимое архива вместе больше 2 ГиБ.',
  comparison_zip_compression_ratio: 'Файл или архив сжат больше чем в 100 раз.',
  comparison_zip_empty: 'В архиве нет ни одного PDF-документа.',
};

const MODULE_UNAVAILABLE = 'Модуль «Сравнение версий» ещё недоступен';

/** The part of the module that is not wired, named after a colon so that no word has to agree with it. */
function notWired(part: string): string {
  return `${MODULE_UNAVAILABLE}. На этом стенде пока не подключена его часть: ${part}. Ничего не создано и не изменено; вернитесь позже.`;
}

/** `dependency`s of the comparison modules (`error-codes.json`, `dependency_unavailable` notes). */
export const COMPARISON_DEPENDENCY_SENTENCES: Readonly<Record<string, string>> = {
  comparison_uploads: notWired('загрузка файлов для сравнения'),
  comparison_version_orders: notWired('смена порядка версий'),
  version_pages: notWired('чтение страниц версий'),
  comparison_matrix: notWired('сопоставление листов'),
  comparison_series: notWired('сравнение соседних версий'),
  comparison_pair_tiles: notWired('показ листов пары'),
  comparison_overview: notWired('сводка по комплектам'),
  comparison_modules:
    'Модуль «Сравнение версий» выключен на этом стенде, поэтому его операции ничего не делают. Включает его администратор стенда.',
  comparison_versions_module:
    'Подтверждение пар листов и сводка по подтверждённым парам больше здесь не ведутся: сопоставление листов версий — в разделе «Сравнение версий». Ничего не создано.',
};

/** `storage_integrity_error` of a comparison file: the received bytes are not the declared ones. */
export const COMPARISON_INTEGRITY_SENTENCE =
  'Принятый файл не совпал с заявленным: другая контрольная сумма или другой размер. Файл не опубликован; его нужно отправить заново.';

/** The `failure_reason` a file or a set of an upload may carry. */
export const UPLOAD_FAILURE_REASON_SENTENCES: Readonly<Record<string, string>> = {
  comparison_file_sha256: 'Контрольная сумма принятого файла не совпала с заявленной. Отправьте файл заново.',
  comparison_file_size: 'Размер принятого файла не совпал с заявленным. Отправьте файл заново.',
  staged_upload_lost: 'Хранилище больше не держит присланные части файла. Отправьте файл заново.',
  batch_cancelled: 'Загрузка удалена до того, как файл был принят.',
  comparison_sets_limit: 'Комплектов в загрузке больше 100: этот не поместился. Исключите лишний комплект и повторите.',
};

export const UNDESCRIBED_FAILURE = 'Причина не описана этим клиентом; код ошибки передан администратору.';

/** The sentence of a file's `failure_reason`, including the refusals of the PDF envelope (`content_<constraint>`). */
export function uploadFailureReasonSentence(
  reason: string | undefined,
  envelope: (constraint: string) => string | null,
): string {
  if (reason === undefined || reason === '') return '';
  const known = UPLOAD_FAILURE_REASON_SENTENCES[reason];
  if (known !== undefined) return known;
  if (reason.startsWith('content_')) {
    const sentence = envelope(reason.slice('content_'.length));
    if (sentence !== null) return sentence;
  }
  return UNDESCRIBED_FAILURE;
}

function detail(error: ApiError, key: string): string | null {
  const value = error.details[key];
  return typeof value === 'string' ? value : null;
}

/** The sentence of a registered comparison reason, or `null` when the refusal has none. */
export function comparisonReasonSentence(error: ApiError): string | null {
  switch (error.errorCode) {
    case 'conflict': {
      const reason = detail(error, 'conflict_reason');
      return reason === null ? null : (COMPARISON_CONFLICT_SENTENCES[reason] ?? null);
    }
    case 'validation_failed': {
      const reason = detail(error, 'constraint');
      return reason === null ? null : (COMPARISON_CONSTRAINT_SENTENCES[reason] ?? null);
    }
    case 'dependency_unavailable': {
      const reason = detail(error, 'dependency');
      return reason === null ? null : (COMPARISON_DEPENDENCY_SENTENCES[reason] ?? null);
    }
    case 'storage_integrity_error':
      return detail(error, 'role') === 'comparison_file_size' || detail(error, 'expected_sha256') !== null
        ? COMPARISON_INTEGRITY_SENTENCE
        : null;
    default:
      return null;
  }
}

export type ComparisonFailureKind = FailureKind | 'matrix_stale' | 'module_unavailable';

export interface ComparisonFailure {
  readonly kind: ComparisonFailureKind;
  /** The Russian sentence a screen renders. Never a thrown value's own message. */
  readonly detail: string;
  readonly correlationId: string | null;
  readonly retryable: boolean;
  /** The module is not wired or is off: a state, shown as such. */
  readonly moduleUnavailable: boolean;
  /** `409 comparison_matrix_stale`: the draft is rebased, not lost. */
  readonly matrixStale: boolean;
  /** `409 comparison_version_order_stale`. */
  readonly orderStale: boolean;
}

/** Any dependency refusal of the comparison surface is the module state, whichever reason it names. */
function isModuleUnavailable(error: unknown): boolean {
  return error instanceof ApiError && error.errorCode === 'dependency_unavailable' &&
    COMPARISON_DEPENDENCY_SENTENCES[detail(error, 'dependency') ?? ''] !== undefined;
}

/** Classify what a comparison read or command threw, and say it in Russian. */
export function comparisonFailure(error: unknown): ComparisonFailure {
  const base = failureMessage(error);
  const moduleUnavailable = isModuleUnavailable(error);
  if (error instanceof ApiError) {
    const sentence = comparisonReasonSentence(error);
    const reason = detail(error, 'conflict_reason');
    return {
      kind: moduleUnavailable ? 'module_unavailable' : reason === 'comparison_matrix_stale' ? 'matrix_stale' : base.kind,
      detail: sentence ?? base.detail,
      correlationId: base.correlationId,
      retryable: base.retryable,
      moduleUnavailable,
      matrixStale: error.errorCode === 'conflict' && reason === 'comparison_matrix_stale',
      orderStale: error.errorCode === 'conflict' && reason === 'comparison_version_order_stale',
    };
  }
  return {
    kind: base.kind,
    detail: base.detail,
    correlationId: base.correlationId,
    retryable: base.retryable,
    moduleUnavailable: false,
    matrixStale: false,
    orderStale: false,
  };
}
