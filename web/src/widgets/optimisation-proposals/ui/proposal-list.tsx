'use client';

/**
 * A pass's proposals (`W60-OPT-PROPOSALS-01`): the decision filter, the cards of one page and
 * the paging. The filter narrows the page; the pass's counts by decision always count every
 * proposal.
 */

import { useState } from 'react';
import type { ReactNode } from 'react';

import type {
  OptimisationProposal,
  OptimisationProposalPage,
  ProposalDecision,
  ProposalDecisionState,
} from '@/shared/api';
import type { FailureMessage } from '@/shared/api/failure-message';
import { failureMessage } from '@/shared/api/failure-message';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import {
  DECISION_STATES,
  DECISION_STATE_LABELS,
  useProposalDecisions,
} from '@/entities/optimisation-proposal';
import { ProposalDecisionForm } from '@/features/decide-optimisation-proposal';

import styles from './optimisation-proposals.module.css';
import { ProposalCard, ProposalHistoryView } from './proposal-card';

export interface DecisionFilterProps {
  readonly selected: ProposalDecisionState | null;
  readonly counts: Readonly<Record<ProposalDecisionState, number>>;
  readonly total: number;
  readonly onSelect: (state: ProposalDecisionState | null) => void;
}

/** «Все» and one button per decision state, each with how many proposals stand in it. */
export function DecisionFilter({ selected, counts, total, onSelect }: DecisionFilterProps) {
  return (
    <nav className={styles.filters} aria-label="Фильтр по решению" data-decision-filter={selected ?? 'all'}>
      <button
        type="button"
        className={selected === null ? 'am-button' : 'am-button am-button--quiet'}
        aria-pressed={selected === null}
        onClick={() => onSelect(null)}
      >
        Все ({total})
      </button>
      {DECISION_STATES.map((state) => (
        <button
          key={state}
          type="button"
          className={selected === state ? 'am-button' : 'am-button am-button--quiet'}
          aria-pressed={selected === state}
          onClick={() => onSelect(state)}
        >
          {DECISION_STATE_LABELS[state]} ({counts[state]})
        </button>
      ))}
    </nav>
  );
}

export interface ProposalHistoryPanelViewProps {
  readonly open: boolean;
  readonly pending: boolean;
  readonly failure: FailureMessage | null;
  /** The history once it is read; `null` before. */
  readonly items: readonly ProposalDecision[] | null;
  readonly onToggle: () => void;
  readonly onRetry: () => void;
}

/** The history disclosure from state already in hand. Rendered by the static harness. */
export function ProposalHistoryPanelView({
  open,
  pending,
  failure,
  items,
  onToggle,
  onRetry,
}: ProposalHistoryPanelViewProps) {
  return (
    <div>
      <button
        type="button"
        className="am-button am-button--quiet am-button--small"
        aria-expanded={open}
        onClick={onToggle}
      >
        История решений
      </button>
      {open && pending ? <LoadingState what="истории решений" /> : null}
      {open && failure !== null ? (
        <ErrorState
          title="История решений не прочитана"
          detail={failure.detail}
          correlationId={failure.correlationId}
          onRetry={onRetry}
        />
      ) : null}
      {open && items !== null ? <ProposalHistoryView items={items} /> : null}
    </div>
  );
}

export interface ProposalHistoryProps {
  readonly proposal: OptimisationProposal;
}

/** The decision history, read only once it is opened. */
export function ProposalHistory({ proposal }: ProposalHistoryProps) {
  const [open, setOpen] = useState(false);
  const history = useProposalDecisions(proposal.optimisation_proposal_id, open);
  return (
    <ProposalHistoryPanelView
      open={open}
      pending={history.isPending}
      failure={history.error === null ? null : failureMessage(history.error)}
      items={history.data === undefined ? null : history.data.items}
      onToggle={() => setOpen(!open)}
      onRetry={() => void history.refetch()}
    />
  );
}

export interface ProposalListViewProps {
  readonly page: OptimisationProposalPage;
  /** Whether the session holds `expert`; the API checks again. */
  readonly canDecide: boolean;
  readonly onDecision: (state: ProposalDecisionState | null) => void;
  /** Move to another page; `null` while a page is on its way. */
  readonly onPage: ((offset: number) => void) | null;
  /** Draw the controls of one proposal; the container passes the live form. */
  readonly controlsFor?: ((proposal: OptimisationProposal) => ReactNode) | undefined;
  readonly historyFor?: ((proposal: OptimisationProposal) => ReactNode) | undefined;
}

export function ProposalListView({
  page,
  canDecide,
  onDecision,
  onPage,
  controlsFor,
  historyFor,
}: ProposalListViewProps) {
  const pass = page.optimisation_pass;
  return (
    <div data-proposal-list={page.total}>
      <DecisionFilter
        selected={page.decision}
        counts={pass.decision_counts}
        total={pass.proposal_count}
        onSelect={onDecision}
      />
      {page.items.length === 0 ? (
        <EmptyState
          title={
            pass.proposal_count === 0
              ? 'В этом проходе нет предложений'
              : 'Нет предложений в выбранном состоянии'
          }
          detail={
            pass.proposal_count === 0
              ? 'Для строк спецификации, однозначно сопоставленных с прайс-листом, не нашлось более дешёвой позиции той же единицы и валюты от поставщика из вендор-листа.'
              : 'Выберите другое состояние или «Все».'
          }
        />
      ) : (
        page.items.map((proposal) => (
          <ProposalCard
            key={proposal.optimisation_proposal_id}
            proposal={proposal}
            controls={canDecide ? (controlsFor?.(proposal) ?? null) : null}
            history={historyFor?.(proposal) ?? null}
          />
        ))
      )}
      {page.total > 0 ? (
        <p className="am-note" data-proposal-paging={`${page.offset}-${page.next_offset ?? 'end'}`}>
          Показано {page.offset + 1}–{page.offset + page.items.length} из {page.total}.{' '}
          <button
            type="button"
            className="am-button am-button--quiet am-button--small"
            disabled={onPage === null || page.offset === 0}
            onClick={() => onPage?.(Math.max(0, page.offset - page.limit))}
          >
            Назад
          </button>{' '}
          <button
            type="button"
            className="am-button am-button--quiet am-button--small"
            disabled={onPage === null || page.next_offset === null}
            onClick={() => page.next_offset !== null && onPage?.(page.next_offset)}
          >
            Далее
          </button>
        </p>
      ) : null}
    </div>
  );
}

export interface ProposalListProps {
  readonly page: OptimisationProposalPage;
  readonly canDecide: boolean;
  readonly onDecision: (state: ProposalDecisionState | null) => void;
  readonly onPage: ((offset: number) => void) | null;
}

/** The live list: decision forms for an expert and a lazily read history under each card. */
export function ProposalList({ page, canDecide, onDecision, onPage }: ProposalListProps) {
  return (
    <ProposalListView
      page={page}
      canDecide={canDecide}
      onDecision={onDecision}
      onPage={onPage}
      controlsFor={(proposal) => (
        <ProposalDecisionForm passId={page.optimisation_pass.optimisation_pass_id} proposal={proposal} />
      )}
      historyFor={(proposal) => <ProposalHistory proposal={proposal} />}
    />
  );
}
