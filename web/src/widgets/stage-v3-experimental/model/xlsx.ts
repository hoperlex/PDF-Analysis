import type { StageChainRun, StageChangeCard } from '@/shared/api';
import { parameterRows, reportCoverage, reportGlobalConsolidation, reportSnapshot, reportSources, v3Cards } from './report';

/** ZIP STORE/CRC32/OOXML writer copied and adapted from this repository's
 * entities/audit-run/lib/extended-xlsx.ts (SPRINT2-SECTION-1030 source).
 * Tables are stage-specific; no new dependency, cross-entity import or model call.
 * All cells are literal inline strings, never formulas or remote links. */
type RecordValue = Record<string, unknown>;
type Row = readonly unknown[];
interface Table { readonly name: string; readonly rows: Row[] }
const MAX_CELL = 32_767;
const RAW_CHUNK = 32_000;
const MAX_PACKAGE = 64 * 1024 * 1024;
const XML_HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>';
const MAIN = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main';
const REL = 'http://schemas.openxmlformats.org/package/2006/relationships';
const OFFICE_REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships';
const MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
function object(value: unknown): RecordValue | null { return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RecordValue : null; }
function json(value: unknown): string { return JSON.stringify(value ?? null, null, 2) ?? 'null'; }
function cell(value: unknown): string { return value === null || value === undefined ? '' : typeof value === 'string' ? value : typeof value === 'object' ? json(value) : String(value); }
function escapeXml(value: string): string { return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;'); }
function spreadsheetText(value: string): string {
  const literal = value.replace(/_x[0-9a-f]{4}_/gi, (match) => `_x005F_${match.slice(1)}`);
  return escapeXml(literal).replace(/\r/g, '&#13;');
}
function column(index: number): string {
  let value = index + 1; let result = '';
  while (value > 0) { const digit = (value - 1) % 26; result = String.fromCharCode(65 + digit) + result; value = Math.floor((value - 1) / 26); }
  return result;
}
function rawChunks(value: string): string[] {
  const chunks: string[] = [];
  for (let start = 0; start < value.length;) {
    let end = Math.min(start + RAW_CHUNK, value.length);
    const last = value.charCodeAt(end - 1); const next = value.charCodeAt(end);
    if (end < value.length && last >= 0xD800 && last <= 0xDBFF && next >= 0xDC00 && next <= 0xDFFF) end -= 1;
    chunks.push(value.slice(start, end)); start = end;
  }
  return chunks;
}

function tables(runId: string, cards: readonly StageChangeCard[], run: StageChainRun | undefined): Table[] {
  const snapshot = reportSnapshot(runId, cards, run);
  const progress = object(run?.experimental_progress);
  const sourceReport = object(progress?.source_report);
  const summary: Row[] = [['Показатель', 'Значение'], ['Тип', 'Технический предварительный отчёт V3; не экспертное заключение'],
    ['Запуск', runId], ['Состояние', run?.state], ['Устарело', snapshot.stale], ['Метод', snapshot.engine],
    ['Версия отчёта', snapshot.report_version], ['Закреплённый план', snapshot.plan_version], ['Границы плана', snapshot.limits], ['Известные единицы работы', snapshot.known_units], ['Исходная версия PDF-proverka', progress?.source_version],
    ['SHA256 источников', sourceReport?.source_sha256], ['Сохранённых карточек', snapshot.saved_cards], ['Параметров', snapshot.parameters], ['Карточек с экранными фрагментами', snapshot.display_excerpt_cards],
    ['Покрытие', progress?.coverage], ['Процедуры', progress?.procedures], ['Ограничения', snapshot.limitations],
    ['Межпакетная сверка, краткие сведения', snapshot.global_consolidation_summary],
    ['Значения', 'Исходные значения Miner и значения независимой машинной сверки находятся в разных столбцах.'],
    ['Решения', 'Сохранённые экспертные решения показаны отдельно; несохранённые оценки не включены.'],
    ['Страницы', 'Физическая страница PDF (с 1) получена из сохранённого профиля; имя файла и ID не используются как номер листа.'],
    ['Длинные цитаты', 'Sources: соединить части одного source_id по порядку без разделителей. Cards: отдельно соединить части before/after.'],
    ['Полные данные', 'RawJSONchunks: соединить второй столбец по порядку без разделителей; сохраняет весь исходный снимок.']];
  const cardRows: Row[] = [['Карточка', 'Тип записи', 'Часть', 'Заголовок', 'Класс', 'Категория', 'Система', 'Исходные свидетельства', 'Текст', 'Сохранённое решение эксперта', 'Причина решения', 'ID решения', 'Устарело', 'Метаданные экранных фрагментов; полные тексты в Sources/RawJSONchunks']];
  const parameters: Row[] = [['Карточка', 'Событие', 'Параметр ID', 'Объект', 'Название', 'Было (Miner)', 'Стало (Miner)', 'Единица (Miner)', 'Место',
    'Вердикт машинной сверки (не экспертный)', 'Было после сверки', 'Стало после сверки', 'Единица после сверки', 'Объяснение сверки',
    'Источники события', 'Источники сверки', 'ID задания сверки', 'Сохранённое решение эксперта']];
  for (const card of v3Cards(cards)) {
    cardRows.push([card.card_id, 'Карточка', '', card.title, card.class_name, card.category, card.system, card.evidence_ids,
      '', card.verdict?.decision, card.verdict?.reason, card.verdict?.verdict_id, card.stale, object(card.experimental)?.display_text]);
    for (const [kind, value] of [['before', card.before], ['after', card.after]]) {
      rawChunks(value ?? '').forEach((chunk, ordinal) => cardRows.push([card.card_id, kind, ordinal + 1, '', '', '', '', '', chunk]));
    }
    for (const row of parameterRows(card)) parameters.push([card.card_id, row.eventId, row.parameterId, row.subject,
      row.name, row.oldValue, row.newValue, row.unit, row.location, row.verdict || 'PENDING', row.verifiedOldValue,
      row.verifiedNewValue, row.verifiedUnit, row.explanation, row.eventSources.map((source) => source.sourceId),
      row.verificationSources.map((source) => source.sourceId), row.raw.verification_work_item_id, card.verdict?.decision]);
  }
  const sources: Row[] = [['ID источника', 'Сторона', 'Физическая страница PDF (с 1)', 'Версия PDF', 'Профиль страницы', 'Content key фрагмента', 'Content key страницы', 'Координаты как сохранены', 'Происхождение цитаты', 'Часть цитаты', 'Всего частей', 'Полная цитата, последовательные части']];
  for (const source of reportSources(cards, run)) {
    const quote = typeof source.quote === 'string' ? source.quote : '';
    const chunks = rawChunks(quote); if (chunks.length === 0) chunks.push('');
    chunks.forEach((chunk, ordinal) => sources.push([source.source_id, source.side, source.page_number, source.version_uid,
      source.profile_id, source.content_key, source.page_content_key, source.box_anchor, source.quote_source, ordinal + 1, chunks.length, chunk]));
  }
  const coverage: Row[] = [['Сторона', 'Физическая страница PDF (с 1)', 'Версия PDF', 'Профиль страницы', 'Сопоставление', 'Обработка', 'Регионов', 'Обработанные регионы', 'Блоков', 'Непарная страница требует разбора', 'Причина исключения']];
  for (const page of reportCoverage(run)) coverage.push([page.side, page.page_number, page.version_uid, page.profile_id,
    page.mapping_status, page.analysis_status, page.region_ids, page.analysed_region_ids, page.block_count,
    page.requires_unmatched_review, page.exclusion_reason]);
  const global = reportGlobalConsolidation(run);
  const globalRows: Row[] = [['Вид сохранённой записи', 'ID', 'Часть', 'Всего частей', 'Полный JSON записи, последовательные части без разделителей']];
  if (global !== null) {
    const append = (kind: string, id: unknown, value: unknown) => { const payload = json(value).replace(/[\uFFFE\uFFFF]/g, (character) => `\\u${character.charCodeAt(0).toString(16).padStart(4, '0')}`); const chunks = rawChunks(payload); chunks.forEach((chunk, index) => globalRows.push([kind, id, index + 1, chunks.length, chunk])); };
    append('Манифест и покрытие', global.manifest_sha256, snapshot.global_consolidation_summary);
    for (const [key, label] of [['groups', 'Группа'], ['decisions', 'Модельная рекомендация и применение'], ['original_events', 'Исходное событие'], ['original_hints', 'Исходная классификация'], ['parameter_verifications', 'Исходная машинная сверка']] as const) {
      const value = global[key];
      const records = Array.isArray(value) ? value : [];
      for (const record of records) { const row = object(record); append(label, row?.group_id ?? row?.pair_id ?? row?.event_id ?? row?.projectchange_id ?? row?.work_item_id ?? row?.parameter_id ?? row?.hint_id ?? '', record); }
    }
  }
  const raw = json(snapshot).replace(/[\uFFFE\uFFFF]/g, (character) => `\\u${character.charCodeAt(0).toString(16).padStart(4, '0')}`);
  const rawRows: Row[] = [['Порядок', 'Полный исходный JSON, последовательные части без разделителей']];
  rawChunks(raw).forEach((chunk, ordinal) => rawRows.push([ordinal + 1, chunk]));
  return [{ name: 'Summary', rows: summary }, { name: 'Cards', rows: cardRows }, { name: 'Parameters', rows: parameters },
    { name: 'Sources', rows: sources }, { name: 'Coverage', rows: coverage }, { name: 'GlobalReceipts', rows: globalRows }, { name: 'RawJSONchunks', rows: rawRows }];
}

const CRC_TABLE = new Uint32Array(256);
for (let index = 0; index < 256; index += 1) {
  let value = index;
  for (let bit = 0; bit < 8; bit += 1) value = value & 1 ? 0xEDB88320 ^ (value >>> 1) : value >>> 1;
  CRC_TABLE[index] = value >>> 0;
}
function crc32(bytes: Uint8Array): number {
  let value = 0xFFFFFFFF;
  for (const byte of bytes) value = (value >>> 8) ^ (CRC_TABLE[(value ^ byte) & 0xFF] ?? 0);
  return (value ^ 0xFFFFFFFF) >>> 0;
}
function archive(parts: readonly { readonly name: string; readonly content: string }[]): ArrayBuffer {
  const encoder = new TextEncoder();
  const records = parts.map((part) => { const name = encoder.encode(part.name); const data = encoder.encode(part.content); return { name, data, crc: crc32(data), offset: 0 }; });
  const localSize = records.reduce((size, part) => size + 30 + part.name.length + part.data.length, 0);
  const centralSize = records.reduce((size, part) => size + 46 + part.name.length, 0);
  const total = localSize + centralSize + 22;
  if (total > MAX_PACKAGE) throw new Error('Технический XLSX: превышен предел 64 МиБ. Используйте полную выгрузку JSON.');
  const buffer = new ArrayBuffer(total); const output = new Uint8Array(buffer); const view = new DataView(buffer);
  let offset = 0;
  for (const part of records) {
    part.offset = offset;
    view.setUint32(offset, 0x04034B50, true); view.setUint16(offset + 4, 20, true); view.setUint16(offset + 6, 0x0800, true);
    view.setUint16(offset + 12, 33, true); view.setUint32(offset + 14, part.crc, true);
    view.setUint32(offset + 18, part.data.length, true); view.setUint32(offset + 22, part.data.length, true);
    view.setUint16(offset + 26, part.name.length, true);
    output.set(part.name, offset + 30); output.set(part.data, offset + 30 + part.name.length);
    offset += 30 + part.name.length + part.data.length;
  }
  for (const part of records) {
    view.setUint32(offset, 0x02014B50, true); view.setUint16(offset + 4, 20, true); view.setUint16(offset + 6, 20, true);
    view.setUint16(offset + 8, 0x0800, true); view.setUint16(offset + 14, 33, true); view.setUint32(offset + 16, part.crc, true);
    view.setUint32(offset + 20, part.data.length, true); view.setUint32(offset + 24, part.data.length, true);
    view.setUint16(offset + 28, part.name.length, true); view.setUint32(offset + 42, part.offset, true);
    output.set(part.name, offset + 46); offset += 46 + part.name.length;
  }
  view.setUint32(offset, 0x06054B50, true); view.setUint16(offset + 8, records.length, true); view.setUint16(offset + 10, records.length, true);
  view.setUint32(offset + 12, centralSize, true); view.setUint32(offset + 16, localSize, true);
  return buffer;
}

export function formatStageV3Xlsx(runId: string, cards: readonly StageChangeCard[], run: StageChainRun | undefined): { readonly content: ArrayBuffer; readonly mediaType: string; readonly fileName: string } {
  let replacementCount = 0;
  const clean = (value: unknown, sheet: string): string => {
    const source = cell(value);
    if (source.length > MAX_CELL) throw new Error(`Технический XLSX: ячейка листа ${sheet} превышает 32767 символов. Текст не усечён; используйте полную выгрузку JSON.`);
    let cleaned = '';
    for (const character of source) {
      const point = character.codePointAt(0) ?? 0;
      if (point === 9 || point === 10 || point === 13 || point >= 32 && point <= 0xD7FF || point >= 0xE000 && point <= 0xFFFD || point >= 0x10000 && point <= 0x10FFFF) cleaned += character;
      else { cleaned += '\uFFFD'; replacementCount += 1; }
    }
    return cleaned;
  };
  const cleaned = tables(runId, cards, run).map((table) => ({ name: table.name, rows: table.rows.map((row) => row.map((value) => clean(value, table.name))) }));
  cleaned[0]?.rows.push(['Замены недопустимых для XML символов в представлении', String(replacementCount)], ['Исходные значения', 'RawJSONchunks сохраняет исходный JSON; замены относятся только к табличному представлению.']);
  const parts: { name: string; content: string }[] = [];
  const sheetNodes: string[] = []; const relationships: string[] = []; const overrides: string[] = [];
  cleaned.forEach((table, index) => {
    const id = index + 1;
    if (table.rows.length > 1_048_576) throw new Error('Технический XLSX: превышен предел строк Excel. Используйте полную выгрузку JSON.');
    sheetNodes.push(`<sheet name="${escapeXml(table.name)}" sheetId="${id}" r:id="rId${id}"/>`);
    relationships.push(`<Relationship Id="rId${id}" Type="${OFFICE_REL}/worksheet" Target="worksheets/sheet${id}.xml"/>`);
    overrides.push(`<Override PartName="/xl/worksheets/sheet${id}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`);
    const rows = table.rows.map((row, number) => `<row r="${number + 1}">${row.map((value, cellIndex) => `<c r="${column(cellIndex)}${number + 1}" t="inlineStr"><is><t xml:space="preserve">${spreadsheetText(value)}</t></is></c>`).join('')}</row>`).join('');
    parts.push({ name: `xl/worksheets/sheet${id}.xml`, content: `${XML_HEAD}<worksheet xmlns="${MAIN}"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><sheetData>${rows}</sheetData></worksheet>` });
  });
  parts.push({ name: '[Content_Types].xml', content: `${XML_HEAD}<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>${overrides.join('')}</Types>` });
  parts.push({ name: '_rels/.rels', content: `${XML_HEAD}<Relationships xmlns="${REL}"><Relationship Id="rId1" Type="${OFFICE_REL}/officeDocument" Target="xl/workbook.xml"/></Relationships>` });
  parts.push({ name: 'xl/workbook.xml', content: `${XML_HEAD}<workbook xmlns="${MAIN}" xmlns:r="${OFFICE_REL}"><bookViews><workbookView/></bookViews><sheets>${sheetNodes.join('')}</sheets></workbook>` });
  parts.push({ name: 'xl/_rels/workbook.xml.rels', content: `${XML_HEAD}<Relationships xmlns="${REL}">${relationships.join('')}</Relationships>` });
  return { content: archive(parts), mediaType: MIME, fileName: `${runId}-v3-technical.xlsx` };
}
