'use client';

/**
 * The memory's cases as a table, newest capture first (`D-495`): when it was captured, the section, the category, the latest
 * decision, where the case stands and whether it came from test or real documents, and the button that opens it.
 *
 * It draws what the server sent and derives nothing. A case is HISTORY, not a verdict in force: while the finding exists the
 * ledger decides, and the heading says so. The list carries no text of the finding (the contract's summary has none), so the
 * gist is one press away, in the case.
 */

import type { DecisionMemoryCaseId, DecisionMemoryCaseSummary } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import type { ErrorStateProps } from '@/shared/ui';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { MEMORY_DATA_CLASS_LABELS, MEMORY_REASON_LABELS, MEMORY_VERDICT_LABELS } from '@/entities/decision-memory';
import { CATEGORY_LABELS } from '@/entities/expert-decision';
import { SeverityBadge } from '@/entities/finding';
import { findProjectSection, projectSectionTitle } from '@/entities/project';

import { MemoryStatusBadge } from './status-badge';
import styles from './decision-memory.module.css';

export interface DecisionMemoryListProps {
  readonly cases: readonly DecisionMemoryCaseSummary[];
  readonly isLoading: boolean;
  readonly error: ErrorStateProps | null;
  /** The list is narrowed by a filter or a project, so an empty page is about that selection and not about the memory. */
  readonly narrowed: boolean;
  readonly onOpen: (caseId: DecisionMemoryCaseId) => void;
  readonly onResetFilters?: (() => void) | undefined;
}

/** The category by its Russian heading; a category this build does not know is left as sent, never given a name. */
export function memoryCategoryLabel(category: string): string {
  return (CATEGORY_LABELS as Readonly<Record<string, string | undefined>>)[category] ?? category;
}

/** The section by its short name with the full title as a tooltip; empty when the case carries none. */
export function MemorySectionCell({ code }: { readonly code: string | null }) {
  if (code === null) return <span className={styles.muted}>—</span>;
  const section = findProjectSection(code);
  // A code this build does not know is left as sent, never given a name.
  if (section === null) return <>{code}</>;
  return (
    <span className="am-badge am-badge--inert" title={projectSectionTitle(section)} data-section-cell={section.code}>
      {section.abbr}
    </span>
  );
}

function CaseRow({ item, onOpen }: { readonly item: DecisionMemoryCaseSummary; readonly onOpen: (caseId: DecisionMemoryCaseId) => void }) {
  return (
    <tr
      data-memory-case={item.case_id}
      data-memory-status={item.status}
      data-memory-verdict={item.current_verdict ?? 'none'}
      data-memory-data-class={item.data_class}
    >
      <td>
        <time dateTime={item.captured_at}>{formatInstant(item.captured_at)}</time>
      </td>
      <td><MemorySectionCell code={item.section_code} /></td>
      <td>{memoryCategoryLabel(item.category)}</td>
      <td>
        {item.current_verdict === null ? <span className={styles.muted}>—</span> : (
          <span className="am-kb__verdict" data-verdict={item.current_verdict}>{MEMORY_VERDICT_LABELS[item.current_verdict]}</span>
        )}
        {item.current_severity === null ? null : (
          <span className={styles.inline}><SeverityBadge severity={item.current_severity} title="Важность, решённая экспертом" /></span>
        )}
        {item.decision_count > 1 ? <span className={`${styles.muted} ${styles.inline}`}>решений: {item.decision_count}</span> : null}
      </td>
      <td>
        <MemoryStatusBadge status={item.status} />
        {item.status_reason_code === null ? null : (
          <span className={`${styles.muted} ${styles.inline}`} data-memory-reason={item.status_reason_code}>
            {MEMORY_REASON_LABELS[item.status_reason_code]}
          </span>
        )}
      </td>
      <td>{MEMORY_DATA_CLASS_LABELS[item.data_class]}</td>
      <td>
        <button type="button" className="am-button am-button--quiet am-button--small" data-memory-open={item.case_id} onClick={() => onOpen(item.case_id)}>
          Открыть
        </button>
      </td>
    </tr>
  );
}

export function DecisionMemoryList({ cases, isLoading, error, narrowed, onOpen, onResetFilters }: DecisionMemoryListProps) {
  if (error !== null) return <ErrorState {...error} />;
  if (isLoading) return <LoadingState what="память решений" />;
  if (cases.length === 0) {
    return narrowed ? (
      <EmptyState
        title="В памяти решений нет дел под этот отбор."
        detail="Снимите отбор или выберите все проекты."
        action={onResetFilters === undefined ? undefined : (
          <button type="button" className="am-button am-button--quiet" onClick={onResetFilters}>Сбросить отбор</button>
        )}
      />
    ) : (
      <EmptyState title="Память решений пока пуста." detail="Дело появляется, когда эксперт принимает или отклоняет находку." />
    );
  }
  return (
    <div className={styles.tableFrame}>
      <table className={styles.table} data-memory-table="" data-record-count={cases.length} aria-label="Дела памяти решений, новые сверху">
        <thead>
          <tr>
            <th scope="col">Записано</th>
            <th scope="col">Раздел</th>
            <th scope="col">Категория</th>
            <th scope="col">Решение</th>
            <th scope="col">Состояние</th>
            <th scope="col">Данные</th>
            <th scope="col"><span className={styles.visuallyHidden}>Действие</span></th>
          </tr>
        </thead>
        <tbody>
          {cases.map((item) => <CaseRow key={item.case_id} item={item} onOpen={onOpen} />)}
        </tbody>
      </table>
    </div>
  );
}
