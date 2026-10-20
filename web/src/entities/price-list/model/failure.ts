/**
 * A refused price-list upload or vendor-list change, said in Russian (`W60-PRICE-LIST-01`).
 *
 * The API refuses a file that cannot be a price list with `validation_failed`,
 * `field: content` and one `constraint`; each constraint has its own sentence here, which says
 * what to do about it. Everything else falls back to the shared reading of the catalog code
 * (`failureMessage`), so no refusal is ever shown as the API's English message.
 */

import { ApiError } from '@/shared/api';
import type { FailureMessage } from '@/shared/api/failure-message';
import { failureMessage } from '@/shared/api/failure-message';

/** Every file constraint `uploadPriceList` can answer, with what the expert should do. */
export const UPLOAD_CONSTRAINT_TEXT: Readonly<Record<string, string>> = {
  non_empty: 'Файл пуст.',
  'byte_size <= 10485760': 'Файл больше 10 MiB. Разделите прайс-лист на части.',
  price_list_format:
    'Книги Excel 97–2003 не читаются: сохраните прайс-лист как книгу Excel нового формата или как CSV.',
  price_list_unreadable:
    'Файл не удалось прочитать: книга Excel повреждена или текст CSV искажён.',
  price_list_encoding:
    'Текст файла не в кодировке UTF-8 и не в кириллической кодировке 1251. Сохраните его как CSV в UTF-8.',
  'xlsx_part_size <= 67108864': 'Книга Excel после распаковки слишком велика.',
  price_list_header:
    'В первых 20 непустых строках нет заголовка со столбцами наименования, единицы измерения и цены.',
  price_list_header_ambiguous:
    'Наименование, единицу измерения или цену можно взять из нескольких столбцов. Оставьте один такой столбец и загрузите файл снова.',
  'data_rows <= 20000': 'В прайс-листе больше 20 000 строк данных. Разделите его на части.',
  price_list_no_positions:
    'Ни одна строка не прочитана как позиция: проверьте наименования, единицы измерения и цены.',
};

/** What a refused vendor-list change means, by its reason. */
export const VENDOR_LIST_CONFLICT_TEXT =
  'Список изменили, пока вы его редактировали. Обновите вкладку и внесите изменение снова.';
export const INHERIT_WITH_ENTRIES_TEXT =
  'Чтобы вернуться к общему списку, сначала удалите записи списка проекта.';

function constraintOf(error: unknown): string | null {
  if (!(error instanceof ApiError) || error.errorCode !== 'validation_failed') return null;
  const constraint = error.details['constraint'];
  return typeof constraint === 'string' ? constraint : null;
}

/** The sentence for a refused upload: the file's own reason when it has one. */
export function uploadFailureMessage(error: unknown): FailureMessage {
  const base = failureMessage(error, {
    idempotency_key_reuse:
      'Этот запрос уже был отправлен с другим файлом. Выберите файл заново и повторите загрузку.',
  });
  const constraint = constraintOf(error);
  const detail = constraint === null ? undefined : UPLOAD_CONSTRAINT_TEXT[constraint];
  if (detail !== undefined) return { ...base, detail };
  if (constraint === 'plain_base_name' || constraint === 'char_length <= 255') {
    return { ...base, detail: 'Имя файла не подходит: переименуйте файл и загрузите его снова.' };
  }
  return base;
}

/** The sentence for a refused vendor-list change. */
export function vendorListFailureMessage(error: unknown): FailureMessage {
  const base = failureMessage(error, { conflict: VENDOR_LIST_CONFLICT_TEXT });
  if (constraintOf(error) === 'inherit_has_no_entries') {
    return { ...base, detail: INHERIT_WITH_ENTRIES_TEXT };
  }
  return base;
}
