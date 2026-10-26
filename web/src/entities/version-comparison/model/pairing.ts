/**
 * An expert's approval of a sheet pairing, in a reviewer's words (`COMPARE-PERSISTED-SUMMARY-01`).
 *
 * The server decides everything: which pairs the comparison proposes, whether the pair is still
 * proposed when the expert confirms, what is stored and what the stored pairs' differences are.
 * This module only finds the approval for a proposal row, says who may press the buttons, says
 * what the state of the approved pairs' evidence means, and reads a refusal in Russian. A
 * proposal is never an approval: until an expert confirms it, a pair stays what the system
 * suggested.
 */

import type {
  ApprovedSheetPair,
  ApprovedSheetPairs,
  Role,
  SheetPairing,
} from '@/shared/api';
import { ApiError } from '@/shared/api';
import type { FailureKind } from '@/shared/api/failure-message';
import { failureMessage } from '@/shared/api/failure-message';

/** Whether to draw «Подтвердить пару» and «Отозвать». Only `expert`; `admin` alone is refused (`R-60`). */
export function canApproveSheetPairing(roles: readonly Role[]): boolean {
  return roles.includes('expert');
}

export type EvidenceState = ApprovedSheetPairs['evidence_state'];

/** What the state of the approved pairs' raw differences means for the reviewer. */
export const EVIDENCE_STATE_TEXT: Readonly<Record<EvidenceState, string>> = {
  none: 'Подтверждённых пар пока нет.',
  sealed:
    'Различия пересчитаны по тексту листов и сверены с контрольной суммой, сохранённой при подтверждении. ' +
    'Они получены без участия ИИ.',
  text_changed:
    'Текст подтверждённого листа теперь не тот, который видел эксперт. Различия не показаны. ' +
    'Отзовите такую пару и подтвердите её заново.',
  seal_changed:
    'Текст листов прежний, но контрольная сумма различий не совпала с сохранённой при подтверждении. ' +
    'Различия не показаны, чтобы не выдать неподтверждённое за подтверждённое.',
  too_large:
    'Различия подтверждённых пар слишком велики для одного ответа. Они не сокращены и не показаны.',
};

export const LINK_STATE_TEXT: Readonly<Record<ApprovedSheetPair['state'], string>> = {
  verified: 'Текст листов тот, который видел эксперт.',
  text_changed: 'Текст листа изменился после подтверждения.',
};

/** Whether the proposal row can be approved at all: a proposed pair of two present pages. */
export function isApprovablePair(sheet: SheetPairing): boolean {
  return (
    (sheet.status === 'unchanged' || sheet.status === 'changed') &&
    sheet.source_page_number !== null &&
    sheet.target_page_number !== null &&
    sheet.suggestion_sha256 !== null
  );
}

/**
 * The active approval of exactly this pair of pages, or `null`. A page number is a coordinate in
 * an immutable version, so two pages name one pair only when both numbers agree.
 */
export function approvalOf(
  approved: ApprovedSheetPairs | null | undefined,
  sheet: SheetPairing,
): ApprovedSheetPair | null {
  if (approved === null || approved === undefined) return null;
  return (
    approved.items.find(
      (item) =>
        item.source_page_number === sheet.source_page_number &&
        item.target_page_number === sheet.target_page_number,
    ) ?? null
  );
}

/** The `conflict_reason` values the two pairing operations refuse with. */
export type PairingConflictReason =
  | 'sheet_pair_not_proposed'
  | 'sheet_page_already_paired'
  | 'sheet_pair_limit_reached'
  | 'sheet_pair_too_large'
  | 'approved_text_changed'
  | 'sheet_link_not_active'
  | 'comparison_not_available';

const CONFLICT_REASONS: readonly PairingConflictReason[] = [
  'sheet_pair_not_proposed',
  'sheet_page_already_paired',
  'sheet_pair_limit_reached',
  'sheet_pair_too_large',
  'approved_text_changed',
  'sheet_link_not_active',
  'comparison_not_available',
];

/** What each refusal means for the reviewer. Nothing was stored in any of them. */
export const PAIRING_CONFLICT_TEXT: Readonly<Record<PairingConflictReason, string>> = {
  sheet_pair_not_proposed:
    'Сравнение, пересчитанное в момент подтверждения, больше не предлагает эту пару листов. ' +
    'Пара не подтверждена; сравнение обновлено.',
  sheet_page_already_paired:
    'Один из этих листов уже входит в подтверждённую пару. Сначала отзовите ту пару.',
  sheet_pair_limit_reached:
    'В сравнении уже подтверждено 32 пары — больше одного набора различий не вмещает. ' +
    'Отзовите ненужную пару.',
  sheet_pair_too_large:
    'Различия подтверждённых пар вместе с этой парой слишком велики. Пара не подтверждена.',
  approved_text_changed:
    'Текст листа ранее подтверждённой пары изменился. Отзовите такую пару и подтвердите заново, ' +
    'прежде чем подтверждать другие.',
  sheet_link_not_active: 'Эта пара уже отозвана. Ничего не изменено; сравнение обновлено.',
  comparison_not_available:
    'Сравнение, которое вы смотрели, сейчас построить нельзя, поэтому пара не отозвана. ' +
    'Обновите страницу и повторите.',
};

/** `403` on a pairing operation: the role, not the credential, is what is missing. */
export const PAIRING_NOT_PERMITTED_DETAIL =
  'Подтверждать и отзывать пары листов может только пользователь с ролью «Эксперт». У вашей ' +
  'учётной записи этой роли нет, поэтому ничего не изменено.';

export type PairingFailureKind = PairingConflictReason | 'not_permitted' | 'not_found' | FailureKind;

export interface PairingFailure {
  readonly kind: PairingFailureKind;
  /** The Russian sentence a screen renders. Never a thrown value's own message. */
  readonly detail: string;
  readonly correlationId: string | null;
  readonly retryable: boolean;
}

function conflictReasonOf(error: ApiError): PairingConflictReason | null {
  const reason = error.details['conflict_reason'];
  return CONFLICT_REASONS.find((known) => known === reason) ?? null;
}

/** Classify anything a pairing operation threw, and say it in Russian. */
export function pairingFailure(error: unknown): PairingFailure {
  if (error instanceof ApiError) {
    const base = { correlationId: error.correlationId, retryable: error.retryable };
    const reason = error.errorCode === 'conflict' ? conflictReasonOf(error) : null;
    if (reason !== null) return { ...base, kind: reason, detail: PAIRING_CONFLICT_TEXT[reason] };
    if (error.errorCode === 'permission_denied') {
      return { ...base, kind: 'not_permitted', detail: PAIRING_NOT_PERMITTED_DETAIL };
    }
    if (error.errorCode === 'not_found') {
      return {
        ...base,
        kind: 'not_found',
        detail:
          'Такой версии, листа или пары в этом документе и проекте нет. Ничего не изменено; ' +
          'откройте версию заново из списка документов проекта.',
      };
    }
  }
  const failure = failureMessage(error, {
    validation_failed: 'Сервер не принял подтверждение пары. Ничего не изменено.',
    idempotency_key_reuse:
      'Это действие уже было отправлено с другими данными. Ничего не изменено; обновите сравнение.',
  });
  return {
    kind: failure.kind,
    detail: failure.detail,
    correlationId: failure.correlationId,
    retryable: failure.retryable,
  };
}
