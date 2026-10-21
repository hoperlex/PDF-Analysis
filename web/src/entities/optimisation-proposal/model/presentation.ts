/**
 * How an optimisation pass and its proposals are said on screen, in Russian
 * (`W60-OPT-PROPOSALS-01`).
 *
 * Every table here is keyed by the contract's own enum, so a member the contract adds without
 * a sentence here is a type error, not an English word on a screen. A price, a quantity and a
 * saving are shown from their exact decimal text — digits regrouped and the point turned into
 * the Russian decimal comma — and never through a JavaScript number, which would round them.
 * A saving that the API leaves out is said to be unknown, never shown as zero.
 */

import type {
  OptimisationPass,
  OptimisationProposal,
  ProposalAnalogBasis,
  ProposalDecisionState,
  ProposalMatchBasis,
  ProposalVerdict,
  VendorListScope,
} from '@/shared/api';
import { currencyLabel, formatUnitPrice } from '@/entities/price-list';

/** A proposal's current decision, as a state. */
export const DECISION_STATE_LABELS: Readonly<Record<ProposalDecisionState, string>> = {
  pending: 'не решено',
  accept: 'принято',
  reject: 'отклонено',
  revise: 'на доработку',
};

/** The decision states in the order the counts and the filter list them. */
export const DECISION_STATES: readonly ProposalDecisionState[] = ['pending', 'accept', 'reject', 'revise'];

/** What an expert's button says. */
export const VERDICT_LABELS: Readonly<Record<ProposalVerdict, string>> = {
  accept: 'Принять',
  reject: 'Отклонить',
  revise: 'На доработку',
};

export const MATCH_BASIS_LABELS: Readonly<Record<ProposalMatchBasis, string>> = {
  code: 'по коду',
  mark: 'по марке',
  name: 'по наименованию',
};

export const ANALOG_BASIS_LABELS: Readonly<Record<ProposalAnalogBasis, string>> = {
  code_family: 'одно семейство кода',
  name_similarity: 'сходство наименований',
};

/** Whose vendor list the pass used. */
export const VENDOR_LIST_SCOPE_LABELS: Readonly<Record<VendorListScope, string>> = {
  global: 'общий список администратора',
  project: 'список проекта',
};

/** An exact decimal text with its digits regrouped and the decimal comma (`16000` → `16 000`). */
export function formatDecimal(text: string): string {
  return formatUnitPrice(text);
}

/** «16 000 руб.»: an exact amount and the currency the price list stated. */
export function formatAmount(text: string, currency: string): string {
  return `${formatDecimal(text)} ${currencyLabel(currency)}`;
}

/** The quantity with its unit, or the specification's own text when it is not a number. */
export function describeQuantity(proposal: OptimisationProposal): string {
  if (proposal.quantity !== null) return `${formatDecimal(proposal.quantity)} ${proposal.unit}`;
  const shown = proposal.quantity_text ?? 'не указано';
  return `«${shown}» (не число), единица: ${proposal.unit}`;
}

/** The saving, or why there is none. Never `0` for an absent figure. */
export function describeSaving(proposal: OptimisationProposal): string {
  if (proposal.saving === null) {
    return 'Экономия не рассчитана: в спецификации количество не записано числом.';
  }
  return `Экономия: ${formatAmount(proposal.saving, proposal.currency)}`;
}

/** Where in the drawings the specification row is: page, sheet, lines, position. */
export function describeProvenance(proposal: OptimisationProposal): string {
  const parts = [`страница ${proposal.page_number}`];
  if (proposal.sheet_label !== null) parts.push(`лист ${proposal.sheet_label}`);
  parts.push(
    proposal.line_start === proposal.line_end
      ? `строка ${proposal.line_start}`
      : `строки ${proposal.line_start}–${proposal.line_end}`,
  );
  if (proposal.row_position !== null) parts.push(`позиция ${proposal.row_position}`);
  return parts.join(', ');
}

/** «не решено — 2, принято — 1, отклонено — 0, на доработку — 0». */
export function describeCounts(pass: OptimisationPass): string {
  return DECISION_STATES.map(
    (state) => `${DECISION_STATE_LABELS[state]} — ${pass.decision_counts[state]}`,
  ).join(', ');
}

/** The suggested download name; the server's `Content-Disposition` wins if it sends one. */
export function proposalsCsvFileName(passId: string): string {
  return `${passId}-proposals.csv`;
}
