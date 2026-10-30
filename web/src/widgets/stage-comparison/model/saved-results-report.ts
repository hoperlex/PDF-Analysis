import type { SavedResultRow, SavedResultSide } from './saved-results';
import { savedResultText } from './saved-results';
import type { Severity, Verdict } from '@/shared/api';
import { VERDICT_LABELS } from '@/entities/expert-decision';
import { SEVERITY_LABELS } from '@/entities/finding';

export const SAVED_COMPARISON_LABELS = { same: 'Совпадает сохранённый разбор', changed: 'Различается сохранённый разбор',
  left_only: 'Запись только слева', right_only: 'Запись только справа' } as const;
export const SAVED_MATCH_LABELS = { finding_uid: 'Один finding_uid', exact_source_content: 'Точные тексты и все исходные привязки',
  exact_preliminary: 'Точный текст и источники предварительного наблюдения' } as const;
export function savedExpertStateText(row: SavedResultRow['left']): string {
  if (row === null) return '';
  const verdict = typeof row.current_verdict === 'string' ? VERDICT_LABELS[row.current_verdict as Verdict] ?? 'неизвестен' : 'не передан';
  const severity = typeof row.decided_severity === 'string' ? SEVERITY_LABELS[row.decided_severity as Severity] ?? 'неизвестна' : 'не назначена';
  return `Текущий вердикт: ${verdict}; экспертная критичность: ${severity}.`;
}
const LIMITATIONS = [
  'Сравниваются два анализа одной неизменяемой версии. Разница не доказывает исправление исходного документа.',
  'Канонические находки сопоставлены по finding_uid, а при разных ID — только по точным текстам, рекомендациям, значениям и полному набору привязок всех исходных и объединённых наблюдений одной версии. Повторы сохранены один к одному. Это соответствие записей для просмотра, не объединение их идентичности.',
  'Предварительные наблюдения сопоставлены только по точной формулировке и реально привязанным источникам. Различия текущего вердикта и экспертной критичности показаны отдельно от различий анализа; решения не переносятся.',
  'Отсутствующий результат не считается пустым. Для недоступной стороны односторонние различия соответствующего типа не вычисляются.',
  'Экспертные состояния показаны как получены при чтении. Это текущая проекция, не восстановленные исторические решения и не транзакционный снимок всех экспертных действий.',
  'Семантически похожие формулировки не объединяются автоматически. Полные исходные ответы сохранены в JSON.',
  'Новые обращения к модели не выполнялись. Сопоставление не записывает решения или переносы.',
];
function html(value: string): string { return value.replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character] ?? character); }
function csv(value: string): string { return `"${(/^[=+\-@\t\r]/.test(value) ? "'" + value : value).replace(/"/g, '""')}"`; }

export function savedResultsReport(left: SavedResultSide, right: SavedResultSide, rows: readonly SavedResultRow[], format: 'json' | 'csv' | 'html') {
  const name = `results-${left.run.run_id}-${right.run.run_id}.${format}`;
  let content: string;
  let mediaType: string;
  if (format === 'json') {
    content = JSON.stringify({ format: 'saved-run-result-comparison/2', left, right, rows, limitations: LIMITATIONS }, null, 2);
    mediaType = 'application/json;charset=utf-8';
  } else if (format === 'csv') {
    const lines = [['Тип', 'Сопоставление', 'Основание соответствия', 'Различается текущее экспертное состояние', 'Экспертное состояние слева', 'Экспертное состояние справа', 'finding_uid слева', 'finding_uid справа', 'Исходный индекс слева', 'Исходный индекс справа', 'Текст слева', 'Текст справа'],
      ...rows.map((row) => [row.kind === 'finding' ? 'Находка' : 'Предварительное наблюдение', SAVED_COMPARISON_LABELS[row.comparison],
        row.matchBasis === null ? '' : SAVED_MATCH_LABELS[row.matchBasis], row.expertStateChanged === null ? '' : row.expertStateChanged ? 'Да' : 'Нет',
        row.kind === 'finding' ? savedExpertStateText(row.left) : '', row.kind === 'finding' ? savedExpertStateText(row.right) : '',
        row.kind === 'finding' ? String(row.left?.finding_uid ?? '') : '', row.kind === 'finding' ? String(row.right?.finding_uid ?? '') : '',
        row.leftIndex === null ? '' : String(row.leftIndex), row.rightIndex === null ? '' : String(row.rightIndex), savedResultText(row.left), savedResultText(row.right)])];
    content = '\uFEFF' + [...LIMITATIONS.map((line) => [line]), ...lines].map((line) => line.map(csv).join(';')).join('\r\n');
    mediaType = 'text/csv;charset=utf-8';
  } else {
    content = `<!doctype html><html lang="ru"><meta charset="utf-8"><title>Сравнение сохранённых результатов</title><style>body{font:16px system-ui;margin:2rem;line-height:1.5}table{border-collapse:collapse;width:100%}td,th{border:1px solid #888;padding:.5rem;vertical-align:top}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Сравнение сохранённых результатов</h1><p>Слева: ${html(left.run.run_id)}. Справа: ${html(right.run.run_id)}.</p><ul>${LIMITATIONS.map((line) => `<li>${html(line)}</li>`).join('')}</ul><table><thead><tr><th>Тип</th><th>Сопоставление</th><th>Основание и экспертное состояние</th><th>Слева</th><th>Справа</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${row.kind === 'finding' ? 'Находка' : 'Предварительное наблюдение'}</td><td>${html(SAVED_COMPARISON_LABELS[row.comparison])}</td><td>${row.matchBasis === null ? 'Нет соответствия' : html(SAVED_MATCH_LABELS[row.matchBasis])}${row.expertStateChanged === null ? '' : `<p>Текущее экспертное состояние ${row.expertStateChanged ? 'различается' : 'совпадает'}.</p>`}</td><td>${row.kind === 'finding' ? `<p>${html(String(row.left?.finding_uid ?? ''))}</p>` : ''}<pre>${html(savedResultText(row.left))}</pre></td><td>${row.kind === 'finding' ? `<p>${html(String(row.right?.finding_uid ?? ''))}</p>` : ''}<pre>${html(savedResultText(row.right))}</pre></td></tr>`).join('')}</tbody></table><details><summary>Полные строки соответствия</summary><pre>${html(JSON.stringify(rows, null, 2))}</pre></details><details><summary>Полные полученные материалы слева</summary><pre>${html(JSON.stringify(left, null, 2))}</pre></details><details><summary>Полные полученные материалы справа</summary><pre>${html(JSON.stringify(right, null, 2))}</pre></details></html>`;
    mediaType = 'text/html;charset=utf-8';
  }
  if (new TextEncoder().encode(content).length > 64 * 1024 * 1024) throw new Error('Выгрузка превышает 64 МиБ. Файл не создан; записи не исключались.');
  return { name, content, mediaType };
}
