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
import { pdfPageUrl } from '@/features/open-evidence';
import {
  ANALOG_BASIS_LABELS,
  DECISION_EVENT_LABELS,
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

/**
 * «Решение: принято, Фамилия И., 2026-10-20 09:30:00 UTC» and its comment, or «не решено». A withdrawn decision
 * (`UI-B-12`) says so — «решение снято», by whom and when — and the proposal is `pending` again.
 */
export function ProposalDecisionLine({ decision }: ProposalDecisionLineProps) {
  if (decision === null) {
    return <p className={styles.decision}>Решение: {DECISION_STATE_LABELS.pending}.</p>;
  }
  return (
    <p className={styles.decision}>
      Решение: <strong>{DECISION_EVENT_LABELS[decision.verdict]}</strong>, {decision.actor_label},{' '}
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
  /**
   * `UI-B-09`: the object URL of the pass's version PDF once it is fetched. Absent or `null`, the card offers no
   * link; the list above says why (loading, or the refusal).
   */
  readonly documentUrl?: string | null | undefined;
}

/** The page a proposal names, when it names one a PDF reader can be pointed at. */
export function namedPage(proposal: OptimisationProposal): number | null {
  return Number.isInteger(proposal.page_number) && proposal.page_number >= 1 ? proposal.page_number : null;
}

export function ProposalCard({ proposal, controls, history, documentUrl }: ProposalCardProps) {
  const page = namedPage(proposal);
  const sheetUrl = documentUrl === undefined || documentUrl === null || page === null ? null : pdfPageUrl(documentUrl, page);
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
      <p className={styles.provenance}>
        Спецификация: {describeProvenance(proposal)}.
        {sheetUrl === null ? null : (
          <>
            {' '}
            {/* `UI-B-09`: the version's PDF on the proposal's page, in the browser's own reader (the review's «Открыть PDF ↗»). */}
            <a
              href={sheetUrl}
              target="_blank"
              rel="noopener noreferrer"
              data-open-sheet={page}
              aria-label={`Открыть лист: PDF версии на странице ${page}, в новой вкладке`}
            >
              Открыть лист ↗
            </a>
          </>
        )}
      </p>
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
      <p className={styles.figures}>
        Количество: {describeQuantity(proposal)}. {describeSaving(proposal)}
      </p>
      <div className={styles.basis}>
        <p className={styles.hint}>
          Строка сопоставлена {MATCH_BASIS_LABELS[proposal.matched_basis]}; аналог выбран:{' '}
          {ANALOG_BASIS_LABELS[proposal.analog_basis]}, доля общих слов {formatDecimal(proposal.name_similarity)}.
        </p>
        <p className={styles.hint}>{proposal.rationale}</p>
      </div>
      {/* The verdict, its form and its history in the last column (`UI-B-06`): the original's «Решение» column. */}
      <div className={styles.judgement}>
        <ProposalDecisionLine decision={proposal.current_decision} />
        {controls}
        {history}
      </div>
    </article>
  );
}
