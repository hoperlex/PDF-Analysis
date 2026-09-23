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
 * `author_label` is **the login of the reviewer who recorded the event**, derived by the
 * server from the authenticated credential. Wave 41 replaced `OD-12`'s single configured
 * label with it, because three experts producing one indistinguishable voice is precisely
 * what `P04` cannot measure. It still authorizes nothing, and **the UI never sends one** —
 * it only displays what the server recorded, which is the half of `OD-12` that was always
 * the point.
 *
 * The sealed contract's own description of this field still carries the old sentence.
 * Correcting it is a reseal and is registered as `D-86`; this comment is ahead of it
 * deliberately, rather than repeating something that stopped being true.
 *
 * An empty history renders `NotApplicableState`, not `EmptyState`: `shared/ui` names this
 * exact case — a decision history on a finding nobody has judged — as the not-applicable
 * one. The question has not been asked yet, which is different from the answer being none.
 */

import type { DecisionEvent, DecisionEventType } from '@/shared/api';
import type { ErrorStateProps } from '@/shared/ui';
import { ErrorState, LoadingState, NotApplicableState } from '@/shared/ui';
import { formatInstant } from '@/shared/lib';
import { VERDICT_LABELS, orderEvents } from '@/entities/expert-decision';

export interface DecisionHistoryProps {
  readonly events: readonly DecisionEvent[];
  readonly isLoading?: boolean | undefined;
  readonly error?: ErrorStateProps | null | undefined;
}

/**
 * Russian labels. Contract values stay in `data-event-type` and on the decision itself;
 * see `RunStateBadge` for why the owner's ruling does not touch the machine value.
 */
const EVENT_TYPE_LABELS: Readonly<Record<DecisionEventType, string>> = {
  accept: 'приём',
  reject: 'отклонение',
  comment: 'комментарий',
  revoke: 'отзыв',
};

/*
 * The local copy of `VERDICT_LABELS` that stood here is deleted, not merged. Two sessions
 * repaired this widget within the hour; one exported the entity's table and imported it, the
 * other wrote a second table with the same four values. Both render correctly TODAY, and that
 * is exactly the failure this programme keeps finding: a second description maintained by
 * hand with nothing tying it to the first. The entity owns the verdict vocabulary.
 */

export function DecisionHistory({ events, isLoading, error }: DecisionHistoryProps) {
  if (isLoading === true) return <LoadingState what="историю решений" />;
  if (error !== undefined && error !== null) return <ErrorState {...error} />;

  const ordered = orderEvents(events);

  if (ordered.length === 0) {
    return (
      <NotApplicableState
        title="Решений пока нет"
        detail={<p>Эту находку ещё никто не оценивал. Принятие или отклонение создаст первое событие.</p>}
      />
    );
  }

  return (
    <section className="am-history" data-event-count={ordered.length}>
      <h3>История</h3>
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
              <span className="am-history__type">{EVENT_TYPE_LABELS[event.event_type]}</span>
              {/*
                * Two sessions reached this repair independently within the hour, from
                * different directions: one rendering the screens for a UI overview, one
                * teaching the language guard that contract vocabulary is translated. Both
                * replaced the raw `event.verdict`; this keeps `data-verdict` as well, so the
                * machine value has a home at THIS node and not only on the badge beside it.
                */}
              {event.verdict !== null && event.verdict !== undefined ? (
                <span className="am-history__verdict" data-verdict={event.verdict}>
                  {' → '}
                  {VERDICT_LABELS[event.verdict]}
                </span>
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
