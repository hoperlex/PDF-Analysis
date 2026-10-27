/**
 * How «Настройки анализа» words an analysis profile (`W59-ANALYSIS-SETTINGS-01`).
 *
 * The status is the contract's closed `AnalysisProfileStatus`; each value gets one Russian
 * label, and a value this build does not know is reported as such rather than guessed. A
 * draft is said to need an expert's review in so many words, because a draft profile is
 * executable and a reviewer reading its findings must know it was never reviewed. A `reviewed`
 * profile is NOT said to be expert-verified: under `R-146ag` (accepted risk `A-7`) the status means
 * a lane answered the record's open questions and no person reviewed it.
 *
 * Whether the label of a reviewed profile says that no person reviewed it is the switch
 * `SHOW_REVIEW_INDICATION` (`R-146ba`, accepted risk `A-10`). With the switch off the label is the
 * contract's own word «проверен», which claims nothing about who; with it on the label is the
 * sentence it was before the beta. It is read when the label is asked for, not when this module loads.
 */

import type { AnalysisProfileStatus } from '@/shared/api';
import { ANALYSIS_PROFILE_STATUS_VALUES } from '@/shared/api';
import { SHOW_REVIEW_INDICATION } from '@/shared/config';

export const ANALYSIS_PROFILE_STATUS_LABELS: Readonly<Record<AnalysisProfileStatus, string>> = {
  draft: 'черновик, требует экспертной проверки',
  get reviewed(): string {
    return SHOW_REVIEW_INDICATION ? 'рабочая версия, проверка человеком не проводилась' : 'проверен';
  },
};

/** What a section with no registered profile shows instead of one. */
export const NO_PROFILE_LABEL = 'профиль не создан';

/** Why it matters, beside {@link NO_PROFILE_LABEL}. */
export const NO_PROFILE_CONSEQUENCE = 'Прогон версии этого раздела будет отклонён.';

/**
 * What АР shows instead (`PROD-11-AR-V1-V2-REMOVAL-01`, `ADR-0024`): АР has no text profile, and it
 * is not a missing one. Its analysis is the group of six AR v3 checks, started from its own control.
 */
export const AR_NO_TEXT_PROFILE_LABEL = 'текстовый профиль не используется';

/** Why, beside {@link AR_NO_TEXT_PROFILE_LABEL}. */
export const AR_NO_TEXT_PROFILE_CONSEQUENCE =
  'Версия АР анализируется группой из шести проверок АР v3; обычный прогон по ней будет отклонён.';

/** The note on a version screen where АР has no ordinary start (no pack, or none yet read). */
export const AR_START_NOTE =
  'Версия АР анализируется группой из шести проверок АР v3, а не обычным прогоном. Группа ' +
  'становится доступной, когда на сервере установлен проверенный экспертом набор; состояние ' +
  'набора — в разделе «Настройки анализа».';

/** The label of a status this build does not know. Never a guess at its meaning. */
export const UNKNOWN_STATUS_LABEL = 'состояние вне набора, известного этой версии приложения';

export function isKnownAnalysisProfileStatus(value: string): value is AnalysisProfileStatus {
  return (ANALYSIS_PROFILE_STATUS_VALUES as readonly string[]).includes(value);
}

export function analysisProfileStatusLabel(status: string): string {
  return isKnownAnalysisProfileStatus(status) ? ANALYSIS_PROFILE_STATUS_LABELS[status] : UNKNOWN_STATUS_LABEL;
}

/**
 * The first twelve characters of a hex digest, for a row; the full value is in the details.
 * A digest shorter than that is shown whole.
 */
export function shortDigest(digest: string): string {
  return digest.length > 12 ? `${digest.slice(0, 12)}…` : digest;
}
