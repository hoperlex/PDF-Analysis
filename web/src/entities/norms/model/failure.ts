/**
 * What a failed norms read or designation says (`W55A-WEB-NORMS`).
 *
 * The seal registered no new error code (CD-19); the norms refusals are three catalog codes
 * told apart by one classifier each, and each gets its own sentence here because the
 * catalog's generic one cannot say what to do next:
 *
 *   `required_norm_unavailable` + `reference_kind`  no current snapshot (`norms_snapshot`),
 *                                                   a target without a complete index
 *                                                   (`norm_embedding_build`), a PDF without a
 *                                                   confirmed binding (`norm_source`);
 *   `validation_failed` + `constraint: norms_search_too_broad`  the search was cancelled
 *                                                   by its time limit;
 *   `conflict` + `conflict_reason: stale_current_snapshot`  another administrator
 *                                                   designated first.
 *
 * Everything else is the shared reading (`failureMessage`): never a thrown message, and a
 * value that is not a request failure is an unexpected error, not a transport one.
 */

import { ApiError } from '@/shared/api';
import type { FailureKind } from '@/shared/api/failure-message';
import { failureMessage } from '@/shared/api/failure-message';

export type NormFailureKind =
  | 'no_current_snapshot'
  | 'index_incomplete'
  | 'source_unbound'
  | 'search_too_broad'
  | 'stale_current_snapshot'
  | FailureKind;

export interface NormFailure {
  readonly kind: NormFailureKind;
  readonly detail: string;
  readonly correlationId: string | null;
  readonly retryable: boolean;
}

/** The refusal search answers before any snapshot is current, and the screen's own state. */
export const NO_CURRENT_SNAPSHOT_DETAIL =
  'Поиск по нормам заработает, когда администратор назначит текущий снимок нормативной базы. ' +
  'Пока он не назначен, искать не в чем: это отказ, а не пустой результат.';

const REFERENCE_KINDS: Readonly<Record<string, readonly [NormFailureKind, string]>> = {
  norms_snapshot: ['no_current_snapshot', NO_CURRENT_SNAPSHOT_DETAIL],
  norm_embedding_build: [
    'index_incomplete',
    'Этот снимок нельзя сделать текущим: поисковый индекс по нему построен не полностью.',
  ],
  norm_source: [
    'source_unbound',
    'PDF нормативного документа недоступен: у него нет подтверждённой привязки к исходному файлу.',
  ],
};

export function normFailure(error: unknown): NormFailure {
  if (error instanceof ApiError) {
    const base = { correlationId: error.correlationId, retryable: error.retryable };
    const details = error.details;
    if (error.errorCode === 'required_norm_unavailable') {
      const reference = details['reference_kind'];
      const known = typeof reference === 'string' ? REFERENCE_KINDS[reference] : undefined;
      if (known !== undefined) return { ...base, kind: known[0], detail: known[1] };
    }
    if (error.errorCode === 'validation_failed' && details['constraint'] === 'norms_search_too_broad') {
      return {
        ...base,
        kind: 'search_too_broad',
        detail:
          'Запрос слишком широкий: поиск не уложился в отведённое время и остановлен. ' +
          'Уточните его — добавьте обозначение документа, номер пункта или ещё одно слово.',
      };
    }
    if (error.errorCode === 'conflict' && details['conflict_reason'] === 'stale_current_snapshot') {
      return {
        ...base,
        kind: 'stale_current_snapshot',
        detail:
          'Текущий снимок уже сменил другой администратор. Ничего не изменено; список снимков ' +
          'обновлён — проверьте его и назначьте снова, если это всё ещё нужно.',
      };
    }
  }
  const failure = failureMessage(error, {
    validation_failed:
      'Запрос не принят: поисковая строка должна содержать от одного до двухсот символов, ' +
      'а продолжение списка — относиться к этому же запросу.',
    not_found: 'Такого нормативного документа или снимка нет.',
  });
  return {
    kind: failure.kind,
    detail: failure.detail,
    correlationId: failure.correlationId,
    retryable: failure.retryable,
  };
}
