'use client';

/**
 * The knowledge base as the original's table (`UI-B-34`, `kb-table`): one decision a row, the columns the original reads
 * across -- type, project, section, severity, the decision, the gist, the reason, the date -- and the way to the finding.
 *
 * It is the default view of the screen, as the original's is; the rows as events (the widget's other view) stay one press away.
 * It draws what the server sent and derives nothing: the project, the document and the section are the record's own
 * `project_name`, `document_name` and `section` (read by the server when the page is read; no further request), and
 * a section the record does not carry leaves the cell empty, with no label made up for the absence.
 *
 * **Not in the table: the original's «ID» column.** A finding's display number is not an identity here (AGENTS §4); the
 * row carries `data-finding-uid` and the link is built from the identities the record carries (`ADR-0010`), so the column
 * would print a number nothing resolves. A row is still one **event**: a finding the reviewer returned to carries two
 * rows, and the cell of the date says how many decisions the finding holds.
 */

import Link from 'next/link';

import type { DecisionRecord, KnowledgeBaseEntry, ProposalDecisionRecord } from '@/shared/api';
import { formatInstant, routes } from '@/shared/lib';
import { CATEGORY_LABELS, VERDICT_LABELS } from '@/entities/expert-decision';
import { DECISION_EVENT_LABELS } from '@/entities/optimisation-proposal';
import { SeverityBadge } from '@/entities/finding';
import { findProjectSection, projectSectionTitle } from '@/entities/project';

import { EVENT_TYPE_LABELS, decisionCountWords } from '../model/labels';
import styles from './knowledge-base.module.css';

export interface KnowledgeBaseTableProps {
  /** The rows, newest first, as the server sent them: a decision on a finding or on an optimisation proposal. */
  readonly entries: readonly KnowledgeBaseEntry[];
  /** «Все»: a finding's type says «Замечание» before its category, as in the events view. */
  readonly kindLabel?: boolean | undefined;
}

/** The section of a row: its short name with the full title as a tooltip, nothing when the record carries none. */
function SectionCell({ code }: { readonly code: string | undefined }) {
  if (code === undefined) return <td className={styles.cellMuted}>—</td>;
  const section = findProjectSection(code);
  // A code this build does not know is left as sent, never given a name.
  if (section === null) return <td>{code}</td>;
  return (
    <td>
      <span className="am-badge am-badge--inert" title={projectSectionTitle(section)} data-section-cell={section.code}>
        {section.abbr}
      </span>
    </td>
  );
}

function PlaceCell({ project, document }: { readonly project: string; readonly document: string }) {
  return (
    <td>
      <span className={styles.project}>{project}</span>
      <span className={styles.document}>{document}</span>
    </td>
  );
}

function FindingRow({ record, kindLabel }: { readonly record: DecisionRecord; readonly kindLabel: boolean }) {
  return (
    <tr
      data-decision-id={record.decision_id}
      data-finding-uid={record.finding_uid}
      data-category={record.category}
      data-event-type={record.event_type}
      data-current-verdict={record.current_verdict}
      data-verdict={record.verdict ?? 'none'}
    >
      <td className="am-kb__category">
        {kindLabel ? 'Замечание · ' : null}
        {CATEGORY_LABELS[record.category]}
      </td>
      <PlaceCell project={record.project_name} document={record.document_name} />
      <SectionCell code={record.section} />
      <td data-decided-severity={record.severity}>
        {record.severity === undefined ? '—' : <SeverityBadge severity={record.severity} title="Важность, решённая экспертом" />}
      </td>
      <td>
        <span className="am-kb__verdict" data-verdict={record.current_verdict}>
          {VERDICT_LABELS[record.current_verdict]}
        </span>
        <span className={`am-kb__event ${styles.event}`}>{EVENT_TYPE_LABELS[record.event_type]}</span>
      </td>
      <td>{record.finding_text}</td>
      <td className={record.comment === null || record.comment === undefined ? styles.cellMuted : undefined}>
        {record.comment === null || record.comment === undefined ? '—' : record.comment}
      </td>
      <td>
        <time dateTime={record.recorded_at}>{formatInstant(record.recorded_at)}</time>
        <span className={styles.document}>{record.author_label}</span>
        <span className={styles.document} data-event-count={record.decision_event_count}>
          {decisionCountWords(record.decision_event_count)}
        </span>
      </td>
      <td>
        {/* `ADR-0010`, `UI-B-38`: the link is built from `project_uid`, `run_id` and `finding_uid`; «Разбор» opens on that finding. */}
        <Link
          className="am-kb__link"
          href={`${routes.review(record.project_uid, record.run_id)}?finding=${encodeURIComponent(record.finding_uid)}`}
        >
          Открыть находку
        </Link>
      </td>
    </tr>
  );
}

function ProposalRow({ record }: { readonly record: ProposalDecisionRecord }) {
  return (
    <tr data-proposal-decision-id={record.proposal_decision_id} data-proposal-verdict={record.verdict}>
      <td className="am-kb__category">Предложение</td>
      <PlaceCell project={record.project_name} document={record.document_name} />
      <SectionCell code={record.section} />
      <td className={styles.cellMuted}>—</td>
      <td>
        <span className="am-kb__verdict" data-verdict={record.verdict}>
          {DECISION_EVENT_LABELS[record.verdict]}
        </span>
      </td>
      <td>
        {record.row_text} · поставщик {record.proposed_vendor} · ед. {record.unit}
      </td>
      <td className={record.comment === null ? styles.cellMuted : undefined}>{record.comment === null ? '—' : record.comment}</td>
      <td>
        <time dateTime={record.decided_at}>{formatInstant(record.decided_at)}</time>
        <span className={styles.document}>{record.actor_label}</span>
      </td>
      <td>
        <Link
          className="am-kb__link"
          href={routes.documentOptimisation(record.project_uid, record.document_uid, record.optimisation_pass_id)}
        >
          Открыть оптимизацию
        </Link>
      </td>
    </tr>
  );
}

export function KnowledgeBaseTable({ entries, kindLabel = false }: KnowledgeBaseTableProps) {
  return (
    <div className={styles.tableFrame}>
      <table className={styles.table} data-knowledge-base-table="" aria-label="Решения проверяющего, новые сверху">
        <thead>
          <tr>
            <th scope="col">Тип</th>
            <th scope="col">Проект</th>
            <th scope="col">Раздел</th>
            <th scope="col">Важность</th>
            <th scope="col">Решение</th>
            <th scope="col">Суть</th>
            <th scope="col">Причина решения</th>
            <th scope="col">Дата</th>
            <th scope="col">Находка</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) =>
            entry.kind === 'finding' && entry.finding !== undefined ? (
              <FindingRow key={`finding:${entry.finding.decision_id}`} record={entry.finding} kindLabel={kindLabel} />
            ) : entry.kind === 'proposal' && entry.proposal !== undefined ? (
              <ProposalRow key={`proposal:${entry.proposal.proposal_decision_id}`} record={entry.proposal} />
            ) : null,
          )}
        </tbody>
      </table>
    </div>
  );
}
