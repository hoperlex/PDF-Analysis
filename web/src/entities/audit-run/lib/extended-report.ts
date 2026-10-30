import type { ExtendedRunReview } from '@/shared/api';
import { formatExtendedRunXlsx } from './extended-xlsx';

type RecordValue = Record<string, unknown>;
export type ExtendedReportFormat = 'md' | 'html' | 'json' | 'xlsx';
export interface ExtendedReportFile { readonly content: string | ArrayBuffer; readonly mediaType: string; readonly fileName: string }

const STATUS: Readonly<Record<string, string>> = { queued: 'Запланировано', not_started: 'Ожидает начала', running: 'Выполняется',
  completed: 'Завершено', partial: 'Частично', failed: 'Ошибка', skipped: 'Пропущено', unavailable: 'Недоступно' };
const HTML_ENTITIES: Readonly<Record<string, string>> = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
function object(value: unknown): RecordValue | null { return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RecordValue : null; }
function objects(value: unknown): RecordValue[] { return Array.isArray(value) ? value.flatMap((item) => { const row = object(item); return row === null ? [] : [row]; }) : []; }
function plain(value: unknown): string { return typeof value === 'string' ? value : value === null || value === undefined ? 'Не передано' : JSON.stringify(value, null, 2) ?? 'Не передано'; }
function html(value: unknown): string { return plain(value).replace(/[&<>"']/g, (char) => HTML_ENTITIES[char] ?? char); }
function md(value: unknown): string { return plain(value).replace(/([\\`*_{}\[\]()#+.!|>])/g, '\\$1').replace(/</g, '&lt;').replace(/&(?!(?:lt|gt);)/g, '&amp;').replace(/>/g, '&gt;'); }
function code(value: unknown): string {
  const body = JSON.stringify(value, null, 2) ?? 'null';
  const lengths = [...body.matchAll(/`+/g)].map((match) => match[0].length);
  const fence = '`'.repeat(Math.max(3, ...lengths) + 1);
  return `${fence}json\n${body}\n${fence}`;
}

function procedureMarkdown(value: unknown): string {
  return objects(value).map((item) => `- ${md(item.title || item.id)}: ${md(STATUS[plain(item.status)] ?? item.status)}${item.reason ? `; ограничение: ${md(item.reason)}` : ''}`).join('\n');
}
function observationMarkdown(item: RecordValue, index: number): string {
  const lines = [`### ${index + 1}. ${md(item.title)}`, md(item.description), `Идентификатор: ${md(item.observation_id)}. Источники: ${md(item.source_ids)}.`,
    `Нормативный статус: ${md(item.norm_status ?? 'Не проверено')}. Актуальность и применимость цитат требуют проверки эксперта.`];
  if (item.review !== undefined || item.critic !== undefined) lines.push('Рекомендация машинного критика — не решение эксперта:', code(item.review ?? item.critic));
  if (item.correction !== undefined) lines.push('Исправленный кандидат отдельно от исходного наблюдения; исходник не удалён:', code(item.correction));
  lines.push('Полная сохранённая запись наблюдения:', code(item));
  return lines.join('\n\n');
}

/** Local projection of an already authorised API reading; no model, mutation or accepted-only filter. */
export function formatExtendedRunReport(reading: ExtendedRunReview, format: ExtendedReportFormat): ExtendedReportFile {
  if (format === 'xlsx') return formatExtendedRunXlsx(reading);
  const result = object(reading.result);
  const windows = objects(result?.windows);
  const observations = objects(result?.observations);
  const raw = JSON.stringify(reading, null, 2) ?? 'null';
  const base = `analysis-${reading.run_id}`;
  if (format === 'json') return { content: raw, mediaType: 'application/json;charset=utf-8', fileName: `${base}.json` };
  const disclaimer = 'Предварительный машинный анализ. Рекомендации критика и исправленные кандидаты не являются решениями эксперта. Нормативные значения из исторических рубрик не подтверждены; редакция и применимость цитат требуют отдельной проверки. Все переданные записи сохранены, без фильтра по модельному принятию или отклонению.';
  const metadata = { run_id: reading.run_id, status: reading.status, workflow_version: result?.workflow_version,
    section: result?.section, rules_sha256: result?.rules_sha256, source_provenance: result?.source_provenance,
    coverage: result?.coverage, window_progress: result?.window_progress, primary_text_status: result?.primary_text_status,
    visual_phase_complete: result?.visual_phase_complete, report: result?.report };
  const pendingPrimary = result?.primary_text_status === 'pending'
    ? 'Базовый текстовый анализ ещё выполняется. Сохранённый визуальный проход не является завершением всей проверки окна.' : '';
  if (format === 'md') {
    const blocks = ['# Предварительный анализ раздела', disclaimer, pendingPrimary, '## Состояние, покрытие и происхождение', code(metadata),
      '## Фактические процедуры', procedureMarkdown(result?.procedures), `## Общий свод: ${observations.length} записей`,
      ...observations.map(observationMarkdown)];
    for (const [index, window] of windows.entries()) blocks.push(`## Окно ${index + 1}: ${md(window.window_id)}`,
      `Состояние: ${md(STATUS[plain(window.status)] ?? window.status)}`, procedureMarkdown(window.procedures),
      ...(window.visual_phase_complete === true && window.status === 'running' ? ['Визуальный проход сохранён; оставшиеся процедуры окна ещё не завершены.'] : []),
      'Все сохранённые данные окна, включая первоначальные наблюдения и рекомендации:', code(window));
    blocks.push('## Полная исходная запись API', 'Включены все наблюдения, окна, цитаты, источники, ограничения и исправленные кандидаты. Повторяющиеся записи сохранены как часть происхождения.', code(reading));
    return { content: blocks.join('\n\n') + '\n', mediaType: 'text/markdown;charset=utf-8', fileName: `${base}.md` };
  }
  const procedureHtml = (value: unknown) => `<ol>${objects(value).map((item) => `<li><strong>${html(item.title || item.id)}</strong>: ${html(STATUS[plain(item.status)] ?? item.status)}${item.reason ? `<p>${html(item.reason)}</p>` : ''}</li>`).join('')}</ol>`;
  const rows = observations.map((item, index) => `<article><h3>${index + 1}. ${html(item.title)}</h3><p>${html(item.description)}</p><p>Исходное наблюдение сохранено. Решение эксперта не принято этой моделью.</p><pre>${html(JSON.stringify(item, null, 2))}</pre></article>`).join('');
  const windowHtml = windows.map((window, index) => `<section><h2>Окно ${index + 1}: ${html(window.window_id)}</h2><p>${html(STATUS[plain(window.status)] ?? window.status)}</p>${window.visual_phase_complete === true && window.status === 'running' ? '<p>Визуальный проход сохранён; оставшиеся процедуры окна ещё не завершены.</p>' : ''}${procedureHtml(window.procedures)}<pre>${html(JSON.stringify(window, null, 2))}</pre></section>`).join('');
  const content = `<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Предварительный анализ раздела</title><style>body{max-width:1100px;margin:32px auto;padding:0 20px;font:16px/1.5 system-ui,sans-serif;color:#15202b;background:#fff}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f7;padding:16px}article,section{border-top:1px solid #c9d1d9;padding:16px 0}h1,h2,h3{line-height:1.2}</style></head><body><h1>Предварительный анализ раздела</h1><p>${html(disclaimer)}</p>${pendingPrimary ? `<p>${html(pendingPrimary)}</p>` : ''}<h2>Состояние, покрытие и происхождение</h2><pre>${html(JSON.stringify(metadata, null, 2))}</pre><h2>Фактические процедуры</h2>${procedureHtml(result?.procedures)}<h2>Общий свод: ${observations.length} записей</h2>${rows}${windowHtml}<h2>Полная исходная запись API</h2><p>Все переданные записи, источники, цитаты и ограничения без фильтра по модельной рекомендации.</p><pre>${html(raw)}</pre></body></html>`;
  return { content, mediaType: 'text/html;charset=utf-8', fileName: `${base}.html` };
}
