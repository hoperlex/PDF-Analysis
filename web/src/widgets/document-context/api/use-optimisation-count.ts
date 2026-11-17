'use client';

/**
 * The number on the frame's «Оптимизация» tab (`UIP-G-09`): the proposals of the document's latest optimisation pass, and
 * how many of them have no decision in force. `listOptimisationPasses` with the document and `limit=1` answers the newest
 * pass with its counts by decision; no new operation is needed.
 *
 * **The key.** The tab's own pass picker reads the same operation without `limit` under `queryKeys.optimisation.passes`, so
 * this read cannot share that entry (it would file one pass where the picker expects all of them). It files under the
 * prefix every decision, import, carry-over and new pass already invalidates (`queryKeys.optimisation.allPasses`), so the
 * number follows the decisions made on the tab without a rule of its own.
 *
 * **No pass is no number**, never a zero: a document nobody ran an optimisation over has nothing to count, and a read
 * that failed says nothing either (`null`).
 */

import { useQuery } from '@tanstack/react-query';

import type { DocumentUid, OptimisationPassList, ProjectUid } from '@/shared/api';
import { listOptimisationPasses, queryKeys } from '@/shared/api';

import type { OptimisationCount } from '../model/version-tabs';

export function useOptimisationCount(projectUid: string, documentUid: string | undefined): OptimisationCount | null | undefined {
  const query = useQuery<OptimisationPassList>({
    queryKey: [...queryKeys.optimisation.allPasses(), 'tab-count', projectUid, documentUid ?? ''],
    enabled: documentUid !== undefined,
    queryFn: async () =>
      (
        await listOptimisationPasses({
          path: { project_uid: projectUid as ProjectUid },
          query: { document_uid: documentUid as DocumentUid, limit: 1 },
        })
      ).data,
  });
  if (query.isError) return null;
  if (query.data === undefined) return undefined;
  const pass = query.data.items[0];
  return pass === undefined ? null : { proposals: pass.proposal_count, undecided: pass.decision_counts.pending };
}
