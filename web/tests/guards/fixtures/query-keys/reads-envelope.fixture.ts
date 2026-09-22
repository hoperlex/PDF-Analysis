/**
 * `D-57`'s read half, character for character: `runQuery.data?.data`.
 *
 * `getQueryData<RunStatus>(key)` used to make this pair of lines an assertion rather than
 * a check, so reading `.data` off a `RunStatus` was a silent `undefined` at render time.
 * `tsc` must reject it now.
 */

import type { QueryClient } from '@tanstack/react-query';

import type { RunId, RunStatus } from '@/shared/api';
import { queryKeys } from '@/shared/api';

declare const client: QueryClient;
declare const runId: RunId;

export function readsAnEnvelope(): RunStatus | undefined {
  const entry = client.getQueryData(queryKeys.runs.detail(runId));
  return entry?.data;
}
