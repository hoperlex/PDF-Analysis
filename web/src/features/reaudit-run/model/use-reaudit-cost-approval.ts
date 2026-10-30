'use client';

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import type { RunCostConsent } from '@/shared/api';
import { estimateRunCost, getRunStatus, isTerminalRunState } from '@/shared/api';
import { useIntentKey } from '@/shared/lib';
import { ceilingMicros, microsAsUsd, usableCostEstimate } from '@/shared/ui';

type Approval = { requestKey: string; digest: string; minimum: number; ceiling: string; approved: boolean };

/** One fresh reading per queue confirmation, bound to the selected source Run. */
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
  const estimate = !reading.isError && !reading.isFetching && reading.data?.sourceRunId === sourceRunId
    ? reading.data.estimate : null;
  const updatedAt = reading.dataUpdatedAt;
  useEffect(() => {
    if (estimate === null || requestKey === null) return;
    setApproval({ requestKey, digest: estimate.estimate_digest,
      minimum: Math.max(estimate.billing === 'metered' ? 1 : 0, estimate.estimated_cost_micros),
      ceiling: microsAsUsd(estimate.recommended_ceiling_micros), approved: false });
  }, [estimate, requestKey, updatedAt]);
  const current = approval?.requestKey === requestKey ? approval : null;
  const amount = current === null ? null : ceilingMicros(current.ceiling, current.minimum);
  const consent: RunCostConsent | undefined = current?.approved === true && estimate !== null
    && current.digest === estimate.estimate_digest && amount !== null
    ? { estimate_digest: current.digest, ceiling_micros: amount, confirmed: true } : undefined;
  const signature = `reaudit:${sourceRunId}:${requestKey}:${current === null || amount === null ? 'awaiting-cost' : `${current.digest}:${amount}`}`;
  const idempotencyKey = useIntentKey(signature);
  return {
    estimate, consent, idempotencyKey, ceiling: current?.ceiling ?? '', approved: current?.approved === true,
    pending: sourceRunId !== null && (reading.isPending || reading.isFetching),
    error: reading.error,
    clear: () => setApproval(null),
    refresh: () => {
      setApproval((previous) => previous === null ? null : { ...previous, approved: false });
      void reading.refetch();
    },
    setCeiling: (value: string) => setApproval((previous) => previous === null ? null : { ...previous, ceiling: value, approved: false }),
    setApproved: (value: boolean) => setApproval((previous) => previous === null ? null : { ...previous, approved: value }),
  };
}
