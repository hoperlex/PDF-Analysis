/**
 * `W57B-NORMS-CATALOGUE-XLSX-01` — «Скачать Excel» beside the CSV button: offered on the
 * CSV's exportability rule, named by the shared helper, and the workbook's two source
 * refusals said in words rather than as an empty file.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ErrorCode, ErrorEnvelope, RunState } from '@/shared/api';
import {
  ApiError, EXPORTABLE_RUN_STATES, OPERATIONS, RUN_STATE_VALUES, isExportableRunState, xlsxFileName,
} from '@/shared/api';
import { ExportPanel, xlsxFailure } from '@/widgets/export-panel';

import { RUN_ID, render } from '../review/fixtures';

function panel(runState: RunState) {
  return render(createElement(ExportPanel, {
    runId: RUN_ID, runState, providerMode: 'recorded', onExport: () => {},
  }));
}

function refusal(status: number, code: ErrorCode, details: Record<string, string> = {}): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.7.0',
    error_code: code,
    message: 'English the client never prints.',
    correlation_id: 'cid-xlsx-1',
    retryable: false,
    details,
  };
  return new ApiError(status, envelope, 'cid-xlsx-1');
}

describe('«Скачать Excel»', () => {
  it.each(EXPORTABLE_RUN_STATES)('is offered beside the CSV for %s', (state) => {
    const markup = panel(state);
    expect(markup).toContain('data-intent="export"');
    expect(markup).toContain('data-intent="export-xlsx"');
    expect(markup).toContain('Скачать Excel');
  });

  it.each(RUN_STATE_VALUES.filter((state) => !isExportableRunState(state)))('is not offered for %s', (state) => {
    expect(panel(state)).not.toContain('data-intent="export-xlsx"');
  });

  it('names the file after the run and asks the workbook operation', () => {
    expect(xlsxFileName(RUN_ID)).toBe(`${RUN_ID}-findings.xlsx`);
    expect(OPERATIONS.exportRunXlsx.path).toBe('/runs/{run_id}/export.xlsx');
  });

  it('says the workbook’s two source refusals in words, with the correlation id', () => {
    const labels = xlsxFailure(refusal(422, 'storage_integrity_error', { role: 'source.structured_companion' }));
    expect(labels.title).toBe('Excel не выгружен');
    expect(labels.detail).toContain('«Лист/стр.»');
    expect(labels.correlationId).toBe('cid-xlsx-1');
    const citations = xlsxFailure(refusal(422, 'required_norm_unavailable', { reference_kind: 'norm_retrieval_set' }));
    expect(citations.detail).toContain('Цитаты норм');
    const state = xlsxFailure(refusal(409, 'state_transition_not_allowed'));
    expect(state.detail).not.toContain('English the client never prints');
  });
});
