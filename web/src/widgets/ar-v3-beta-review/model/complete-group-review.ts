import type { ArV3BetaGroupReview, ArV3RunGroupId } from '@/shared/api';

const SCOPES = ['F1', 'F2', 'A1', 'A2', 'S1', 'S2'] as const;
const REVIEW_STATES: ReadonlySet<string> = new Set([
  'pending', 'failed', 'verification_refused', 'available',
]);

/** Reject a mixed-group, partial or contradictory answer before displaying evidence. */
export function completeArV3GroupReview(
  review: ArV3BetaGroupReview,
  requestedGroupId: ArV3RunGroupId,
): boolean {
  if (!review || review.group_id !== requestedGroupId || !Array.isArray(review.members)
    || review.members.length !== SCOPES.length) return false;
  if (review.members.some((member) => !member || typeof member !== 'object')) return false;
  if (new Set(review.members.map((member) => member.run_id)).size !== SCOPES.length) return false;
  return review.members.every((member, index) =>
    member.scope_id === SCOPES[index]
    && REVIEW_STATES.has(member.review_state)
    && (member.review_state === 'available'
      ? member.review !== null
        && Array.isArray(member.review.topics)
        && Array.isArray(member.review.provisional_citations)
      : member.review === null),
  );
}
