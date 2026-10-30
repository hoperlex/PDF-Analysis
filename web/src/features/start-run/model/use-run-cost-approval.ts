'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';

import type { RunCostEstimate } from '@/shared/api';
import { estimateRunCost } from '@/shared/api';
import { ceilingMicros, microsAsUsd, usableCostEstimate } from '@/shared/ui';

import type { RunCostConsent, StartRunIntent } from './start-run-intent';
import { startRunBody } from './start-run-intent';

type EstimateVariables = { signature: string; body: Parameters<typeof estimateRunCost>[0]['body'] };
type Reading = { signature: string; estimate: RunCostEstimate };
type Approval = { signature: string; digest: string; minimum: number; ceiling: string; approved: boolean };

export function useRunCostApproval(intent: StartRunIntent) {
  const [approval, setApproval] = useState<Approval | null>(null);
  const reading = useMutation<Reading, unknown, EstimateVariables>({
    mutationFn: async ({ signature, body }) => {
      const estimate = (await estimateRunCost({ body })).data;
      if (!usableCostEstimate(estimate) || estimate.scope !== 'run' || estimate.version_uid !== body.version_uid
          || estimate.relaxed_limits !== (body.relaxed_limits === true)) {
        throw new Error('Ответ оценки стоимости не соответствует выбранным параметрам.');
      }
      return { signature, estimate };
    },
  });
  const estimate = reading.data?.signature === intent.signature ? reading.data.estimate : null;
  const current = estimate !== null && approval?.signature === intent.signature && approval.digest === estimate.estimate_digest ? approval : null;
  const ceiling = current?.ceiling ?? '';
  const approved = current?.approved === true;
  const amount = estimate === null ? null : ceilingMicros(ceiling, estimate.estimated_cost_micros);
  const draftAmount = approval?.signature === intent.signature ? ceilingMicros(approval.ceiling, approval.minimum) : null;
  const draftConsent: RunCostConsent | undefined = draftAmount === null || approval === null ? undefined
    : { estimate_digest: approval.digest, ceiling_micros: draftAmount, confirmed: true };
  const consent: RunCostConsent | undefined = estimate !== null && approved && amount !== null
    ? { estimate_digest: estimate.estimate_digest, ceiling_micros: amount, confirmed: true } : undefined;
  const reset = () => { setApproval(null); reading.reset(); };
  return {
    estimate, ceiling, approved, consent, draftConsent, pending: reading.isPending,
    error: reading.variables?.signature === intent.signature ? reading.error : null,
    reset,
    request: () => {
      // Re-reading the same payload clears agreement, while its retry key survives.
      setApproval((previous) => previous?.signature === intent.signature ? { ...previous, approved: false } : null);
      reading.reset();
      reading.mutate({ signature: intent.signature, body: startRunBody(intent.command('estimate-only')) }, {
        onSuccess: ({ signature, estimate: value }) => setApproval({ signature, digest: value.estimate_digest,
          minimum: value.estimated_cost_micros, ceiling: microsAsUsd(value.recommended_ceiling_micros), approved: false }),
      });
    },
    setCeiling: (value: string) => setApproval((previous) => previous === null ? null : { ...previous, ceiling: value, approved: false }),
    setApproved: (value: boolean) => setApproval((previous) => previous === null ? null : { ...previous, approved: value }),
  };
}
