import type { ExtendedRunReview } from '@/shared/api';
import { formatExtendedRunXlsx } from './extended-xlsx';
import { EXTENDED_ADVICE, EXTENDED_CORRECTION_ACTION, EXTENDED_NORM_STATUS, extendedReasonText } from './extended-labels';

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
const MD_SYNTAX = new Set('\\`*_{}[]()#+.!|>');
function md(value: unknown): string {
  let escaped = '';
  for (const character of plain(value)) escaped += MD_SYNTAX.has(character) ? `\\${character}` : character;
  return escaped.replace(/</g, '&lt;').replace(/&(?!(?:lt|gt);)/g, '&amp;').replace(/>/g, '&gt;');
}
function code(value: unknown): string {
  const body = JSON.stringify(value, null, 2) ?? 'null';
  const lengths = [...body.matchAll(/`+/g)].map((match) => match[0].length);
  const fence = '`'.repeat(Math.max(3, ...lengths) + 1);
  return `${fence}json\n${body}\n${fence}`;
}
function physicalPage(value: unknown): string { return typeof value === 'number' && Number.isSafeInteger(value) && value > 0 ? String(value) : 'Не передана'; }
function evidenceMarkdown(value: unknown): string { return objects(value).map((entry) => `Источник ${md(entry.source_id)}:\n\n${md(entry.quote)}`).join('\n\n'); }
function evidenceHtml(value: unknown): string { return `<ul>${objects(value).map((entry) => `<li>Источник ${html(entry.source_id)}<blockquote>${html(entry.quote)}</blockquote></li>`).join('')}</ul>`; }

function procedureMarkdown(value: unknown): string {
  return objects(value).map((item) => `- ${md(item.title || item.id)}: ${md(STATUS[plain(item.status)] ?? item.status)}${item.reason ? `; ограничение: ${md(item.reason)}` : ''}`).join('\n');
}
function crossWindowMarkdown(value: unknown): string {
  const body = object(value);
  if (body === null) return '';
  return ['## Сверка источников между окнами', `Состояние: ${md(STATUS[plain(body.status)] ?? 'Не передано')}.`,
    'Принятая политика относится ко всему прогону, а не к каждому локальному окну. Выполненный план не доказывает проверку всех возможных сочетаний или глобальную смысловую полноту.',
    code({ version: body.version, policy: body.policy, source_sha256: body.source_sha256, manifest_sha256: body.manifest_sha256, coverage: body.coverage, phase_coverage: body.phase_coverage, reason: body.reason }),
    '### Сохранённые квитанции межоконного прохода', code(body.batches),
    '### Необработанные сочетания', code(body.pending_batches), '### Пропуски и ограничения', code(body.omitted),
    '### Учтённые фрагменты источников', code(body.pieces),
    'Все исходные локальные и межоконные наблюдения приведены вместе ниже; рекомендации критика, нормативные сверки и исправления не являются экспертными решениями.'].join('\n\n');
}
function crossWindowHtml(value: unknown): string {
  const body = object(value);
  if (body === null) return '';
  return `<section><h2>Сверка источников между окнами</h2><p>Состояние: ${html(STATUS[plain(body.status)] ?? 'Не передано')}. Политика относится ко всему прогону, а не к каждому локальному окну. Проверка всех возможных сочетаний и глобальная смысловая полнота не подтверждены.</p><pre>${html(JSON.stringify({ version: body.version, policy: body.policy, source_sha256: body.source_sha256, manifest_sha256: body.manifest_sha256, coverage: body.coverage, phase_coverage: body.phase_coverage, reason: body.reason }, null, 2))}</pre>${[['batches', 'Сохранённые квитанции'], ['pending_batches', 'Необработанные сочетания'], ['omitted', 'Пропуски и ограничения'], ['pieces', 'Учтённые фрагменты источников']].map(([key, title]) => `<details><summary>${html(title)}</summary><pre>${html(JSON.stringify(body[key ?? ''], null, 2))}</pre></details>`).join('')}<p>Все исходные наблюдения, рекомендации и отдельные сверки сохранены в полном снимке API; решения эксперта не создаются.</p></section>`;
}
function observationMarkdown(item: RecordValue, index: number, sourceIndex: ReadonlyMap<string, RecordValue>): string {
  const lines = [`### ${index + 1}. ${md(item.title)}`, md(item.description), `Идентификатор: ${md(item.observation_id)}. Источники: ${md(item.source_ids)}.`,
    `Нормативный статус: ${md(EXTENDED_NORM_STATUS[plain(item.norm_status)] ?? 'Требует проверки')}. Актуальность и применимость цитат требуют проверки эксперта.`];
  const critic = object(item.review ?? item.critic);
  const correction = object(item.correction);
  const original = object(correction?.original);
  const candidate = object(correction?.candidate);
  if (item.origin_scope === 'global_cross_window') lines.push(`Происхождение: межоконная сверка; пакет ${md(item.cross_window_batch_key)}; исходные окна ${md(item.window_ids)}.`);
  if (item.source_evidence !== undefined) lines.push('Дословные цитаты исходного наблюдения:', evidenceMarkdown(item.source_evidence));
  if (critic !== null) lines.push('#### Рекомендация машинного критика — не решение эксперта', md(EXTENDED_ADVICE[plain(critic.llm_decision)] ?? 'Требуется проверка'),
    `Основание: ${md(extendedReasonText(critic.human_taxonomy_reason))}`, md(critic.explanation), `Предложение: ${md(critic.suggested_fix)}`, evidenceMarkdown(critic.source_evidence));
  else lines.push('Машинная критика этого наблюдения не подтверждена переданными данными.');
  if (correction !== null) lines.push('#### Предложенное уточнение, исходник сохранён', md(EXTENDED_CORRECTION_ACTION[plain(correction.action)] ?? 'Требуется проверка'),
    `Основание: ${md(extendedReasonText(correction.reason))}`, 'Исходный вариант:', md(original?.title ?? item.title), md(original?.description ?? item.description),
    'Предложенный кандидат:', candidate === null ? 'Новый текст не предложен.' : `${md(candidate.title)}\n\n${md(candidate.description)}\n\n${evidenceMarkdown(candidate.source_evidence)}`, `Требуемый контекст: ${md(correction.required_context)}`);
  if (Array.isArray(item.source_ids)) for (const id of item.source_ids) {
    const source = sourceIndex.get(plain(id));
    lines.push(`Источник ${md(id)}; физическая страница PDF: ${md(physicalPage(source?.page_number))}; версия: ${md(source?.version_uid)}; SHA256: ${md(source?.crop_sha256 ?? source?.artifact_sha256 ?? source?.text_sha256)}.`,
      source?.quote ? md(source.quote) : 'Цитата источника не передана.');
  }
  if (item.norm_assessment !== undefined) lines.push('Модельная сверка нормативных цитат, не подтверждение применимости:', code(item.norm_assessment));
  for (const norm of objects(item.norm_candidates)) lines.push(`Нормативный кандидат: ${md(norm.designation)}, пункт ${md(norm.clause_number)}, страница ${md(norm.page_label)}.`, md(norm.quote));
  lines.push('Полная запись наблюдения и все дополнительные поля сохранены в исходных данных API в конце отчёта.');
  return lines.join('\n\n');
}

function parametersMarkdown(value: unknown): string {
  const body = object(value);
  if (body === null) return '';
  return ['## Параметры проекта из источников',
    'Предварительные значения с дословными источниками. Это не утверждённый паспорт, нормативная проверка или полный перечень параметров. Единицы не пересчитывались; разные кандидаты сохранены отдельно.',
    code({ status: body.status, policy: body.policy, coverage: body.coverage, manifest_sha256: body.manifest_sha256, reason: body.reason }),
    ...(body.visual_context_policy === undefined ? [] : ['### Контекст для визуального прохода',
      'Квитанции различают подготовленный запрос и сохранённый ответ; предоставленные кандидаты не считаются визуально подтверждёнными.',
      code({ policy: body.visual_context_policy, receipts: body.visual_context_receipts })]),
    ...(body.review_context_policy === undefined ? [] : ['### Контекст для комплексной сверки, критики и предложений исправления',
      'Предварительные значения переданы с источниками и явными пропусками. Новые допустимые ссылки ответа или решения эксперта из них не создаются; подготовка запроса и получение ответа различаются.',
      code({ policy: body.review_context_policy, receipts: body.review_context_receipts })]),
    ...objects(body.facts).map((fact, index) => [`### Параметр ${index + 1}: ${md(fact.name)}`,
      `Значение: ${md(fact.value)}; единица: ${md(fact.unit)}; предмет: ${md(fact.subject)}.`,
      evidenceMarkdown(fact.source_evidence), code(fact)].join('\n\n')),
    '### Квитанции извлечения параметров', code(body.batches),
    '### Неотобранные фрагменты и ограничения', code({ pending: body.pending, omitted: body.omitted,
      pending_manifest_truncated: body.pending_manifest_truncated, omitted_manifest_truncated: body.omitted_manifest_truncated })].join('\n\n');
}
function parametersHtml(value: unknown): string {
  const body = object(value);
  if (body === null) return '';
  return `<section><h2>Параметры проекта из источников</h2><p>Предварительные значения, не утверждённый паспорт или нормативная проверка. Единицы не пересчитывались. Контекст для изображений помечает подготовку/ответ отдельно и не является визуальным подтверждением. Отсутствие кандидата не доказывает отсутствие параметра в проекте.</p><pre>${html(JSON.stringify({ status: body.status, policy: body.policy, coverage: body.coverage, manifest_sha256: body.manifest_sha256, reason: body.reason, visual_context_policy: body.visual_context_policy, visual_context_receipts: body.visual_context_receipts, review_context_policy: body.review_context_policy, review_context_receipts: body.review_context_receipts }, null, 2))}</pre>${objects(body.facts).map((fact, index) => `<article><h3>${index + 1}. ${html(fact.name)}</h3><p>Значение: ${html(fact.value)}; единица: ${html(fact.unit)}; предмет: ${html(fact.subject)}.</p>${evidenceHtml(fact.source_evidence)}<pre>${html(JSON.stringify(fact, null, 2))}</pre></article>`).join('')}<details><summary>Квитанции и неотобранные источники</summary><pre>${html(JSON.stringify({ batches: body.batches, pending: body.pending, omitted: body.omitted }, null, 2))}</pre></details></section>`;
}

/** Local projection of an already authorised API reading; no model, mutation or accepted-only filter. */
export function formatExtendedRunReport(reading: ExtendedRunReview, format: ExtendedReportFormat): ExtendedReportFile {
  if (format === 'xlsx') return formatExtendedRunXlsx(reading);
  const result = object(reading.result);
  const windows = objects(result?.windows);
  const observations = objects(result?.observations);
  const sourceIndex = new Map<string, RecordValue>(objects(result?.sources).map((source) => [plain(source.source_id), { ...source, version_uid: typeof source.version_uid === 'string' && source.version_uid ? source.version_uid : result?.version_uid }] as const));
  const raw = JSON.stringify(reading, null, 2) ?? 'null';
  const base = `analysis-${reading.run_id}`;
  if (format === 'json') return { content: raw, mediaType: 'application/json;charset=utf-8', fileName: `${base}.json` };
  const disclaimer = 'Предварительный машинный анализ. Рекомендации критика и исправленные кандидаты не являются решениями эксперта. Нормативные значения из исторических рубрик не подтверждены; редакция и применимость цитат требуют отдельной проверки. Все переданные записи сохранены, без фильтра по модельному принятию или отклонению.';
  const metadata = { run_id: reading.run_id, status: reading.status, workflow_version: result?.workflow_version,
    section: result?.section, version_uid: result?.version_uid, rules_sha256: result?.rules_sha256, source_provenance: result?.source_provenance,
    coverage: result?.coverage, text_coverage: result?.text_coverage, consolidation: result?.consolidation, coverage_version: result?.coverage_version,
    coverage_budget_mode: result?.coverage_budget_mode, estimated_text_characters: result?.estimated_text_characters, comprehensive_piece_characters: result?.comprehensive_piece_characters,
    phase_coverage: result?.phase_coverage, phase_call_limits: result?.phase_call_limits,
    norm_paragraph_context_policy: result?.norm_paragraph_context_policy,
    window_progress: result?.window_progress, primary_text_status: result?.primary_text_status,
    visual_phase_complete: result?.visual_phase_complete, report: result?.report };
  const pendingPrimary = result?.primary_text_status === 'pending'
    ? 'Базовый текстовый анализ ещё выполняется. Сохранённый визуальный проход не является завершением всей проверки окна.' : '';
  if (format === 'md') {
    const blocks = ['# Предварительный анализ раздела', disclaimer, pendingPrimary, '## Состояние, покрытие и происхождение', code(metadata),
      '## Фактические процедуры', procedureMarkdown(result?.procedures), crossWindowMarkdown(result?.global_cross_window), parametersMarkdown(result?.project_parameters),
      ...(object(result?.norm_paragraph_context_policy) === null ? [] : ['## Фактически подготовленный нормативный контекст',
        'Подготовленный запрос и сохранённый ответ отмечены отдельно. Соседние абзацы — контекст, а не дополнительные разрешённые цитаты. Актуальность редакции и применимость не подтверждены.', code(result?.normative_context_receipts)]),
      ...(Array.isArray(result?.norm_lookup_receipts) ? ['## Журнал нормативного поиска',
        'Исходные предложенные запросы, реальные ответы поиска/кэша, ошибки и непрочитанные страницы. Отсутствие попаданий не доказывает отсутствие нормы. Журнал не создаёт обращений, решений или записей каталога.', code(result.norm_lookup_receipts)] : []),
      `## Общий свод: ${observations.length} записей`,
      ...observations.map((item, index) => observationMarkdown(item, index, sourceIndex))];
    for (const [index, window] of windows.entries()) blocks.push(`## Окно ${index + 1}: ${md(window.window_id)}`,
      `Состояние: ${md(STATUS[plain(window.status)] ?? window.status)}`, procedureMarkdown(window.procedures),
      ...(window.visual_phase_complete === true && window.status === 'running' ? ['Визуальный проход сохранён; оставшиеся процедуры окна ещё не завершены.'] : []),
      'Все сохранённые данные окна, включая первоначальные наблюдения и рекомендации:', code(window));
    blocks.push('## Полная исходная запись API', 'Включены все наблюдения, окна, цитаты, источники, ограничения и исправленные кандидаты. Повторяющиеся записи сохранены как часть происхождения.', code(reading));
    return { content: blocks.join('\n\n') + '\n', mediaType: 'text/markdown;charset=utf-8', fileName: `${base}.md` };
  }
  const procedureHtml = (value: unknown) => `<ol>${objects(value).map((item) => `<li><strong>${html(item.title || item.id)}</strong>: ${html(STATUS[plain(item.status)] ?? item.status)}${item.reason ? `<p>${html(item.reason)}</p>` : ''}</li>`).join('')}</ol>`;
  const rows = observations.map((item, index) => {
    const critic = object(item.review ?? item.critic);
    const correction = object(item.correction);
    const original = object(correction?.original);
    const candidate = object(correction?.candidate);
    const sources = (Array.isArray(item.source_ids) ? item.source_ids : []).map((id) => { const source = sourceIndex.get(plain(id)); return `<li>Источник ${html(id)}; физическая страница PDF: ${html(physicalPage(source?.page_number))}; версия: ${html(source?.version_uid)}; SHA256: ${html(source?.crop_sha256 ?? source?.artifact_sha256 ?? source?.text_sha256)}.${source?.quote ? `<blockquote>${html(source.quote)}</blockquote>` : '<p>Цитата не передана.</p>'}</li>`; }).join('');
    const advice = critic === null ? '<p>Машинная критика не подтверждена переданными данными.</p>' : `<section><h4>Рекомендация критика — не решение эксперта</h4><strong>${html(EXTENDED_ADVICE[plain(critic.llm_decision)] ?? 'Требуется проверка')}</strong><p>${html(extendedReasonText(critic.human_taxonomy_reason))}</p><p>${html(critic.explanation)}</p><p>Предложение: ${html(critic.suggested_fix)}</p>${evidenceHtml(critic.source_evidence)}</section>`;
    const fixed = correction === null ? '' : `<section><h4>Уточнение, исходник сохранён</h4><p>${html(EXTENDED_CORRECTION_ACTION[plain(correction.action)] ?? 'Требуется проверка')}. ${html(extendedReasonText(correction.reason))}</p><h5>Исходный вариант</h5><strong>${html(original?.title ?? item.title)}</strong><p>${html(original?.description ?? item.description)}</p><h5>Предложенный кандидат</h5>${candidate === null ? '<p>Новый текст не предложен.</p>' : `<strong>${html(candidate.title)}</strong><p>${html(candidate.description)}</p>${evidenceHtml(candidate.source_evidence)}`}<p>Требуемый контекст: ${html(correction.required_context)}</p></section>`;
    const norms = `<section><h4>Нормативные данные — применимость не подтверждена</h4><p>Статус: ${html(EXTENDED_NORM_STATUS[plain(item.norm_status)] ?? 'Требует проверки')}</p>${objects(item.norm_candidates).map((norm) => `<p>${html(norm.designation)}, пункт ${html(norm.clause_number)}, страница ${html(norm.page_label)}</p><blockquote>${html(norm.quote)}</blockquote>`).join('')}${item.norm_assessment === undefined ? '' : `<details><summary>Сохранённая модельная сверка цитат</summary><pre>${html(JSON.stringify(item.norm_assessment, null, 2))}</pre></details>`}</section>`;
    const origin = item.origin_scope === 'global_cross_window' ? `<p>Происхождение: межоконная сверка; пакет ${html(item.cross_window_batch_key)}; исходные окна ${html(item.window_ids)}.</p>` : '';
    return `<article><h3>${index + 1}. ${html(item.title)}</h3><p>${html(item.description)}</p>${origin}<p>Исходное наблюдение сохранено. Решение эксперта не принято этой моделью.</p>${item.source_evidence === undefined ? '' : `<section><h4>Цитаты исходного наблюдения</h4>${evidenceHtml(item.source_evidence)}</section>`}${advice}${fixed}<section><h4>Исходные материалы</h4><ul>${sources}</ul></section>${norms}</article>`;
  }).join('');
  const windowHtml = windows.map((window, index) => `<section><h2>Окно ${index + 1}: ${html(window.window_id)}</h2><p>${html(STATUS[plain(window.status)] ?? window.status)}</p>${window.visual_phase_complete === true && window.status === 'running' ? '<p>Визуальный проход сохранён; оставшиеся процедуры окна ещё не завершены.</p>' : ''}${procedureHtml(window.procedures)}<pre>${html(JSON.stringify(window, null, 2))}</pre></section>`).join('');
  const normContextHtml = object(result?.norm_paragraph_context_policy) === null ? '' : `<section><h2>Фактически подготовленный нормативный контекст</h2><p>Подготовка запроса и наличие сохранённого ответа отмечены отдельно. Исходные абзацы и соседний текст ограничены; сокращения сохранены. Цитаты закреплены отдельно за каждым наблюдением. Соседние абзацы не создают новых разрешённых ссылок; актуальность и применимость не подтверждены.</p><pre>${html(JSON.stringify(result?.normative_context_receipts, null, 2))}</pre></section>`;
  const normSearchHtml = !Array.isArray(result?.norm_lookup_receipts) ? '' : `<section><h2>Журнал нормативного поиска</h2><p>Все сохранённые запросы, полученные ответы и использование кэша, ошибки, сокращённые цитаты и непрочитанное продолжение выдачи. Отсутствие попаданий не доказывает отсутствие документа или требования. Это ручной разбор исходных действий, без новых запросов и записей нормативного каталога.</p><pre>${html(JSON.stringify(result.norm_lookup_receipts, null, 2))}</pre></section>`;
  const content = `<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Предварительный анализ раздела</title><style>body{max-width:1100px;margin:32px auto;padding:0 20px;font:16px/1.5 system-ui,sans-serif;color:#15202b;background:#fff}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f7;padding:16px}article,section{border-top:1px solid #c9d1d9;padding:16px 0}h1,h2,h3{line-height:1.2}</style></head><body><h1>Предварительный анализ раздела</h1><p>${html(disclaimer)}</p>${pendingPrimary ? `<p>${html(pendingPrimary)}</p>` : ''}<h2>Состояние, покрытие и происхождение</h2><pre>${html(JSON.stringify(metadata, null, 2))}</pre><h2>Фактические процедуры</h2>${procedureHtml(result?.procedures)}${crossWindowHtml(result?.global_cross_window)}${parametersHtml(result?.project_parameters)}${normContextHtml}${normSearchHtml}<h2>Общий свод: ${observations.length} записей</h2>${rows}${windowHtml}<h2>Полная исходная запись API</h2><p>Все переданные записи, источники, цитаты и ограничения без фильтра по модельной рекомендации.</p><pre>${html(raw)}</pre></body></html>`;
  return { content, mediaType: 'text/html;charset=utf-8', fileName: `${base}.html` };
}
