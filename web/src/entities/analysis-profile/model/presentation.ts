/**
 * How «Настройки анализа» words an analysis profile (`W59-ANALYSIS-SETTINGS-01`).
 *
 * The status is the contract's closed `AnalysisProfileStatus`; each value gets one Russian
 * label, and a value this build does not know is reported as such rather than guessed. A
 * draft is said to need an expert's review in so many words, because a draft profile is
 * executable and a reviewer reading its findings must know it was never reviewed.
 */

import type { AnalysisProfileStatus } from '@/shared/api';
import { ANALYSIS_PROFILE_STATUS_VALUES } from '@/shared/api';

export const ANALYSIS_PROFILE_STATUS_LABELS: Readonly<Record<AnalysisProfileStatus, string>> = {
  builtin: 'встроенный',
  draft: 'черновик, требует экспертной проверки',
  reviewed: 'проверен экспертом',
};

/** What a section with no registered profile shows instead of one. */
export const NO_PROFILE_LABEL = 'профиль не создан';

/** Why it matters, beside {@link NO_PROFILE_LABEL}. */
export const NO_PROFILE_CONSEQUENCE = 'Прогон версии этого раздела будет отклонён.';

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
