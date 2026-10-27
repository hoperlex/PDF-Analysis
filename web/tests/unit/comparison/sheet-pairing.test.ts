/**
 * An expert's approval of a sheet pairing on the comparison screen
 * (`COMPARE-PERSISTED-SUMMARY-01`, B1).
 *
 * Rendered through the screen harness with seeded caches -- the version, its set's versions, the
 * comparison answer with its `approved_pairs` and the account -- plus the controls' views and the
 * entity's pure helpers. Each test reads what a reviewer sees and the `data-` attributes an
 * instrument reads.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type {
  Account,
  ApprovedSheetPair,
  ApprovedSheetPairs,
  DocumentVersion,
  ErrorCode,
  ErrorEnvelope,
  SheetPairing,
  VersionComparison,
} from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import { COMPARISON_DIFF_LIMIT, VERSION_PAGE_LIMIT } from '@/entities/document-version';
import {
  EVIDENCE_STATE_TEXT,
  LINK_STATE_TEXT,
  PAIRING_CONFLICT_TEXT,
  PAIRING_NOT_PERMITTED_DETAIL,
  SheetPairingControlsView,
  approvalOf,
  approveSignature,
  canApproveSheetPairing,
  isApprovablePair,
  pairingFailure,
  withdrawSignature,
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

const SHEET_CHANGED: SheetPairing = {
  status: 'changed', source_page_number: 2, target_page_number: 2, pairing_basis: 'similar_text',
  similarity_permille: 900, shared_line_count: 8, suggestion_sha256: SHA, textless: false,
};
const SHEET_UNCHANGED: SheetPairing = {
  status: 'unchanged', source_page_number: 1, target_page_number: 1, pairing_basis: 'exact_text',
  similarity_permille: 1000, shared_line_count: null, suggestion_sha256: 'b'.repeat(64), textless: false,
};
const SHEET_REMOVED: SheetPairing = {
  status: 'removed', source_page_number: 3, target_page_number: null, pairing_basis: null,
  similarity_permille: null, shared_line_count: null, suggestion_sha256: null, textless: false,
};

const ITEM: ApprovedSheetPair = {
  sheet_link_id: LINK, source_page_number: 2, target_page_number: 2, state: 'verified',
  suggestion_sha256: SHA, approved_by_label: 'Иванова Е. В.', approved_at: '2026-10-27T08:00:00Z',
  link_revision: 1,
  diff: {
    source_line_count: 2, target_line_count: 2, added_line_count: 1, removed_line_count: 1,
    evidence_sha256: 'c'.repeat(64),
    hunks: [
      { tag: 'equal', source_start: 0, source_end: 1, target_start: 0, target_end: 1,
        source_lines: [], target_lines: [], hunk_id: null },
      { tag: 'replace', source_start: 1, source_end: 2, target_start: 1, target_end: 2,
        source_lines: ['размер 30\n'], target_lines: ['размер 35\n'], hunk_id: `${LINK}:0` },
    ],
  },
};

function approved(over: Partial<ApprovedSheetPairs> = {}): ApprovedSheetPairs {
  return {
    link_revision: 1, evidence_state: 'sealed', raw_evidence_seal_sha256: 'd'.repeat(64),
    items: [ITEM], ...over,
  };
}

function compared(pairs: ApprovedSheetPairs | null | undefined): VersionComparison {
  return {
    project_uid: PROJECT_UID, document_uid: DOCUMENT_UID,
    source_version_uid: OLDER, target_version_uid: NEWER,
    mode: 'version', outcome: 'compared', refusal: null,
    source: { version_uid: OLDER, version_ordinal: 1, page_count: 3, sha256: SHA, project_stage: 'P',
      section_code: 'AR', run_id: `run_${ULID}`, text_layer_sha256: SHA },
    target: { version_uid: NEWER, version_ordinal: 2, page_count: 2, sha256: SHA, project_stage: 'P',
      section_code: 'AR', run_id: 'run_01M2545JSD15ETSNNV904X991K', text_layer_sha256: SHA },
    comparison_sha256: SHA,
    sheets: [SHEET_UNCHANGED, SHEET_CHANGED, SHEET_REMOVED],
    sheet_diffs: { offset: 0, limit: COMPARISON_DIFF_LIMIT, total: 0, next_offset: null, items: [] },
    findings: null,
    ...(pairs === undefined ? {} : { approved_pairs: pairs }),
  };
}

function screen(pairs: ApprovedSheetPairs | null | undefined, roles: Account['roles'] | null): string {
  const client = newClient();
  client.setQueryData(queryKeys.versions.detail(OLDER), version({}));
  client.setQueryData(queryKeys.versions.list(DOCUMENT_UID, undefined, VERSION_PAGE_LIMIT), {
    items: [version({ version_uid: NEWER, version_ordinal: 2 }), version({})], page: { next_cursor: null },
  });
  client.setQueryData(
    queryKeys.versions.comparison(OLDER, NEWER, 'version', 0, COMPARISON_DIFF_LIMIT),
    compared(pairs),
  );
  if (roles !== null) client.setQueryData(queryKeys.account.me(), { roles } as Account);
  return renderScreen(client, createElement(StageComparisonPage, { projectUid: PROJECT_UID, versionUid: OLDER }));
}

function visible(markup: string): string {
  return markup.replace(/<[^>]*>/g, ' ').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ');
}

function apiError(status: number, code: ErrorCode, details?: Record<string, string>): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.9.0', error_code: code, message: 'A caller-safe sentence.',
    correlation_id: 'cid-pairing', retryable: false, ...(details === undefined ? {} : { details }),
  };
  return new ApiError(status, envelope, 'cid-pairing');
}

describe('the sheet table offers an approval only for a proposed pair, and only to an expert', () => {
  it('shows «Подтвердить пару» on every proposed pair for an expert and nowhere else', () => {
    const markup = screen(approved({ items: [], evidence_state: 'none', link_revision: null,
      raw_evidence_seal_sha256: null }), ['expert']);
    expect(visible(markup)).toContain('Подтверждение эксперта');
    expect(markup.match(/data-pairing-state="offered"/g)).toHaveLength(2);
    expect(visible(markup)).toContain('Подтвердить пару');
    // the removed sheet has no counterpart to approve
    expect(markup.match(/data-sheet-status="removed"[^]*?<\/tr>/)?.[0]).not.toContain('data-pairing-state');
  });

  it('draws no button for an administrator who is not an expert, and says who may', () => {
    const markup = screen(approved({ items: [], evidence_state: 'none', link_revision: null,
      raw_evidence_seal_sha256: null }), ['admin']);
    expect(markup).not.toContain('data-pairing-state="offered"');
    expect(markup).toContain('data-pairing-state="read-only"');
    expect(visible(markup)).toContain('Подтвердить пару может эксперт.');
  });

  it('draws no button while the account is not known', () => {
    expect(screen(approved(), null)).not.toContain('data-pairing-state="offered"');
  });

  it('shows the approval on its row, with who approved, and «Отозвать» only to an expert', () => {
    const expert = screen(approved(), ['expert']);
    expect(expert).toContain('data-pairing-state="approved"');
    expect(expert).toContain(`data-sheet-link="${LINK}"`);
    expect(visible(expert)).toContain('Пара подтверждена: Иванова Е. В.');
    expect(visible(expert)).toContain('Отозвать');
    const reader = screen(approved(), ['admin']);
    expect(reader).toContain('data-pairing-state="approved"');
    expect(visible(reader)).not.toContain('Отозвать');
  });

  it('works against a server that sends no approved_pairs at all', () => {
    const markup = screen(undefined, ['expert']);
    expect(markup).toContain('data-pairing-state="offered"');
    expect(markup).not.toContain('data-approved-pairs');
  });
});

describe('the approved pairs section serves only what the server sealed', () => {
  it('lists the approved pair with its differences and their hunk identities', () => {
    const markup = screen(approved(), ['expert']);
    expect(markup).toContain('data-approved-pairs="sealed"');
    expect(markup).toContain(`data-raw-evidence-seal="${'d'.repeat(64)}"`);
    expect(markup).toContain(`data-hunk-id="${LINK}:0"`);
    expect(markup).toContain(`data-evidence-sha256="${'c'.repeat(64)}"`);
    const text = visible(markup);
    expect(text).toContain('Подтверждённые пары листов');
    expect(text).toContain(EVIDENCE_STATE_TEXT.sealed);
    expect(text).toContain('Подтвердил: Иванова Е. В.');
    expect(text).toContain('Добавлено строк: 1 · удалено строк: 1.');
    expect(text).toContain('размер 30');
    expect(text).toContain('размер 35');
  });

  it.each([
    ['text_changed', 'text_changed'],
    ['seal_changed', 'verified'],
    ['too_large', 'verified'],
  ] as const)('says why it shows no difference when the evidence is %s', (state, linkState) => {
    const markup = screen(approved({
      evidence_state: state, raw_evidence_seal_sha256: null,
      items: [{ ...ITEM, state: linkState, diff: null }],
    }), ['expert']);
    expect(markup).toContain(`data-approved-pairs="${state}"`);
    expect(markup).toContain(`data-approved-pair-state="${linkState}"`);
    expect(visible(markup)).toContain(EVIDENCE_STATE_TEXT[state]);
    expect(visible(markup)).toContain(LINK_STATE_TEXT[linkState]);
    expect(markup).not.toContain('data-hunk-id');
  });

  it('says there is nothing approved when nothing is', () => {
    const markup = screen(approved({ items: [], evidence_state: 'none', link_revision: null,
      raw_evidence_seal_sha256: null }), ['expert']);
    expect(visible(markup)).toContain(EVIDENCE_STATE_TEXT.none);
  });

  it('still tells the reviewer that a pair is only a suggestion until an expert confirms it', () => {
    expect(visible(screen(approved(), ['expert']))).toContain('пока эксперт не подтвердил пару, они ничего не утверждают');
  });
});

describe('the entity matches approvals and reads refusals', () => {
  it('matches an approval by both page numbers', () => {
    expect(approvalOf(approved(), SHEET_CHANGED)).toBe(ITEM);
    expect(approvalOf(approved(), { ...SHEET_CHANGED, target_page_number: 3 })).toBeNull();
    expect(approvalOf(approved(), { ...SHEET_CHANGED, source_page_number: 1 })).toBeNull();
    expect(approvalOf(null, SHEET_CHANGED)).toBeNull();
    expect(approvalOf(undefined, SHEET_CHANGED)).toBeNull();
  });

  it('approves only a proposed pair of two present pages with a digest', () => {
    expect(isApprovablePair(SHEET_CHANGED)).toBe(true);
    expect(isApprovablePair(SHEET_UNCHANGED)).toBe(true);
    expect(isApprovablePair(SHEET_REMOVED)).toBe(false);
    expect(isApprovablePair({ ...SHEET_CHANGED, suggestion_sha256: null })).toBe(false);
    expect(isApprovablePair({ ...SHEET_CHANGED, status: 'added' })).toBe(false);
  });

  it('lets only an expert approve', () => {
    expect(canApproveSheetPairing(['expert'])).toBe(true);
    expect(canApproveSheetPairing(['admin', 'expert'])).toBe(true);
    expect(canApproveSheetPairing(['admin'])).toBe(false);
    expect(canApproveSheetPairing([])).toBe(false);
  });

  it('reads every conflict_reason, the role refusal and anything else in Russian', () => {
    for (const reason of Object.keys(PAIRING_CONFLICT_TEXT) as (keyof typeof PAIRING_CONFLICT_TEXT)[]) {
      expect(pairingFailure(apiError(409, 'conflict', { conflict_reason: reason }))).toMatchObject({
        kind: reason, detail: PAIRING_CONFLICT_TEXT[reason], correlationId: 'cid-pairing',
      });
    }
    expect(pairingFailure(apiError(403, 'permission_denied')).detail).toBe(PAIRING_NOT_PERMITTED_DETAIL);
    expect(pairingFailure(apiError(409, 'conflict', { conflict_reason: 'something_else' })).kind).toBe('conflict');
    expect(pairingFailure(apiError(404, 'not_found')).kind).toBe('not_found');
  });

  it('keys an intent by the pair, the proposal shown and the view', () => {
    const command = {
      projectUid: PROJECT_UID, documentUid: DOCUMENT_UID, sourceVersionUid: OLDER, targetVersionUid: NEWER,
      mode: 'version' as const, sourceRunId: null, targetRunId: null,
      sourcePageNumber: 2, targetPageNumber: 2, suggestionSha256: SHA,
    };
    expect(approveSignature(command)).toBe(approveSignature({ ...command }));
    expect(approveSignature(command)).not.toBe(approveSignature({ ...command, suggestionSha256: 'b'.repeat(64) }));
    expect(approveSignature(command)).not.toBe(approveSignature({ ...command, targetPageNumber: 3 }));
    expect(approveSignature(command)).not.toBe(approveSignature({ ...command, mode: 'stage' }));
    expect(withdrawSignature({ ...command, sheetLinkId: LINK })).not.toBe(approveSignature(command));
  });
});

describe('the controls show what would be stored and where a refusal went', () => {
  const view = (over: Partial<Parameters<typeof SheetPairingControlsView>[0]> = {}) =>
    renderToStaticMarkup(createElement(SheetPairingControlsView, {
      sheet: SHEET_CHANGED, approval: null, mayDecide: true, confirming: true, pending: false,
      failure: null, onOpen: () => undefined, onConfirm: () => undefined,
      onCancel: () => undefined, onWithdraw: () => undefined, ...over,
    }));

  it('names the two sheets and what is stored, and offers confirm and cancel', () => {
    const text = visible(view());
    expect(text).toContain('Лист 2 более ранней версии и лист 2 более поздней версии.');
    expect(text).toContain('какие листы вы сопоставили и какой текст они содержали');
    expect(text).toContain('Пару можно отозвать; запись о подтверждении при этом остаётся.');
    expect(text).toContain('Подтвердить');
    expect(text).toContain('Отмена');
  });

  it('disables both buttons while the confirmation is in flight', () => {
    const markup = view({ pending: true });
    expect(visible(markup)).toContain('Сохраняем…');
    expect(markup.match(/disabled=""/g)).toHaveLength(2);
  });

  it('shows a refusal beside the button, with its correlation id, and offers the button again', () => {
    const failure = pairingFailure(apiError(409, 'conflict', { conflict_reason: 'sheet_page_already_paired' }));
    const markup = view({ confirming: false, failure });
    expect(markup).toContain('data-pairing-failure="sheet_page_already_paired"');
    expect(visible(markup)).toContain(PAIRING_CONFLICT_TEXT.sheet_page_already_paired);
    expect(visible(markup)).toContain('cid-pairing');
    expect(visible(markup)).toContain('Подтвердить пару');
  });

  it('shows «Отозвать» on an approval while no withdrawal is in flight, and a busy label during one', () => {
    expect(visible(view({ confirming: false, approval: ITEM }))).toContain('Отозвать');
    expect(visible(view({ confirming: false, approval: ITEM, pending: true }))).toContain('Отзываем…');
  });
});
