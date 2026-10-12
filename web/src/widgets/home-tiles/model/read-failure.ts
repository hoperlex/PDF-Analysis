/**
 * Failure states for the two reads the home page owns: `getDashboardSummary` and
 * `listRegistrations` (`W50-HOME-01`). `listProjects` is classified by the project entity's
 * own `classifyProjectListFailure`, which already words that read.
 *
 * One classifier and two tables of whole sentences rather than one sentence with the read's
 * name substituted into it: a noun pasted into a Russian sentence has to agree with the words
 * around it, and `gender-agreement.guard.test.ts` (`D-95`) is about exactly that defect.
 *
 * **No raw message reaches the screen.** The detail is the shared reading's
 * (`shared/api/failure-message.ts`): the catalog's sentence for the code, one of the two
 * authorization sentences, or the fixed sentence for a transport failure or an unexpected
 * error. A thrown value this client does not recognise is never printed, whatever
 * its `message` says.
 */

import type { ErrorCode } from '@/shared/api';
import { ApiError } from '@/shared/api';
import { failureMessage } from '@/shared/api/failure-message';

export type HomeReadFailureKind =
  | 'request_invalid'
  | 'dependency_unavailable'
  | 'not_authenticated'
  | 'not_permitted'
  | 'server_error'
  | 'unrecognized'
  | 'transport'
  | 'unknown';

export interface HomeReadFailure {
  readonly kind: HomeReadFailureKind;
  readonly title: string;
  readonly detail: string;
  readonly correlationId: string | null;
  readonly retryable: boolean;
  readonly errorCode: ErrorCode | null;
}

/** The titles of one read, each a whole sentence. */
interface ReadTitles {
  readonly rejected: string;
  readonly unavailable: string;
  readonly notAuthenticated: string;
  readonly notPermitted: string;
  readonly failed: string;
  readonly undelivered: string;
}

const SUMMARY_TITLES: ReadTitles = {
  rejected: 'Запрос сводки отклонён.',
  unavailable: 'Зависимость, нужная сводке, недоступна.',
  notAuthenticated: 'Чтение сводки не авторизовано.',
  notPermitted: 'Вам не разрешено читать сводку.',
  failed: 'Сводку прочитать не удалось.',
  undelivered: 'Запрос сводки не дошёл до сервера.',
};

const REGISTRATIONS_TITLES: ReadTitles = {
  rejected: 'Запрос заявок на регистрацию отклонён.',
  unavailable: 'Зависимость, нужная заявкам на регистрацию, недоступна.',
  notAuthenticated: 'Чтение заявок на регистрацию не авторизовано.',
  notPermitted: 'Вам не разрешено читать заявки на регистрацию.',
  failed: 'Заявки на регистрацию прочитать не удалось.',
  undelivered: 'Запрос заявок на регистрацию не дошёл до сервера.',
};

const UNRECOGNIZED_TITLE = 'Сервер сообщил об ошибке, которую этот клиент не распознаёт.';

/**
 * The detail, the correlation id and whether to offer a retry are the shared reading's
 * (`failureMessage`, `C-23`) — the same sentence the identity screens print for the same
 * failure. This classifier adds only what is the home page's own: the tile's title and the
 * kind on its `data-` attribute.
 */
function classify(error: unknown, titles: ReadTitles): HomeReadFailure {
  const shared = failureMessage(error);
  const base = {
    correlationId: shared.correlationId,
    retryable: shared.retryable,
    errorCode: shared.errorCode,
    detail: shared.detail,
  };

  if (error instanceof ApiError) {
    switch (error.errorCode) {
      case 'validation_failed':
        return { ...base, kind: 'request_invalid', title: titles.rejected };
      case 'dependency_unavailable':
        return { ...base, kind: 'dependency_unavailable', title: titles.unavailable };
      case 'authentication_required':
        return { ...base, kind: 'not_authenticated', title: titles.notAuthenticated };
      case 'permission_denied':
        return { ...base, kind: 'not_permitted', title: titles.notPermitted };
      default:
        return { ...base, kind: 'server_error', title: titles.failed };
    }
  }
  if (shared.kind === 'unrecognized') return { ...base, kind: 'unrecognized', title: UNRECOGNIZED_TITLE };
  if (shared.kind === 'transport') return { ...base, kind: 'transport', title: titles.undelivered };
  return { ...base, kind: 'unknown', title: titles.failed };
}

/** Classify anything thrown by the home page's `getDashboardSummary`. */
export function classifySummaryFailure(error: unknown): HomeReadFailure {
  return classify(error, SUMMARY_TITLES);
}

/**
 * Classify anything thrown by the home page's `listRegistrations`.
 *
 * A `permission_denied` here is a session whose roles changed after it signed in: the
 * administrator's role was taken away while the session still lists it. It is the error
 * state, never a count kept from an earlier answer.
 */
export function classifyRegistrationsFailure(error: unknown): HomeReadFailure {
  return classify(error, REGISTRATIONS_TITLES);
}
