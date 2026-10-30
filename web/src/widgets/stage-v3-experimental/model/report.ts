import type { StageCardEvidence, StageChainRun, StageChangeCard } from '@/shared/api';

export const V3_ENGINE = 'v3_native_text_experimental';
export const V3_REPORT_VERSION = 'stage-v3-source-report/1';
export type JsonObject = Record<string, unknown>;

export function object(value: unknown): JsonObject | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as JsonObject : null;
}
export function string(value: unknown): string { return typeof value === 'string' ? value : ''; }
function objects(value: unknown): JsonObject[] {
  return Array.isArray(value) ? value.flatMap((item) => { const row = object(item); return row === null ? [] : [row]; }) : [];
}
function strings(value: unknown): string[] { return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []; }

export const VERIFICATION_WORDS: Readonly<Record<string, string>> = {
  CONFIRMED: 'Подтверждено машинной сверкой', CORRECTED: 'Уточнено машинной сверкой',
  CONFLICT: 'Противоречие — нужна проверка', UNREADABLE: 'Не удалось прочитать',
};

export interface V3Source {
  readonly sourceId: string;
  readonly side: string;
  readonly pageNumber: number | null;
  readonly profileId: string;
  readonly versionUid: string;
  readonly quote: string;
  readonly raw: JsonObject | null;
  readonly anchor: StageCardEvidence | undefined;
}
export interface V3Parameter {
  readonly key: string;
  readonly parameterId: string;
  readonly eventId: string;
  readonly subject: string;
  readonly name: string;
  readonly oldValue: string;
  readonly newValue: string;
  readonly unit: string;
  readonly location: string;
  readonly verdict: string;
  readonly verifiedOldValue: string;
  readonly verifiedNewValue: string;
  readonly verifiedUnit: string;
  readonly explanation: string;
  readonly eventSources: readonly V3Source[];
  readonly verificationSources: readonly V3Source[];
  readonly raw: JsonObject;
}

function eventIndex(root: JsonObject): Map<string, JsonObject> {
  const index = new Map<string, JsonObject>();
  const visit = (row: JsonObject) => {
    const identity = string(row.event_id);
    if (identity !== '') index.set(identity, row);
    for (const related of objects(row.related_events)) visit(related);
  };
  visit(root);
  return index;
}

export function parameterRows(card: StageChangeCard): V3Parameter[] {
  const body = object(card.experimental);
  if (body?.engine !== V3_ENGINE) return [];
  const events = eventIndex(body);
  const catalogue = new Map<string, JsonObject>();
  for (const event of [body, ...events.values()]) {
    for (const source of objects(event.sources)) catalogue.set(string(source.source_id), source);
  }
  const sources = (references: readonly string[]): V3Source[] => [...new Set(references)].map((sourceId) => {
    const raw = catalogue.get(sourceId) ?? null;
    const anchor = card.evidence?.find((item) => item.source_id === sourceId);
    return { sourceId, raw, anchor, side: string(raw?.side) || anchor?.side || '',
      pageNumber: typeof raw?.page_number === 'number' ? raw.page_number : null,
      profileId: string(raw?.profile_id) || anchor?.profile_id || '', versionUid: string(raw?.version_uid),
      quote: string(raw?.quote) };
  });
  return objects(body.parameters).map((parameter, ordinal) => {
    const verification = object(parameter.verification);
    const eventId = string(parameter.event_id) || string(body.event_id);
    const event = events.get(eventId) ?? body;
    const verificationIds = strings(parameter.verification_source_ids);
    if (verificationIds.length === 0) {
      verificationIds.push(...objects(verification?.evidence_refs).map((reference) => string(reference.block_id)).filter(Boolean));
    }
    const eventIds = strings(parameter.event_source_ids);
    return { key: `${card.card_id}:${ordinal}`, parameterId: string(parameter.parameter_id), eventId,
      subject: string(event.engineering_subject), name: string(parameter.name),
      oldValue: string(parameter.old_value), newValue: string(parameter.new_value), unit: string(parameter.unit),
      location: string(parameter.location), verdict: string(verification?.verdict),
      verifiedOldValue: string(verification?.old_value), verifiedNewValue: string(verification?.new_value),
      verifiedUnit: string(verification?.unit), explanation: string(verification?.explanation),
      eventSources: sources(eventIds.length === 0 ? card.evidence_ids : eventIds),
      verificationSources: sources(verificationIds), raw: parameter };
  });
}

export function v3Cards(cards: readonly StageChangeCard[]): StageChangeCard[] {
  return cards.filter((card) => object(card.experimental)?.engine === V3_ENGINE);
}

export function reportSources(cards: readonly StageChangeCard[], run: StageChainRun | undefined): JsonObject[] {
  const report = object(object(run?.experimental_progress)?.source_report);
  const catalogue = new Map<string, JsonObject>();
  for (const source of objects(report?.source_catalogue)) catalogue.set(string(source.source_id), source);
  for (const card of v3Cards(cards)) {
    const body = object(card.experimental);
    if (body === null) continue;
    for (const event of [body, ...eventIndex(body).values()]) {
      for (const source of objects(event.sources)) if (!catalogue.has(string(source.source_id))) catalogue.set(string(source.source_id), source);
    }
  }
  return [...catalogue.values()];
}

export function reportCoverage(run: StageChainRun | undefined): JsonObject[] {
  return objects(object(object(object(run?.experimental_progress)?.source_report)?.coverage)?.pages);
}

export function reportSnapshot(runId: string, cards: readonly StageChangeCard[], run: StageChainRun | undefined) {
  const selected = v3Cards(cards);
  return { report_version: V3_REPORT_VERSION, run_id: runId,
    engine: V3_ENGINE, scope: 'all_saved_v3_cards',
    status: run?.state ?? null, stale: run?.stale ?? selected.some((card) => card.stale),
    experimental_progress: run?.experimental_progress ?? null,
    source_catalogue: reportSources(cards, run), coverage_pages: reportCoverage(run),
    saved_cards: selected.length, parameters: selected.reduce((total, card) => total + parameterRows(card).length, 0),
    limitations: ['Только собственный текст PDF; графика и сканы не проверялись.',
      'Машинная сверка не является решением эксперта; нормы не проверены.',
      'Включены сохранённые карточки и решения; несохранённые оценки не включены.',
      'Для старых карточек каталог цитат или идентификаторы параметров могут отсутствовать.'],
    cards: selected };
}

function csvCell(value: string): string {
  // Text stays text when opened by spreadsheet applications, including model
  // output beginning with a formula sigil. JSON preserves the exact raw value.
  const safe = /^[\s]*[=+\-@\t\r]/.test(value) ? "'" + value : value;
  return '"' + safe.replaceAll('"', '""') + '"';
}
function sourceText(sources: readonly V3Source[]): string {
  return sources.map((source) => [source.sourceId, source.side, source.versionUid,
    source.pageNumber === null ? '' : `стр.${source.pageNumber}`, source.profileId,
    source.quote, source.raw?.box_anchor === undefined ? '' : JSON.stringify(source.raw.box_anchor)].filter(Boolean).join(' | ')).join('\n');
}

export function parameterCsv(runId: string, cards: readonly StageChangeCard[]): string {
  const lines = [['Запуск', 'Карточка', 'Тип записи', 'Событие', 'Параметр ID', 'Объект', 'Параметр',
    'Было (Miner)', 'Стало (Miner)', 'Единица (Miner)', 'Место', 'Машинная сверка',
    'Было после сверки', 'Стало после сверки', 'Единица после сверки', 'Объяснение сверки',
    'Источники события', 'Источники сверки', 'Сохранённое решение эксперта', 'Причина решения', 'Устарело']];
  for (const card of v3Cards(cards)) {
    const rows = parameterRows(card);
    if (rows.length === 0) {
      lines.push([runId, card.card_id, 'Наблюдение без параметров', string(object(card.experimental)?.event_id),
        '', '', card.title, '', '', '', '', 'Не проверено', '', '', '', '',
        card.evidence_ids.join('\n'), '', card.verdict?.decision ?? '', card.verdict?.reason ?? '', String(card.stale)]);
    }
    for (const row of rows) lines.push([runId, card.card_id, 'Параметр', row.eventId, row.parameterId,
      row.subject, row.name, row.oldValue, row.newValue, row.unit, row.location,
      VERIFICATION_WORDS[row.verdict] ?? 'Не проверено', row.verifiedOldValue, row.verifiedNewValue,
      row.verifiedUnit, row.explanation, sourceText(row.eventSources), sourceText(row.verificationSources),
      card.verdict?.decision ?? '', card.verdict?.reason ?? '', String(card.stale)]);
  }
  return '\uFEFF' + lines.map((row) => row.map(csvCell).join(';')).join('\r\n');
}

function html(value: string): string {
  return value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&#39;');
}
function sourceHtml(source: V3Source): string {
  return `<li><code>${html(source.sourceId)}</code> · ${html(source.side === 'left' ? 'П' : source.side === 'right' ? 'Р' : source.side)}${source.pageNumber === null ? '' : ` · стр.${source.pageNumber}`}<br>${html(source.versionUid)}<blockquote>${html(source.quote || 'Полная цитата в сохранённой карточке не передана.')}</blockquote></li>`;
}

export function reportHtml(runId: string, cards: readonly StageChangeCard[], run: StageChainRun | undefined): string {
  const snapshot = reportSnapshot(runId, cards, run);
  const sections = snapshot.cards.map((card) => {
    const parameters = parameterRows(card).map((row) => `<section><h3>${html(row.name || 'Параметр без названия')}</h3>
      <p>${html(row.subject)} · ${html(row.location)}</p><p>Событие: <code>${html(row.eventId)}</code>; параметр: <code>${html(row.parameterId || 'Идентификатор не сохранён')}</code></p>
      <table><thead><tr><th>Версия значений</th><th>Было</th><th>Стало</th><th>Единица</th></tr></thead><tbody>
      <tr><th>Исходный Miner</th><td>${html(row.oldValue)}</td><td>${html(row.newValue)}</td><td>${html(row.unit)}</td></tr>
      <tr><th>Машинная сверка</th><td>${html(row.verifiedOldValue)}</td><td>${html(row.verifiedNewValue)}</td><td>${html(row.verifiedUnit)}</td></tr></tbody></table>
      <p><strong>${html(VERIFICATION_WORDS[row.verdict] ?? 'Не проверено')}</strong> ${html(row.explanation)}</p>
      <details><summary>Источники события</summary><ul>${row.eventSources.map(sourceHtml).join('')}</ul></details>
      <details open><summary>Источники машинной сверки</summary>${row.verificationSources.length === 0 ? '<p>Привязка сверки к источникам не сохранена.</p>' : `<ul>${row.verificationSources.map(sourceHtml).join('')}</ul>`}</details></section>`).join('');
    return `<article><h2>${html(card.title)}</h2><p>Карточка <code>${html(card.card_id)}</code> · ${card.stale ? 'Устарела' : 'Не отмечена устаревшей'}</p>
      <p>Сохранённое решение эксперта: ${html(card.verdict?.decision === 'accepted' ? 'Принято' : card.verdict?.decision === 'rejected' ? 'Не принято' : 'Не сохранено')}. ${html(card.verdict?.reason ?? '')}</p>
      ${parameters || '<p>Структурированные параметры не переданы; исходное наблюдение сохранено в JSON.</p>'}</article>`;
  }).join('');
  const raw = html(JSON.stringify(snapshot, null, 2));
  const coverage = snapshot.coverage_pages.map((page) => `<tr><td>${html(string(page.side) === 'left' ? 'П' : string(page.side) === 'right' ? 'Р' : string(page.side))}</td><td>${html(String(page.page_number ?? 'Не передано'))}</td><td>${html(string(page.version_uid))}</td><td>${html(string(page.mapping_status))}</td><td>${html(string(page.analysis_status))}</td><td>${html(string(page.exclusion_reason))}</td></tr>`).join('');
  const catalogue = snapshot.source_catalogue.map((source) => `<li><code>${html(string(source.source_id))}</code> · ${html(string(source.side))} · стр.${html(String(source.page_number ?? 'Не передано'))}<br>${html(string(source.version_uid))}<blockquote>${html(string(source.quote))}</blockquote></li>`).join('');
  return `<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; base-uri 'none'; form-action 'none'"><title>V3 — параметры и источники</title>
    <style>body{font:15px system-ui,sans-serif;margin:2rem;max-width:1200px;line-height:1.5}table{border-collapse:collapse;width:100%}td,th{border:1px solid #aaa;padding:.5rem;text-align:left;white-space:pre-wrap}article{border-top:2px solid #777;margin-top:2rem}blockquote,pre{white-space:pre-wrap;overflow-wrap:anywhere}code{overflow-wrap:anywhere}@media print{details>summary{display:none}details>*{display:block}article{break-before:page}}</style></head><body><h1>V3 — параметры и источники</h1>
    <p>Запуск: <code>${html(runId)}</code> · состояние: ${html(snapshot.status ?? 'Не передано')} · сохранённых карточек: ${snapshot.saved_cards} · параметров: ${snapshot.parameters}</p>
    <ul>${snapshot.limitations.map((item) => `<li>${html(item)}</li>`).join('')}</ul><p>Для PDF используйте печать браузера и «Сохранить как PDF».</p>
    <h2>Покрытие исходных страниц</h2>${coverage === '' ? '<p>Постраничное покрытие не сохранено.</p>' : `<table><thead><tr><th>Сторона</th><th>Физическая страница PDF</th><th>Версия</th><th>Сопоставление</th><th>Обработка</th><th>Причина исключения</th></tr></thead><tbody>${coverage}</tbody></table>`}
    ${sections}<details><summary>Полный каталог сохранённых источников · ${snapshot.source_catalogue.length}</summary><ul>${catalogue}</ul></details>
    <details><summary>Полный сохранённый снимок</summary><pre>${raw}</pre></details></body></html>`;
}
