'use client';

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import type { RunCostConsent, StageId } from '@/shared/api';
import { estimateRunCost, getRunStatus, isTerminalRunState } from '@/shared/api';
import { useIntentKey } from '@/shared/lib';
import { ceilingMicros, microsAsUsd, usableCostEstimate } from '@/shared/ui';

type Approval = { requestKey: string; digest: string; minimum: number; ceiling: string; approved: boolean };

/**
 * One fresh reading per chosen stage, bound to the source run and the stage (`R-151i`): the price is for the stages the new
 * run computes and its digest names the source and the stage, so a consent read for another stage or for a re-audit is not
 * this one. The server refuses a stage whose output it cannot take here, before any consent is asked for.
 */
export function useStartFromStageCostApproval(sourceRunId: string | null, stageId: StageId | null, requestKey: string | null) {
  const [approval, setApproval] = useState<Approval | null>(null);
  const wanted = sourceRunId !== null && stageId !== null && requestKey !== null;
  const reading = useQuery({
    queryKey: ['start-from-stage-cost-estimate', sourceRunId, stageId, requestKey],
    enabled: wanted,
    staleTime: 0, gcTime: 0, retry: false, refetchOnWindowFocus: false,
    queryFn: async ({ signal }) => {
      if (sourceRunId === null || stageId === null) throw new Error('Этап для запуска не выбран.');
      const run = (await getRunStatus({ path: { run_id: sourceRunId } }, { signal })).data;
      if (run.run_id !== sourceRunId || !isTerminalRunState(run.state)
          || typeof run.version_uid !== 'string' || !/^ver_[0-9A-HJKMNP-TV-Z]{26}$/.test(run.version_uid)) {
        throw new Error('Исходный прогон не соответствует выбранному завершённому прогону.');
      }
      const body = { version_uid: run.version_uid, start_from_run_id: sourceRunId, start_stage_id: stageId };
      const estimate = (await estimateRunCost({ body }, { signal })).data;
      if (!usableCostEstimate(estimate) || estimate.scope !== 'run' || estimate.version_uid !== run.version_uid
          || estimate.relaxed_limits !== false || estimate.start_from_run_id !== sourceRunId
          || estimate.start_stage_id !== stageId) {
        throw new Error('Оценка стоимости не соответствует запуску с выбранного этапа.');
      }
      return { sourceRunId, stageId, estimate };
    },
  });
  const estimate = !reading.isError && !reading.isFetching && reading.data?.sourceRunId === sourceRunId
    && reading.data?.stageId === stageId ? reading.data.estimate : null;
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
  const signature = `start-from-stage:${sourceRunId}:${stageId}:${requestKey}:${current === null || amount === null ? 'awaiting-cost' : `${current.digest}:${amount}`}`;
  const idempotencyKey = useIntentKey(signature);
  return {
    estimate, consent, idempotencyKey, ceiling: current?.ceiling ?? '', approved: current?.approved === true,
    pending: wanted && (reading.isPending || reading.isFetching),
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
