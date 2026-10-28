/**
 * The deterministic verdict of a transition, in a reviewer's words.
 *
 * The contract carries the verdict as a list of codes beside the counts of the transition's `summary`
 * (`ComparisonVerdictCode`, CMP-SEAL-C1 decision 4), and the sentence is the client's. The sentences are
 * the original's `series.summary()` verdict strings (`backend/app/services/version_comparison/series.py:54-62`,
 * inventory §4.2), in the same order and with the same figures, joined with «; » as the table does
 * (`version-comparison.js:144`). A model never writes this: it is arithmetic over the sheet statuses.
 *
 * One addition, from plan §4.0 rule 6: a transition that holds a pair resting on an accepted AI link says
 * so, because a verdict an AI link shaped must not read as a purely deterministic one.
 */

import type { ComparisonTransitionSummary, ComparisonVerdictCode } from '@/shared/api';

export const NO_VERDICT_YET = 'вывод ещё не сформирован';

function part(code: ComparisonVerdictCode, summary: ComparisonTransitionSummary, all: readonly ComparisonVerdictCode[]): string {
  switch (code) {
    case 'incomplete':
      return 'переход досчитан не полностью';
    case 'content_same':
      return 'основное содержание совпадает' + (all.includes('zones_only') ? ', изменены только служебные зоны' : '');
    case 'zones_only':
      return all.includes('content_same') ? '' : 'изменены только служебные зоны';
    case 'different':
      return (
        `есть отличия на ${summary.different} л.` +
        (summary.style_only > 0 ? ` (из них только оформление линий — ${summary.style_only})` : '')
      );
    case 'composition_changed':
      return `изменён состав (+${summary.added} / −${summary.removed} л.)`;
    case 'needs_review':
      return `нужна проверка: ${summary.needs_review}`;
    case 'calculation_failed':
      return `ошибка расчёта: ${summary.failed}`;
  }
}

/** The AI note, which is not a verdict code: it comes from the count of pairs that depend on an AI link. */
export function aiDependenceNote(summary: ComparisonTransitionSummary): string {
  const count = summary.ai_dependent ?? 0;
  return count > 0 ? `${count} пар опираются на связь, предложенную ИИ` : '';
}

export interface VerdictPart {
  /** The code the sentence part says, or `ai` for the note about pairs that rest on an AI link. */
  readonly code: ComparisonVerdictCode | 'ai';
  readonly text: string;
}

/** The parts of the sentence, each with the code it says: the screen marks each in a `data-` attribute. */
export function verdictParts(
  codes: readonly ComparisonVerdictCode[] | undefined,
  summary: ComparisonTransitionSummary,
): VerdictPart[] {
  const parts: VerdictPart[] = (codes ?? [])
    .map((code) => ({ code, text: part(code, summary, codes ?? []) }))
    .filter((entry) => entry.text !== '');
  const note = aiDependenceNote(summary);
  if (note !== '') parts.push({ code: 'ai', text: note });
  return parts;
}

/** The whole sentence of a transition; empty codes (a transition that has not run) say so. */
export function verdictSentence(
  codes: readonly ComparisonVerdictCode[] | undefined,
  summary: ComparisonTransitionSummary,
): string {
  const parts = verdictParts(codes, summary);
  return parts.length === 0 ? NO_VERDICT_YET : parts.map((entry) => entry.text).join('; ');
}
