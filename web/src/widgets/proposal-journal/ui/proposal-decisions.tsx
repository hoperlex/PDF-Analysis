/**
 * The knowledge base's «Предложения» half (`R-151h`): the expert's decisions on optimisation proposals, newest first,
 * each with its project, document, section, the specification row and the proposed vendor -- as the original's
 * knowledge base lists them beside the remarks under «Тип». Presentational: the page reads `listProposalDecisionJournal`.
 */

import Link from 'next/link';

import type { ProposalDecisionRecord } from '@/shared/api';
import type { ErrorStateProps } from '@/shared/ui';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { formatInstant, routes } from '@/shared/lib';
import { DECISION_EVENT_LABELS } from '@/entities/optimisation-proposal';

import styles from './proposal-decisions.module.css';

export interface ProposalDecisionsProps {
  readonly records: readonly ProposalDecisionRecord[];
  readonly isLoading?: boolean | undefined;
  readonly error?: ErrorStateProps | null | undefined;
}

export function ProposalDecisions({ records, isLoading, error }: ProposalDecisionsProps) {
  if (isLoading === true) return <LoadingState what="решения по предложениям" />;
  if (error !== undefined && error !== null) return <ErrorState {...error} />;
  if (records.length === 0) {
    return <EmptyState title="Решений по предложениям оптимизации нет." detail="Решения появляются, когда эксперт принимает, отклоняет или возвращает предложение на доработку." />;
  }
  return (
    <ol className={styles.list} data-proposal-decisions={records.length}>
      {records.map((record) => (
        <li key={record.proposal_decision_id} className={styles.row} data-proposal-verdict={record.verdict}>
          <div className={styles.head}>
            <span className={styles.verdict}>{DECISION_EVENT_LABELS[record.verdict]}</span>
            <time dateTime={record.decided_at}>{formatInstant(record.decided_at)}</time>
            <span>{record.actor_label}</span>
          </div>
          <p className={styles.text}>{record.row_text}</p>
          <p className={styles.meta}>
            Поставщик: {record.proposed_vendor} · ед. {record.unit} ·{' '}
            {/* `UI-B-02`: the link opens the document's optimisation tab on the pass the decision was made in. */}
            <Link href={routes.documentOptimisation(record.project_uid, record.document_uid, record.optimisation_pass_id)}>
              {record.project_name} · {record.document_name}
            </Link>
            {record.section === undefined ? null : <> · {record.section}</>}
          </p>
          {record.comment === null ? null : <p className={styles.comment}>{record.comment}</p>}
        </li>
      ))}
    </ol>
  );
}
