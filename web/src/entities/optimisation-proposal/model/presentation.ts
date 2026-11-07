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
  ProposalDecision,
  ProposalDecisionCarryoverReport,
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
  revoke: 'Снять решение',
};

/**
 * What a recorded decision event says, in the past: a history line, the proposal's decision line, the knowledge base.
 * `revoke` (`UI-B-12`) is the withdrawal of the decision before it; it is an event, never a state of a proposal, which
 * stands `pending` again.
 */
export const DECISION_EVENT_LABELS: Readonly<Record<ProposalVerdict, string>> = {
  accept: 'принято',
  reject: 'отклонено',
  revise: 'на доработку',
  revoke: 'решение снято',
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

/** The suggested name of the pass's workbook (`UI-B-15`), from the pass identity alone. */
export function proposalsXlsxFileName(passId: string): string {
  return `${passId}-proposals.xlsx`;
}

/**
 * `UI-B-14`: «↩ Перенесено из V2», the mark of a decision that an expert carried over from an earlier version's pass
 * (the original's wording); `null` for a decision made directly. The ordinal is the version's display order, never an
 * identity.
 */
export function carriedFromLabel(decision: Pick<ProposalDecision, 'carried_from'>): string | null {
  return decision.carried_from === null ? null : `↩ Перенесено из V${decision.carried_from.version_ordinal}`;
}

/** One earlier version a pass's decisions can be carried from: its display ordinal, and the pass to carry them from. */
export interface CarrySource {
  readonly versionOrdinal: number;
  readonly pass: OptimisationPass;
}

/** The decisions in force of a pass (`accept`, `reject` and `revise`); the pending ones carry nothing. */
export function decidedCount(pass: OptimisationPass): number {
  const counts = pass.decision_counts;
  return counts.accept + counts.reject + counts.revise;
}

/**
 * `UI-B-14`: the earlier versions whose decisions can be carried into `target`, newest version first, each with the pass
 * to carry from. A pass is a source only when it belongs to an earlier version of the same document set (the server
 * refuses any other); of several passes over one version the newest that holds a decision in force is offered, or the
 * newest when none does. A version with no pass offers nothing, and a pass is never offered for itself.
 */
export function carrySources(passes: readonly OptimisationPass[], target: OptimisationPass): readonly CarrySource[] {
  const byVersion = new Map<number, OptimisationPass[]>();
  for (const pass of passes) {
    if (pass.document_uid !== target.document_uid || pass.version_ordinal >= target.version_ordinal) continue;
    byVersion.set(pass.version_ordinal, [...(byVersion.get(pass.version_ordinal) ?? []), pass]);
  }
  return [...byVersion.entries()]
    .sort(([left], [right]) => right - left)
    .map(([versionOrdinal, ofVersion]) => ({
      versionOrdinal,
      // `passes` is newest first, so the first with a decision is the newest with one.
      pass: ofVersion.find((pass) => decidedCount(pass) > 0) ?? ofVersion[0]!,
    }));
}

/**
 * What a carryover did, in sentences: how many of the source's decisions were carried, then each reason the rest were
 * not. Every source decision is in exactly one count, so the sentences add up to `source_decided`.
 */
export function describeCarryover(report: ProposalDecisionCarryoverReport): readonly string[] {
  const version = `V${report.source_version_ordinal}`;
  if (report.source_decided === 0) return [`В ${version} нет решений для переноса.`];
  const lines = [`Перенесено ${report.carried} из ${report.source_decided} решений ${version}.`];
  if (report.target_decided > 0) {
    lines.push(`Уже решено в этом проходе, оставлено как есть: ${report.target_decided}.`);
  }
  if (report.ambiguous > 0) {
    lines.push(`Не перенесено, потому что одинаковых предложений несколько: ${report.ambiguous}.`);
  }
  if (report.unmatched > 0) {
    lines.push(`Не перенесено, потому что такого предложения в этом проходе нет: ${report.unmatched}.`);
  }
  return lines;
}
