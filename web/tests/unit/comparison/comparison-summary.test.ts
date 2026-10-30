/**
 * The summary of the approved pairs on the comparison screen (`COMPARE-PERSISTED-SUMMARY-01`, B2).
 *
 * Rendered through the screen harness with seeded caches, plus the view's states and the entity's
 * pure helpers. What a reviewer must be able to read: the server's label, that a replayed recording
 * is not a model call, whether the text still describes the approved set, which change each
 * statement is about, and that a rejected reply is an answer with a reason and no text. The button
 * is an expert's, asks after a confirmation, and exists only for a set the server sealed.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type {
  Account,
  ApprovedSheetPair,
  ApprovedSheetPairs,
  ComparisonSummary,
  DocumentVersion,
  ErrorCode,
  ErrorEnvelope,
  VersionComparison,
} from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import { COMPARISON_DIFF_LIMIT, VERSION_PAGE_LIMIT } from '@/entities/document-version';
import {
  ComparisonSummaryView,
  RECORDED_MODE_TEXT,
  SUMMARY_CONFLICT_TEXT,
  SUMMARY_NOT_CURRENT_TEXT,
  SUMMARY_NOT_PERMITTED_DETAIL,
  SUMMARY_NOT_SEALED_TEXT,
  SUMMARY_REJECTION_TEXT,
  SUMMARY_UNAVAILABLE_DETAIL,
  canOfferSummary,
  citationText,
  summaryFailure,
  summarySignature,
} from '@/entities/version-comparison';
import { StageComparisonPage } from '@/_pages/stage-comparison';

import { newClient, renderScreen } from '../screens/harness';

const ULID = '01M2545JSD15ETSNNV904X991J';
const PROJECT_UID = `prj_${ULID}`;
const DOCUMENT_UID = `doc_${ULID}`;
const OLDER = `ver_${ULID}`;
const NEWER = 'ver_01M2545JSD15ETSNNV904X991K';
const LINK = `sln_${ULID}`;
const SHA = 'a'.repeat(64);
const LABEL = 'Сводка подготовлена моделью, проверка человеком не проводилась';

function version(over: Partial<DocumentVersion>): DocumentVersion {
  return {
    version_uid: OLDER, document_uid: DOCUMENT_UID, project_uid: PROJECT_UID, version_ordinal: 1,
    media_type: 'application/pdf', byte_size: 1, sha256: SHA, page_count: 2,
    published_at: '2026-10-20T08:00:00Z', input_manifest: [],
    classification: {
      version_uid: over.version_uid ?? OLDER, project_stage: 'P', section_code: 'AR',
      confirmed_by_user_uid: `usr_${ULID}`, confirmed_at: '2026-10-20T08:00:00Z', revision: 1,
    },
    ...over,
  };
}

const ITEM: ApprovedSheetPair = {
  sheet_link_id: LINK, source_page_number: 2, target_page_number: 3, state: 'verified',
  suggestion_sha256: SHA, approved_by_label: 'Иванова Е. В.', approved_at: '2026-10-27T08:00:00Z',
  link_revision: 1,
  diff: {
    source_line_count: 2, target_line_count: 2, added_line_count: 1, removed_line_count: 1,
    evidence_sha256: 'c'.repeat(64),
    hunks: [{ tag: 'replace', source_start: 1, source_end: 2, target_start: 1, target_end: 2,
      source_lines: ['размер 30\n'], target_lines: ['размер 35\n'], hunk_id: `${LINK}:0` }],
  },
};

const STORED: ComparisonSummary = {
  summary_id: `evt_${ULID}`, link_revision: 1, state: 'ready', rejection_reason: null, label: LABEL,
  statements: [{ text: 'Размер изменён с 30 на 35.', hunk_ids: [`${LINK}:0`] }],
  prompt_version: 'comparison-summary-v1', provider_mode: 'recorded', model_identity: 'recorded',
  input_sha256: SHA, raw_evidence_seal_sha256: 'd'.repeat(64), cost_basis: 'unmetered',
  is_current: true, created_by_label: 'Иванова Е. В.', created_at: '2026-10-27T09:00:00Z',
};

function approved(over: Partial<ApprovedSheetPairs> = {}): ApprovedSheetPairs {
  return {
    link_revision: 1, evidence_state: 'sealed', raw_evidence_seal_sha256: 'd'.repeat(64),
    items: [ITEM], ...over,
  };
}

function compared(pairs: ApprovedSheetPairs): VersionComparison {
  return {
    project_uid: PROJECT_UID, document_uid: DOCUMENT_UID,
    source_version_uid: OLDER, target_version_uid: NEWER,
    mode: 'version', outcome: 'compared', refusal: null,
    source: { version_uid: OLDER, version_ordinal: 1, page_count: 3, sha256: SHA, project_stage: 'P',
      section_code: 'AR', run_id: `run_${ULID}`, text_layer_sha256: SHA },
    target: { version_uid: NEWER, version_ordinal: 2, page_count: 3, sha256: SHA, project_stage: 'P',
      section_code: 'AR', run_id: 'run_01M2545JSD15ETSNNV904X991K', text_layer_sha256: SHA },
    comparison_sha256: SHA, sheets: [],
    sheet_diffs: { offset: 0, limit: COMPARISON_DIFF_LIMIT, total: 0, next_offset: null, items: [] },
    findings: null, approved_pairs: pairs,
  };
}

function screen(pairs: ApprovedSheetPairs, roles: Account['roles'] | null): string {
  const client = newClient();
  client.setQueryData(queryKeys.versions.detail(OLDER), version({}));
  client.setQueryData(queryKeys.versions.list(DOCUMENT_UID, undefined, VERSION_PAGE_LIMIT), {
    items: [version({ version_uid: NEWER, version_ordinal: 2 }), version({})], page: { next_cursor: null },
  });
  client.setQueryData(
    queryKeys.versions.comparison(OLDER, NEWER, 'version', 0, COMPARISON_DIFF_LIMIT), compared(pairs),
  );
  if (roles !== null) client.setQueryData(queryKeys.account.me(), { roles } as Account);
  return renderScreen(client, createElement(StageComparisonPage, { projectUid: PROJECT_UID, versionUid: OLDER }));
}

function visible(markup: string): string {
  return markup.replace(/<[^>]*>/g, ' ').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ');
}

function apiError(status: number, code: ErrorCode, details?: Record<string, string>): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.13.0', error_code: code, message: 'A caller-safe sentence.',
    correlation_id: 'cid-summary', retryable: false, ...(details === undefined ? {} : { details }),
  };
  return new ApiError(status, envelope, 'cid-summary');
}

describe('the summary section on the comparison screen', () => {
  it('says that no summary was prepared and offers it to an expert for a sealed set', () => {
    const markup = screen(approved(), ['expert']);
    expect(markup).toContain('data-comparison-summary="none"');
    expect(visible(markup)).toContain('Сводка по подтверждённым парам');
    expect(visible(markup)).toContain('Сводка ещё не подготовлена.');
    expect(markup).toContain('data-summary-offer="offered"');
    expect(visible(markup)).toContain('Подготовить сводку');
  });

  it('offers nothing to an administrator who is not an expert, and nothing for a set that is not sealed', () => {
    expect(screen(approved(), ['admin'])).not.toContain('data-summary-offer');
    const unsealed = screen(approved({ evidence_state: 'text_changed', raw_evidence_seal_sha256: null,
      items: [{ ...ITEM, state: 'text_changed', diff: null }] }), ['expert']);
    expect(unsealed).toContain('data-summary-offer="blocked"');
    expect(visible(unsealed)).toContain(SUMMARY_NOT_SEALED_TEXT);
    expect(unsealed).not.toContain('data-summary-offer="offered"');
    // nothing approved: no section content to offer or explain
    const empty = screen(approved({ items: [], evidence_state: 'none', link_revision: null,
      raw_evidence_seal_sha256: null }), ['expert']);
    expect(empty).not.toContain('data-summary-offer');
  });

  it('shows a ready summary with the fixed label, the recorded note and what each statement is about', () => {
    const markup = screen(approved({ summary: STORED }), ['expert']);
    expect(markup).toContain('data-comparison-summary="ready"');
    expect(markup).toContain('data-summary-label');
    const text = visible(markup);
    expect(text).toContain(LABEL);
    expect(text).toContain(RECORDED_MODE_TEXT);
    expect(text).toContain('Размер изменён с 30 на 35.');
    expect(text).toContain('Относится к: лист 2 → лист 3, изменение 1.');
    expect(text).toContain('Подготовил запрос: Иванова Е. В.');
    expect(text).not.toContain(SUMMARY_NOT_CURRENT_TEXT);
    expect(text).toContain('Подготовить сводку заново');
  });

  it('says so when the summary no longer describes the approved set', () => {
    const markup = screen(approved({ summary: { ...STORED, is_current: false } }), ['expert']);
    expect(markup).toContain('data-summary-current="no"');
    expect(visible(markup)).toContain(SUMMARY_NOT_CURRENT_TEXT);
  });

  it('shows a rejected reply as an answer with its reason and no text, and leaves the differences alone', () => {
    const rejected: ComparisonSummary = {
      ...STORED, state: 'rejected', rejection_reason: 'unknown_hunk_reference', statements: [],
    };
    const markup = screen(approved({ summary: rejected }), ['expert']);
    expect(markup).toContain('data-comparison-summary="rejected"');
    expect(markup).toContain('data-summary-rejection="unknown_hunk_reference"');
    const text = visible(markup);
    expect(text).toContain(SUMMARY_REJECTION_TEXT.unknown_hunk_reference);
    expect(text).toContain('Различия подтверждённых пар не изменены.');
    expect(markup).not.toContain('data-summary-statement');
    // the raw differences are still there beside it
    expect(markup).toContain(`data-hunk-id="${LINK}:0"`);
  });
});

describe('the summary view states', () => {
  const view = (over: Partial<Parameters<typeof ComparisonSummaryView>[0]> = {}) =>
    renderToStaticMarkup(createElement(ComparisonSummaryView, {
      approved: approved(), mayDecide: true, confirming: true, pending: false, failure: null,
      onOpen: () => undefined, onConfirm: () => undefined, onCancel: () => undefined, ...over,
    }));

  it('says what is sent before it is sent, and what a repeat does', () => {
    const text = visible(view());
    expect(text).toContain('Будет сделан один запрос к модели по изменившимся строкам подтверждённых пар.');
    expect(text).toContain('Сводка не заменяет и не меняет различия; проверка человеком не проводится.');
    expect(text).toContain('Повторный запрос по тем же строкам вернёт уже сохранённую сводку.');
    expect(text).toContain('Подготовить');
    expect(text).toContain('Отмена');
  });

  it('disables both buttons while the request is in flight', () => {
    const markup = view({ pending: true });
    expect(visible(markup)).toContain('Готовим…');
    expect(markup.match(/disabled=""/g)).toHaveLength(2);
  });

  it('shows a refusal with its correlation id', () => {
    const failure = summaryFailure(apiError(409, 'conflict', { conflict_reason: 'summary_input_empty' }));
    const markup = view({ confirming: false, failure });
    expect(markup).toContain('data-summary-failure="summary_input_empty"');
    expect(visible(markup)).toContain(SUMMARY_CONFLICT_TEXT.summary_input_empty);
    expect(visible(markup)).toContain('cid-summary');
  });
});

describe('the entity reads citations, offers and refusals', () => {
  it('turns a cited identity back into sheets and a change number, and is honest about an absent one', () => {
    expect(citationText(approved(), STORED.statements[0]!)).toBe('лист 2 → лист 3, изменение 1');
    const gone = { text: 'x', hunk_ids: [`sln_01M2545JSD15ETSNNV904X9999:0`, `${LINK}:0`] };
    expect(citationText(approved(), gone)).toBe(
      'изменение, которого больше нет среди подтверждённых пар; лист 2 → лист 3, изменение 1',
    );
  });

  it('offers a summary only to an expert and only for a sealed, non-empty set', () => {
    expect(canOfferSummary(true, approved())).toBe(true);
    expect(canOfferSummary(false, approved())).toBe(false);
    expect(canOfferSummary(true, approved({ evidence_state: 'seal_changed' }))).toBe(false);
    expect(canOfferSummary(true, approved({ items: [] }))).toBe(false);
  });

  it('reads every refusal in Russian', () => {
    for (const reason of Object.keys(SUMMARY_CONFLICT_TEXT) as (keyof typeof SUMMARY_CONFLICT_TEXT)[]) {
      expect(summaryFailure(apiError(409, 'conflict', { conflict_reason: reason })))
        .toMatchObject({ kind: reason, detail: SUMMARY_CONFLICT_TEXT[reason] });
    }
    expect(summaryFailure(apiError(403, 'permission_denied')).detail).toBe(SUMMARY_NOT_PERMITTED_DETAIL);
    expect(summaryFailure(apiError(503, 'dependency_unavailable', { dependency: 'comparison_summary_model' }))
      .detail).toBe(SUMMARY_UNAVAILABLE_DETAIL);
    expect(summaryFailure(apiError(422, 'analysis_input_invalid', { reason: 'recording_missing' })).kind)
      .toBe('no_recording');
    expect(summaryFailure(apiError(503, 'dependency_unavailable', { dependency: 'storage' })).kind)
      .not.toBe('no_model');
  });

  it('keys an intent by the view, the revision and the seal shown', () => {
    const command = {
      projectUid: PROJECT_UID, documentUid: DOCUMENT_UID, sourceVersionUid: OLDER,
      targetVersionUid: NEWER, mode: 'version' as const, sourceRunId: null, targetRunId: null,
      linkRevision: 1, sealSha256: SHA,
    };
    expect(summarySignature(command)).toBe(summarySignature({ ...command }));
    expect(summarySignature(command)).not.toBe(summarySignature({ ...command, linkRevision: 2 }));
    expect(summarySignature(command)).not.toBe(summarySignature({ ...command, sealSha256: 'b'.repeat(64) }));
  });
});
