'use client';

/**
 * The reading behind the line under «Запустить» (`READINESS-WEB-01`, plan 2026-11-09 §8): `getRunStartReadiness` for one version,
 * with the same body as the estimate (`estimateRequest`), so the readiness and the start are about the same run.
 *
 * It writes nothing and calls no model. It is filed under `execution`, so a command on a server (which can change which cells have a
 * server and how they are paid) refreshes it, and it is read again on tab return. A start the server sends back because the access
 * changed (`cost_estimate_binding_changed`) invalidates it too (`./use-run-cost-approval.ts`).
 *
 * **Four readings, none of them an error screen.** `loading` (nothing is said yet), `ready` (the answer), `unavailable` (the typed
 * 503 of a server that has no layout port, or the refusal of a comparison PDF: the line stays «Маршрут: автоматически», as it was) and `failed` (any other refusal: said
 * in a line, and the button stays, because the start asks the server again and the server decides). A refusal is not hidden behind the
 * old line: that would say a route the server did not.
 */

import { useQuery } from '@tanstack/react-query';

import type { RunStartReadiness, VersionUid } from '@/shared/api';
import { getRunStartReadiness, queryKeys } from '@/shared/api';

import { comparisonOnlyRefusal, estimateRequest } from './one-click-start';
import { layoutNotAvailable } from './readiness';

export const runStartReadinessKey = (versionUid: VersionUid): readonly unknown[] =>
  [...queryKeys.execution.all(), 'start-readiness', versionUid];

export type RunStartReadinessReading =
  | { readonly state: 'loading' }
  | { readonly state: 'ready'; readonly readiness: RunStartReadiness }
  | { readonly state: 'unavailable' }
  | { readonly state: 'failed'; readonly error: unknown; readonly retry: () => void };

/** `enabled` is false for an account that is not offered the start at all: the read is refused to it and is not sent. */
export function useRunStartReadiness(versionUid: VersionUid, enabled = true): RunStartReadinessReading {
  const query = useQuery<RunStartReadiness>({
    queryKey: runStartReadinessKey(versionUid),
    queryFn: async () => (await getRunStartReadiness({ body: estimateRequest(versionUid, false) })).data,
    refetchOnWindowFocus: 'always',
    staleTime: 0,
    // A line, not a screen: no retries before it says what it knows (the answer to a 503 is the old line, at once).
    retry: false,
    enabled,
  });
  if (query.data !== undefined) return { state: 'ready', readiness: query.data };
  if (query.isError) {
    // Neither answer has a line to add: the 503 says the server has no layout, and a comparison PDF is not analysed as a section
    // (the page already says so beside the control). The control's own words stand.
    if (layoutNotAvailable(query.error) || comparisonOnlyRefusal(query.error)) return { state: 'unavailable' };
    return { state: 'failed', error: query.error, retry: () => void query.refetch() };
  }
  return { state: 'loading' };
}
