/**
 * Which cache entries an appended decision invalidates.
 *
 * `web/docs/PC01_UI_SEAM.md` §6 names all three: appending a decision invalidates the
 * finding's decision history and its detail, **and** the run's finding list, because the
 * verdict projection appears in the list too. Forgetting the third is how a screen shows
 * `accepted` in the detail panel and `pending` in the row behind it.
 *
 * It lives here, next to the ledger, so that both `record-verdict` and `append-comment`
 * invalidate the same set — two features each maintaining their own list is the same
 * divergence one list away.
 *
 * The run key is built with default filters. React Query matches a query key by deep
 * partial equality, so `['runs','findings',id,{}]` matches every filtered finding list of
 * that run rather than only the unfiltered one.
 */

import type { FindingUid, RunId } from '@/shared/api';
import { queryKeys } from '@/shared/api';

/** The keys to invalidate after a decision event is accepted by the server. */
export function decisionCacheKeys(
  findingUid: FindingUid,
  runId: RunId,
): readonly (readonly unknown[])[] {
  return [
    queryKeys.findings.decisions(findingUid),
    queryKeys.findings.detail(findingUid),
    queryKeys.runs.findings(runId),
  ];
}
