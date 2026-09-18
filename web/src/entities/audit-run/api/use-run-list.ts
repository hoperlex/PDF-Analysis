'use client';

/**
 * The runs of one published version — `listRuns`, on mount.
 *
 * **This does not poll and must not.** `useRunStatus` is the one polling loop in this
 * application, and it reads one run. A list that polled would be a second cadence for the
 * same question. It would also be a loop with nothing to wait for: `D-20` records that
 * `execute_run` is inline, so a run is already terminal when `startRun` answers and no
 * client can observe a `running` one. A screen that waited for `running` here would wait
 * forever, and this one does not wait.
 *
 * Each item is the whole `RunStatus`, byte-identical to what `getRunStatus` answers for
 * that run — `W18-SEAL` asserts that equality server-side — so the list rows and the run
 * screen cannot disagree about a run's state.
 */

import { useQuery } from '@tanstack/react-query';

import type { RunStatusPage, VersionUid } from '@/shared/api';
import { listRuns, queryKeys } from '@/shared/api';

/** Page size. */
export const RUN_PAGE_LIMIT = 50;

export function useRunList(versionUid: VersionUid, cursor?: string) {
  return useQuery<RunStatusPage>({
    queryKey: queryKeys.runs.list(versionUid, cursor, RUN_PAGE_LIMIT),
    queryFn: async () => {
      const response = await listRuns({
        path: { version_uid: versionUid },
        query: { ...(cursor === undefined ? {} : { cursor }), limit: RUN_PAGE_LIMIT },
      });
      return response.data;
    },
  });
}
