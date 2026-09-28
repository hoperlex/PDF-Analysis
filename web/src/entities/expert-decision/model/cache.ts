/**
 * Which cache entries an appended decision invalidates.
 *
 * `web/docs/PC01_UI_SEAM.md` §6 names three: appending a decision invalidates the
 * finding's decision history and its detail, **and** the run's finding list, because the
 * verdict projection appears in the list too. Forgetting one is how a screen shows
 * `accepted` in the detail panel and `pending` in the row behind it.
 *
 * `W38-KB` adds the fourth, and it is the same rule one screen further out: the knowledge
 * base is the journal of every decision, so the event just appended belongs at the top of
 * it. A reviewer who accepts a finding and then opens the knowledge base without seeing
 * their own decision has no way to tell a stale cache from a lost write.
 *
 * `W46-WIRE` adds the fifth: the dashboard's one read counts findings by verdict over the
 * whole deployment, including a finding nobody has judged as `pending` — an accept or a
 * reject moves a finding out of that count the moment the server accepts it, so the
 * summary is invalidated alongside the journal it is built from the same rule the journal
 * itself already gets.
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
    /*
     * The knowledge base, which is the journal of every decision this deployment has
     * taken — so an accept recorded on the review screen changes it too. Built with the
     * default filters, for the reason the run key is: a partial key matches every
     * filtered page of the journal rather than only the unfiltered one.
     */
    queryKeys.findings.journal(),
    // The dashboard's one read. See this function's own header.
    queryKeys.dashboard.summary(),
  ];
}
