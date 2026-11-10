/**
 * Fixtures of the readiness line (`READINESS-WEB-01`): what `getRunStartReadiness` answers for one version, in the shapes the
 * line, the blocked state, the plan window and the cost dialog read. Every string is Cyrillic, an identifier or a contract value,
 * so the language guard can render them.
 */

import type { RunCostEstimate, RunStartReadiness, RunStartReadinessCell } from '@/shared/api';

export const DIGEST = 'e'.repeat(64);

export function readinessCell(
  row: RunStartReadinessCell['row'],
  model: string,
  over: Partial<RunStartReadinessCell> = {},
): RunStartReadinessCell {
  const role = over.role ?? 'main';
  return { cell_key: `${row}:${role}`, row, role, model_id: model, effort: 'medium', available: true, access: 'subscription', reasons: [], ...over };
}

/** A cell no server can serve: it names itself, has no access and says why. */
export function missingCell(row: RunStartReadinessCell['row'], model: string, role: RunStartReadinessCell['role'] = 'main'): RunStartReadinessCell {
  const cell = readinessCell(row, model, { role, available: false, reasons: ['not_on_any_server'] });
  delete cell.access;
  return cell;
}

/** The cells of an analysis of the second version: text, blocks, cross-check and norms (the critic and the refinement are the third's). */
export const CLAUDE_CELLS: readonly RunStartReadinessCell[] = [
  readinessCell('text', 'claude-sonnet-5-5'),
  readinessCell('blocks', 'claude-opus-5-5'),
  readinessCell('cross_check', 'claude-sonnet-5-5'),
  readinessCell('norms', 'claude-sonnet-5-5'),
];

/** The layout is on and every cell is on a subscription: the estimate is 0 and the press of the button is the consent. */
export function readiness(over: Partial<RunStartReadiness> = {}): RunStartReadiness {
  return {
    route: 'stage_plan', ready: true, kit: 'claude_only', access: 'subscription', cells: [...CLAUDE_CELLS],
    estimate_digest: DIGEST, estimated_cost_micros: 0, recommended_ceiling_micros: 0, stage_plan_digest: DIGEST, ...over,
  };
}

/** One cell is paid by an API key: the total is `mixed`, and the start asks once. */
export const READINESS_MIXED: RunStartReadiness = readiness({
  access: 'mixed',
  cells: [...CLAUDE_CELLS.slice(0, 3), readinessCell('norms', 'claude-sonnet-5-5', { access: 'api' })],
  estimated_cost_micros: 1_200_000,
  recommended_ceiling_micros: 1_500_000,
});

/** Every cell is paid by an API key. */
export const READINESS_API: RunStartReadiness = readiness({
  access: 'api', cells: CLAUDE_CELLS.map((cell) => ({ ...cell, access: 'api' as const })), estimated_cost_micros: 2_000_000, recommended_ceiling_micros: 2_500_000,
});

/** The blocks row names a model no server has, so the start is not possible and the answer carries no total access. */
export function blockedReadiness(): RunStartReadiness {
  const blocked = readiness({
    ready: false,
    cells: [readinessCell('text', 'claude-sonnet-5-5'), missingCell('blocks', 'claude-opus-5-5'), readinessCell('cross_check', 'claude-sonnet-5-5')],
  });
  delete blocked.access;
  delete blocked.estimate_digest;
  return blocked;
}

/** The layout is off: the route is the automatic one as before and the answer holds no cell. */
export const READINESS_LEGACY: RunStartReadiness = { route: 'legacy', ready: true, cells: [] };

/** The blocks row as an ensemble scheme, in the wrong order on purpose: the legs are read before the judge. */
export const ENSEMBLE_CELLS: readonly RunStartReadinessCell[] = [
  readinessCell('text', 'claude-sonnet-5-5'),
  readinessCell('blocks', 'claude-sonnet-5-5', { role: 'judge' }),
  readinessCell('blocks', 'claude-opus-5-5', { role: 'leg1', effort: 'high' }),
  readinessCell('blocks', 'gpt-6-astra', { role: 'leg2' }),
];

/** The lines of an estimate that names its models (consent v2): one is on a subscription and one is billed. */
export function modelLines(): NonNullable<RunCostEstimate['models']> {
  return [
    { model_id: 'claude-opus-5-5', access: 'subscription', calls: 6, input_tokens: 1000, output_tokens: 200, estimated_cost_micros: 0, rate_sha256: 'a'.repeat(64) },
    { model_id: 'claude-sonnet-5-5', access: 'api', calls: 4, input_tokens: 1000, output_tokens: 200, estimated_cost_micros: 1_200_000, rate_sha256: 'b'.repeat(64) },
  ];
}
