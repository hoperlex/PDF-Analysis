/**
 * `UI-A-73`: «↩ Перенесено из V2» -- the mark of a decision that an expert carried over from an earlier version's
 * finding (the original's wording on a finding whose verdict was carried), or `null` for a decision made directly.
 *
 * The argument is the contract's `DecisionCarriedFrom` (a finding decision's source: `DecisionEvent.carried_from`,
 * `DecisionRecord.carried_from`, `Finding.current_verdict_carried_from`) or `ProposalDecisionCarriedFrom` (an
 * optimisation proposal's: `ProposalDecision.carried_from`, `AcceptedOptimisationProposal.carried_from`); both name the
 * source's version by its display ordinal, which is shown and never used as an identity. Absent and `null` say the same
 * thing -- the decision was made directly -- so the mark is simply not drawn.
 */
export function carriedFromMark(
  carriedFrom: { readonly version_ordinal: number } | null | undefined,
): string | null {
  return carriedFrom === null || carriedFrom === undefined ? null : `↩ Перенесено из V${carriedFrom.version_ordinal}`;
}
