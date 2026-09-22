/**
 * The one way to fill `queryKeys.runs.detail(runId)` from a query.
 *
 * `D-57`: that key is read by two screens and written by four sites, and for as long as
 * each site chose its own shape the key held a `RunStatus` for one screen and a
 * `{ data: RunStatus }` envelope for another. The key now carries its value type
 * (`DataTag`, see `shared/api/query-keys.ts`), which makes `setQueryData` and
 * `getQueryData` the compiler's business.
 *
 * `useQuery` is the hole the type system does not close in `@tanstack/react-query`
 * 5.102.8: it infers the value from the `queryFn` and ignores the tag. So the `queryFn`
 * lives here, once, beside the key it fills, and its return type is stated rather than
 * inferred — `Promise<RunStatus>`, not `Promise<ApiResponse<RunStatus>>`. The unwrap
 * happens at the transport boundary, where the envelope stops being interesting.
 *
 * `web/tests/guards/query-key-shape.guard.test.ts` holds the other half: no site outside
 * this entity may pass `queryKeys.runs.detail(...)` as a `queryKey`.
 */

import type { RunId, RunStatus } from '@/shared/api';
import { getRunStatus, queryKeys } from '@/shared/api';

/** Options for one run's status, ready for `useQuery`, `fetchQuery` or `prefetchQuery`. */
export function runStatusQueryOptions(runId: RunId) {
  return {
    queryKey: queryKeys.runs.detail(runId),
    queryFn: async ({ signal }: { signal: AbortSignal }): Promise<RunStatus> => {
      const response = await getRunStatus({ path: { run_id: runId } }, { signal });
      return response.data;
    },
  };
}
