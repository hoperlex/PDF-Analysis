'use client';

/** @jsxRuntime automatic */

/**
 * The ledger, oldest first.
 *
 * Every event that was ever appended, in the client-visible order `(recorded_at,
 * decision_id)` that `P02_SEAMS.md` §5.3 fixes. Nothing is collapsed, summarised or hidden
 * behind "show older": the whole point of an append-only ledger is that the reviewer can
 * see that the accept from ten minutes ago is still there under the comment from just now.
 *
 * `author_label` is `OD-12`'s configured local reviewer label. It is a label, not a subject
 * identity, and it authorizes nothing — the UI never sends one, it only displays what the
 * server recorded.
 *
 * An empty history renders `NotApplicableState`, not `EmptyState`: `shared/ui` names this
 * exact case — a decision history on a finding nobody has judged — as the not-applicable
 * one. The question has not been asked yet, which is different from the answer being none.
 */

import type { DecisionEvent } from '@/shared/api';
import type { ErrorStateProps } from '@/shared/ui';
import { ErrorState, LoadingState, NotApplicableState } from '@/shared/ui';
import { formatInstant } from '@/shared/lib';
import { orderEvents } from '@/entities/expert-decision';

export interface DecisionHistoryProps {
  readonly events: readonly DecisionEvent[];
  readonly isLoading?: boolean | undefined;
  readonly error?: ErrorStateProps | null | undefined;
}

export function DecisionHistory({ events, isLoading, error }: DecisionHistoryProps) {
  if (isLoading === true) return <LoadingState what="the decision history" />;
  if (error !== undefined && error !== null) return <ErrorState {...error} />;

  const ordered = orderEvents(events);

  if (ordered.length === 0) {
    return (
      <NotApplicableState
        title="No decisions yet"
        detail={<p>Nobody has judged this finding. Accepting or rejecting appends the first event.</p>}
      />
    );
  }

  return (
    <section className="am-history" data-event-count={ordered.length}>
      <h3>History</h3>
      <ol className="am-history__events">
        {ordered.map((event) => (
          <li
            key={event.decision_id}
            className="am-history__event"
            data-decision-id={event.decision_id}
            data-event-type={event.event_type}
            data-verdict={event.verdict ?? 'none'}
          >
            <p className="am-history__line">
              <span className="am-history__type">{event.event_type}</span>
              {event.verdict !== null && event.verdict !== undefined ? (
                <span className="am-history__verdict"> → {event.verdict}</span>
              ) : null}
              <span className="am-history__at"> {formatInstant(event.recorded_at)}</span>
              <span className="am-history__author"> {event.author_label}</span>
            </p>
            {event.comment !== null && event.comment !== undefined ? (
              <p className="am-history__comment" data-comment={event.comment}>
                {event.comment}
              </p>
            ) : null}
          </li>
        ))}
      </ol>
    </section>
  );
}
