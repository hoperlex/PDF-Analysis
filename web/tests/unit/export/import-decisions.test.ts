/**
 * «Загрузить решения из Excel» (`R-151d`, `importRunDecisions`).
 *
 * The expert loads the workbook «Скачать Excel» produced back, edited; the server matches rows by «ID
 * замечания». These cases pin what the control says: the counts, each refused row with its reason in
 * words, a foreign file refused whole, and that the control is an expert's (the panel offers it only
 * when asked to).
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { DecisionImportReport, ErrorEnvelope, RunId } from '@/shared/api';
import { ApiError } from '@/shared/api';
import { IMPORT_REFUSAL_LABELS, ImportDecisionsView, importFailure } from '@/features/import-decisions';
import type { ImportDecisionsViewProps } from '@/features/import-decisions';
import { ExportPanel } from '@/widgets/export-panel';

const RUN = 'run_01M5B0000000000000000000R1' as RunId;

function view(over: Partial<ImportDecisionsViewProps> = {}): string {
  return renderToStaticMarkup(createElement(ImportDecisionsView, {
    pending: false, report: null, failure: null, onChoose: () => {}, ...over,
  }));
}

const REPORT: DecisionImportReport = {
  run_id: RUN, recorded: 2, unchanged: 40, refused: 2,
  rows: [
    { row: 2, outcome: 'recorded', finding_uid: 'fnd_01M5B0000000000000000000F1' },
    { row: 7, outcome: 'refused', reason: 'unknown_finding' },
    { row: 9, outcome: 'refused', finding_uid: 'fnd_01M5B0000000000000000000F3', reason: 'finding_not_in_run' },
  ],
};

function refusal(constraint: string): ApiError {
  const envelope = {
    contract_version: '1.49.0', error_code: 'validation_failed', message: 'refused',
    correlation_id: 'cor_1', retryable: false, details: { field: 'file', constraint },
  } as unknown as ErrorEnvelope;
  return new ApiError(422, envelope, 'cor_1');
}

describe('the decision import control', () => {
  it('offers the file choice in words', () => {
    const markup = view();
    expect(markup).toContain('Загрузить решения из Excel');
    expect(markup).toContain('accept=".xlsx,');
  });

  it('says the counts and each refused row with its reason', () => {
    const markup = view({ report: REPORT });
    expect(markup).toContain('Записано 2 · без изменений 40 · отклонено 2');
    expect(markup).toContain(`Строка 7: ${IMPORT_REFUSAL_LABELS.unknown_finding}`);
    expect(markup).toContain(`Строка 9: ${IMPORT_REFUSAL_LABELS.finding_not_in_run}`);
    expect(markup).not.toContain('Строка 2:');
  });

  it('says a foreign file is not our export, and what to do', () => {
    expect(importFailure(refusal('not_our_export'))).toContain('Скачайте Excel заново');
    expect(importFailure(refusal('too_large'))).toBe('Файл больше 10 MiB.');
  });

  it('is offered on the export panel only to an expert', () => {
    const panel = (mayImportDecisions: boolean): string => renderToStaticMarkup(createElement(ExportPanel, {
      runId: RUN, runState: 'published', providerMode: 'live', onExport: () => {}, mayImportDecisions,
    }));
    expect(() => panel(false)).not.toThrow();
    expect(panel(false)).not.toContain('Загрузить решения из Excel');
  });
});
