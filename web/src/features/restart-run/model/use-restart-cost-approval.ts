'use client';

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import type { RestartPoint, RunCostConsent } from '@/shared/api';
import { estimateRunCost, getRunStatus } from '@/shared/api';
import { useIntentKey } from '@/shared/lib';
import { ceilingMicros, microsAsUsd, usableCostEstimate } from '@/shared/ui';

import { computedFrom, restartableRun, takenBefore } from './points';
import { RestartSourceChanged } from './refusals';

type Approval = { requestKey: string; digest: string; minimum: number; ceiling: string; approved: boolean };

const SOURCE_CHANGED = 'Состояние прогона изменилось: перезапустить его уже нельзя.';
const ESTIMATE_MISMATCH = 'Оценка стоимости не соответствует перезапуску с выбранного этапа.';

/**
 * One fresh reading per chosen chip, bound to the source run and the restart point (`RUN-RESTART-01`): the price is for the chips the
 * new run computes and its digest names the source and the chip, so a consent read for another chip, for a start from a stage or for a
 * re-audit is not this one. The server refuses a chip whose output it cannot take here, before any consent is asked for.
 *
 * The source is read once before the price, as the re-audit and the start from a stage read theirs: the version the price is for, and
 * the state it must still be in. A one-shot read, no schedule.
 */
export function useRestartCostApproval(sourceRunId: string | null, point: RestartPoint | null, requestKey: string | null) {
  const [approval, setApproval] = useState<Approval | null>(null);
  const wanted = sourceRunId !== null && point !== null && requestKey !== null;
  const reading = useQuery({
    queryKey: ['restart-run-cost-estimate', sourceRunId, point, requestKey],
    enabled: wanted,
    staleTime: 0, gcTime: 0, retry: false, refetchOnWindowFocus: false,
    queryFn: async ({ signal }) => {
      if (sourceRunId === null || point === null) throw new Error('Этап для перезапуска не выбран.');
      const run = (await getRunStatus({ path: { run_id: sourceRunId } }, { signal })).data;
      if (run.run_id !== sourceRunId || !restartableRun(run)
          || typeof run.version_uid !== 'string' || !/^ver_[0-9A-HJKMNP-TV-Z]{26}$/.test(run.version_uid)) {
        throw new RestartSourceChanged(SOURCE_CHANGED);
      }
      const body = { version_uid: run.version_uid, start_from_run_id: sourceRunId, restart_point: point };
      const estimate = (await estimateRunCost({ body }, { signal })).data;
      if (!usableCostEstimate(estimate) || estimate.version_uid !== run.version_uid
          || estimate.relaxed_limits !== false || estimate.start_from_run_id !== sourceRunId
          || estimate.restart_point !== point) {
        throw new RestartSourceChanged(ESTIMATE_MISMATCH);
      }
      return { sourceRunId, point, estimate };
    },
  });
  const estimate = !reading.isError && !reading.isFetching && reading.data?.sourceRunId === sourceRunId
    && reading.data?.point === point ? reading.data.estimate : null;
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
  const signature = `restart-run:${sourceRunId}:${point}:${requestKey}:${current === null || amount === null ? 'awaiting-cost' : `${current.digest}:${amount}`}`;
  const idempotencyKey = useIntentKey(signature);
  return {
    estimate,
    /** The chips the new run takes from the source, as the server's estimate says (the contract's own rule where it names none). */
    taken: estimate === null || point === null ? null : (estimate.reused_restart_points ?? takenBefore(point)),
    /** The chips the new run computes. */
    computed: estimate === null || point === null ? null : (estimate.computed_restart_points ?? computedFrom(point)),
    consent, idempotencyKey, ceiling: current?.ceiling ?? '', approved: current?.approved === true,
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
