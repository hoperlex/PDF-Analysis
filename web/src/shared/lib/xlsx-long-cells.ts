/**
 * Cells longer than Excel allows, moved to a sheet of their own instead of refusing the workbook
 * (owner 2026-11-18).
 *
 * Excel opens no cell longer than 32 767 characters (UTF-16 code units). The two technical
 * workbooks the browser writes (`entities/audit-run/lib/extended-xlsx.ts`,
 * `widgets/stage-v3-experimental/model/xlsx.ts`) used to refuse the whole file when one value was
 * longer — on a large run a JSON value of the «Summary» sheet was, and the expert got no workbook.
 *
 * Now such a cell keeps the beginning of its value and a reference — key, sheet name, number of
 * parts — and the **whole** value goes to the `LongText` sheet in parts of 32 000, joined in order
 * without separators, the rule `RawJSONchunks` already states. Nothing is cut away: the parts are
 * the value, beginning included. The sheet exists only when a value needs it.
 */

/** Excel's limit for one cell, in UTF-16 code units. */
export const XLSX_MAX_CELL = 32_767;

/** One part on the `LongText` sheet; under the limit, as `RawJSONchunks` parts are. */
export const LONG_TEXT_PART = 32_000;

/** How much of a long value stays in its own cell, before the reference. */
export const LONG_TEXT_HEAD = 2_000;

/** The sheet the long values go to. */
export const LONG_TEXT_SHEET = 'LongText';

const LONG_TEXT_HEADER = ['Ключ', 'Лист', 'Ячейка', 'Часть', 'Всего частей', 'Полный текст, последовательные части без разделителей'] as const;

/** The column letters of a zero-based column index: 0 → A, 26 → AA. */
export function xlsxColumn(index: number): string {
  let value = index + 1;
  let result = '';
  while (value > 0) {
    const digit = (value - 1) % 26;
    result = String.fromCharCode(65 + digit) + result;
    value = Math.floor((value - 1) / 26);
  }
  return result;
}

/** `value` in parts of at most `size` code units, never splitting a surrogate pair. */
export function splitUtf16(value: string, size: number): string[] {
  const parts: string[] = [];
  for (let start = 0; start < value.length;) {
    let end = Math.min(start + size, value.length);
    const last = value.charCodeAt(end - 1);
    const next = value.charCodeAt(end);
    if (end < value.length && last >= 0xD800 && last <= 0xDBFF && next >= 0xDC00 && next <= 0xDFFF) end -= 1;
    parts.push(value.slice(start, end));
    start = end;
  }
  return parts;
}

export interface XlsxTextTable {
  readonly name: string;
  readonly rows: string[][];
}

/**
 * The same tables with every cell over {@link XLSX_MAX_CELL} replaced by its beginning and a
 * reference, plus the `LongText` table holding those values whole — or `null` when no cell was
 * too long. Cell addresses are the ones the writer gives: row `n` of the table is Excel row
 * `n + 1`, column `c` is {@link xlsxColumn}`(c)`.
 */
export function moveLongCells(tables: readonly XlsxTextTable[]): { readonly tables: XlsxTextTable[]; readonly longText: XlsxTextTable | null } {
  const longRows: string[][] = [[...LONG_TEXT_HEADER]];
  let count = 0;
  const moved = tables.map((table) => ({
    name: table.name,
    rows: table.rows.map((row, rowIndex) => row.map((value, columnIndex) => {
      if (value.length <= XLSX_MAX_CELL) return value;
      count += 1;
      const key = `T-${String(count)}`;
      const parts = splitUtf16(value, LONG_TEXT_PART);
      const cell = `${xlsxColumn(columnIndex)}${String(rowIndex + 1)}`;
      parts.forEach((part, index) => longRows.push([key, table.name, cell, String(index + 1), String(parts.length), part]));
      const head = splitUtf16(value, LONG_TEXT_HEAD)[0] ?? '';
      return `${head}… [продолжение: лист ${LONG_TEXT_SHEET}, ключ ${key}, частей ${String(parts.length)}]`;
    })),
  }));
  return { tables: moved, longText: longRows.length > 1 ? { name: LONG_TEXT_SHEET, rows: longRows } : null };
}

/** The «Summary» row that says what the `LongText` sheet is, for a workbook that has one. */
export const LONG_TEXT_SUMMARY_ROW: readonly [string, string] = [
  'Длинные значения',
  `Значения длиннее ${String(XLSX_MAX_CELL)} символов (предел ячейки Excel): в ячейке начало и ключ, полный текст на листе ${LONG_TEXT_SHEET}. Части одного ключа соединять по порядку без разделителей.`,
];
