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
 * Every row is one **event**, not one finding. A finding the reviewer returned to carries
 * two rows, and `decision_event_count` on each says so — which is the fact a knowledge
 * base is read for: that this question has been asked before.
 */

import Link from 'next/link';

import type { DecisionRecord, DecisionEventType, FindingCategory, Verdict } from '@/shared/api';
import type { ErrorStateProps } from '@/shared/ui';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { formatInstant } from '@/shared/lib';
import { VERDICT_LABELS } from '@/entities/expert-decision';

export interface KnowledgeBaseProps {
  readonly records: readonly DecisionRecord[];
  readonly isLoading?: boolean | undefined;
  readonly error?: ErrorStateProps | null | undefined;
}

/**
 * Category headings. The contract value stays in `data-category` on the row, so the
 * machine value has a home and the reviewer reads Russian — the owner's 2026-09-22 ruling,
 * and the same split `RunStateBadge` and `DecisionHistory` already make.
 */
export const CATEGORY_LABELS: Readonly<Record<FindingCategory, string>> = {
  internal_contradiction: 'Внутреннее противоречие',
  explicit_placeholder: 'Явный пропуск',
};

/** Event labels, the same four `DecisionHistory` uses. */
const EVENT_TYPE_LABELS: Readonly<Record<DecisionEventType, string>> = {
  accept: 'приём',
  reject: 'отклонение',
  comment: 'комментарий',
  revoke: 'отзыв',
};

function verdictLabel(verdict: Verdict): string {
  return VERDICT_LABELS[verdict] ?? verdict;
}

export function KnowledgeBase({ records, isLoading, error }: KnowledgeBaseProps) {
  if (isLoading === true) return <LoadingState what="базу знаний" />;
  if (error !== undefined && error !== null) return <ErrorState {...error} />;

  if (records.length === 0) {
    return (
      <EmptyState
        title="Решений пока нет"
        detail={
          <p>
            В этой установке ещё не принято ни одного решения по находкам. Первый приём или
            отклонение на экране проверки появится здесь.
          </p>
        }
      />
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
                {verdictLabel(record.current_verdict)}
              </span>
              <span className="am-kb__event">{EVENT_TYPE_LABELS[record.event_type]}</span>
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
