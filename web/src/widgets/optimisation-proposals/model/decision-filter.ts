/**
 * `D-372`: which decision a pass's proposals are filtered by, and where that choice lives.
 *
 * The filter is the strip's «Все» and one button per decision state (`DecisionFilter`). It was component state, so a saved link, a reload
 * and Back/Forward lost it (`UI-PARITY-01`, completion scenario 5); it is in the address now (`?decision=accept`), like the layout beside it
 * and like the filters of «База знаний». «Все» is the absent parameter. It is a view and not a place, so choosing it REPLACES the history
 * entry.
 *
 * Pure: a query string in, a query string out. A value outside the closed set is read as «Все» and is never echoed; a parameter that is not
 * this one (`tab`, `pass`, `layout`) is carried through a write untouched.
 */

import type { ProposalDecisionState } from '@/shared/api';
import { DECISION_STATES } from '@/entities/optimisation-proposal';

export const PROPOSAL_DECISION_PARAM = 'decision';

type Params = Pick<URLSearchParams, 'get' | 'toString'>;

function isDecisionState(value: unknown): value is ProposalDecisionState {
  return typeof value === 'string' && (DECISION_STATES as readonly string[]).includes(value);
}

/** The decision the address filters by, or `null` for «Все». */
export function readProposalDecision(params: Params): ProposalDecisionState | null {
  const value = params.get(PROPOSAL_DECISION_PARAM);
  return isDecisionState(value) ? value : null;
}

/** The query after the reader chooses; «Все» is the absent parameter. */
export function writeProposalDecision(params: Params, next: ProposalDecisionState | null): URLSearchParams {
  const written = new URLSearchParams(params.toString());
  if (next === null) written.delete(PROPOSAL_DECISION_PARAM);
  else written.set(PROPOSAL_DECISION_PARAM, next);
  return written;
}
