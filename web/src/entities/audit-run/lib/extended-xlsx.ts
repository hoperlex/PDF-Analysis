import type { ExtendedRunReview } from '@/shared/api';

/** Preliminary local export. OOXML layout follows comparison/report/technical_export.py;
 * ZIP STORE and CRC32 are implemented here without a package or a paid/server call. */
type RecordValue = Record<string, unknown>;
type Row = readonly unknown[];
interface Table { readonly name: string; readonly rows: Row[] }
interface Entry { readonly scope: string; readonly item: RecordValue }
const MAX_CELL = 32_767;
const RAW_CHUNK = 32_000;
const MAX_PACKAGE = 64 * 1024 * 1024;
const XML_HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>';
const MAIN = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main';
const REL = 'http://schemas.openxmlformats.org/package/2006/relationships';
const OFFICE_REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships';
const MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
function object(value: unknown): RecordValue | null { return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RecordValue : null; }
function objects(value: unknown): RecordValue[] { return Array.isArray(value) ? value.flatMap((item) => { const row = object(item); return row === null ? [] : [row]; }) : []; }
function text(value: unknown): string { return typeof value === 'string' ? value : ''; }
function json(value: unknown): string { return JSON.stringify(value ?? null, null, 2) ?? 'null'; }
function cell(value: unknown): string { return value === null || value === undefined ? '' : typeof value === 'string' ? value : typeof value === 'object' ? json(value) : String(value); }
function escapeXml(value: string): string { return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;'); }
function spreadsheetText(value: string): string {
  // Protect literal OOXML escape-looking text (including in RawJSONchunks).
  const literal = value.replace(/_x[0-9a-f]{4}_/gi, (match) => `_x005F_${match.slice(1)}`);
  return escapeXml(literal).replace(/\r/g, '&#13;');
}
function column(index: number): string {
  let value = index + 1;
  let result = '';
  while (value > 0) { const digit = (value - 1) % 26; result = String.fromCharCode(65 + digit) + result; value = Math.floor((value - 1) / 26); }
  return result;
}
function rawChunks(value: string): string[] {
  const chunks: string[] = [];
  for (let start = 0; start < value.length;) {
    let end = Math.min(start + RAW_CHUNK, value.length);
    const last = value.charCodeAt(end - 1);
    const next = value.charCodeAt(end);
    if (end < value.length && last >= 0xD800 && last <= 0xDBFF && next >= 0xDC00 && next <= 0xDFFF) end -= 1;
    chunks.push(value.slice(start, end)); start = end;
  }
  return chunks;
}

function tables(reading: ExtendedRunReview): Table[] {
  const result = object(reading.result);
  const windows = objects(result?.windows);
  // Repeated window/global records retain their scope; no model-based admission filter.
  const entries: Entry[] = [
    ...objects(result?.observations).map((item) => ({ scope: 'Общий свод', item })),
    ...windows.flatMap((window) => objects(window.observations).map((item) => ({ scope: `Окно ${text(window.window_id)}`, item }))),
  ];
  const sourceEntries: Entry[] = [
    ...objects(result?.sources).map((item) => ({ scope: 'Общий свод', item })),
    ...windows.flatMap((window) => objects(window.sources).map((item) => ({ scope: `Окно ${text(window.window_id)}`, item }))),
  ];
  const sourcePages = new Map<string, number>();
  for (const { item } of sourceEntries) if (typeof item.page_number === 'number' && Number.isSafeInteger(item.page_number) && item.page_number > 0) sourcePages.set(text(item.source_id), item.page_number);
  const pages = (item: RecordValue) => Array.isArray(item.source_ids)
    ? [...new Set(item.source_ids.flatMap((id) => { const page = sourcePages.get(text(id)); return page === undefined ? [] : [page]; }))].join(', ') : '';
  const summary: Row[] = [
    ['Показатель', 'Значение'], ['Тип', 'ТЕХНИЧЕСКИЙ ПРЕДВАРИТЕЛЬНЫЙ ОТЧЁТ; не экспертное заключение'],
    ['Прогон', reading.run_id], ['Версия исходного PDF', result?.version_uid], ['Состояние ответа', reading.status], ['План', result?.workflow_version],
    ['Раздел', result?.section], ['Отпечаток рубрик SHA256', result?.rules_sha256], ['Происхождение', result?.source_provenance],
    ['Покрытие', result?.coverage], ['Покрытие комплексной сверки текста (страницы)', result?.text_coverage], ['Версия покрытия', result?.coverage_version], ['Покрытие процедур', result?.phase_coverage], ['Принятые лимиты пакетов процедур в окне', result?.phase_call_limits], ['Прогресс окон', result?.window_progress], ['Базовый текстовый анализ', result?.primary_text_status],
    ['Визуальный проход сохранён', result?.visual_phase_complete], ['Процедуры', result?.procedures],
    ['Режим бюджета покрытия', result?.coverage_budget_mode], ['Символов исходного текста в оценке', result?.estimated_text_characters], ['Целевой текстовый фрагмент, символов', result?.comprehensive_piece_characters],
    ['Глобальных кандидатов', objects(result?.observations).length], ['Записей с учётом окон', entries.length], ['Группировка повторов, исходники сохранены', result?.consolidation],
    ['Критика и уточнение', 'Только рекомендации модели. Исходные наблюдения сохранены, решение эксперта не подменяется.'],
    ['Нормы', 'Ни исторические пороги, ни актуальность и применимость нормативных ссылок этим отчётом не подтверждены.'],
    ['Страницы', 'Только физические номера страниц PDF из source.page_number, начиная с 1. Номера листов не выводятся из имени или ID.'],
    ['Дубли', 'Общий свод и записи окон показаны отдельно с областью происхождения; это не дополнительные уникальные находки.'],
    ['Полные данные', 'RawJSONchunks: соединить второй столбец по порядку, без разделителей. Все исходные поля API сохранены.'],
    ['Ограничения', result?.warnings], ['Причина состояния', result?.reason],
  ];
  const candidates: Row[] = [['Область', 'ID наблюдения', 'Исходный заголовок', 'Исходное описание', 'ID источников', 'Физические страницы PDF (с 1)', 'Статус проверки норм', 'Статус машинной критики', 'Причина отсутствия критики', 'Окно исходной записи', 'Явное происхождение', 'Ключ межоконного пакета', 'Исходные окна межоконного наблюдения']];
  const critics: Row[] = [['Область', 'ID наблюдения', 'ID входа критика', 'Рекомендация модели (код, не решение эксперта)', 'Основание (код)', 'Пояснение', 'Уверенность модели', 'Источники проверены моделью', 'Зависимость от контекста', 'Предложение', 'Доказательства из источников', 'Статус']];
  const corrections: Row[] = [['Область', 'ID наблюдения', 'Действие (предложение)', 'Исходный заголовок', 'Исходное описание', 'Предложенный заголовок', 'Предложенное описание', 'ID источников кандидата', 'Источники кандидата', 'Нормативные свидетельства кандидата (не подтверждены)', 'Причина', 'Требуемый контекст', 'Статус']];
  const norms: Row[] = [['Область', 'ID наблюдения', 'Физические страницы PDF (с 1)', 'Статус', 'Вид записи', 'Сохранённые нормативные данные', 'Ограничение']];
  const addCritic = (scope: string, id: unknown, value: unknown) => {
    const row = object(value); if (row === null) return;
    critics.push([scope, id ?? row.observation_id, row.input_id, row.llm_decision, row.human_taxonomy_reason, row.explanation, row.confidence, row.evidence_checked, row.source_dependency, row.suggested_fix, row.source_evidence, row.status]);
  };
  const addCorrection = (scope: string, id: unknown, value: unknown, fallback?: RecordValue) => {
    const row = object(value); if (row === null) return;
    const original = object(row.original) ?? fallback;
    const candidate = object(row.candidate);
    corrections.push([scope, id ?? row.observation_id, row.action, original?.title, original?.description, candidate?.title, candidate?.description, candidate?.source_ids, candidate?.source_evidence, candidate?.norm_evidence, row.reason, row.required_context, row.status]);
  };
  for (const { scope, item } of entries) {
    candidates.push([scope, item.observation_id, item.title, item.description, item.source_ids, pages(item), item.norm_status, item.review_status, item.review_reason, item.window_id, item.origin_scope, item.cross_window_batch_key, item.window_ids]);
    addCritic(scope, item.observation_id, item.review ?? item.critic);
    addCorrection(scope, item.observation_id, item.correction, item);
    norms.push([scope, item.observation_id, pages(item), item.norm_status, 'Состояние', item.norm_reason, 'Редакция, актуальность и применимость требуют экспертной проверки.']);
    if (item.norm_assessment !== undefined) norms.push([scope, item.observation_id, pages(item), item.norm_status, 'Модельная сверка цитат', item.norm_assessment, 'Модельная рекомендация, не нормативное заключение.']);
    for (const candidate of objects(item.norm_candidates)) norms.push([scope, item.observation_id, pages(item), item.norm_status, 'Кандидат нормативной ссылки', candidate, 'Кандидат не подтверждён экспертом.']);
  }
  for (const window of windows) {
    const scope = `Квитанция окна ${text(window.window_id)}`;
    for (const row of objects(window.reviews)) addCritic(`${scope} · reviews`, row.observation_id, row);
    for (const row of objects(window.critiques)) addCritic(`${scope} · critiques`, row.observation_id, row);
    for (const row of objects(window.corrections)) addCorrection(scope, row.observation_id, row);
  }
  const batchRows: Row[] = [['Область', 'Ключ пакета', 'Окно', 'Процедура', 'Порядковый номер (с 1)', 'Состояние', 'Входных элементов', 'ID входных записей', 'ID источников', 'Физические страницы PDF (с 1)', 'Символов на входе', 'Диапазоны текстовых фрагментов (не PDF-координаты)', 'Ограничение (код)']];
  const addBatch = (scope: string, row: RecordValue, windowId?: unknown) => batchRows.push([scope, row.batch_key, row.window_id ?? windowId, row.procedure, typeof row.index === 'number' ? row.index + 1 : '', row.status, row.input_count, row.input_ids, row.source_ids, row.page_numbers, row.input_characters, row.context_ranges, row.reason]);
  for (const row of objects(result?.batches)) addBatch('Общий свод', row);
  for (const window of windows) for (const row of objects(window.batches)) addBatch('Квитанция окна', row, window.window_id);
  const sources: Row[] = [['Область', 'ID источника', 'Тип источника', 'Вид данных', 'Физическая страница PDF (с 1)', 'Версия PDF', 'SHA256 изображения/слоя', 'SHA256 текста', 'Координаты как сохранены', 'Цитата', 'Происхождение цитаты', 'Поле текстового диапазона', 'Начальный индекс в записи (с 0)', 'Конечный индекс в записи (с 0), как сохранён', 'Индекс распознанной записи (с 0)', 'SHA256 исходного текста страницы/записи', 'Исходные окна', 'Роль исходного артефакта', 'SHA256 замороженного источника']];
  for (const { scope, item } of sourceEntries) sources.push([scope, item.source_id, item.source_type ?? item.source_kind, item.kind,
    typeof item.page_number === 'number' && Number.isSafeInteger(item.page_number) && item.page_number > 0 ? item.page_number : '',
    text(item.version_uid) || text(result?.version_uid), item.crop_sha256 ?? item.artifact_sha256, item.text_sha256, item.bbox_norm ?? item.box, item.quote, item.quote_source,
    item.character_field, item.character_start, item.character_end, item.entry_ordinal, item.page_text_sha256, item.window_ids, item.origin_artifact_role, item.source_sha256]);
  const windowRows: Row[] = [['Окно', 'Порядковый номер (с 1)', 'Состояние окна', 'Визуальный проход сохранён (не всё окно)', 'Покрытие', 'ID процедуры', 'Название процедуры', 'Состояние процедуры', 'Причина']];
  for (const window of windows) {
    const prefix = [window.window_id, typeof window.index === 'number' ? window.index + 1 : '', window.status, window.visual_phase_complete, window.coverage];
    windowRows.push([...prefix, '', '', '', window.reason]);
    for (const procedure of objects(window.procedures)) windowRows.push([...prefix, procedure.id, procedure.title, procedure.status, procedure.reason]);
  }
  const global = object(result?.global_cross_window);
  const globalRows: Row[] = [['Вид записи межоконного прохода (лимиты на весь прогон)', 'Ключ', 'Часть', 'Всего частей', 'Полный JSON, последовательные части без разделителей']];
  if (global !== null) {
    const append = (kind: string, key: unknown, value: unknown) => {
      const payload = json(value).replace(/[\uFFFE\uFFFF]/g, (character) => `\\u${character.charCodeAt(0).toString(16).padStart(4, '0')}`);
      const chunks = rawChunks(payload);
      chunks.forEach((chunk, index) => globalRows.push([kind, key, index + 1, chunks.length, chunk]));
    };
    append('Полная сохранённая запись global_cross_window', global.manifest_sha256 ?? global.source_sha256 ?? '', global);
    for (const [key, label] of [['batches', 'Квитанция'], ['pending_batches', 'Необработанное сочетание'], ['pieces', 'Учтённый фрагмент'], ['omitted', 'Пропуск/ограничение']] as const) {
      const records = global[key];
      if (!Array.isArray(records)) continue;
      for (const record of records) { const item = object(record); append(label, item?.batch_key ?? item?.pair_id ?? item?.source_id ?? '', record); }
    }
  }
  const parameterBody = object(result?.project_parameters);
  const parameterRows: Row[] = [['ID кандидата', 'Название', 'Тип', 'Значение как в источнике', 'Единица как в источнике', 'Предмет/объект', 'Источники', 'Точные цитаты и диапазоны', 'Ключ пакета', 'Статус']];
  for (const fact of objects(parameterBody?.facts)) parameterRows.push([fact.fact_id, fact.name, fact.parameter_type, fact.value,
    fact.unit, fact.subject, fact.source_ids, fact.source_evidence, fact.batch_key, fact.status]);
  const parameterReceipts: Row[] = [['Часть', 'Всего частей', 'Полная запись параметров, JSON, последовательные части без разделителей']];
  if (parameterBody !== null) {
    const payload = json(parameterBody).replace(/[\uFFFE\uFFFF]/g, (character) => `\\u${character.charCodeAt(0).toString(16).padStart(4, '0')}`);
    const chunks = rawChunks(payload);
    chunks.forEach((chunk, index) => parameterReceipts.push([index + 1, chunks.length, chunk]));
  }
  const normContextRows: Row[] = [['Окно', 'Пакет', 'Часть', 'Всего частей', 'Полная квитанция нормативного контекста, JSON, последовательные части без разделителей']];
  for (const receipt of objects(result?.normative_context_receipts)) {
    const payload = json(receipt).replace(/[\uFFFE\uFFFF]/g, (character) => `\\u${character.charCodeAt(0).toString(16).padStart(4, '0')}`);
    const chunks = rawChunks(payload);
    chunks.forEach((chunk, index) => normContextRows.push([receipt.window_id, receipt.batch_index, index + 1, chunks.length, chunk]));
  }
  const lookupRows: Row[] = [['Окно', 'ID наблюдения', 'Проход поиска', 'Состояние', 'Часть', 'Всего частей', 'Полная квитанция нормативного поиска, JSON, последовательные части без разделителей']];
  for (const receipt of objects(result?.norm_lookup_receipts)) {
    const payload = json(receipt).replace(/[\uFFFE\uFFFF]/g, (character) => `\\u${character.charCodeAt(0).toString(16).padStart(4, '0')}`);
    const chunks = rawChunks(payload);
    chunks.forEach((chunk, index) => lookupRows.push([receipt.window_id, receipt.observation_id, receipt.lookup_pass_ordinal, receipt.status, index + 1, chunks.length, chunk]));
  }
  // XML-illegal noncharacters are escaped as JSON escapes, preserving the JSON value.
  const raw = json(reading).replace(/[\uFFFE\uFFFF]/g, (character) => `\\u${character.charCodeAt(0).toString(16).padStart(4, '0')}`);
  const rawRows: Row[] = [['Порядок', 'Полная исходная запись JSON, последовательные части без разделителей']];
  rawChunks(raw).forEach((chunk, index) => rawRows.push([index + 1, chunk]));
  return [{ name: 'Summary', rows: summary }, { name: 'Candidates', rows: candidates }, { name: 'Critic', rows: critics },
    { name: 'Corrections', rows: corrections }, { name: 'Sources', rows: sources }, { name: 'Norms', rows: norms },
    { name: 'Windows', rows: windowRows }, { name: 'Batches', rows: batchRows }, { name: 'GlobalCrossWindow', rows: globalRows },
    { name: 'ProjectParameters', rows: parameterRows }, { name: 'ParameterReceipts', rows: parameterReceipts },
    { name: 'NormativeContext', rows: normContextRows }, { name: 'NormLookups', rows: lookupRows }, { name: 'RawJSONchunks', rows: rawRows }];
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
  const buffer = new ArrayBuffer(total);
  const output = new Uint8Array(buffer);
  const view = new DataView(buffer);
  let offset = 0;
  for (const part of records) {
    part.offset = offset;
    view.setUint32(offset, 0x04034B50, true); view.setUint16(offset + 4, 20, true);
    view.setUint16(offset + 6, 0x0800, true); // UTF-8, stored, no encryption/data descriptor.
    view.setUint16(offset + 12, 33, true); // DOS date 1980-01-01; time stays zero.
    view.setUint32(offset + 14, part.crc, true); view.setUint32(offset + 18, part.data.length, true); view.setUint32(offset + 22, part.data.length, true);
    view.setUint16(offset + 26, part.name.length, true);
    output.set(part.name, offset + 30); output.set(part.data, offset + 30 + part.name.length);
    offset += 30 + part.name.length + part.data.length;
  }
  for (const part of records) {
    view.setUint32(offset, 0x02014B50, true); view.setUint16(offset + 4, 20, true); view.setUint16(offset + 6, 20, true);
    view.setUint16(offset + 8, 0x0800, true); view.setUint16(offset + 14, 33, true);
    view.setUint32(offset + 16, part.crc, true); view.setUint32(offset + 20, part.data.length, true); view.setUint32(offset + 24, part.data.length, true);
    view.setUint16(offset + 28, part.name.length, true); view.setUint32(offset + 42, part.offset, true);
    output.set(part.name, offset + 46); offset += 46 + part.name.length;
  }
  view.setUint32(offset, 0x06054B50, true); view.setUint16(offset + 8, records.length, true); view.setUint16(offset + 10, records.length, true);
  view.setUint32(offset + 12, centralSize, true); view.setUint32(offset + 16, localSize, true);
  return buffer;
}

export function formatExtendedRunXlsx(reading: ExtendedRunReview): { readonly content: ArrayBuffer; readonly mediaType: string; readonly fileName: string } {
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
  const cleaned = tables(reading).map((table) => ({ name: table.name, rows: table.rows.map((row) => row.map((value) => clean(value, table.name))) }));
  cleaned[0]?.rows.push(['Замены недопустимых для XML символов в представлении', String(replacementCount)], ['Исходные значения', 'RawJSONchunks сохраняет исходный JSON; замены относятся только к табличному представлению.']);
  const parts: { name: string; content: string }[] = [];
  const sheetNodes: string[] = [];
  const relationships: string[] = [];
  const overrides: string[] = [];
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
  return { content: archive(parts), mediaType: MIME, fileName: `analysis-${reading.run_id}-technical.xlsx` };
}
