'use client';

/** @jsxRuntime automatic */

/**
 * The knowledge base: every decision this deployment has taken, newest first.
 *
 * A pure widget — contract models and callbacks in, markup out, per seam §3.4. It holds no
 * query and no mutation, and it derives nothing: `ADR-0012` makes the knowledge base a
 * **projection** over the decision journal, the server computes it, and this renders what
 * the server sent. A count assembled here would be a second answer to a question the
 * server already answers.
 *
 * **What it deliberately does not show.** The legacy `decisions_log.json` carried
 * `customer_confirmed` and `fixed_by_customer` beside each record. Neither is derivable
 * from anything this system holds: they are a feedback loop with the customer that this
 * system does not have. They are named in `docs/program/W38-KB.md` and left out rather
 * than invented, because a column that always reads "no" is worse than a missing one.
 *
 * **Each row says where it belongs** (`UI-PARITY-P0A`): «Проект · Документ · Раздел», from the
 * record's own `project_name`, `document_name` and `section`. The two names are joined by the
 * server at read time and stored nowhere. `section` is the expert-confirmed section of the
 * finding's version and is absent while that version is unclassified; the row then carries the
 * project and the document and no third part — no label is made up for the absence.
 *
 * Every row is one **event**, not one finding. A finding the reviewer returned to carries
 * two rows, and `decision_event_count` on each says so — which is the fact a knowledge
 * base is read for: that this question has been asked before.
 */

import Link from 'next/link';

import type { DecisionRecord, DecisionEventType, KnowledgeBaseEntry, ProposalDecisionRecord } from '@/shared/api';
import {
  DECISION_EVENT_TYPE_VALUES,
  FINDING_CATEGORY_VALUES,
  VERDICT_VALUES,
} from '@/shared/api';
import type { ErrorStateProps } from '@/shared/ui';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { formatInstant, routes } from '@/shared/lib';
import { CATEGORY_LABELS, VERDICT_LABELS } from '@/entities/expert-decision';
import { DECISION_EVENT_LABELS } from '@/entities/optimisation-proposal';
import { SeverityBadge } from '@/entities/finding';
import { findProjectSection, projectSectionTitle } from '@/entities/project';

import styles from './knowledge-base.module.css';

/**
 * What narrows the list the reader is looking at, and the way back out of it (`D-313`). The page
 * passes it only while a category, a verdict or a project is chosen; it is then what makes an
 * empty page say «По выбранному отбору решений нет» instead of claiming that the installation
 * has taken no decision at all, which an empty filtered page cannot know.
 */
export interface KnowledgeBaseNarrowing {
  /** Clears the category and the verdict. Absent when neither is chosen, so no button does nothing. */
  readonly onResetFilters?: (() => void) | undefined;
  /** Where «Все проекты» leads: this screen with the project taken out of the address. Absent when no project is chosen. */
  readonly allProjectsHref?: string | undefined;
}

export interface KnowledgeBaseProps {
  readonly records: readonly DecisionRecord[];
  /**
   * `D-317`: «Все» -- both journals merged, newest first. When present it is the list, and `records` is not read:
   * a decision on a finding is drawn as in «Замечания» with «Замечание» before its category, a decision on an
   * optimisation proposal in the same row form with «Предложение».
   */
  readonly entries?: readonly KnowledgeBaseEntry[] | undefined;
  readonly isLoading?: boolean | undefined;
  readonly error?: ErrorStateProps | null | undefined;
  /** Present while the list is narrowed by a category, a verdict or a project; absent for the whole journal. */
  readonly narrowing?: KnowledgeBaseNarrowing | undefined;
}

// Category headings come from `CATEGORY_LABELS` in `entities/expert-decision`: the page's
// filter reads the same table, and it moved there so the page keeps no static import of
// this widget (`W50-LAZY-01`).

/** Event labels, the same four `DecisionHistory` uses. */
const EVENT_TYPE_LABELS: Readonly<Record<DecisionEventType, string>> = {
  accept: 'приём',
  reject: 'отклонение',
  comment: 'комментарий',
  revoke: 'отзыв',
};

function hasValue(values: readonly string[], value: unknown): boolean {
  return typeof value === 'string' && values.includes(value);
}

/**
 * «Проект · Документ · Раздел». The section is its catalogue name, as the dashboard and the
 * project structure print it; a code the catalogue does not hold never gets here
 * (`hasInvalidVocabulary`).
 */
function placeOf(record: DecisionRecord): string {
  const parts = [record.project_name, record.document_name];
  if (record.section !== undefined) {
    const section = findProjectSection(record.section);
    if (section !== null) parts.push(projectSectionTitle(section));
  }
  return parts.join(' · ');
}

function hasInvalidVocabulary(record: DecisionRecord): boolean {
  return (
    (record.section !== undefined && findProjectSection(record.section) === null) ||
    !hasValue(FINDING_CATEGORY_VALUES, record.category) ||
    !hasValue(DECISION_EVENT_TYPE_VALUES, record.event_type) ||
    !hasValue(VERDICT_VALUES, record.current_verdict) ||
    (record.verdict !== null &&
      record.verdict !== undefined &&
      !hasValue(VERDICT_VALUES, record.verdict))
  );
}

/** One decision on a finding, as «Замечания» lists it; in «Все» its category follows «Замечание». */
function FindingRecordItem({ record, kindLabel = false }: { readonly record: DecisionRecord; readonly kindLabel?: boolean }) {
  return (
    <li
      className="am-kb__record"
      data-decision-id={record.decision_id}
      data-finding-uid={record.finding_uid}
      data-category={record.category}
      data-event-type={record.event_type}
      data-current-verdict={record.current_verdict}
      data-verdict={record.verdict ?? 'none'}
    >
      <p className="am-kb__heading">
        <span className="am-kb__category">
          {kindLabel ? 'Замечание · ' : null}
          {CATEGORY_LABELS[record.category]}
        </span>
        <span className="am-kb__verdict" data-verdict={record.current_verdict}>
          {VERDICT_LABELS[record.current_verdict]}
        </span>
        {/*
         * `WEB-REVIEW-FOLLOWUPS-01`: the severity the expert decided with THIS event
         * (the row is an event), beside the verdict. A row that carries none -- a
         * comment, a reject, a legacy accept -- renders nothing here.
         */}
        {record.severity === undefined ? null : (
          <span data-decided-severity={record.severity}>
            {'важность '}
            <SeverityBadge severity={record.severity} title="Важность, решённая экспертом" />
          </span>
        )}
        <span className="am-kb__event">{EVENT_TYPE_LABELS[record.event_type]}</span>
      </p>
      <p className="am-kb__meta" data-record-place="true">
        {placeOf(record)}
      </p>
      <p className="am-kb__text">{record.finding_text}</p>
      {record.comment !== null && record.comment !== undefined ? (
        <p className="am-kb__comment">{record.comment}</p>
      ) : null}
      <p className="am-kb__meta">
        <span className="am-kb__author">{record.author_label}</span>
        <time dateTime={record.recorded_at}>{formatInstant(record.recorded_at)}</time>
        {/*
         * The count, said in words rather than shown as a bare number: a record
         * whose finding carries more than one event is the case a knowledge base
         * exists to surface, and a lone digit beside a timestamp reads as an
         * ordinal.
         */}
        <span className="am-kb__events" data-event-count={record.decision_event_count}>
          {record.decision_event_count === 1
            ? 'одно решение по находке'
            : `решений по находке: ${record.decision_event_count}`}
        </span>
        {/*
         * The way back to the finding. `ADR-0010`: the link is built from
         * `project_uid`, `run_id` and `finding_uid`, the identities the record carries, and
         * never from a display number or a path the server did not send. `UI-B-38`: «Разбор»
         * reads `?finding=` and opens on that finding, as the original opens the object.
         */}
        <Link
          className="am-kb__link"
          href={`${routes.review(record.project_uid, record.run_id)}?finding=${encodeURIComponent(record.finding_uid)}`}
        >
          Открыть находку
        </Link>
      </p>
    </li>
  );
}

/**
 * `D-317`: one decision on an optimisation proposal in «Все», in the row form of a finding's: the verdict, where it
 * was taken, the specification row and the proposed vendor, the comment, who and when, and the way to the document's
 * optimisation.
 */
function ProposalRecordItem({ record }: { readonly record: ProposalDecisionRecord }) {
  // The section by its title, as a finding's place names it; a code this build does not know is left as sent.
  const section = record.section === undefined ? null : findProjectSection(record.section);
  const place = [
    record.project_name,
    record.document_name,
    ...(record.section === undefined ? [] : [section === null ? record.section : projectSectionTitle(section)]),
  ];
  return (
    <li className="am-kb__record" data-proposal-decision-id={record.proposal_decision_id} data-proposal-verdict={record.verdict}>
      <p className="am-kb__heading">
        <span className="am-kb__category">Предложение</span>
        <span className="am-kb__verdict" data-verdict={record.verdict}>
          {DECISION_EVENT_LABELS[record.verdict]}
        </span>
      </p>
      <p className="am-kb__meta" data-record-place="true">
        {place.join(' · ')}
      </p>
      <p className="am-kb__text">
        {record.row_text} · поставщик {record.proposed_vendor} · ед. {record.unit}
      </p>
      {record.comment === null ? null : <p className="am-kb__comment">{record.comment}</p>}
      <p className="am-kb__meta">
        <span className="am-kb__author">{record.actor_label}</span>
        <time dateTime={record.decided_at}>{formatInstant(record.decided_at)}</time>
        <Link className="am-kb__link" href={routes.documentOptimisation(record.project_uid, record.document_uid, record.optimisation_pass_id)}>
          Открыть оптимизацию
        </Link>
      </p>
    </li>
  );
}

/** The header line of the table of rows (`UI-B-34`); the columns are the rows' own, in `knowledge-base.module.css`. */
function Legend() {
  return (
    <div className={styles.legend} aria-hidden="true">
      <span>Находка и решение</span>
      <span>Суть и комментарий</span>
      <span>Кто и когда</span>
    </div>
  );
}

export function KnowledgeBase({ records: findingRecords, entries, isLoading, error, narrowing }: KnowledgeBaseProps) {
  if (isLoading === true) return <LoadingState what="базу знаний" />;
  if (error !== undefined && error !== null) return <ErrorState {...error} />;
  // In «Все» the findings' vocabulary is checked on the finding entries, as in «Замечания».
  const records = entries === undefined
    ? findingRecords
    : entries.flatMap((entry) => (entry.kind === 'finding' && entry.finding !== undefined ? [entry.finding] : []));

  if (records.some(hasInvalidVocabulary)) {
    return (
      <section className="am-kb" data-knowledge-base-fault="closed-vocabulary">
        <ErrorState
          title="Запись решения содержит неизвестное значение."
          detail="Категорию, событие или вердикт нельзя показать достоверно — частичная запись скрыта."
        />
      </section>
    );
  }

  // «Все» is empty only when neither journal has an entry: a page of proposals alone is a page, not «нет решений».
  if (entries !== undefined && entries.length > 0) {
    return (
      <section className="am-kb" data-record-count={entries.length} data-knowledge-base-kind="all">
        <Legend />
        <ol className={`am-kb__records ${styles.records}`}>
          {entries.map((entry) =>
            entry.kind === 'finding' && entry.finding !== undefined ? (
              <FindingRecordItem key={`finding:${entry.finding.decision_id}`} record={entry.finding} kindLabel />
            ) : entry.kind === 'proposal' && entry.proposal !== undefined ? (
              <ProposalRecordItem key={`proposal:${entry.proposal.proposal_decision_id}`} record={entry.proposal} />
            ) : null,
          )}
        </ol>
      </section>
    );
  }

  if (records.length === 0 && narrowing !== undefined) {
    // An empty page under a filter says nothing about the installation: only the whole journal
    // can say that no decision was taken. So the sentence is about the selection, and the way out
    // of it is on the screen.
    return (
      <div data-knowledge-base-empty="narrowed">
        <EmptyState
          title="По выбранному отбору решений нет"
          detail={
            <p>
              Ни одно решение не подходит под выбранный отбор. Его можно снять и посмотреть, что
              есть без него.
            </p>
          }
          action={
            <>
              {narrowing.onResetFilters === undefined ? null : (
                <button type="button" className="am-button am-button--quiet" onClick={narrowing.onResetFilters}>
                  Сбросить категорию и вердикт
                </button>
              )}
              {narrowing.allProjectsHref === undefined ? null : (
                <Link className="am-button am-button--quiet" href={narrowing.allProjectsHref}>
                  Все проекты
                </Link>
              )}
            </>
          }
        />
      </div>
    );
  }

  if (records.length === 0) {
    return (
      <div data-knowledge-base-empty="installation">
        <EmptyState
          title="Решений пока нет"
          detail={
            <p>
              В этой установке ещё не принято ни одного решения по находкам. Первый приём или
              отклонение на экране проверки появится здесь.
            </p>
          }
        />
      </div>
    );
  }

  return (
    <section className="am-kb" data-record-count={records.length}>
      <Legend />
      <ol className={`am-kb__records ${styles.records}`}>
        {records.map((record) => (
          <FindingRecordItem key={record.decision_id} record={record} />
        ))}
      </ol>
    </section>
  );
}
