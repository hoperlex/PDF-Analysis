/**
 * The PDF report window and the block «Сводка MD и отчёт для заказчика» (`version-comparison-md-report.js`,
 * `version-comparison.js:277-333`): which controls a report offers in each state, what its progress says, and the specification
 * block's figures (`version-comparison.js:237-275`).
 *
 * The rules mirror what the server accepts (`CMP-SEAL-C2` §3 operation descriptions): «Отменить» for a queued, running or paused
 * report; «Продолжить» for a paused, partial, failed or cancelled one; «Пересобрать PDF» (no model call, nothing spent) for a
 * report whose text is complete — a completed one, or one that failed while writing the PDF; «Удалить» for a report that is not
 * live; «Подготовить отчёт для заказчика» for a finished analytic report; the downloads for the files it holds.
 */

import type {
  ComparisonReport,
  ComparisonReportPart,
  ComparisonSpecTotals,
  ComparisonSpecification,
} from '@/shared/api';

import { REPORT_KIND_LABELS, UNIT_MARKS } from './ai-words';

export function isLiveReport(report: Pick<ComparisonReport, 'state'>): boolean {
  return report.state === 'queued' || report.state === 'running' || report.state === 'paused';
}

export function canCancelReport(report: Pick<ComparisonReport, 'state'>): boolean {
  return isLiveReport(report);
}

export function canContinueReport(report: Pick<ComparisonReport, 'state'>): boolean {
  return report.state === 'paused' || report.state === 'partial' || report.state === 'failed' || report.state === 'cancelled';
}

/** «Пересобрать PDF» writes the PDF again from the stored text; it needs the text complete (`rebuildComparisonReportPdf`). */
export function canRebuildReport(report: Pick<ComparisonReport, 'state' | 'stage'>): boolean {
  return report.state === 'completed' || (report.state === 'failed' && report.stage === 'pdf_writing');
}

export function canDeleteReport(report: Pick<ComparisonReport, 'state'>): boolean {
  return !isLiveReport(report);
}

export function canStartReport(report: Pick<ComparisonReport, 'state'>): boolean {
  return report.state === 'draft';
}

/** «Подготовить отчёт для заказчика» is offered on a finished analytic report (`prepareComparisonClientReport`). */
export function canPrepareClientReport(report: Pick<ComparisonReport, 'state' | 'kind'>): boolean {
  return report.kind === 'analytic' && (report.state === 'completed' || report.state === 'partial');
}

export function hasArtifact(report: Pick<ComparisonReport, 'artifacts'>, kind: 'report_pdf' | 'source_md'): boolean {
  return report.artifacts.some((artifact) => artifact.kind === kind);
}

/** A report that has its PDF can be downloaded; the source MD is the file it was made from. */
export function pdfName(report: Pick<ComparisonReport, 'report_id' | 'kind'>): string {
  return `${report.kind === 'client' ? 'otchet-dlya-zakazchika' : 'analiticheskiy-otchet'}-${report.report_id.slice(-6)}.pdf`;
}

export function sourceMdName(report: Pick<ComparisonReport, 'report_id'>): string {
  return `svodka-${report.report_id.slice(-6)}.md`;
}

function n(value: number): string {
  return value.toLocaleString('ru-RU');
}

/** «переходов N из M» (client) or «анализ N из M · проверка N из M» (analytic) (`:285-291`). */
export function reportProgressLine(report: Pick<ComparisonReport, 'kind' | 'parts'>): string {
  const total = report.parts.length;
  if (total === 0) return '';
  if (report.kind === 'client') {
    const done = report.parts.filter((part) => part.selection === 'done').length;
    const failed = report.parts.filter((part) => part.selection === 'failed').length;
    return `переходов ${n(done)} из ${n(total)}${failed > 0 ? ` · не подготовлено ${n(failed)}` : ''}`;
  }
  const analysed = report.parts.filter((part) => part.analysis === 'done').length;
  const verified = report.parts.filter((part) => part.verification === 'done').length;
  const failed = report.parts.filter((part) => part.analysis === 'failed' || part.verification === 'failed').length;
  return `анализ ${n(analysed)} из ${n(total)} · проверка ${n(verified)} из ${n(total)}${failed > 0 ? ` · брак ${n(failed)}` : ''}`;
}

/** The recall line the PDF prints on every page («изменённых листов N, описано K, отброшено проверкой D») is the report's; the client names the kind. */
export function reportKindLine(report: Pick<ComparisonReport, 'kind'>): string {
  return REPORT_KIND_LABELS[report.kind];
}

export function unitMark(mark: ComparisonReportPart['selection']): { readonly mark: string; readonly word: string } {
  return mark === undefined ? { mark: '—', word: 'нет обращения' } : UNIT_MARKS[mark];
}

export function usageLine(report: Pick<ComparisonReport, 'job'>): string {
  const spend = report.job?.spend;
  if (spend === undefined || spend.calls === 0) return '';
  return `обращений ${n(spend.calls)} · токены: вход ${n(spend.input_tokens)}, выход ${n(spend.output_tokens)}`;
}

// ------------------------------------------------------------------------------ the specification block

/** «изменено / +добавлено / −удалено / ?неясно» (`:262`): `3 / +1 / −2 / ?1`; the last only when something is unclear. */
export function positionsLine(totals: ComparisonSpecTotals | undefined): string {
  if (totals === undefined) return '—';
  return `${n(totals.changed)} / +${n(totals.added)} / −${n(totals.removed)}${totals.unclear > 0 ? ` / ?${n(totals.unclear)}` : ''}`;
}

/** «покрыто N из M» over the blocks of both sides (`specPct`, `:204`). */
export function coverageLine(spec: Pick<ComparisonSpecification, 'coverage_a' | 'coverage_b'>): string {
  const a = spec.coverage_a;
  const b = spec.coverage_b;
  if (a === undefined && b === undefined) return '—';
  const covered = (a?.blocks_covered ?? 0) + (b?.blocks_covered ?? 0);
  const total = (a?.blocks_total ?? 0) + (b?.blocks_total ?? 0);
  return `${n(covered)} из ${n(total)}`;
}

export function coveragePercent(spec: Pick<ComparisonSpecification, 'coverage_a' | 'coverage_b'>): number {
  const covered = (spec.coverage_a?.blocks_covered ?? 0) + (spec.coverage_b?.blocks_covered ?? 0);
  const total = (spec.coverage_a?.blocks_total ?? 0) + (spec.coverage_b?.blocks_total ?? 0);
  return total > 0 ? Math.round((100 * covered) / total) : 100;
}

/** «Листов СО» A / B: «3 / 4» with the older version first. */
export function specSheetsLine(spec: Pick<ComparisonSpecification, 'sheets_a' | 'sheets_b'>): string {
  return `${spec.sheets_a} / ${spec.sheets_b}`;
}

/** The header line of the block: «полное сравнение: N из M переходов · листовой ИИ: K» (`:253-256`). */
export function specMethodsLine(specs: readonly Pick<ComparisonSpecification, 'method' | 'state'>[]): string {
  const applicable = specs.filter((spec) => spec.state !== 'not_applicable');
  const whole = applicable.filter((spec) => spec.method === 'whole').length;
  const sheet = applicable.filter((spec) => spec.method === 'sheet_ai').length;
  return `полное сравнение: ${whole} из ${applicable.length} переходов · листовой ИИ: ${sheet}`;
}
