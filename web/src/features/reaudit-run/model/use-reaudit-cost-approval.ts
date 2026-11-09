'use client';

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import type { RunCostConsent } from '@/shared/api';
import { estimateRunCost, getRunStatus, isTerminalRunState } from '@/shared/api';
import { useIntentKey } from '@/shared/lib';
import { ceilingMicros, microsAsUsd, usableCostEstimate } from '@/shared/ui';

type Approval = { requestKey: string; digest: string; minimum: number; ceiling: string };

/**
 * One fresh reading per queue confirmation, bound to the selected source Run.
 *
 * `RUN-START-ONE-01b` (plan v3 §8), the one-button rule for a repeated Run. The person's act is the click on
 * «Повторный аудит»; the hook reads the source Run and estimates its version, and then there are two cases:
 *
 * - **`unmetered`**: the estimate charges nothing (`billing: unmetered`, which the server prices at 0 and accepts
 *   with `ceiling_micros: 0`). The click is the agreement, so the page sends `consent` as soon as the estimate has
 *   been read, with no panel and no tick-box.
 * - **otherwise**: the page shows ONE dialog with the figure and `ceiling`, and its «Запустить» is the agreement.
 *   The ceiling is typed with `setCeiling`.
 *
 * `consent` is the consent the estimate and the ceiling AS THEY STAND would give: it exists once the estimate is
 * fresh and the ceiling is one the estimate accepts. It is never the agreement by itself; the page decides, from
 * `unmetered` and from the person's press, whether to send it. A reading in flight, a reading that failed and one
 * for another source Run give no estimate and no consent. `refresh` forgets the reading and asks again (after the
 * server said the digest is stale), and the new reading is agreed to on the same terms.
 */
export function useReauditCostApproval(sourceRunId: string | null, requestKey: string | null) {
  const [approval, setApproval] = useState<Approval | null>(null);
  const reading = useQuery({
    queryKey: ['reaudit-cost-estimate', sourceRunId, requestKey],
    enabled: sourceRunId !== null && requestKey !== null,
    staleTime: 0, gcTime: 0, retry: false, refetchOnWindowFocus: false,
    queryFn: async ({ signal }) => {
      if (sourceRunId === null) throw new Error('Повторный прогон не выбран.');
      const run = (await getRunStatus({ path: { run_id: sourceRunId } }, { signal })).data;
      if (run.run_id !== sourceRunId || !isTerminalRunState(run.state)
          || typeof run.version_uid !== 'string' || !/^ver_[0-9A-HJKMNP-TV-Z]{26}$/.test(run.version_uid)) {
        throw new Error('Исходный прогон не соответствует выбранной завершённой задаче.');
      }
      const body = { version_uid: run.version_uid, reaudit_of_run_id: sourceRunId };
      const estimate = (await estimateRunCost({ body }, { signal })).data;
      if (!usableCostEstimate(estimate) || estimate.scope !== 'run' || estimate.version_uid !== run.version_uid
          || estimate.relaxed_limits !== false) {
        throw new Error('Оценка стоимости не соответствует повторному прогону.');
      }
      return { sourceRunId, estimate };
    },
  });
  const read = !reading.isError && !reading.isFetching && reading.data?.sourceRunId === sourceRunId
    ? reading.data.estimate : null;
  const updatedAt = reading.dataUpdatedAt;
  useEffect(() => {
    if (read === null || requestKey === null) return;
    setApproval({ requestKey, digest: read.estimate_digest,
      minimum: Math.max(read.billing === 'metered' ? 1 : 0, read.estimated_cost_micros),
      ceiling: microsAsUsd(read.recommended_ceiling_micros) });
  }, [read, requestKey, updatedAt]);
  // The estimate is offered only together with its ceiling, so the page never draws a figure without the field that
  // goes with it, or sends a ceiling that belongs to the reading before this one.
  const current = approval?.requestKey === requestKey && read !== null && approval.digest === read.estimate_digest
    ? approval : null;
  const estimate = current === null ? null : read;
  const amount = current === null ? null : ceilingMicros(current.ceiling, current.minimum);
  const consent: RunCostConsent | undefined = current !== null && amount !== null
    ? { estimate_digest: current.digest, ceiling_micros: amount, confirmed: true } : undefined;
  const signature = `reaudit:${sourceRunId}:${requestKey}:${current === null || amount === null ? 'awaiting-cost' : `${current.digest}:${amount}`}`;
  const idempotencyKey = useIntentKey(signature);
  return {
    estimate, consent, idempotencyKey, ceiling: current?.ceiling ?? '',
    /** The estimate charges nothing: the click is the agreement, and `consent` can be sent as it stands. */
    unmetered: estimate !== null && estimate.billing === 'unmetered',
    pending: sourceRunId !== null && (reading.isPending || reading.isFetching),
    error: reading.error,
    /** Forget this reading and ask again; the new one is agreed to on the same terms. */
    refresh: () => {
      setApproval(null);
      void reading.refetch();
    },
    setCeiling: (value: string) => setApproval((previous) => previous === null ? null : { ...previous, ceiling: value }),
  };
}
