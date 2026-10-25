/**
 * Every way starting the six AR v3 checks can fail, as one explicit sentence each.
 *
 * `startArV3BetaGroup` refuses before any Run exists, from the server's own state, in a small
 * closed set of ways (`src/auditmanager/runs/v3_group.py`). Each gets a sentence of its own,
 * because each is fixed by a different person: the administrator installs the pack, the
 * reader confirms the section, the text is shortened, the norms stand is prepared. A single
 * «не удалось запустить» would send all of them to the same place.
 *
 * What none of them offers: another provider mode, another pack, another section or profile,
 * or the legacy single-run start «instead». `startRun` is not a fallback for the six checks —
 * it is a different run with different provenance — and the screen that presents these
 * refusals never presents it as one.
 *
 * A code outside this set — a catalog code the start does not raise, a code this client's
 * contract does not know, a request that produced no envelope — is `generic`, worded by the
 * shared `failureMessage`, with the correlation id. It is never silence and never one of the
 * sentences above.
 */

import {
  ApiError,
  AUTHENTICATION_REQUIRED_DETAIL,
  PERMISSION_DENIED_DETAIL,
  failureMessage,
} from '@/shared/api';
import { inputBudgetSentence } from '@/entities/audit-run';

export type ArV3GroupStartFailureKind =
  | 'pack_unavailable'
  | 'provider_unavailable'
  | 'norm_unavailable'
  | 'version_unclassified'
  | 'section_not_ar'
  | 'input_invalid'
  | 'input_budget_exceeded'
  | 'key_reused'
  | 'in_progress'
  | 'stale_intent'
  | 'not_found'
  | 'not_authenticated'
  | 'not_permitted'
  | 'malformed_answer'
  | 'generic';

export interface ArV3GroupStartFailure {
  readonly kind: ArV3GroupStartFailureKind;
  /** `unsupported` offers no retry (the same request is refused again); `error` may. */
  readonly presentation: 'unsupported' | 'error';
  readonly title: string;
  readonly detail: string;
  readonly correlationId: string | null;
  readonly retryable: boolean;
}

/** The dependency name `v3_group.py` raises when the reviewed pack cannot be used. */
const PACK_DEPENDENCY = 'ar_v3_trusted_pack';

const NOTHING_CREATED = 'Ни одна из шести проверок не создана.';

/** The kinds whose cure is the version's «Стадия и раздел» panel, and so carry its link. */
export const CLASSIFICATION_LINK_KINDS: ReadonlySet<ArV3GroupStartFailureKind> = new Set([
  'version_unclassified',
  'section_not_ar',
]);

function fromApiError(error: ApiError): ArV3GroupStartFailure | null {
  const base = { correlationId: error.correlationId, retryable: error.retryable };

  switch (error.errorCode) {
    case 'dependency_unavailable':
      if (error.details.dependency === PACK_DEPENDENCY) {
        return {
          ...base,
          kind: 'pack_unavailable',
          presentation: 'unsupported',
          retryable: false,
          title: 'Пакет проверенных норм АР v3 недоступен.',
          detail:
            'Пакет не установлен на сервере или установлен с ошибкой, поэтому шесть проверок не ' +
            `запускаются. ${NOTHING_CREATED} Повтор не поможет, пока администратор не установит пакет.`,
        };
      }
      return {
        ...base,
        kind: 'provider_unavailable',
        presentation: 'error',
        title: 'Зависимость, нужная шести проверкам, недоступна.',
        detail:
          `${NOTHING_CREATED} Повтор использует тот же ключ идемпотентности, и шесть проверок не ` +
          'запускаются вместо этого в другом режиме провайдера.',
      };
    case 'required_norm_unavailable':
      return {
        ...base,
        kind: 'norm_unavailable',
        presentation: 'unsupported',
        title: 'Нормативный источник для шести проверок недоступен.',
        detail:
          'Снимок норм или набор источников, который нужен шести проверкам, не подготовлен на ' +
          `сервере. ${NOTHING_CREATED} Тот же запрос будет отклонён снова, пока источник не ` +
          'подготовлен; проверки по другим нормам вместо него не запускаются.',
      };
    case 'version_classification_required':
      return {
        ...base,
        kind: 'version_unclassified',
        presentation: 'unsupported',
        title: 'У версии не подтверждены стадия и раздел.',
        detail:
          'Шесть проверок АР v3 выбираются по разделу, который подтвердил эксперт, и без такого ' +
          'подтверждения не запускаются. Подтвердите стадию и раздел на экране этой версии, в ' +
          'панели «Стадия и раздел», затем запустите шесть проверок снова.',
      };
    case 'section_profile_unavailable':
      return {
        ...base,
        kind: 'section_not_ar',
        presentation: 'unsupported',
        title: 'Шесть проверок АР v3 выполняются только для раздела АР.',
        detail:
          'Подтверждённый раздел этой версии другой, поэтому шесть проверок не запущены. ' +
          'Проверки по профилю другого раздела вместо них не запускаются.',
      };
    case 'analysis_input_invalid':
      return {
        ...base,
        kind: 'input_invalid',
        presentation: 'unsupported',
        title: 'Входные данные версии не подходят для шести проверок.',
        detail:
          'У версии нет исходного документа или другого входа, который нужен проверкам. ' +
          `${NOTHING_CREATED} Тот же запрос будет отклонён снова.`,
      };
    case 'analysis_input_budget_exceeded': {
      const figures = inputBudgetSentence(error.details);
      return {
        ...base,
        kind: 'input_budget_exceeded',
        presentation: 'unsupported',
        title: 'Текст версии больше бюджета входа анализа.',
        detail:
          `${NOTHING_CREATED}${figures === null ? '' : ` ${figures}`} ` +
          'Повтор с тем же текстом получит тот же отказ.',
      };
    }
    case 'idempotency_key_reuse':
      return {
        ...base,
        kind: 'key_reused',
        presentation: 'error',
        title: 'Этот ключ запуска уже использован для другого запроса.',
        detail: `${NOTHING_CREATED} Повторной отправки не было.`,
      };
    case 'idempotency_key_in_progress':
      return {
        ...base,
        kind: 'in_progress',
        presentation: 'error',
        title: 'Этот запрос на шесть проверок ещё выполняется.',
        detail:
          'Повтор спрашивает о том же запросе под тем же ключом. Новый ключ означал бы вторую ' +
          'группу из шести проверок.',
      };
    case 'idempotency_key_stale':
      return {
        ...base,
        kind: 'stale_intent',
        presentation: 'error',
        title: 'Записанный результат этого запроса на шесть проверок больше недоступен.',
        detail: 'Он не домысливается: откройте разбор группы по её идентификатору, если он известен.',
      };
    case 'not_found':
      return {
        ...base,
        kind: 'not_found',
        presentation: 'error',
        title: 'Такой версии не существует.',
        detail: `${NOTHING_CREATED} Обновите страницу версии и попробуйте снова.`,
      };
    case 'authentication_required':
      return {
        ...base,
        kind: 'not_authenticated',
        presentation: 'error',
        title: 'Запуск шести проверок не авторизован.',
        detail: AUTHENTICATION_REQUIRED_DETAIL,
      };
    case 'permission_denied':
      return {
        ...base,
        kind: 'not_permitted',
        presentation: 'error',
        title: 'Вам не разрешено запускать шесть проверок.',
        detail: PERMISSION_DENIED_DETAIL,
      };
    default:
      return null;
  }
}

/**
 * The server accepted the start (202) and the answer does not carry a group address the
 * settings screen can open. The group may exist, so this is not a refusal: a retry under the
 * same key replays the start and returns the same group.
 */
export const MALFORMED_GROUP_ANSWER: ArV3GroupStartFailure = {
  kind: 'malformed_answer',
  presentation: 'error',
  title: 'Ответ сервера не соответствует контракту.',
  detail:
    'Сервер принял запрос, но не вернул корректный идентификатор группы, поэтому разбор не ' +
    'открыт. Повтор с тем же ключом вернёт ту же группу, а не создаст вторую.',
  correlationId: null,
  retryable: true,
};

/** Classify anything thrown by `startArV3BetaGroup`. */
export function classifyArV3GroupStartFailure(error: unknown): ArV3GroupStartFailure {
  if (error instanceof ApiError) {
    const known = fromApiError(error);
    if (known !== null) return known;
  }
  const generic = failureMessage(error);
  return {
    kind: 'generic',
    presentation: 'error',
    title: 'Запрос на шесть проверок не выполнен.',
    detail: generic.detail,
    correlationId: generic.correlationId,
    retryable: generic.retryable,
  };
}
