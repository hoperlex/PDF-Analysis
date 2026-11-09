'use client';

/**
 * `UI-B-06`: a pass's proposals as the original's table -- one header over every row, one proposal a row, the verdict with its form
 * and its history in the last column. The columns are the original's, in its order, on what this contract carries: the number,
 * the specification row (its provenance, text and «Открыть лист»), the position now in the price list, the cheaper analog, the saving,
 * the basis of the match (the original's «Риски» and «Норма» wait for a contract, `R-150g`), and the decision.
 *
 * It draws the same proposals as `ProposalCard` with the same pieces (`PositionText`, `ProposalFigures`, `ProposalBasisNotes`,
 * `ProposalDecisionLine`) and the same markers (`data-proposal`, `data-decision`, `data-open-sheet`), so the decision form, the
 * history and the journey address a row as they address a card. The sheet's block strip stands in a row of its own under the
 * proposal, across every column, as the original opens the blocks under its row.
 */

import { Fragment } from 'react';
import type { ReactNode } from 'react';

import type { OptimisationProposal } from '@/shared/api';
import { DECISION_STATE_LABELS, describeProvenance, formatAmount } from '@/entities/optimisation-proposal';

import styles from './optimisation-proposals.module.css';
import {
  PositionText,
  ProposalBasisNotes,
  ProposalDecisionLine,
  ProposalFigures,
  ProposalSheetLink,
} from './proposal-card';

/** The columns, in the original's order; the count is what a block row spans. */
const COLUMNS = [
  '№',
  'Строка спецификации',
  'Сейчас в прайс-листе',
  'Дешёвый аналог',
  'Экономия',
  'Основание',
  'Решение',
] as const;

export interface ProposalTableProps {
  readonly items: readonly OptimisationProposal[];
  /** The controls of one proposal (the decision form), for an expert; the container passes the live one. */
  readonly controlsFor?: ((proposal: OptimisationProposal) => ReactNode) | undefined;
  readonly historyFor?: ((proposal: OptimisationProposal) => ReactNode) | undefined;
  /** `UI-B-09`: the block strip of the sheet a proposal names. */
  readonly blocksFor?: ((proposal: OptimisationProposal) => ReactNode) | undefined;
  /** The object URL of the pass's version PDF once it is fetched; absent or `null`, no «Открыть лист». */
  readonly documentUrl?: string | null | undefined;
  /** Whether the session may decide: without it a row carries no controls. */
  readonly canDecide: boolean;
}

function ProposalRow({
  proposal,
  controls,
  history,
  blocks,
  documentUrl,
}: {
  readonly proposal: OptimisationProposal;
  readonly controls: ReactNode;
  readonly history: ReactNode;
  readonly blocks: ReactNode;
  readonly documentUrl: string | null | undefined;
}) {
  const current = formatAmount(proposal.current_unit_price, proposal.currency);
  const proposed = formatAmount(proposal.proposed_unit_price, proposal.currency);
  return (
    <Fragment>
      <tr data-proposal={proposal.optimisation_proposal_id} data-decision={proposal.current_verdict}>
        <td className={styles.numberCell}>
          <strong>{proposal.ordinal}</strong>
          <span className={styles.state}>{DECISION_STATE_LABELS[proposal.current_verdict]}</span>
        </td>
        <td>
          <span className={styles.hint}>
            Спецификация: {describeProvenance(proposal)}.
            <ProposalSheetLink proposal={proposal} documentUrl={documentUrl} />
          </span>
          <blockquote className={styles.quote}>{proposal.row_text}</blockquote>
        </td>
        <td>
          <PositionText
            position={proposal.matched_position}
            vendor={proposal.matched_position.vendor}
            price={current}
            unit={proposal.unit}
          />
        </td>
        <td>
          <PositionText
            position={proposal.proposed_position}
            vendor={proposal.proposed_vendor}
            price={proposed}
            unit={proposal.unit}
          />
        </td>
        <td>
          <ProposalFigures proposal={proposal} />
        </td>
        <td>
          <ProposalBasisNotes proposal={proposal} />
        </td>
        <td className={styles.judgement}>
          <ProposalDecisionLine decision={proposal.current_decision} />
          {controls}
          {history}
        </td>
      </tr>
      {blocks === null ? null : (
        <tr data-proposal-blocks-row={proposal.optimisation_proposal_id}>
          <td colSpan={COLUMNS.length}>{blocks}</td>
        </tr>
      )}
    </Fragment>
  );
}

export function ProposalTable({ items, controlsFor, historyFor, blocksFor, documentUrl, canDecide }: ProposalTableProps) {
  return (
    <div className={styles.tableFrame}>
      <table className={styles.proposalTable} data-proposal-table="" aria-label="Предложения прохода по порядку">
        <thead>
          <tr>
            {COLUMNS.map((name) => (
              <th key={name} scope="col">
                {name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((proposal) => (
            <ProposalRow
              key={proposal.optimisation_proposal_id}
              proposal={proposal}
              controls={canDecide ? (controlsFor?.(proposal) ?? null) : null}
              history={historyFor?.(proposal) ?? null}
              blocks={blocksFor?.(proposal) ?? null}
              documentUrl={documentUrl}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
