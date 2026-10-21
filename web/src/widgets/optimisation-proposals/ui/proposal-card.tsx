'use client';

/**
 * One proposal (`W60-OPT-PROPOSALS-01`): a specification row, the price-list position it was
 * matched to, the cheaper position proposed instead, both prices, the saving where it can be
 * computed and the expert's current decision.
 *
 * Every figure is the API's exact text: a price is a price-list position's stored price, and
 * the saving is stated only where a numeric quantity makes it so — otherwise the card says it
 * was not computed, and never shows a zero.
 */

import type { ReactNode } from 'react';

import type { OptimisationProposal, ProposalDecision, ProposalPosition } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import {
  ANALOG_BASIS_LABELS,
  DECISION_STATE_LABELS,
  MATCH_BASIS_LABELS,
  VERDICT_LABELS,
  describeProvenance,
  describeQuantity,
  describeSaving,
  formatAmount,
  formatDecimal,
} from '@/entities/optimisation-proposal';

import styles from './optimisation-proposals.module.css';

function PositionColumn({
  title,
  position,
  vendor,
  price,
  unit,
}: {
  readonly title: string;
  readonly position: ProposalPosition;
  readonly vendor: string | null;
  readonly price: string;
  readonly unit: string;
}) {
  return (
    <td className={styles.cell}>
      <strong>{title}</strong>
      <br />
      {position.name}
      {position.mark !== null ? <> · марка {position.mark}</> : null}
      {position.code !== null ? <> · код {position.code}</> : null}
      <br />
      Поставщик: {vendor ?? 'не указан'}
      <br />
      Цена за {unit}: <strong>{price}</strong>
    </td>
  );
}

export interface ProposalDecisionLineProps {
  readonly decision: ProposalDecision | null;
}

/** «Решение: принято, Фамилия И., 2026-10-20 09:30:00 UTC» and its comment, or «не решено». */
export function ProposalDecisionLine({ decision }: ProposalDecisionLineProps) {
  if (decision === null) {
    return <p className={styles.decision}>Решение: {DECISION_STATE_LABELS.pending}.</p>;
  }
  return (
    <p className={styles.decision}>
      Решение: <strong>{DECISION_STATE_LABELS[decision.verdict]}</strong>, {decision.actor_label},{' '}
      {formatInstant(decision.decided_at)}
      {decision.comment !== null ? <> — {decision.comment}</> : null}
    </p>
  );
}

export interface ProposalHistoryViewProps {
  readonly items: readonly ProposalDecision[];
}

/** Every decision of the proposal, oldest first; the last one is current. */
export function ProposalHistoryView({ items }: ProposalHistoryViewProps) {
  if (items.length === 0) {
    return <p className="am-note">Решений по этому предложению ещё не было.</p>;
  }
  return (
    <ol className={styles.history} data-proposal-history={items.length}>
      {items.map((entry) => (
        <li key={entry.proposal_decision_id}>
          {VERDICT_LABELS[entry.verdict]} — {entry.actor_label}, {formatInstant(entry.decided_at)}
          {entry.comment !== null ? <>: {entry.comment}</> : null}
        </li>
      ))}
    </ol>
  );
}

export interface ProposalCardProps {
  readonly proposal: OptimisationProposal;
  /** The decision controls an expert is offered; `null` for anyone else. */
  readonly controls: ReactNode;
  /** The history disclosure. */
  readonly history: ReactNode;
}

export function ProposalCard({ proposal, controls, history }: ProposalCardProps) {
  const current = formatAmount(proposal.current_unit_price, proposal.currency);
  const proposed = formatAmount(proposal.proposed_unit_price, proposal.currency);
  return (
    <article
      className={styles.card}
      data-proposal={proposal.optimisation_proposal_id}
      data-decision={proposal.current_verdict}
    >
      <div className={styles.cardHead}>
        <h4 className={styles.cardTitle}>Предложение {proposal.ordinal}</h4>
        <span className={styles.state}>{DECISION_STATE_LABELS[proposal.current_verdict]}</span>
      </div>
      <p className={styles.provenance}>Спецификация: {describeProvenance(proposal)}.</p>
      <blockquote className={styles.quote}>{proposal.row_text}</blockquote>
      <div className={styles.frame}>
        <table className={styles.table}>
          <tbody>
            <tr>
              <PositionColumn
                title="Сейчас в прайс-листе"
                position={proposal.matched_position}
                vendor={proposal.matched_position.vendor}
                price={current}
                unit={proposal.unit}
              />
              <PositionColumn
                title="Дешёвый аналог"
                position={proposal.proposed_position}
                vendor={proposal.proposed_vendor}
                price={proposed}
                unit={proposal.unit}
              />
            </tr>
          </tbody>
        </table>
      </div>
      <p>
        Количество: {describeQuantity(proposal)}. {describeSaving(proposal)}
      </p>
      <p className={styles.hint}>
        Строка сопоставлена {MATCH_BASIS_LABELS[proposal.matched_basis]}; аналог выбран:{' '}
        {ANALOG_BASIS_LABELS[proposal.analog_basis]}, доля общих слов {formatDecimal(proposal.name_similarity)}.
      </p>
      <p className={styles.hint}>{proposal.rationale}</p>
      <ProposalDecisionLine decision={proposal.current_decision} />
      {controls}
      {history}
    </article>
  );
}
