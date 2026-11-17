'use client';

/**
 * The knowledge base as the original's table (`UI-B-34`, `kb-table`): one decision a row, the columns the original reads
 * across -- type, object and document, section, severity, the gist, the reason, the date -- and the way to the finding.
 *
 * **A row is one or two lines (`UIP-S12-02`, `Г12-B`).** There is no «Решение» column: the verdict is the stripe at the row's
 * left edge and the sign in the first cell (`VerdictMark`: ✓ green, ✕ red, the word as its accessible name), so the colour
 * is never the only carrier. The object and the document are one cell on one line, cut with a tooltip when they do not fit;
 * the date is one line in the reader's local time (`UIP-G-13`), and the exact UTC stamp, the event, the author and how many
 * decisions the finding holds are its tooltip. The gist and the reason are cut at two lines with the whole text as a tooltip.
 * A decision carried over from an earlier version says so under the reason, not in a cell of its own.
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
 *
 * **A carried decision says where it came from** (`D-344`): the cell of the decision carries «↩ Перенесено из V#» when the
 * record names a source (`carried_from`), as «Разбор», the history and «Принято» do. An optimisation proposal's row carries no
 * such mark: its record has no `carried_from` yet (`D-335`).
 */

import Link from 'next/link';
import type { ReactNode } from 'react';

import type { DecisionRecord, KnowledgeBaseEntry, ProposalDecisionRecord, ProposalVerdict } from '@/shared/api';
import { formatInstant, formatInstantUtc, routes } from '@/shared/lib';
import { CATEGORY_LABELS, CarriedMark, VerdictMark } from '@/entities/expert-decision';
import { DECISION_EVENT_LABELS } from '@/entities/optimisation-proposal';
import { SeverityBadge } from '@/entities/finding';
import { findProjectSection, projectSectionTitle } from '@/entities/project';

import { EVENT_TYPE_LABELS, decisionCountWords, sentenceCase } from '../model/labels';
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

/** The object and its document in one line; what does not fit is cut and the whole is the tooltip. */
function PlaceCell({ project, document }: { readonly project: string; readonly document: string }) {
  const place = `${project} · ${document}`;
  return (
    <td>
      <span className={styles.place} title={place}>
        {place}
      </span>
    </td>
  );
}

/** The decision's own words, cut at two lines with the whole text as the tooltip. */
function Clamped({ text }: { readonly text: string }) {
  return (
    <span className={styles.clamp} title={text}>
      {text}
    </span>
  );
}

/**
 * The reason of a decision, and under it the mark of a decision carried over from an earlier version. A missing reason is a
 * dash, never a blank; a decision made directly draws no mark and no empty wrapper (`D-344`, `D-335`).
 */
function ReasonCell({
  reason,
  carriedFrom,
  aside,
}: {
  readonly reason: string | null | undefined;
  readonly carriedFrom: { readonly version_ordinal: number } | undefined;
  /** A quiet word under the reason: what a decision with no reason of its own says. */
  readonly aside?: string | undefined;
}) {
  return (
    <td>
      {reason !== null && reason !== undefined ? <Clamped text={reason} /> : aside === undefined ? <span className={styles.cellMuted}>—</span> : null}
      {aside === undefined ? null : <span className={`${styles.cellMuted} ${styles.aside}`}>{aside}</span>}
      {carriedFrom === undefined ? null : (
        <span className={styles.carried}>
          <CarriedMark carriedFrom={carriedFrom} />
        </span>
      )}
    </td>
  );
}

/**
 * The date on one line, in the reader's local time (`UIP-G-13`); the tooltip says the rest: the event, the exact UTC stamp, who,
 * and how many decisions the finding holds.
 */
function DateCell({ at, tooltip, eventCount }: { readonly at: string; readonly tooltip: string; readonly eventCount?: number | undefined }) {
  return (
    <td className={styles.cellDate}>
      <time dateTime={at} title={tooltip} {...(eventCount === undefined ? {} : { 'data-event-count': eventCount })}>
        {formatInstant(at)}
      </time>
    </td>
  );
}

/** The first cell: the verdict's sign, then the type (`Замечание · ` before the category in «Все»). */
function TypeCell({ sign, children }: { readonly sign: ReactNode; readonly children: ReactNode }) {
  return (
    <td>
      <span className={styles.typeLine}>
        {sign}
        <span className="am-kb__category">{children}</span>
      </span>
    </td>
  );
}

function FindingRow({ record, kindLabel }: { readonly record: DecisionRecord; readonly kindLabel: boolean }) {
  const tooltip = [
    EVENT_TYPE_LABELS[record.event_type],
    formatInstantUtc(record.recorded_at),
    record.author_label,
    decisionCountWords(record.decision_event_count),
  ].join(' · ');
  return (
    <tr
      data-decision-id={record.decision_id}
      data-finding-uid={record.finding_uid}
      data-category={record.category}
      data-event-type={record.event_type}
      data-current-verdict={record.current_verdict}
      data-verdict={record.verdict ?? 'none'}
    >
      <TypeCell sign={<VerdictMark verdict={record.current_verdict} />}>
        {kindLabel ? 'Замечание · ' : null}
        {CATEGORY_LABELS[record.category]}
      </TypeCell>
      <PlaceCell project={record.project_name} document={record.document_name} />
      <SectionCell code={record.section} />
      <td data-decided-severity={record.severity}>
        {record.severity === undefined ? '—' : <SeverityBadge severity={record.severity} title="Критичность, решённая экспертом" />}
      </td>
      <td>
        <Clamped text={record.finding_text} />
      </td>
      {/*
       * `D-344`, `UI-A-73`: a decision the expert carried over from an earlier version's finding says so, «↩ Перенесено из V2»,
       * under the reason, as «Разбор» draws it beside the verdict. `carried_from` is the record's own (the server's structured link).
       */}
      <ReasonCell reason={record.comment} carriedFrom={record.carried_from} />
      <DateCell at={record.recorded_at} tooltip={tooltip} eventCount={record.decision_event_count} />
      <td className={styles.cellLink}>
        {/* `ADR-0010`, `UI-B-38`: the link is built from `project_uid`, `run_id` and `finding_uid`; «Разбор» opens on that finding. */}
        <Link
          className="am-kb__link"
          href={`${routes.review(record.project_uid, record.run_id)}?finding=${encodeURIComponent(record.finding_uid)}`}
        >
          Открыть замечание
        </Link>
      </td>
    </tr>
  );
}

/** A proposal's verdict as the sign of the first cell: accepted ✓, rejected ✕; «на доработку» and «решение снято» carry none. */
function proposalSign(verdict: ProposalVerdict) {
  if (verdict === 'accept') return <VerdictMark verdict="accepted" />;
  if (verdict === 'reject') return <VerdictMark verdict="rejected" />;
  return null;
}

function ProposalRow({ record }: { readonly record: ProposalDecisionRecord }) {
  const tooltip = [formatInstantUtc(record.decided_at), record.actor_label].join(' · ');
  return (
    <tr data-proposal-decision-id={record.proposal_decision_id} data-proposal-verdict={record.verdict}>
      <TypeCell sign={proposalSign(record.verdict)}>Предложение</TypeCell>
      <PlaceCell project={record.project_name} document={record.document_name} />
      <SectionCell code={record.section} />
      <td className={styles.cellMuted}>—</td>
      <td>
        <Clamped text={`${record.row_text} · поставщик ${record.proposed_vendor} · ед. ${record.unit}`} />
      </td>
      {/*
       * `D-335`, `UI-B-14`: a decision carried over from an earlier version's pass says so under the reason, as a finding's does;
       * a decision made directly has none and draws nothing -- not an empty wrapper either.
       */}
      <ReasonCell
        reason={record.comment}
        carriedFrom={record.carried_from}
        aside={record.verdict === 'revise' || record.verdict === 'revoke' ? sentenceCase(DECISION_EVENT_LABELS[record.verdict]) : undefined}
      />
      <DateCell at={record.decided_at} tooltip={tooltip} />
      <td className={styles.cellLink}>
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
            <th scope="col" className={styles.colType}>Тип</th>
            <th scope="col" className={styles.colPlace}>Объект · документ</th>
            <th scope="col" className={styles.colSection}>Раздел</th>
            <th scope="col" className={styles.colSeverity}>Критичность</th>
            <th scope="col" className={styles.colText}>Суть</th>
            <th scope="col" className={styles.colReason}>Причина решения</th>
            <th scope="col" className={styles.colDate}>Дата</th>
            <th scope="col" className={styles.colLink}>Замечание</th>
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
