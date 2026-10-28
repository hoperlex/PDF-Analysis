/**
 * The screens that carry the «no human reviewed this» wording, rendered the way the other tests
 * render them (`REVIEW-INDICATION-SWITCH-01`, `R-146ba`).
 *
 * One function per surface, each returning static markup, so the default test (the real constant)
 * and the per-state test (the constant set for one case) read the same screens. The data are the
 * fixtures the AR v3 tests already use; nothing here knows the switch.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

import type {
  Account,
  AnalysisProfileListItem,
  AnalysisProfileStatus,
  ApprovedSheetPair,
  ApprovedSheetPairs,
  ArV3BetaGroupReview,
  ComparisonSummary,
  RunStatus,
} from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { AR_V3_BETA_PROFILE_ID } from '@/entities/audit-run';
import { ComparisonSummaryView } from '@/entities/version-comparison';
import { StartArV3GroupView } from '@/features/start-ar-v3-group';
import { AnalysisProfileTable } from '@/widgets/analysis-profile-table';
import { ArV3BetaPack } from '@/widgets/ar-v3-beta-pack';
import { ArV3BetaReview } from '@/widgets/ar-v3-beta-review';
import { ArV3BetaStatus } from '@/widgets/ar-v3-beta-status';
import { RunProgress } from '@/widgets/run-progress';

import { installedPackFixture } from '../analysis-settings/ar-v3-beta-pack-fixtures';
import {
  AVAILABLE_RUN_ID, GROUP_ID, accountFixture, groupReviewFixture, runFindingsPage, v3FindingFixture,
} from '../analysis-settings/ar-v3-beta-review-fixtures';
import { PROJECT_UID, VERSION_UID, runStatus } from '../review/fixtures';
import { newClient, renderScreen, renderWith } from '../screens/harness';

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

/** The frozen source-disposition preview of the AR v3 beta. */
export function betaStatus(): string {
  return renderToStaticMarkup(createElement(ArV3BetaStatus));
}

/** The review of the one scope the fixture makes available. */
export type AvailableReview = NonNullable<ArV3BetaGroupReview['members'][number]['review']>;

export interface ReviewOptions {
  readonly roles?: Account['roles'];
  /** Change the available scope's review before it is drawn. */
  readonly edit?: (review: AvailableReview) => void;
}

/** The group review with its available scope and that scope's findings. */
export function groupReview(options: ReviewOptions = {}): string {
  const review = groupReviewFixture();
  const available = review.members[0]?.review;
  if (available !== null && available !== undefined) options.edit?.(available);
  const client = newClient();
  client.setQueryData(queryKeys.runs.arV3GroupReview(GROUP_ID), review);
  client.setQueryData(queryKeys.runs.findings(AVAILABLE_RUN_ID), { data: runFindingsPage([v3FindingFixture()]) });
  client.setQueryData(queryKeys.account.me(), accountFixture(options.roles ?? ['expert']));
  return renderScreen(client, createElement(ArV3BetaReview, { groupId: GROUP_ID }));
}

/** The group lookup, before a group is named. */
export function groupLookup(): string {
  return renderScreen(newClient(), createElement(ArV3BetaReview, { groupId: null }));
}

/** The control that starts the six checks, idle. */
export function startControl(): string {
  return renderToStaticMarkup(createElement(StartArV3GroupView, {
    projectUid: PROJECT_UID, versionUid: VERSION_UID, pending: false, failure: null, onSend: () => undefined,
  }));
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

/** An AR v3 beta Run in the given state; `count` is the published-finding count the server reports. */
export function v3Run(state: RunStatus['state'], count: number | null): string {
  return runScreen({ state, analysis_profile_id: AR_V3_BETA_PROFILE_ID, stages: [] }, count);
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

/** The pack panel with an installed pack: its attestation record. */
export function packPanel(): string {
  const client = newClient();
  client.setQueryData(queryKeys.runs.arV3PackStatus(), installedPackFixture());
  return renderScreen(client, createElement(ArV3BetaPack));
}

/** The text a reader sees: tags out, entities left as they are, white space collapsed. */
export function visible(markup: string): string {
  return markup.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ');
}
