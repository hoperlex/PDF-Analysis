'use client';

/**
 * The review panel's saved reading of a run, for a reader that only looks at it (`RUN-SCREEN-01a`).
 *
 * `ExtendedReview` owns the read and its polling (`getExtendedRunReview`, `extendedReviewPollInterval`). The run screen's rail
 * needs the same reading's `procedures` and live window, and must not read the endpoint a second time or poll on its own: it
 * subscribes to the panel's query entry with `skipToken`, which never fetches, so it sees every reading the panel receives and
 * adds no request. Until the panel has read once the value is `undefined`, and the rail draws what the stage states say.
 */

import { skipToken, useQuery } from '@tanstack/react-query';

import type { ExtendedRunReview } from '@/shared/api';

/** The one key of the panel's entry; the panel fills it, this module only looks. */
export const extendedReviewKey = (runId: string) => ['extended-run-review', runId] as const;

export function useExtendedReviewReading(runId: string): ExtendedRunReview | undefined {
  return useQuery<ExtendedRunReview>({ queryKey: extendedReviewKey(runId), queryFn: skipToken }).data;
}
