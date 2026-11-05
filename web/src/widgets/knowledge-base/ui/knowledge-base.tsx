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

import type { DecisionRecord, DecisionEventType } from '@/shared/api';
import {
  DECISION_EVENT_TYPE_VALUES,
  FINDING_CATEGORY_VALUES,
  VERDICT_VALUES,
} from '@/shared/api';
import type { ErrorStateProps } from '@/shared/ui';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { formatInstant } from '@/shared/lib';
import { CATEGORY_LABELS, VERDICT_LABELS } from '@/entities/expert-decision';
import { SeverityBadge } from '@/entities/finding';
import { findProjectSection, projectSectionTitle } from '@/entities/project';

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

export function KnowledgeBase({ records, isLoading, error, narrowing }: KnowledgeBaseProps) {
  if (isLoading === true) return <LoadingState what="базу знаний" />;
  if (error !== undefined && error !== null) return <ErrorState {...error} />;

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
      <ol className="am-kb__records">
        {records.map((record) => (
          <li
            key={record.decision_id}
            className="am-kb__record"
            data-decision-id={record.decision_id}
            data-finding-uid={record.finding_uid}
            data-category={record.category}
            data-event-type={record.event_type}
            data-current-verdict={record.current_verdict}
            data-verdict={record.verdict ?? 'none'}
          >
            <p className="am-kb__heading">
              <span className="am-kb__category">{CATEGORY_LABELS[record.category]}</span>
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
               * `project_uid` and `run_id`, both identities the record carries, and never
               * from a display number or a path the server did not send.
               */}
              <Link
                className="am-kb__link"
                href={`/projects/${record.project_uid}/runs/${record.run_id}/review`}
              >
                Открыть прогон
              </Link>
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
