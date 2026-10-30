'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';

import type { RunCostEstimate, StartArV3BetaGroupRequest, VersionUid } from '@/shared/api';
import { estimateArV3GroupCost } from '@/shared/api';
import { ceilingMicros, microsAsUsd, usableCostEstimate } from '@/shared/ui';

export type ArV3CostConsent = NonNullable<StartArV3BetaGroupRequest['cost_consent']>;
type Reading = { signature: string; estimate: RunCostEstimate };
type Variables = { signature: string; body: Parameters<typeof estimateArV3GroupCost>[0]['body'] };
type Approval = { signature: string; digest: string; minimum: number; ceiling: string; approved: boolean };

/** Held by the caller's intent so an estimate/approval survives a temporary control unmount. */
export function useArV3CostApproval(versionUid: VersionUid, relaxedLimits: boolean) {
  const signature = `ar-v3-cost:${versionUid}:${relaxedLimits}`;
  const [approval, setApproval] = useState<Approval | null>(null);
  const reading = useMutation<Reading, unknown, Variables>({
    mutationFn: async ({ signature: requestSignature, body }) => {
      const estimate = (await estimateArV3GroupCost({ body })).data;
      if (!usableCostEstimate(estimate) || estimate.scope !== 'ar_v3_group' || estimate.version_uid !== body.version_uid
          || estimate.relaxed_limits !== (body.relaxed_limits === true)) {
        throw new Error('Ответ оценки стоимости не соответствует выбранным параметрам.');
      }
      return { signature: requestSignature, estimate };
    },
  });
  const estimate = reading.data?.signature === signature ? reading.data.estimate : null;
  const current = estimate !== null && approval?.signature === signature && approval.digest === estimate.estimate_digest ? approval : null;
  const ceiling = current?.ceiling ?? '';
  const approved = current?.approved === true;
  const amount = estimate === null ? null : ceilingMicros(ceiling, Math.max(estimate.billing === 'metered' ? 1 : 0, estimate.estimated_cost_micros));
  const draftAmount = approval?.signature === signature ? ceilingMicros(approval.ceiling, approval.minimum) : null;
  const draftConsent: ArV3CostConsent | undefined = draftAmount === null || approval === null ? undefined
    : { estimate_digest: approval.digest, ceiling_micros: draftAmount, confirmed: true };
  const consent: ArV3CostConsent | undefined = estimate !== null && approved && amount !== null
    ? { estimate_digest: estimate.estimate_digest, ceiling_micros: amount, confirmed: true } : undefined;
  const reset = () => { setApproval(null); reading.reset(); };
  return {
    estimate, ceiling, approved, consent, draftConsent, pending: reading.isPending,
    error: reading.variables?.signature === signature ? reading.error : null,
    reset,
    request: () => {
      setApproval((previous) => previous?.signature === signature ? { ...previous, approved: false } : null);
      reading.reset();
      reading.mutate({ signature, body: { version_uid: versionUid, ...(relaxedLimits ? { relaxed_limits: true } : {}) } }, {
        onSuccess: ({ signature: requestSignature, estimate: value }) => setApproval({ signature: requestSignature,
          digest: value.estimate_digest, minimum: Math.max(value.billing === 'metered' ? 1 : 0, value.estimated_cost_micros),
          ceiling: microsAsUsd(value.recommended_ceiling_micros), approved: false }),
      });
    },
    setCeiling: (value: string) => setApproval((previous) => previous === null ? null : { ...previous, ceiling: value, approved: false }),
    setApproved: (value: boolean) => setApproval((previous) => previous === null ? null : { ...previous, approved: value }),
  };
}

export type ArV3CostApproval = ReturnType<typeof useArV3CostApproval>;
