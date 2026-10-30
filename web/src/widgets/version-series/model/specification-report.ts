import type { ComparisonSpecification, ComparisonSpecChange, ComparisonSpecPosition } from '@/shared/api';
import { SPEC_CHANGE_KIND_LABELS, SPEC_FIELD_LABELS, SPEC_PHASE_LABELS, SPEC_STATE_LABELS } from '@/entities/version-series';

export interface SpecificationReport {
  readonly format: 'whole-specification-api-projection/1'; readonly received_at: string;
  readonly specification: ComparisonSpecification; readonly changes: readonly ComparisonSpecChange[]; readonly limitations: readonly string[];
}
export type SpecificationReportFormat = 'json' | 'csv' | 'html';
const COLUMNS = ['pos', 'name', 'mark', 'code', 'supplier', 'unit', 'quantity', 'mass', 'note', 'section', 'parent'] as const;
const MAX_BYTES = 64 * 1024 * 1024;
function html(value: unknown): string { return String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }
function csv(value: unknown): string { const text = String(value ?? ''); return '"' + (/^[\s]*[=+\-@\t\r]/.test(text) ? "'" : '') + text.replace(/"/g, '""') + '"'; }
function position(value: ComparisonSpecPosition | undefined): string { return value === undefined ? 'Позиция на этой стороне не передана' : COLUMNS.filter((key) => value[key] !== undefined).map((key) => `${SPEC_FIELD_LABELS[key] ?? key}: ${value[key]}`).join('\n'); }
function page(value: ComparisonSpecPosition | undefined): string { return value?.page === undefined ? 'Страница не передана' : `Физическая страница PDF ${value.page.page_number}; версия ${value.page.version_uid}`; }

export function formatSpecificationReport(report: SpecificationReport, format: SpecificationReportFormat): { readonly content: string; readonly mediaType: string; readonly fileName: string } {
  const spec = report.specification;
  let content: string;
  if (format === 'json') content = JSON.stringify(report, null, 2) ?? 'null';
  else if (format === 'csv') {
    const rows = [['Переход', 'Изменение ID', 'Тип', 'Описание', 'Было (API-проекция)', 'Стало (API-проекция)', 'Страница A', 'Страница B', 'Изменённые поля', 'Ограничения']];
    for (const change of report.changes) rows.push([spec.transition_id, change.change_id, SPEC_CHANGE_KIND_LABELS[change.kind], change.text ?? '', position(change.old), position(change.new), page(change.old), page(change.new), change.fields.map((field) => `${SPEC_FIELD_LABELS[field.field] ?? field.field}: ${field.was ?? '—'} → ${field.now ?? '—'}`).join('\n'), report.limitations.join('\n')]);
    content = '\uFEFF' + rows.map((row) => row.map(csv).join(';')).join('\r\n');
  } else {
    const rows = report.changes.map((change) => `<article><h2>${html(SPEC_CHANGE_KIND_LABELS[change.kind])}</h2><p>ID: <code>${html(change.change_id)}</code></p><p>${html(change.text)}</p><table><thead><tr><th>Сторона A, было</th><th>Сторона B, стало</th></tr></thead><tbody><tr><td>${html(page(change.old))}<pre>${html(position(change.old))}</pre></td><td>${html(page(change.new))}<pre>${html(position(change.new))}</pre></td></tr></tbody></table><ul>${change.fields.map((field) => `<li>${html(SPEC_FIELD_LABELS[field.field] ?? field.field)}: ${html(field.was)} → ${html(field.now)}</li>`).join('')}</ul></article>`).join('');
    content = `<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><title>СО — полученная API-проекция</title><style>body{font:16px/1.5 system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:1rem}pre,p{white-space:pre-wrap;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%}td,th{border:1px solid #aaa;padding:.6rem;vertical-align:top}article{border-top:1px solid #aaa;margin-top:2rem}code{overflow-wrap:anywhere}</style></head><body><h1>Спецификация — полученная API-проекция</h1><p>Переход: ${html(spec.transition_id)}. Состояние: ${html(SPEC_STATE_LABELS[spec.state])}. ${spec.phase === undefined ? '' : `Этап: ${html(SPEC_PHASE_LABELS[spec.phase])}.`} Получено изменений позиций: ${report.changes.length}.</p><ul>${report.limitations.map((line) => `<li>${html(line)}</li>`).join('')}</ul><h2>Сохранённое покрытие и происхождение</h2><pre>${html(JSON.stringify(spec, null, 2))}</pre>${rows}<details><summary>Полная полученная запись API</summary><pre>${html(JSON.stringify(report, null, 2))}</pre></details></body></html>`;
  }
  if (new TextEncoder().encode(content).length > MAX_BYTES) throw new Error('Выгрузка API-проекции превышает 64 МиБ. Файл не создан; данные не усекались.');
  return { content, mediaType: format === 'json' ? 'application/json;charset=utf-8' : format === 'csv' ? 'text/csv;charset=utf-8' : 'text/html;charset=utf-8', fileName: `specification-${spec.transition_id}.${format}` };
}
