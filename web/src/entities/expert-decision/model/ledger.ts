/**
 * The decision ledger, client side: append-only, and projected exactly as the server
 * projects it.
 *
 * `P02_SEAMS.md` §5.3 and §5.4 are the rule. Every event is a new `decision_id`; nothing
 * is ever updated and nothing is ever removed. The current verdict is a **projection** of
 * the event list, not a field somebody edits — which is why appending a comment after a
 * verdict cannot overwrite that verdict: a comment carries `verdict: null`, so the most
 * recent verdict-bearing event is still the accept or the reject that came before it.
 *
 * `PD-01`: a revocation moves the projection to `pending` and never restores an earlier
 * superseded verdict. That falls out of the same rule rather than being a special case —
 * `revoke` carries `verdict: 'pending'`, so it *is* the most recent verdict-bearing event
 * and the projection reads `pending`. There is no stack to pop and no history to rewind.
 *
 * The server owns this projection (`finding_current_verdict` is the single definition, and
 * §5.4 says `B4`, `B5` and `B6` all read it and none recomputes it). This module is the
 * client's optimistic echo of it, used to render a history the user just appended to
 * before the refetch lands, and to prove in a test that appending never overwrites. Where
 * the server's projection and this one are both available, the server's wins — see
 * `reconcile` below.
 */

import type { DecisionEvent, DecisionId, Verdict } from '@/shared/api';

/** The projection of §5.4, with the same column names the seam document uses. */
export interface VerdictProjection {
  readonly current_verdict: Verdict;
  /** The verdict-bearing event's identity, or null when nothing has judged this finding. */
  readonly latest_verdict_decision_id: DecisionId | null;
  /** The comment of the most recent event carrying one, whatever its event type. */
  readonly latest_comment: string | null;
  /** The most recent event of **any** type. */
  readonly latest_decision_id: DecisionId | null;
  /** That event's `recorded_at` — so appending a comment moves it. */
  readonly decision_recorded_at: string | null;
  readonly decision_event_count: number;
}

/**
 * Client-visible total order: `(recorded_at, decision_id)`.
 *
 * §5.3 fixes this and notes it is stable across pages. The server's `sequence_no` is never
 * returned, so `decision_id` is the tiebreaker for two events recorded in the same
 * transaction. Sorting is by string comparison on both, which is correct for RFC 3339
 * instants in a fixed offset and for the ULID suffix of a `dec_` identity.
 */
export function compareEvents(left: DecisionEvent, right: DecisionEvent): number {
  if (left.recorded_at < right.recorded_at) return -1;
  if (left.recorded_at > right.recorded_at) return 1;
  if (left.decision_id < right.decision_id) return -1;
  if (left.decision_id > right.decision_id) return 1;
  return 0;
}

/** The events in client-visible order, oldest first. Never mutates the input. */
export function orderEvents(events: readonly DecisionEvent[]): readonly DecisionEvent[] {
  return [...events].sort(compareEvents);
}

/**
 * True when this event carries a verdict.
 *
 * `accept` carries `accepted`, `reject` carries `rejected`, `revoke` carries `pending`,
 * and `comment` carries `null`. The test is on the `verdict` field rather than on
 * `event_type`, because the field is what §5.4's projection reads and because a future
 * event type would then need no change here.
 */
export function isVerdictBearing(event: DecisionEvent): boolean {
  return event.verdict !== null && event.verdict !== undefined;
}

/**
 * Project the event list onto the current-verdict view.
 *
 * `pending` when the ledger holds no verdict-bearing event — the same default the server
 * uses, and the reason a finding nobody has judged reads `pending` rather than blank.
 */
export function projectVerdict(events: readonly DecisionEvent[]): VerdictProjection {
  const ordered = orderEvents(events);

  let currentVerdict: Verdict = 'pending';
  let latestVerdictDecisionId: DecisionId | null = null;
  let latestComment: string | null = null;

  // Oldest first, so the last assignment wins and "most recent" needs no comparison.
  for (const event of ordered) {
    if (isVerdictBearing(event)) {
      currentVerdict = event.verdict as Verdict;
      latestVerdictDecisionId = event.decision_id;
    }
    // "Carrying one" is `comment IS NOT NULL`, matching the server view. An empty string
    // is not filtered out here: doing so would make this projection disagree with
    // `finding_current_verdict`, and the append-comment feature already refuses to send
    // one, so a blank can only arrive from the server having stored a blank.
    if (event.comment !== null && event.comment !== undefined) {
      latestComment = event.comment;
    }
  }

  const newest = ordered.length === 0 ? null : (ordered[ordered.length - 1] as DecisionEvent);

  return {
    current_verdict: currentVerdict,
    latest_verdict_decision_id: latestVerdictDecisionId,
    latest_comment: latestComment,
    latest_decision_id: newest === null ? null : newest.decision_id,
    decision_recorded_at: newest === null ? null : newest.recorded_at,
    decision_event_count: ordered.length,
  };
}

/**
 * Append one event, returning a new list. The input is never mutated and never rewritten.
 *
 * Re-appending an event already in the list is a no-op rather than a duplicate row: the
 * same `decision_id` is the same event, which is what makes replaying an idempotent write's
 * response safe. This is the only case in which the returned list is not longer.
 */
export function appendEvent(
  events: readonly DecisionEvent[],
  event: DecisionEvent,
): readonly DecisionEvent[] {
  if (events.some((existing) => existing.decision_id === event.decision_id)) {
    return orderEvents(events);
  }
  return orderEvents([...events, event]);
}

/**
 * The server's projection wins where it exists.
 *
 * `AppendDecisionResponse` carries the server's `current_verdict` alongside the new event.
 * When we have it, we render it: the server holds the single definition, and a client that
 * preferred its own recomputation would be a second source of truth — exactly what the
 * seam's "no global domain store" rule exists to prevent. The recomputed projection fills
 * in only the fields that response does not carry.
 */
export function reconcile(
  events: readonly DecisionEvent[],
  serverVerdict: Verdict | undefined,
): VerdictProjection {
  const projected = projectVerdict(events);
  if (serverVerdict === undefined) return projected;
  return { ...projected, current_verdict: serverVerdict };
}
