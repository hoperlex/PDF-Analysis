import type { RunCostEstimate, RunCostEstimateRequest } from '@/shared/api';

export const APPROVE_COST = 'Подтверждаю оценку и лимит для выбранных параметров';
export const COST_CONSENT = { estimate_digest: 'a'.repeat(64), ceiling_micros: 1_500_000, confirmed: true };

export function costEstimate(body: RunCostEstimateRequest): RunCostEstimate {
  return { estimate_digest: COST_CONSENT.estimate_digest, scope: 'run', version_uid: body.version_uid,
    provider_mode: 'recorded', billing: 'metered', model_id: 'fixture-model', currency: 'USD',
    text_characters: 3000, page_count: 2, windows: 1, calls: 1,
    input_tokens: 2000, output_tokens: body.relaxed_limits ? 64000 : 16000,
    estimated_cost_micros: 1_200_000, recommended_ceiling_micros: COST_CONSENT.ceiling_micros,
    relaxed_limits: body.relaxed_limits === true };
}
