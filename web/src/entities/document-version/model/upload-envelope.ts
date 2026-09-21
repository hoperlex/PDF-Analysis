/**
 * The PC-01 input envelope, stated once, in the words the user is shown.
 *
 * The envelope is a product rule, not a UI preference: one unencrypted PDF, at most
 * 25 MiB and at most 30 pages, every page carrying extractable embedded text. The
 * contract states it on `uploadDocument`, and the server is its authority.
 *
 * Two things live here and nothing else:
 *
 *   1. The rule text, so the panel can show the envelope **before** the user picks a
 *      file. A rule the user only learns by being rejected is a rule the product kept
 *      secret; showing it up front is the difference between a constraint and a trap.
 *   2. A pre-check of the two properties a browser can actually see — the declared media
 *      type and the byte size. Page count, encryption and the text layer are **not**
 *      checked here: reading them would mean parsing the PDF in the browser, which
 *      `P3-WEB-01` rules out as a non-goal, and a client that guessed at them would
 *      either refuse a legal file or promise a rejected one.
 */

/** The frozen envelope, in the units the contract uses. */
export const PC01_UPLOAD_ENVELOPE = {
  /** Exactly one file per upload. There is no multi-file and no archive path. */
  fileCount: 1,
  mediaType: 'application/pdf',
  /** 25 MiB, in bytes. Mebibytes, not megabytes: the contract says MiB. */
  maxBytes: 25 * 1024 * 1024,
  maxBytesLabel: '25 MiB',
  maxPages: 30,
} as const;

/**
 * The envelope as the user reads it, shown before a file is chosen.
 *
 * Each line names one refusal reason the server can return, so a rejection later is
 * recognisable as the rule that was on screen rather than as a surprise.
 */
export const UPLOAD_ENVELOPE_RULES: readonly string[] = [
  'Один PDF за загрузку. Без архива, без сопутствующего файла и без второго документа.',
  `Не более ${PC01_UPLOAD_ENVELOPE.maxBytesLabel}.`,
  `Не более ${PC01_UPLOAD_ENVELOPE.maxPages} страниц.`,
  'Без пароля и без шифрования.',
  'Каждая страница несёт извлекаемый встроенный текст. Отсканированный или чисто графический PDF отклоняется; текст не восстанавливается оптическим распознаванием.',
];

/**
 * Which of the two browser-visible rules a chosen file breaks. `null` means the file
 * passes the checks a browser can make — never that the server will accept it.
 */
export type UploadPrecheckProblem = 'not_pdf' | 'too_large' | 'empty_file';

/** The properties of a chosen file this module reads. A `File` satisfies it. */
export interface ChosenFile {
  readonly name: string;
  readonly size: number;
  readonly type: string;
}

/** Whether a name ends in the PDF extension, case-insensitively. */
function hasPdfExtension(name: string): boolean {
  return name.toLowerCase().endsWith('.pdf');
}

/**
 * Check the media type and the byte size, and nothing else.
 *
 * The browser's declared `type` is trusted only to reject: a file that announces itself
 * as something other than a PDF is refused, and a file announcing nothing falls back to
 * its extension. Neither is evidence of a valid PDF, which is why the server checks
 * again and why a pass here renders no reassurance.
 */
export function precheckUploadFile(file: ChosenFile): UploadPrecheckProblem | null {
  const declared = file.type.trim().toLowerCase();
  const looksPdf =
    declared === PC01_UPLOAD_ENVELOPE.mediaType || (declared === '' && hasPdfExtension(file.name));
  if (!looksPdf) return 'not_pdf';
  if (file.size <= 0) return 'empty_file';
  if (file.size > PC01_UPLOAD_ENVELOPE.maxBytes) return 'too_large';
  return null;
}

/** The user-facing sentence for a pre-check refusal. */
export function precheckProblemMessage(problem: UploadPrecheckProblem): string {
  switch (problem) {
    case 'not_pdf':
      return 'Этот файл не является PDF. Принимается один незашифрованный PDF и ничего больше.';
    case 'empty_file':
      return 'Этот файл пуст.';
    case 'too_large':
      return `Этот файл больше, чем ${PC01_UPLOAD_ENVELOPE.maxBytesLabel}.`;
  }
}

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
