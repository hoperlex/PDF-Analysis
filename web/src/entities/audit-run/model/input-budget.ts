/**
 * The two figures of an `analysis_input_budget_exceeded` refusal, as a sentence
 * (`W55B-WEB-BLOCKS`, `R-118`).
 *
 * `startRun` and `reauditRun` refuse a version whose text is larger than the analysis input
 * budget before any run exists (422, not retryable). The catalog sentence says what that
 * means (`shared/api/catalog-message.ts`, whose comment promises the figures are "rendered
 * beside this sentence by the classifier that consumes it"); the envelope's `details` carry
 * the two numbers that make it actionable: `character_count`, the version's text, and
 * `budget_characters`, what this deployment admits. This module is the ONE place they become
 * words, and both classifiers that can meet the refusal read it: `classifyRunFailure` here
 * (the start-run control) and `executionFailure` in `entities/execution` (the queue's
 * re-audit command).
 *
 * **Exactly as returned, or not at all.** A figure is printed only when it is a non-negative
 * safe integer; when either is missing or is anything else the sentence is absent and the
 * catalog sentence stands alone. A screen that printed `NaN`, a rounded value or the one
 * figure without the other would be inventing what the server did not say. The digits are
 * grouped by threes with a narrow no-break space (U+202F), the Russian typographic grouping,
 * so a seven-digit count stays readable and never breaks across a line.
 *
 * The labels come BEFORE the numbers («символов …: N») so no Russian plural has to agree
 * with a number the server chose.
 */

/** U+202F NARROW NO-BREAK SPACE: the separator between groups of three digits. */
export const DIGIT_GROUP_SEPARATOR = ' ';

export interface InputBudgetFigures {
  readonly characterCount: number;
  readonly budgetCharacters: number;
}

function isCount(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
}

/** Both figures when both are non-negative safe integers; otherwise `null`. */
export function inputBudgetFigures(
  details: Readonly<Record<string, unknown>>,
): InputBudgetFigures | null {
  const characterCount = details.character_count;
  const budgetCharacters = details.budget_characters;
  if (!isCount(characterCount) || !isCount(budgetCharacters)) return null;
  return { characterCount, budgetCharacters };
}

/** `1234567` → `1 234 567`, grouped with {@link DIGIT_GROUP_SEPARATOR}. */
export function groupDigits(value: number): string {
  return String(value).replace(/\B(?=(\d{3})+(?!\d))/g, DIGIT_GROUP_SEPARATOR);
}

/** The figures as one sentence, or `null` when the refusal did not carry both. */
export function inputBudgetSentence(details: Readonly<Record<string, unknown>>): string | null {
  const figures = inputBudgetFigures(details);
  if (figures === null) return null;
  return (
    `Символов в тексте версии: ${groupDigits(figures.characterCount)}; ` +
    `допустимо не более: ${groupDigits(figures.budgetCharacters)}.`
  );
}
