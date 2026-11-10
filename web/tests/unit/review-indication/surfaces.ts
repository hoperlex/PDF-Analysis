/**
 * The screens that carry the «no human reviewed this» wording, rendered the way the other tests
 * render them (`REVIEW-INDICATION-SWITCH-01`, `R-146ba`).
 *
 * One function per surface, each returning static markup, so the default test (the real constant)
 * and the per-state test (the constant set for one case) read the same screens. Nothing here knows the switch.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

import type {
  AnalysisProfileListItem,
  AnalysisProfileStatus,
  ApprovedSheetPair,
  ApprovedSheetPairs,
  ComparisonSummary,
  RunStatus,
} from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { ComparisonSummaryView } from '@/entities/version-comparison';
import { AnalysisProfileTable } from '@/widgets/analysis-profile-table';
import { RunProgress } from '@/widgets/run-progress';

import { PROJECT_UID, runStatus } from '../review/fixtures';
import { newClient, renderWith } from '../screens/harness';

/** The profile table with one profile of the given status. */
export function profileTable(status: AnalysisProfileStatus): string {
  const items: AnalysisProfileListItem[] = [{
    section_code: 'KJ',
    section_name: 'Конструктивные решения',
    profile: {
      analysis_profile_id: 'ap_01M5AXG1K22R027A33VTKZ4681',
      prompt_bundle_id: 'pb_01M5AXG1K2JQQH7R4ACTBW8971',
      profile_version: '1.2.0',
      status,
      prompt_bundle_sha256: '1'.repeat(64),
      content_sha256: 'e'.repeat(64),
      source: null,
    },
  }];
  return renderToStaticMarkup(createElement(AnalysisProfileTable, { items }));
}

/** The run screen over one reading; `count: null` is a reading that does not report the count. */
export function runScreen(overrides: Partial<RunStatus>, count?: number | null): string {
  const status = runStatus(overrides);
  if (count === null) delete status.published_finding_count;
  else if (count !== undefined) status.published_finding_count = count;
  const client = newClient();
  client.setQueryData(queryKeys.runs.detail(status.run_id), status);
  return renderWith(client, createElement(RunProgress, { projectUid: PROJECT_UID, runId: status.run_id }));
}

export const SUMMARY_LABEL = 'Сводка подготовлена моделью, проверка человеком не проводилась';

const HASH = 'd'.repeat(64);

/** The comparison summary with a stored summary and its confirmation sentence. */
export function comparisonSummary(): string {
  const stored: ComparisonSummary = {
    summary_id: 'evt_01M2545JSD15ETSNNV904X991J', link_revision: 1, state: 'ready', rejection_reason: null,
    label: SUMMARY_LABEL, statements: [{ text: 'Размер изменён с 30 на 35.', hunk_ids: ['sln_01M2545JSD15ETSNNV904X991J:0'] }],
    prompt_version: 'comparison-summary-v1', provider_mode: 'recorded', model_identity: 'recorded',
    input_sha256: HASH, raw_evidence_seal_sha256: HASH, cost_basis: 'unmetered', is_current: true,
    created_by_label: 'Иванова Е. В.', created_at: '2026-10-27T09:00:00Z',
  };
  const pair: ApprovedSheetPair = {
    sheet_link_id: 'sln_01M2545JSD15ETSNNV904X991J', source_page_number: 2, target_page_number: 3, state: 'verified',
    suggestion_sha256: HASH, approved_by_label: 'Иванова Е. В.', approved_at: '2026-10-27T08:00:00Z', link_revision: 1,
    diff: {
      source_line_count: 2, target_line_count: 2, added_line_count: 1, removed_line_count: 1, evidence_sha256: HASH,
      hunks: [{ tag: 'replace', source_start: 1, source_end: 2, target_start: 1, target_end: 2,
        source_lines: ['размер 30\n'], target_lines: ['размер 35\n'], hunk_id: 'sln_01M2545JSD15ETSNNV904X991J:0' }],
    },
  };
  const approved: ApprovedSheetPairs = {
    link_revision: 1, evidence_state: 'sealed', raw_evidence_seal_sha256: HASH, items: [pair], summary: stored,
  };
  return renderToStaticMarkup(createElement(ComparisonSummaryView, {
    approved, mayDecide: true, confirming: true, pending: false, failure: null,
    onOpen: () => undefined, onConfirm: () => undefined, onCancel: () => undefined,
  }));
}

/** The text a reader sees: tags out, entities left as they are, white space collapsed. */
export function visible(markup: string): string {
  return markup.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ');
}
