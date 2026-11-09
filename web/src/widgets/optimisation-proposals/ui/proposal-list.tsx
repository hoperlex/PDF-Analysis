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

import { PROPOSAL_LAYOUTS, PROPOSAL_LAYOUT_LABELS } from '../model/layout';
import type { ProposalLayout } from '../model/layout';
import styles from './optimisation-proposals.module.css';
import { ProposalCard, ProposalHistoryView, namedPage } from './proposal-card';
import { ProposalSheetBlocks } from './proposal-sheet-blocks';
import { ProposalTable } from './proposal-table';

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

export interface LayoutSwitchProps {
  readonly selected: ProposalLayout;
  readonly onSelect: (layout: ProposalLayout) => void;
}

/**
 * `UI-B-06`: «Карточки» and «Таблица», the two ways the same page of proposals is drawn. The choice is the screen's address
 * (`?layout=`), written by the container; this draws the two buttons from state already in hand.
 */
export function LayoutSwitch({ selected, onSelect }: LayoutSwitchProps) {
  return (
    <nav className={styles.filters} aria-label="Раскладка предложений" data-proposal-layout={selected}>
      {PROPOSAL_LAYOUTS.map((layout) => (
        <button
          key={layout}
          type="button"
          className={selected === layout ? 'am-button' : 'am-button am-button--quiet'}
          aria-pressed={selected === layout}
          onClick={() => onSelect(layout)}
        >
          {PROPOSAL_LAYOUT_LABELS[layout]}
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

/** `UI-B-09`: the pass's version PDF as the cards' «Открыть лист» needs it. */
export interface SheetDocument {
  /** The object URL once the PDF is fetched; `null` before and on a refusal. */
  readonly url: string | null;
  readonly isLoading: boolean;
  readonly failure: FailureMessage | null;
  readonly onRetry: () => void;
}

/** What the list says while the PDF is on its way or was refused; nothing once it is there. */
function SheetDocumentNote({ sheet }: { readonly sheet: SheetDocument }) {
  if (sheet.isLoading) {
    return (
      <p className="am-note" role="status" data-proposal-sheet="loading">
        Загружается PDF версии: ссылки «Открыть лист» появятся после загрузки.
      </p>
    );
  }
  if (sheet.failure !== null) {
    return (
      <ErrorState
        title="PDF версии не получен: ссылок «Открыть лист» нет"
        detail={sheet.failure.detail}
        correlationId={sheet.failure.correlationId}
        onRetry={sheet.onRetry}
      />
    );
  }
  return null;
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
  /** `UI-B-09`: the block strip of the sheet a proposal names; the container passes the live one. */
  readonly blocksFor?: ((proposal: OptimisationProposal) => ReactNode) | undefined;
  /** `UI-B-09`: the pass's version PDF; absent, the cards offer no «Открыть лист». */
  readonly sheet?: SheetDocument | undefined;
  /**
   * `UI-B-05`/`UI-B-16`: the pass's actions (the export, the import of decisions). The original puts its counts by
   * decision and its buttons in one strip above the table; they stand beside the decision filter here.
   */
  readonly actions?: ReactNode;
  /** The pass's facts, between the strip and the proposals (`UI-B-05`). */
  readonly summary?: ReactNode;
  /** `UI-B-06`: how the page is drawn; «Карточки» when absent. */
  readonly layout?: ProposalLayout | undefined;
  /** `UI-B-06`: the reader chose a layout. Absent, the strip offers no switch. */
  readonly onLayout?: ((layout: ProposalLayout) => void) | undefined;
}

export function ProposalListView({
  page,
  canDecide,
  onDecision,
  onPage,
  controlsFor,
  historyFor,
  blocksFor,
  sheet,
  actions,
  summary,
  layout = 'cards',
  onLayout,
}: ProposalListViewProps) {
  const pass = page.optimisation_pass;
  return (
    <div data-proposal-list={page.total}>
      <div className={styles.strip}>
        <DecisionFilter
          selected={page.decision}
          counts={pass.decision_counts}
          total={pass.proposal_count}
          onSelect={onDecision}
        />
        {onLayout === undefined ? null : <LayoutSwitch selected={layout} onSelect={onLayout} />}
        {actions ?? null}
      </div>
      {summary ?? null}
      {sheet === undefined ? null : <SheetDocumentNote sheet={sheet} />}
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
      ) : layout === 'table' ? (
        <ProposalTable
          items={page.items}
          canDecide={canDecide}
          controlsFor={controlsFor}
          historyFor={historyFor}
          blocksFor={blocksFor}
          documentUrl={sheet?.url ?? null}
        />
      ) : (
        page.items.map((proposal) => (
          <ProposalCard
            key={proposal.optimisation_proposal_id}
            proposal={proposal}
            controls={canDecide ? (controlsFor?.(proposal) ?? null) : null}
            history={historyFor?.(proposal) ?? null}
            blocks={blocksFor?.(proposal) ?? null}
            documentUrl={sheet?.url ?? null}
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
  /** `UI-B-09`: the pass's version PDF; the container reads it once for every card. */
  readonly sheet?: SheetDocument | undefined;
  /** The pass's export and import, beside the decision filter (`UI-B-05`). */
  readonly actions?: ReactNode;
  /** The pass's facts, between the strip and the proposals (`UI-B-05`). */
  readonly summary?: ReactNode;
  /** `UI-B-06`: how the page is drawn, and the reader's choice of it. */
  readonly layout?: ProposalLayout | undefined;
  readonly onLayout?: ((layout: ProposalLayout) => void) | undefined;
}

/** The live list: decision forms for an expert and a lazily read history under each card. */
export function ProposalList({
  page,
  canDecide,
  onDecision,
  onPage,
  sheet,
  actions,
  summary,
  layout,
  onLayout,
}: ProposalListProps) {
  return (
    <ProposalListView
      page={page}
      canDecide={canDecide}
      onDecision={onDecision}
      onPage={onPage}
      sheet={sheet}
      actions={actions}
      summary={summary}
      layout={layout}
      onLayout={onLayout}
      controlsFor={(proposal) => (
        <ProposalDecisionForm passId={page.optimisation_pass.optimisation_pass_id} proposal={proposal} />
      )}
      historyFor={(proposal) => <ProposalHistory proposal={proposal} />}
      blocksFor={(proposal) => {
        // A proposal that names no page has no sheet to show the blocks of.
        const sheetPage = namedPage(proposal);
        const pass = page.optimisation_pass;
        return sheetPage === null ? null : (
          <ProposalSheetBlocks projectUid={pass.project_uid} versionUid={pass.version_uid} page={sheetPage} />
        );
      }}
    />
  );
}
