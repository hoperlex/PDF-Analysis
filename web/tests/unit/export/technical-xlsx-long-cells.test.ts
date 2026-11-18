/**
 * Owner 2026-11-18: a value longer than Excel's cell limit no longer refuses the technical
 * workbook. The cell keeps its beginning and a key; the whole value is on the «LongText» sheet,
 * in parts joined in order without separators. Read back from the real archive the writers
 * produce (ZIP STORE), not from the tables before they are written.
 */
import { describe, expect, it } from 'vitest';

import type { ExtendedRunReview, StageChainRun } from '@/shared/api';
import { formatExtendedRunReport } from '@/entities/audit-run';
import { LONG_TEXT_PART, XLSX_MAX_CELL, moveLongCells, splitUtf16 } from '@/shared/lib/xlsx-long-cells';
import { formatStageV3Xlsx } from '@/widgets/stage-v3-experimental/model/xlsx';

/** name → text of every part of a STORE archive. */
function unzip(buffer: ArrayBuffer): Map<string, string> {
  const view = new DataView(buffer);
  const bytes = new Uint8Array(buffer);
  const decoder = new TextDecoder();
  const parts = new Map<string, string>();
  let offset = 0;
  while (view.getUint32(offset, true) === 0x04034B50) {
    const size = view.getUint32(offset + 18, true);
    const nameLength = view.getUint16(offset + 26, true);
    const extraLength = view.getUint16(offset + 28, true);
    const name = decoder.decode(bytes.subarray(offset + 30, offset + 30 + nameLength));
    const start = offset + 30 + nameLength + extraLength;
    parts.set(name, decoder.decode(bytes.subarray(start, start + size)));
    offset = start + size;
  }
  return parts;
}

const unescapeXml = (value: string) => value.replace(/&#13;/g, '\r').replace(/&quot;/g, '"').replace(/&apos;/g, "'")
  .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');

interface Workbook { readonly sheets: string[]; readonly cells: Map<string, Map<string, string>> }

/** Sheet names in order, and sheet name → cell address → text. */
function workbook(buffer: ArrayBuffer): Workbook {
  const parts = unzip(buffer);
  const sheets = [...(parts.get('xl/workbook.xml') ?? '').matchAll(/<sheet name="([^"]*)"/g)].map((match) => unescapeXml(match[1] ?? ''));
  const cells = new Map<string, Map<string, string>>();
  sheets.forEach((sheet, index) => {
    const xml = parts.get(`xl/worksheets/sheet${String(index + 1)}.xml`) ?? '';
    const byAddress = new Map<string, string>();
    for (const match of xml.matchAll(/<c r="([A-Z]+[0-9]+)" t="inlineStr"><is><t xml:space="preserve">([\s\S]*?)<\/t><\/is><\/c>/g)) {
      byAddress.set(match[1] ?? '', unescapeXml(match[2] ?? ''));
    }
    cells.set(sheet, byAddress);
  });
  return { sheets, cells };
}

/** The value of key `key` on «LongText», its parts joined in order. */
function joined(book: Workbook, key: string): { sheet: string; cell: string; text: string; parts: number } {
  const long = book.cells.get('LongText') ?? new Map<string, string>();
  const rows: { part: number; total: number; sheet: string; cell: string; text: string }[] = [];
  for (let row = 2; long.has(`A${String(row)}`); row += 1) {
    if (long.get(`A${String(row)}`) !== key) continue;
    rows.push({ sheet: long.get(`B${String(row)}`) ?? '', cell: long.get(`C${String(row)}`) ?? '', part: Number(long.get(`D${String(row)}`)),
      total: Number(long.get(`E${String(row)}`)), text: long.get(`F${String(row)}`) ?? '' });
  }
  rows.sort((left, right) => left.part - right.part);
  expect(rows.every((row) => row.total === rows.length)).toBe(true);
  return { sheet: rows[0]?.sheet ?? '', cell: rows[0]?.cell ?? '', text: rows.map((row) => row.text).join(''), parts: rows.length };
}

/** A long text with characters outside the BMP, so a part boundary can fall inside a pair. */
const LONG = 'Пропуск блока 😀 на листе; '.repeat(4_000);

const reading = (originalReview: unknown): ExtendedRunReview => ({ run_id: 'run_01M664JCG1QH0NTEWZTC3PM19K', status: 'completed',
  result: { workflow_version: 'extended-review-v2', procedures: [], observations: [], sources: [], warnings: [], original_review: originalReview } });

function technicalXlsx(value: ExtendedRunReview): ArrayBuffer {
  return formatExtendedRunReport(value, 'xlsx').content as ArrayBuffer;
}

function summaryValue(book: Workbook, label: string): string | undefined {
  const summary = book.cells.get('Summary') ?? new Map<string, string>();
  for (const [address, text] of summary) if (address.startsWith('A') && text === label) return summary.get(`B${address.slice(1)}`);
  return undefined;
}

describe('the technical workbook of an analysis run', () => {
  it('is written when a Summary value is longer than a cell, and keeps that value whole on «LongText»', () => {
    const review = { mode: 'deterministic', notes: LONG };
    const book = workbook(technicalXlsx(reading(review)));
    const expected = JSON.stringify(review, null, 2);
    expect(expected.length).toBeGreaterThan(XLSX_MAX_CELL * 3);

    expect(book.sheets.at(-1)).toBe('LongText');
    for (const sheet of book.cells.values()) for (const text of sheet.values()) expect(text.length).toBeLessThanOrEqual(XLSX_MAX_CELL);

    const cell = summaryValue(book, 'Критик и корректор оригинала (без модели)') ?? '';
    expect(cell.startsWith(expected.slice(0, 1_000))).toBe(true);
    expect(cell).toContain('[продолжение: лист LongText, ключ T-1, частей 4]');

    const whole = joined(book, 'T-1');
    expect(whole).toMatchObject({ sheet: 'Summary', parts: 4 });
    expect(book.cells.get('Summary')?.get(whole.cell)).toBe(cell);
    expect(whole.text).toBe(expected);
    expect(summaryValue(book, 'Длинные значения')).toContain('LongText');
  });

  it('has no «LongText» sheet and no note about it while every value fits', () => {
    const book = workbook(technicalXlsx(reading({ mode: 'deterministic', notes: 'коротко' })));
    expect(book.sheets).not.toContain('LongText');
    expect(summaryValue(book, 'Длинные значения')).toBeUndefined();
  });
});

describe('the technical workbook of a V3 stage run', () => {
  it('is written when a Summary value is longer than a cell, and keeps that value whole on «LongText»', () => {
    const coverage = { skipped: LONG };
    const run = { experimental_progress: { coverage } } as unknown as StageChainRun;
    const book = workbook(formatStageV3Xlsx('run_01M664JCG1QH0NTEWZTC3PM19K', [], run).content);
    for (const sheet of book.cells.values()) for (const text of sheet.values()) expect(text.length).toBeLessThanOrEqual(XLSX_MAX_CELL);
    expect(summaryValue(book, 'Покрытие')).toContain('ключ T-1');
    expect(joined(book, 'T-1').text).toBe(JSON.stringify(coverage, null, 2));
  });
});

describe('the helper', () => {
  it('never splits a surrogate pair and loses nothing', () => {
    const value = `${'a'.repeat(LONG_TEXT_PART - 1)}😀${'b'.repeat(10)}`;
    const parts = splitUtf16(value, LONG_TEXT_PART);
    expect(parts.join('')).toBe(value);
    expect(parts[0]?.length).toBe(LONG_TEXT_PART - 1);
    expect(parts.every((part) => !/[\uD800-\uDBFF]$/.test(part))).toBe(true);
  });

  it('numbers keys in order and leaves a value of exactly the limit in place', () => {
    const atLimit = 'x'.repeat(XLSX_MAX_CELL);
    const { tables, longText } = moveLongCells([{ name: 'S', rows: [['h'], [atLimit], [`${atLimit}y`], [`${atLimit}z`]] }]);
    expect(tables[0]?.rows[1]?.[0]).toBe(atLimit);
    expect(tables[0]?.rows[2]?.[0]).toContain('ключ T-1');
    expect(tables[0]?.rows[3]?.[0]).toContain('ключ T-2');
    expect(longText?.rows.slice(1).map((row) => [row[0], row[2]])).toEqual([['T-1', 'A3'], ['T-1', 'A3'], ['T-2', 'A4'], ['T-2', 'A4']]);
  });
});
