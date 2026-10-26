/**
 * «Перенести решение» on the comparison screen (`W59-DECISION-CARRYOVER-01`).
 *
 * Rendered through the screen harness with seeded caches — the version, its set's versions,
 * the comparison answer with its `carryover_candidates`, and the account — plus the
 * confirmation view and the entity's pure helpers. Each test reads what a reviewer sees and
 * the `data-` attributes an instrument reads.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type {
  Account,
  CarryoverCandidate,
  DocumentVersion,
  ErrorCode,
  ErrorEnvelope,
  FindingComparison,
  FindingMatchProposal,
  VersionComparison,
} from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import {
  CARRYOVER_CONFLICT_TEXT,
  CARRYOVER_NOT_PERMITTED_DETAIL,
  COMPARISON_DIFF_LIMIT,
  VERSION_PAGE_LIMIT,
  canCarryOverDecision,
  carryoverCandidateOf,
  carryoverFailure,
} from '@/entities/document-version';
import { CarryOverDecisionView } from '@/features/carry-over-decision';
import { StageComparisonPage } from '@/_pages/stage-comparison';
import { ComparisonResult } from '@/widgets/version-comparison';

import { newClient, renderScreen } from '../screens/harness';

const ULID = '01M2545JSD15ETSNNV904X991J';
const PROJECT_UID = `prj_${ULID}`;
const DOCUMENT_UID = `doc_${ULID}`;
const OLDER = `ver_${ULID}`;
const NEWER = 'ver_01M2545JSD15ETSNNV904X991K';
const SOURCE_FINDING = 'fnd_01M2545JSD15ETSNNV904X9911';
const TARGET_FINDING = 'fnd_01M2545JSD15ETSNNV904X9912';
const OTHER_TARGET = 'fnd_01M2545JSD15ETSNNV904X9913';
const SHA = 'a'.repeat(64);

function version(over: Partial<DocumentVersion>): DocumentVersion {
  return {
    version_uid: OLDER, document_uid: DOCUMENT_UID, project_uid: PROJECT_UID, version_ordinal: 1,
    media_type: 'application/pdf', byte_size: 1, sha256: SHA, page_count: 1,
    published_at: '2026-10-20T08:00:00Z', input_manifest: [],
    classification: {
      version_uid: over.version_uid ?? OLDER, project_stage: 'P', section_code: 'AR',
      confirmed_by_user_uid: `usr_${ULID}`, confirmed_at: '2026-10-20T08:00:00Z', revision: 1,
    },
    ...over,
  };
}

const OLDER_VERSION = version({});
const NEWER_VERSION = version({ version_uid: NEWER, version_ordinal: 2 });

const CANDIDATE: CarryoverCandidate = {
  proposal_sha256: SHA,
  source_finding_uid: SOURCE_FINDING,
  target_finding_uid: TARGET_FINDING,
  source_decision: {
    decision_id: `dec_${ULID}`, verdict: 'accepted', severity: 'critical',
    comment: 'Проём действительно не показан.', author_label: 'Иванова Е. В.',
    recorded_at: '2026-10-20T08:00:00Z',
  },
};

const ref = (uid: string, text: string) => ({
  finding_uid: uid, category: 'layout' as const, finding_text: text, page_numbers: [1],
});

const UNCHANGED: FindingMatchProposal = {
  kind: 'unchanged', basis: 'exact_issue_and_quotes', proposal_sha256: SHA,
  source_finding: ref(SOURCE_FINDING, 'Нет дверного проёма'),
  target_finding: ref(TARGET_FINDING, 'Нет дверного проёма'),
};
const PROBABLY_FIXED: FindingMatchProposal = {
  kind: 'probably_fixed', basis: 'quotes_absent_from_paired_sheets', proposal_sha256: null,
  source_finding: ref('fnd_01M2545JSD15ETSNNV904X9914', 'Толщина стены не совпадает'),
  target_finding: null,
};

function findings(candidates: readonly CarryoverCandidate[]): FindingComparison {
  return {
    status: 'compared', unavailable_reason: null, source_finding_count: 2, target_finding_count: 1,
    proposals: [UNCHANGED, PROBABLY_FIXED], carryover_candidates: [...candidates],
  };
}

function compared(candidates: readonly CarryoverCandidate[]): VersionComparison {
  return {
    project_uid: PROJECT_UID, document_uid: DOCUMENT_UID,
    source_version_uid: OLDER, target_version_uid: NEWER,
    mode: 'version', outcome: 'compared', refusal: null,
    source: { version_uid: OLDER, version_ordinal: 1, page_count: 1, sha256: SHA, project_stage: 'P',
      section_code: 'AR', run_id: `run_${ULID}`, text_layer_sha256: SHA },
    target: { version_uid: NEWER, version_ordinal: 2, page_count: 1, sha256: SHA, project_stage: 'P',
      section_code: 'AR', run_id: 'run_01M2545JSD15ETSNNV904X991K', text_layer_sha256: SHA },
    comparison_sha256: SHA,
    sheets: [{ status: 'unchanged', source_page_number: 1, target_page_number: 1,
      pairing_basis: 'exact_text', similarity_permille: 1000, shared_line_count: null,
      suggestion_sha256: SHA, textless: false }],
    sheet_diffs: { offset: 0, limit: COMPARISON_DIFF_LIMIT, total: 0, next_offset: null, items: [] },
    findings: findings(candidates),
  };
}

function screen(candidates: readonly CarryoverCandidate[], roles: Account['roles'] | null): string {
  const client = newClient();
  client.setQueryData(queryKeys.versions.detail(OLDER), OLDER_VERSION);
  client.setQueryData(queryKeys.versions.list(DOCUMENT_UID, undefined, VERSION_PAGE_LIMIT), {
    items: [NEWER_VERSION, OLDER_VERSION], page: { next_cursor: null },
  });
  client.setQueryData(
    queryKeys.versions.comparison(OLDER, NEWER, 'version', 0, COMPARISON_DIFF_LIMIT),
    compared(candidates),
  );
  if (roles !== null) client.setQueryData(queryKeys.account.me(), { roles } as Account);
  return renderScreen(client, createElement(StageComparisonPage, { projectUid: PROJECT_UID, versionUid: OLDER }));
}

function visible(markup: string): string {
  return markup.replace(/<[^>]*>/g, ' ').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ');
}

function apiError(status: number, code: ErrorCode, details?: Record<string, string>): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.6.0', error_code: code, message: 'A caller-safe sentence.',
    correlation_id: 'cid-carryover', retryable: false, ...(details === undefined ? {} : { details }),
  };
  return new ApiError(status, envelope, 'cid-carryover');
}

describe('the comparison offers a carryover only where the server listed one', () => {
  it('shows «Перенести решение» on the candidate row for an expert', () => {
    const markup = screen([CANDIDATE], ['expert']);
    expect(markup).toContain('data-carryover-state="offered"');
    expect(visible(markup)).toContain('Перенести решение');
    expect(visible(markup)).toContain('В более ранней версии: принято.');
    expect(visible(markup)).toContain('Решение эксперта');
    // Exactly one row is offered: the «Вероятно, устранено» row has no finding to carry to.
    expect(markup.match(/data-carryover-state="offered"/g)).toHaveLength(1);
  });

  it('draws no button for an administrator who is not an expert, and says who may', () => {
    const markup = screen([CANDIDATE], ['admin']);
    expect(markup).not.toContain('data-carryover-state="offered"');
    expect(markup).toContain('data-carryover-state="read-only"');
    expect(visible(markup)).toContain('Решение более ранней версии может перенести эксперт.');
  });

  it('draws no button while the account is not known', () => {
    expect(screen([CANDIDATE], null)).not.toContain('data-carryover-state="offered"');
  });

  it('offers nothing when the server lists no candidate', () => {
    const markup = screen([], ['expert']);
    expect(markup).not.toContain('data-carryover-state');
  });
});

describe('the entity matches candidates and reads refusals', () => {
  it('matches a candidate by both finding identities and never for a one-sided row', () => {
    expect(carryoverCandidateOf(findings([CANDIDATE]), UNCHANGED)).toBe(CANDIDATE);
    expect(carryoverCandidateOf(findings([{ ...CANDIDATE, target_finding_uid: OTHER_TARGET }]), UNCHANGED))
      .toBeNull();
    expect(carryoverCandidateOf(findings([CANDIDATE]), PROBABLY_FIXED)).toBeNull();
  });

  it('lets only an expert carry', () => {
    expect(canCarryOverDecision(['expert'])).toBe(true);
    expect(canCarryOverDecision(['admin', 'expert'])).toBe(true);
    expect(canCarryOverDecision(['admin'])).toBe(false);
    expect(canCarryOverDecision([])).toBe(false);
  });

  it('reads every conflict_reason, the role refusal and anything else in Russian', () => {
    for (const reason of Object.keys(CARRYOVER_CONFLICT_TEXT) as (keyof typeof CARRYOVER_CONFLICT_TEXT)[]) {
      const failure = carryoverFailure(apiError(409, 'conflict', { conflict_reason: reason }));
      expect(failure).toMatchObject({ kind: reason, detail: CARRYOVER_CONFLICT_TEXT[reason], correlationId: 'cid-carryover' });
    }
    expect(carryoverFailure(apiError(403, 'permission_denied')).detail).toBe(CARRYOVER_NOT_PERMITTED_DETAIL);
    expect(carryoverFailure(apiError(409, 'conflict', { conflict_reason: 'something_else' })).kind).toBe('conflict');
    expect(carryoverFailure(apiError(404, 'not_found')).kind).toBe('not_found');
  });
});

describe('the confirmation shows what would be carried and where', () => {
  const view = (over: Partial<Parameters<typeof CarryOverDecisionView>[0]> = {}) =>
    renderToStaticMarkup(createElement(CarryOverDecisionView, {
      candidate: CANDIDATE,
      target: ref(TARGET_FINDING, 'Нет дверного проёма'),
      confirming: true, pending: false, result: null, failure: null,
      onOpen: () => undefined, onConfirm: () => undefined, onCancel: () => undefined,
      ...over,
    }));

  it('names the older decision with its author, time, severity and comment, and the newer finding', () => {
    const text = visible(view());
    expect(text).toContain('Решение по замечанию более ранней версии: принято');
    expect(text).toContain('значимость: Критическое');
    expect(text).toContain('Иванова Е. В.');
    expect(text).toContain('«Проём действительно не показан.»');
    expect(text).toContain('Получит решение замечание более поздней версии');
    expect(text).toContain('Нет дверного проёма (лист 1)');
    expect(text).toContain('Подтвердить перенос');
    expect(text).toContain('Отмена');
    expect(text).toContain('Решение по более ранней версии не изменится.');
  });

  it('disables both buttons while the confirmation is in flight', () => {
    const markup = view({ pending: true });
    expect(visible(markup)).toContain('Переносим…');
    expect(markup.match(/disabled=""/g)).toHaveLength(2);
  });

  it('reports a carried and an already carried decision differently', () => {
    const result = {
      event: { decision_id: `dec_${ULID.slice(0, -1)}9`, finding_uid: TARGET_FINDING,
        finding_observation_id: `fobs_${ULID}`, event_type: 'accept' as const, verdict: 'accepted' as const,
        comment: 'Решение перенесено.', author_label: 'Иванова Е. В.', recorded_at: '2026-10-20T09:00:00Z' },
      current_verdict: 'accepted' as const, replayed: false, source_finding_uid: SOURCE_FINDING,
      source_decision_id: CANDIDATE.source_decision.decision_id, source_version_uid: OLDER,
      source_version_ordinal: 1, target_version_uid: NEWER, mode: 'version' as const,
    };
    expect(view({ confirming: false, result })).toContain('data-carryover-state="carried"');
    expect(visible(view({ confirming: false, result }))).toContain('Решение перенесено: замечание более поздней версии — принято.');
    const again = view({ confirming: false, result: { ...result, replayed: true } });
    expect(again).toContain('data-carryover-state="replayed"');
    expect(visible(again)).toContain('уже было перенесено ранее');
  });

  it('shows a refusal beside the button, with its correlation id, and offers the button again', () => {
    const failure = carryoverFailure(apiError(409, 'conflict', { conflict_reason: 'carryover_target_already_decided' }));
    const markup = view({ confirming: false, failure });
    expect(markup).toContain('data-carryover-failure="carryover_target_already_decided"');
    expect(visible(markup)).toContain(CARRYOVER_CONFLICT_TEXT.carryover_target_already_decided);
    expect(visible(markup)).toContain('cid-carryover');
    expect(visible(markup)).toContain('Перенести решение');
  });
});

describe('a carried decision stays on the screen after the comparison is read again (BETA-LIVE-JOURNEY-01)', () => {
  // After a carry the comparison is asked again, and the server -- the newer finding now has a
  // decision -- no longer lists the row as a candidate. The live journey carried a decision and
  // found a «—» where the answer had been. The widget keeps the answer by the finding that
  // received the decision and shows it in the row's place.
  const answer = {
    event: { decision_id: `dec_${ULID.slice(0, -1)}9`, finding_uid: TARGET_FINDING,
      finding_observation_id: `fobs_${ULID}`, event_type: 'accept' as const, verdict: 'accepted' as const,
      comment: 'Решение перенесено.', author_label: 'Иванова Е. В.', recorded_at: '2026-10-20T09:00:00Z' },
    current_verdict: 'accepted' as const, replayed: false, source_finding_uid: SOURCE_FINDING,
    source_decision_id: CANDIDATE.source_decision.decision_id, source_version_uid: OLDER,
    source_version_ordinal: 1, target_version_uid: NEWER, mode: 'version' as const,
  };

  function after(carried: Record<string, typeof answer>): string {
    // The comparison as it is read again: the same row, and no candidate.
    return renderScreen(
      newClient(),
      createElement(ComparisonResult, {
        comparison: compared([]),
        onPage: () => undefined,
        carry: { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID },
        carried,
      }),
    );
  }

  it('shows the answer in the row the candidate left', () => {
    const markup = after({ [TARGET_FINDING]: answer });
    expect(markup).toContain('data-carryover-state="carried"');
    expect(visible(markup)).toContain('Решение перенесено: замечание более поздней версии — принято.');
    expect(markup.match(/data-carryover-state="carried"/g)).toHaveLength(1);
  });

  it('shows nothing where nothing was carried', () => {
    expect(after({})).not.toContain('data-carryover-state');
    expect(after({ [OTHER_TARGET]: answer })).not.toContain('data-carryover-state');
  });
});
