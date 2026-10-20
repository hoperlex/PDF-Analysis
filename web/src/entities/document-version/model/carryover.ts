/**
 * The expert-confirmed carryover of a decision to the next version, in a reviewer's words
 * (`W59-DECISION-CARRYOVER-01`).
 *
 * The server decides everything: which pairs could be carried (`findings.carryover_candidates`
 * of the comparison), whether the pair is still proposed when the expert confirms, and what
 * is appended. This module only finds the candidate for a proposal row, says who may press
 * the button, and reads a refusal in Russian. Nothing is carried without that press, and a
 * «Вероятно, устранено» source is never a candidate: it has no finding in the newer version.
 */

import type {
  CarryoverCandidate,
  FindingComparison,
  FindingMatchProposal,
  Role,
} from '@/shared/api';
import { ApiError } from '@/shared/api';
import type { FailureKind } from '@/shared/api/failure-message';
import { failureMessage } from '@/shared/api/failure-message';

/** The four `conflict_reason` values `carryOverDecision` refuses with. */
export type CarryoverConflictReason =
  | 'carryover_pair_not_proposed'
  | 'carryover_source_decision_not_current'
  | 'carryover_target_already_decided'
  | 'carryover_severity_not_carryable';

const CONFLICT_REASONS: readonly CarryoverConflictReason[] = [
  'carryover_pair_not_proposed',
  'carryover_source_decision_not_current',
  'carryover_target_already_decided',
  'carryover_severity_not_carryable',
];

/** What each refusal means for the reviewer. Nothing was carried in any of them. */
export const CARRYOVER_CONFLICT_TEXT: Readonly<Record<CarryoverConflictReason, string>> = {
  carryover_pair_not_proposed:
    'Сравнение, пересчитанное в момент подтверждения, больше не предлагает эту пару замечаний ' +
    'как «Без изменений». Решение не перенесено; сравнение обновлено.',
  carryover_source_decision_not_current:
    'Решение по замечанию более ранней версии изменилось после того, как вы его увидели. ' +
    'Решение не перенесено; посмотрите текущее решение и подтвердите перенос заново.',
  carryover_target_already_decided:
    'По замечанию более поздней версии уже есть решение или комментарий эксперта. Перенос ' +
    'не выполнен, чтобы не перекрыть его.',
  carryover_severity_not_carryable:
    'Исходное решение содержит степень значимости, которую замечание более поздней версии ' +
    'принять не может. Решение не перенесено; примите его вручную.',
};

/** `403` on the carryover: the role, not the credential, is what is missing. */
export const CARRYOVER_NOT_PERMITTED_DETAIL =
  'Перенести решение может только пользователь с ролью «Эксперт». У вашей учётной записи ' +
  'этой роли нет, поэтому ничего не изменено.';

/** Whether to draw «Перенести решение». Only `expert`; `admin` alone is refused (`R-60`). */
export function canCarryOverDecision(roles: readonly Role[]): boolean {
  return roles.includes('expert');
}

/**
 * The carryover candidate the server listed for this proposal row, or `null`. Matched by
 * both finding identities, so a row is never offered another row's decision.
 */
export function carryoverCandidateOf(
  findings: FindingComparison,
  proposal: FindingMatchProposal,
): CarryoverCandidate | null {
  if (proposal.kind !== 'unchanged' || proposal.source_finding === null || proposal.target_finding === null) {
    return null;
  }
  const source = proposal.source_finding.finding_uid;
  const target = proposal.target_finding.finding_uid;
  return (
    findings.carryover_candidates.find(
      (candidate) => candidate.source_finding_uid === source && candidate.target_finding_uid === target,
    ) ?? null
  );
}

export type CarryoverFailureKind = CarryoverConflictReason | 'not_permitted' | 'not_found' | FailureKind;

export interface CarryoverFailure {
  readonly kind: CarryoverFailureKind;
  /** The Russian sentence a screen renders. Never a thrown value's own message. */
  readonly detail: string;
  readonly correlationId: string | null;
  readonly retryable: boolean;
}

function conflictReasonOf(error: ApiError): CarryoverConflictReason | null {
  const reason = error.details['conflict_reason'];
  return CONFLICT_REASONS.find((known) => known === reason) ?? null;
}

/** Classify anything `carryOverDecision` threw, and say it in Russian. */
export function carryoverFailure(error: unknown): CarryoverFailure {
  if (error instanceof ApiError) {
    const base = { correlationId: error.correlationId, retryable: error.retryable };
    const reason = error.errorCode === 'conflict' ? conflictReasonOf(error) : null;
    if (reason !== null) return { ...base, kind: reason, detail: CARRYOVER_CONFLICT_TEXT[reason] };
    if (error.errorCode === 'permission_denied') {
      return { ...base, kind: 'not_permitted', detail: CARRYOVER_NOT_PERMITTED_DETAIL };
    }
    if (error.errorCode === 'not_found') {
      return {
        ...base,
        kind: 'not_found',
        detail:
          'Такой версии в этом документе и проекте нет. Ничего не изменено; откройте версию ' +
          'заново из списка документов проекта.',
      };
    }
  }
  const failure = failureMessage(error, {
    validation_failed: 'Сервер не принял подтверждение переноса. Ничего не изменено.',
    idempotency_key_reuse:
      'Этот перенос уже был отправлен с другими данными. Ничего не изменено; обновите сравнение.',
  });
  return {
    kind: failure.kind,
    detail: failure.detail,
    correlationId: failure.correlationId,
    retryable: failure.retryable,
  };
}
