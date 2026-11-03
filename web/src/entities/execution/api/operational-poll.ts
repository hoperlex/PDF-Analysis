/**
 * The timed refresh of the queue and the journal.
 *
 * The cadence is `OPERATIONAL_LIST_POLLING` in `shared/config`; this module is the one place
 * that connects it to React Query. It is deliberately not a loop: React Query owns the timer,
 * and what it asks this module is "how long until the next read of this query?".
 *
 * The answer depends on how many reads in a row failed. React Query does not keep that
 * number: `fetchFailureCount` restarts at 0 when a read begins and counts retries inside one
 * read. So the streak is kept here, per query, from the two counters that only ever grow -
 * settled successes (`dataUpdateCount`) and settled failures (`errorUpdateCount`) - and is
 * reset by the next success.
 */

import { operationalListInterval } from '@/shared/config';

/** The part of a React Query `Query` this module reads. */
export interface PollableQuery {
  readonly state: {
    readonly dataUpdateCount: number;
    readonly errorUpdateCount: number;
    readonly dataUpdatedAt: number;
    readonly errorUpdatedAt: number;
  };
}

/** What was seen of one query on the previous call. */
export interface FailureLedger {
  readonly dataUpdateCount: number;
  readonly errorUpdateCount: number;
  readonly failures: number;
}

/**
 * The ledger after one more look at the query. Pure, and idempotent for an unchanged state, so
 * it does not matter how often React Query asks.
 *
 * A query seen for the first time with a failed latest read starts at one failure: its earlier
 * history is not known, and one is the least that is true.
 */
export function advanceLedger(previous: FailureLedger | undefined, state: PollableQuery['state']): FailureLedger {
  const { dataUpdateCount, errorUpdateCount } = state;
  if (previous === undefined) {
    return { dataUpdateCount, errorUpdateCount, failures: state.errorUpdatedAt > state.dataUpdatedAt ? 1 : 0 };
  }
  if (dataUpdateCount !== previous.dataUpdateCount) {
    return { dataUpdateCount, errorUpdateCount, failures: 0 };
  }
  return {
    dataUpdateCount,
    errorUpdateCount,
    failures: previous.failures + Math.max(0, errorUpdateCount - previous.errorUpdateCount),
  };
}

const ledgers = new WeakMap<object, FailureLedger>();

/** Reads that failed one after another on this query since its last success. */
export function consecutiveFailures(query: PollableQuery): number {
  const next = advanceLedger(ledgers.get(query), query.state);
  ledgers.set(query, next);
  return next.failures;
}

function tabIsVisible(): boolean {
  return typeof document === 'undefined' || document.visibilityState !== 'hidden';
}

/** The delay before the next timed read of an operational list: the policy applied to its query. */
export function operationalListRefetchInterval(query: PollableQuery): number | false {
  return operationalListInterval({ failures: consecutiveFailures(query), visible: tabIsVisible() });
}

/**
 * The refresh options of an operational list. `refetchIntervalInBackground: false` is the
 * second guard behind the visibility check above: React Query itself skips a due read while
 * the tab is hidden.
 */
export const OPERATIONAL_LIST_POLL = {
  refetchInterval: operationalListRefetchInterval,
  refetchIntervalInBackground: false,
} as const;
