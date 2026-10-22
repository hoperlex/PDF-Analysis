/**
 * The two refusals a run start or a re-audit meets before any run exists because of the
 * version's section (`W59-SECTION-UI-01`, over `W59-SECTION-SEAL-01`).
 *
 * Since the seal a run's analysis profile is routed from the version's expert-confirmed
 * classification — never from a file name, a suggestion or the document's legacy section,
 * and never by falling back to the АР профиль. Each refusal has its own catalog code since
 * `BETA-CONTRACT-SEAL-01` (`D-179`; a draft reported both as `required_norm_unavailable`,
 * told apart by `details.reference_kind`):
 *
 *   `version_classification_required`  the version has no confirmed stage and section;
 *   `section_profile_unavailable`     the confirmed section has no registered text profile.
 *
 * The catalog's own sentence is true and tells a reader nothing to do, so each gets its own. Neither offers another section, a
 * default profile or a retry: the same request is refused again until the reader confirms a
 * section, or until a profile is registered. Worded once here for the start-run control and
 * the queue's re-audit alike, the way the input-budget figures are (`./input-budget.ts`).
 */

export type RoutingRefusalKind = 'version_unclassified' | 'section_profile_unavailable';

export interface RoutingRefusal {
  readonly kind: RoutingRefusalKind;
  readonly title: string;
  readonly detail: string;
}

export const VERSION_UNCLASSIFIED_REFUSAL: RoutingRefusal = {
  kind: 'version_unclassified',
  title: 'У версии не подтверждены стадия и раздел.',
  detail:
    'Анализ выбирается по разделу, который подтвердил эксперт, и без такого подтверждения не ' +
    'запускается. Подтвердите стадию и раздел на экране этой версии, в панели «Стадия и ' +
    'раздел», затем запустите прогон снова.',
};

export const SECTION_PROFILE_UNAVAILABLE_REFUSAL: RoutingRefusal = {
  kind: 'section_profile_unavailable',
  title: 'Для подтверждённого раздела нет профиля анализа.',
  detail:
    'Профиль анализа этого раздела ещё не зарегистрирован, поэтому версию пока нечем ' +
    'проверить. Анализ по другому профилю вместо него не запускается; прогон станет ' +
    'возможен, когда профиль раздела появится.',
};

/** The refusal a catalog code names, or `null` for any other code. */
export function routingRefusal(errorCode: string): RoutingRefusal | null {
  if (errorCode === 'version_classification_required') return VERSION_UNCLASSIFIED_REFUSAL;
  if (errorCode === 'section_profile_unavailable') return SECTION_PROFILE_UNAVAILABLE_REFUSAL;
  return null;
}
