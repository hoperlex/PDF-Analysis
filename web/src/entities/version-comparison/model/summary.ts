/**
 * The summary of the approved pairs, in a reviewer's words (`COMPARE-PERSISTED-SUMMARY-01`, B2).
 *
 * The summary is a model's text beside the raw differences, never inside them. Every statement
 * names the changed spans it is about; this module turns those identities back into «лист X → лист
 * Y, изменение N» so a reviewer can check each statement against the lines. The label is the
 * server's and is shown verbatim: nobody has reviewed the text.
 */

import type { ApprovedSheetPairs, ComparisonSummary, SummaryStatement } from '@/shared/api';
import { ApiError } from '@/shared/api';
import type { FailureKind } from '@/shared/api/failure-message';
import { failureMessage } from '@/shared/api/failure-message';

export type SummaryRejection = NonNullable<ComparisonSummary['rejection_reason']>;

/** Why a reply was refused by the check. The raw differences are never touched by it. */
export const SUMMARY_REJECTION_TEXT: Readonly<Record<SummaryRejection, string>> = {
  reply_not_json: 'Ответ модели не удалось прочитать: это не структура, которую просили.',
  reply_shape_invalid: 'Ответ модели не соответствует требуемому виду: лишние поля, пустые утверждения или утверждения без ссылок на изменения.',
  unknown_hunk_reference: 'Ответ модели ссылается на изменение, которого нет в подтверждённых парах. Такой ответ не показывается целиком.',
};

export const RECORDED_MODE_TEXT =
  'Это воспроизведённый ответ из записи, а не вызов модели: стоимость не списана.';

export const SUMMARY_NOT_CURRENT_TEXT =
  'Сводка относится к прежнему набору подтверждённых пар: после неё пары или их текст менялись. ' +
  'Подготовьте её заново.';

export const SUMMARY_NOT_SEALED_TEXT =
  'Сводка готовится только по подтверждённым парам, различия которых пересчитаны и сверены. Пока ' +
  'таких нет, сводку подготовить нельзя.';

/** The pages and the number of the change a cited identity names, or the identity's honest absence. */
export function citedChange(
  approved: ApprovedSheetPairs,
  hunkId: string,
): { readonly sourcePage: number; readonly targetPage: number; readonly ordinal: number } | null {
  const separator = hunkId.lastIndexOf(':');
  if (separator < 0) return null;
  const link = hunkId.slice(0, separator);
  const ordinal = Number(hunkId.slice(separator + 1));
  const item = approved.items.find((candidate) => candidate.sheet_link_id === link);
  if (item === undefined || !Number.isInteger(ordinal)) return null;
  return { sourcePage: item.source_page_number, targetPage: item.target_page_number, ordinal: ordinal + 1 };
}

/** «лист 2 → лист 2, изменение 1; …» for one statement. */
export function citationText(approved: ApprovedSheetPairs, statement: SummaryStatement): string {
  return statement.hunk_ids
    .map((id) => {
      const change = citedChange(approved, id);
      return change === null
        ? 'изменение, которого больше нет среди подтверждённых пар'
        : `лист ${change.sourcePage} → лист ${change.targetPage}, изменение ${change.ordinal}`;
    })
    .join('; ');
}

/** Whether to offer «Подготовить сводку»: an expert, and a set whose evidence the server sealed. */
export function canOfferSummary(mayDecide: boolean, approved: ApprovedSheetPairs): boolean {
  return mayDecide && approved.evidence_state === 'sealed' && approved.items.length > 0;
}

export type SummaryConflictReason =
  | 'summary_evidence_not_sealed'
  | 'summary_input_empty'
  | 'summary_input_too_large'
  | 'comparison_not_available';

const CONFLICT_REASONS: readonly SummaryConflictReason[] = [
  'summary_evidence_not_sealed',
  'summary_input_empty',
  'summary_input_too_large',
  'comparison_not_available',
];

export const SUMMARY_CONFLICT_TEXT: Readonly<Record<SummaryConflictReason, string>> = {
  summary_evidence_not_sealed: SUMMARY_NOT_SEALED_TEXT,
  summary_input_empty:
    'В подтверждённых парах нет изменившихся строк, поэтому описывать нечего. Модель не вызывалась.',
  summary_input_too_large:
    'Изменившихся строк в подтверждённых парах больше, чем помещается в один запрос. Их не сокращают: ' +
    'отзовите часть пар. Модель не вызывалась.',
  comparison_not_available:
    'Сравнение, которое вы смотрели, сейчас построить нельзя. Обновите страницу и повторите.',
};

export const SUMMARY_NOT_PERMITTED_DETAIL =
  'Подготовить сводку может только пользователь с ролью «Эксперт». У вашей учётной записи этой ' +
  'роли нет, поэтому ничего не изменено и модель не вызывалась.';

export const SUMMARY_UNAVAILABLE_DETAIL =
  'В этом запуске системы нет модели для сводок (она подключена только в режиме воспроизведения ' +
  'записей). Ничего не изменено и ничего не вызвано.';

export type SummaryFailureKind = SummaryConflictReason | 'not_permitted' | 'no_model' | 'no_recording' | FailureKind;

export interface SummaryFailure {
  readonly kind: SummaryFailureKind;
  readonly detail: string;
  readonly correlationId: string | null;
  readonly retryable: boolean;
}

/** Classify anything `generateComparisonSummary` threw, and say it in Russian. */
export function summaryFailure(error: unknown): SummaryFailure {
  if (error instanceof ApiError) {
    const base = { correlationId: error.correlationId, retryable: error.retryable };
    const reason = error.errorCode === 'conflict'
      ? (CONFLICT_REASONS.find((known) => known === error.details['conflict_reason']) ?? null)
      : null;
    if (reason !== null) return { ...base, kind: reason, detail: SUMMARY_CONFLICT_TEXT[reason] };
    if (error.errorCode === 'permission_denied') {
      return { ...base, kind: 'not_permitted', detail: SUMMARY_NOT_PERMITTED_DETAIL };
    }
    if (error.errorCode === 'dependency_unavailable' && error.details['dependency'] === 'comparison_summary_model') {
      return { ...base, kind: 'no_model', detail: SUMMARY_UNAVAILABLE_DETAIL };
    }
    if (error.errorCode === 'analysis_input_invalid') {
      return {
        ...base,
        kind: 'no_recording',
        detail:
          'Для этих подтверждённых пар нет записанного ответа, а вызывать модель в этом режиме нельзя. ' +
          'Ничего не сохранено.',
      };
    }
  }
  const failure = failureMessage(error, {
    validation_failed: 'Сервер не принял запрос на сводку. Ничего не изменено.',
    idempotency_key_reuse:
      'Этот запрос уже был отправлен с другими данными. Ничего не изменено; обновите сравнение.',
  });
  return {
    kind: failure.kind,
    detail: failure.detail,
    correlationId: failure.correlationId,
    retryable: failure.retryable,
  };
}
