/**
 * The PC-01 input envelope, stated once, in the words the user is shown.
 *
 * The envelope is a product rule, not a UI preference: one ZIP archive holding a portal
 * bundle — the PDF the recognition portal exported with its block list (`_blocks.json`)
 * and its recognised text (`_results.md`), plus an optional HTML rendering and stamp
 * audit — at most 250 MiB and at most 500 pages, every page carrying an embedded text
 * layer or at least one portal block. A bare PDF is refused. The contract states it on
 * `uploadDocument`, and the server is its authority.
 *
 * Two things live here and nothing else:
 *
 *   1. The rule text, so the panel can show the envelope **before** the user picks a
 *      file. A rule the user only learns by being rejected is a rule the product kept
 *      secret; showing it up front is the difference between a constraint and a trap.
 *   2. A pre-check of the two properties a browser can actually see — the declared media
 *      type and the byte size. The member set, the page count, encryption and the text
 *      layer are **not** checked here: reading them would mean opening the archive and
 *      parsing the PDF in the browser, which `P3-WEB-01` rules out as a non-goal, and a
 *      client that guessed at them would either refuse a legal file or promise a
 *      rejected one. The server decides what a ZIP is by its first bytes; the browser
 *      only declines what announces itself as something else.
 */

/** The frozen envelope, in the units the contract uses. */
export const PC01_UPLOAD_ENVELOPE = {
  /** Exactly one file per upload: the archive. */
  fileCount: 1,
  /** What a browser declares for a ZIP. Windows browsers say `x-zip-compressed`. */
  mediaType: 'application/zip',
  mediaTypes: ['application/zip', 'application/x-zip-compressed'],
  /** The file input's `accept`: the extension and both media types a browser uses. */
  accept: '.zip,application/zip,application/x-zip-compressed',
  /** 250 MiB, in bytes. Mebibytes, not megabytes: the contract says MiB. */
  maxBytes: 250 * 1024 * 1024,
  maxBytesLabel: '250 MiB',
  /**
   * The browser cannot count pages; it states the limit. The server counts them in the
   * bundle's PDF member and refuses a document over it with `page_count`.
   */
  maxPages: 500,
} as const;

/**
 * The envelope as the user reads it, shown before a file is chosen.
 *
 * Each line names one refusal reason the server can return, so a rejection later is
 * recognisable as the rule that was on screen rather than as a surprise.
 */
export const UPLOAD_ENVELOPE_RULES: readonly string[] = [
  'Один ZIP-архив за загрузку: комплект, который формирует портал распознавания. Отдельный PDF не принимается.',
  'В архиве: PDF-документ, файл блоков и файл распознанного текста с одним общим началом имени и окончаниями _blocks.json и _results.md. Необязательно: файл с окончанием _results.html и аудит штампов с окончанием _stamp_audit.json. Любой другой файл отклоняется.',
  `Не более ${PC01_UPLOAD_ENVELOPE.maxBytesLabel} на архив.`,
  `Не более ${PC01_UPLOAD_ENVELOPE.maxPages} страниц.`,
  'Без пароля и без шифрования: ни PDF, ни файлы архива.',
  'Каждая страница несёт либо извлекаемый встроенный текст, либо хотя бы один блок портала. Страница без того и другого отклоняется; текст не восстанавливается оптическим распознаванием.',
];

/**
 * Which of the two browser-visible rules a chosen file breaks. `null` means the file
 * passes the checks a browser can make — never that the server will accept it.
 */
export type UploadPrecheckProblem = 'not_zip' | 'too_large' | 'empty_file';

/** The properties of a chosen file this module reads. A `File` satisfies it. */
export interface ChosenFile {
  readonly name: string;
  readonly size: number;
  readonly type: string;
}

/** Whether a name ends in the ZIP extension, case-insensitively. */
function hasZipExtension(name: string): boolean {
  return name.toLowerCase().endsWith('.zip');
}

/**
 * Check the media type and the byte size, and nothing else.
 *
 * The browser's declared `type` is trusted only to reject: a file that announces itself
 * as something other than a ZIP is refused, and a file announcing nothing falls back to
 * its extension. Neither is evidence of a valid archive, which is why the server checks
 * the first bytes again and why a pass here renders no reassurance.
 */
export function precheckUploadFile(file: ChosenFile): UploadPrecheckProblem | null {
  const declared = file.type.trim().toLowerCase();
  const looksZip =
    PC01_UPLOAD_ENVELOPE.mediaTypes.some((mediaType) => mediaType === declared) ||
    (declared === '' && hasZipExtension(file.name));
  if (!looksZip) return 'not_zip';
  if (file.size <= 0) return 'empty_file';
  if (file.size > PC01_UPLOAD_ENVELOPE.maxBytes) return 'too_large';
  return null;
}

/** The user-facing sentence for a pre-check refusal. */
export function precheckProblemMessage(problem: UploadPrecheckProblem): string {
  switch (problem) {
    case 'not_zip':
      return 'Этот файл не является ZIP-архивом. Принимается один ZIP-архив — комплект портала распознавания: PDF, файл блоков и файл распознанного текста. Отдельный PDF не принимается.';
    case 'empty_file':
      return 'Этот файл пуст.';
    case 'too_large':
      return `Этот файл больше, чем ${PC01_UPLOAD_ENVELOPE.maxBytesLabel}.`;
  }
}

/**
 * One sentence per constraint the server names when it refuses an upload, stating the
 * rule that was broken and nothing about why the file broke it.
 *
 * The keys are the `details.constraint` values of `validation_failed` on `uploadDocument`:
 * the portal-bundle values registered in `contracts/domain/v1/error-codes.json` and the
 * PDF member's own, which a bundle keeps. A sentence restates the contract's wording for
 * its value and does not add a cause the contract does not name: «зашифрован» is said
 * where the contract says an entry is encrypted, never «зашифрован вами». The server's
 * own message is English for all but one of them, and the envelope does not say whether
 * a message is the catalog's or a call site's (`catalog-message.ts`), so the client
 * states the rule itself.
 */
const UPLOAD_CONSTRAINT_SENTENCES: Readonly<Record<string, string>> = {
  portal_bundle_required:
    'Загружается комплект портала распознавания — ZIP-архив. Отдельный PDF и файл другого вида не принимаются.',
  bundle_unreadable:
    'Оглавление архива не удалось прочитать: файл не читается как ZIP-архив.',
  bundle_entry_count:
    'В архиве больше восьми записей, а комплект портала содержит не больше восьми.',
  bundle_directory_entry:
    'В архиве есть запись-каталог. Комплект портала состоит только из файлов, без каталогов.',
  bundle_member_name:
    'Имя одного из файлов архива не является простым именем файла: оно абсолютное, с буквой диска, с обратной косой чертой или с «..».',
  bundle_symlink:
    'Одна из записей архива помечена как символическая ссылка. Такие записи не принимаются.',
  bundle_encrypted_member:
    'Один из файлов архива зашифрован. Зашифрованные файлы не принимаются.',
  bundle_compression_method:
    'Один из файлов архива сжат способом, который не принимается. Допускаются только хранение без сжатия и обычное сжатие ZIP.',
  bundle_duplicate_member:
    'В архиве повторяется имя файла, в том числе при различии лишь в регистре букв или в записи символов.',
  bundle_stem_mismatch:
    'У файлов архива нет общего начала имени. PDF, файл блоков и файл распознанного текста называются одинаково до окончания.',
  bundle_member_set:
    'Состав архива не совпадает с комплектом портала. Нужны ровно один PDF, один файл с окончанием _blocks.json и один с окончанием _results.md; необязательны файлы с окончаниями _results.html и _stamp_audit.json; других файлов быть не должно.',
  bundle_member_size:
    'Один из файлов архива больше допустимого размера (по заявленному в архиве размеру или по фактическому).',
  bundle_total_size:
    'Файлы архива вместе больше допустимого размера после распаковки (по заявленному размеру или по фактическому).',
  bundle_compression_ratio:
    'Файл или весь архив сжат сильнее, чем допускает комплект портала: отношение распакованного размера к сжатому выше допустимого.',
  blocks_json_invalid:
    'Файл блоков портала не соответствует схеме блоков.',
  blocks_page_count:
    'Страницы в файле блоков не соответствуют числу страниц PDF.',
  results_blocks_mismatch:
    'Файл распознанного текста и файл блоков расходятся: текстовый блок или блок изображения есть в одном из них и отсутствует в другом.',
  stamp_audit_invalid:
    'Файл аудита штампов (_stamp_audit.json) не читается или больше допустимого размера.',
  // The PDF member keeps the envelope constraints it always had.
  pdf_magic_bytes: 'Файл PDF не начинается с признака PDF.',
  parseable_pdf: 'PDF не удалось разобрать.',
  not_encrypted: 'PDF зашифрован. Принимается только PDF без пароля и без шифрования.',
  every_page_has_extractable_text:
    'Хотя бы одна страница не несёт ни извлекаемого встроенного текста, ни блока портала. Текст не восстанавливается оптическим распознаванием.',
  max_bytes: 'Загрузка больше допустимого размера.',
};

/**
 * The two bounds the server writes as a formula, spelled as it spells them. Built from the
 * envelope's own numbers, so a stale spelling — `1 <= page_count <= 30` — is not a rule
 * this client states: it would print a limit the product no longer has.
 */
const PAGE_COUNT_CONSTRAINT = `1 <= page_count <= ${PC01_UPLOAD_ENVELOPE.maxPages}`;
const BYTE_SIZE_CONSTRAINT = `byte_size <= ${PC01_UPLOAD_ENVELOPE.maxBytes}`;

/**
 * The sentence for a `details.constraint` the server named, or `null` when this client
 * has none — in which case the screen shows the constraint's own name and no more.
 */
export function uploadConstraintSentence(constraint: unknown): string | null {
  if (typeof constraint !== 'string') return null;
  if (constraint === PAGE_COUNT_CONSTRAINT) {
    return `Число страниц PDF вне допустимых границ: от 1 до ${PC01_UPLOAD_ENVELOPE.maxPages}.`;
  }
  if (constraint === BYTE_SIZE_CONSTRAINT) {
    return `Размер больше допустимого: не более ${PC01_UPLOAD_ENVELOPE.maxBytesLabel}.`;
  }
  return Object.hasOwn(UPLOAD_CONSTRAINT_SENTENCES, constraint)
    ? (UPLOAD_CONSTRAINT_SENTENCES[constraint] ?? null)
    : null;
}

/** The constraint names this client states a sentence for, for the contract test. */
export const UPLOAD_CONSTRAINTS_STATED: readonly string[] = Object.keys(UPLOAD_CONSTRAINT_SENTENCES);

const BINARY_UNITS = ['B', 'KiB', 'MiB', 'GiB'] as const;

/**
 * A byte count in binary units, matching the contract's MiB. Deliberately not localised,
 * for the same reason `formatInstant` is not: the server render and the browser render
 * must be the same string.
 */
export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return '—';
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < BINARY_UNITS.length - 1) {
    value /= 1024;
    unit += 1;
  }
  const label = BINARY_UNITS[unit] ?? 'B';
  return unit === 0 ? `${value} ${label}` : `${value.toFixed(1)} ${label}`;
}
