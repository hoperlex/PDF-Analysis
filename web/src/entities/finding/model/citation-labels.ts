/**
 * Russian words for the state of one norm citation of a finding.
 *
 * `verified` and `rebound` are the closed `NormCitationState`. The contract defines what
 * each means (`NormCitation`): a rebound citation preserves the cited label and identifies
 * the one matching paragraph, so it is a confirmed citation, not a doubtful one. These
 * labels say that and no more; the choice of colour is the caller's and implies nothing
 * about the expert's decision.
 */
import type { NormCitationState } from '@/shared/api';

export const NORM_CITATION_STATE_LABELS: Readonly<Record<NormCitationState, string>> = {
  verified: 'подтверждена',
  rebound: 'перепривязана',
};

/** What the state means, for a tooltip. */
export const NORM_CITATION_STATE_MEANINGS: Readonly<Record<NormCitationState, string>> = {
  verified: 'Абзац нормы найден по указанному пункту и странице',
  rebound: 'Номер пункта сохранён, абзац найден заново: подходящий оказался один',
};

/** The label of a state, or a sentence saying the state is not one this screen knows. */
export function normCitationStateLabel(state: string): string {
  return (
    (NORM_CITATION_STATE_LABELS as Readonly<Record<string, string | undefined>>)[state] ??
    'состояние вне набора, известного этому приложению'
  );
}

/** The meaning of a state, or nothing for one this screen does not know. */
export function normCitationStateMeaning(state: string): string | undefined {
  return (NORM_CITATION_STATE_MEANINGS as Readonly<Record<string, string | undefined>>)[state];
}
