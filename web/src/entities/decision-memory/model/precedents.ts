/**
 * What the «Прецеденты» of a finding say, as plain functions (`PREC-WEB`, plan-v5 sections 2.3, 2.5 and 7): the caption of a label,
 * who is in the queue «Рекомендовано снять», the line above the list while the vectors are not there yet, the words of a hint.
 *
 * No React and no query: the row, the queue, the card and their tests read the same words. A label is a REFERENCE built from what
 * other experts decided on like findings, never a verdict: the expert decides, and nothing here says otherwise.
 */

import type { PrecedentCase, PrecedentFindingLabel, PrecedentHint, VectorWindow } from '@/shared/api';

/** `none` and `few` show nothing in the row: one to four decisions are not a precedent. */
export function precedentCaption(label: PrecedentFindingLabel): string | null {
  const { votes } = label;
  switch (label.label) {
    case 'none':
    case 'few':
      return null;
    case 'often_rejected':
    case 'cancel_suggested':
      // A finding the AI critic did not review is shown neutrally: a rejection label with no review behind it is only a count (plan-v5 2.3).
      if (!label.critic_reviewed) return `Прецедентов: ${votes.total} (критик не разбирал)`;
      return label.label === 'cancel_suggested'
        ? `Рекомендуется снять · ${votes.rejected} из ${votes.total}`
        : `Обычно отклоняют · ${votes.rejected} из ${votes.total}`;
    case 'likely_accepted':
      return `Обычно принимают · ${votes.accepted} из ${votes.total}`;
    case 'mixed':
      return `Решения расходятся · ${votes.accepted} ✓ / ${votes.rejected} ✕`;
  }
}

/** The tooltip of the mark: where the numbers come from, and that it is a reference and not a decision. */
export function precedentTitle(label: PrecedentFindingLabel): string {
  const { votes } = label;
  return (
    `Решения экспертов по похожим находкам: всего ${votes.total} (отклонено ${votes.rejected}, принято ${votes.accepted}), ` +
    `независимых ${votes.independent}, проектов ${votes.projects}. Это справка, а не решение: решаете вы.`
  );
}

/**
 * Is the finding in the queue «Рекомендовано снять»? Only a `cancel_suggested` label the AI critic reviewed: a finding it did not review
 * is never in the queue, whatever label the server sent (plan-v5 2.3, the owner's «не разбирал — не предлагать»).
 */
export function isCancelSuggested(label: PrecedentFindingLabel | undefined): label is PrecedentFindingLabel {
  return label !== undefined && label.label === 'cancel_suggested' && label.critic_reviewed;
}

const TAIL = 'и появятся утром; после переезда в Яндекс — сразу после прогона';

/**
 * The one line above the list while the run has no precedents yet (plan-v5 section 7). The time and the zone are the setting
 * `vector_window`'s, as `getVectorControl` carries them; while they are not known the line says only that it is night, and invents no hour.
 */
export function precedentsUnavailableLine(window: VectorWindow | null): string {
  return window === null
    ? `Прецеденты считаются ночью ${TAIL}`
    : `Прецеденты считаются ночью (${window.start}–${window.end}, ${window.tz}) ${TAIL}`;
}

/** At most two hints on a card (plan-v5 2.5). */
export const MAX_HINTS = 2;

const VERDICT_PAST: Readonly<Record<PrecedentCase['verdict'], string>> = { accepted: 'принята', rejected: 'отклонена' };

/** One hint as a line. `text` is always an expert's words (the comment of a rejecting decision), never a model's. */
export function precedentHintLine(hint: PrecedentHint, cases: readonly PrecedentCase[]): string {
  switch (hint.code) {
    case 'p1':
      return hint.text === undefined || hint.text === '' ? 'Причина отказов не записана' : `Причина отказов: «${hint.text}»`;
    case 'p4':
      return 'Совет критика расходится с решениями экспертов';
    case 'p5': {
      const verdict = cases.find((one) => one.case_id === hint.case_id)?.verdict;
      return verdict === undefined
        ? 'Такая находка уже была в прошлой версии документа'
        : `Такая находка уже была в прошлой версии документа: ${VERDICT_PAST[verdict]}`;
    }
  }
}

export function shownHints(hints: readonly PrecedentHint[]): readonly PrecedentHint[] {
  return hints.slice(0, MAX_HINTS);
}

export const CASE_VERDICT_MARK: Readonly<Record<PrecedentCase['verdict'], string>> = { accepted: '✓ принято', rejected: '✕ отклонено' };

/** The similarity of a case as a whole percent. */
export function similarityPercent(similarity: number): string {
  return `${Math.round(similarity * 100)} %`;
}
