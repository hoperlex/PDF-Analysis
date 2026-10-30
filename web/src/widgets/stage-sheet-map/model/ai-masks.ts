import type { StageAiReview, StageTextFragment } from '@/shared/api';

/** Mask a complete persisted SAME/MOVED high-confidence decision, never an unresolved subset. */
export function acceptedSameFragments(fragments: readonly StageTextFragment[], reviews: readonly StageAiReview[]): string[] {
  const byId = new Map(fragments.map((fragment) => [fragment.fragment_id, fragment]));
  const accepted = new Set<string>();
  const vetoed = new Set<string>();
  for (const review of reviews) for (const decision of review.decisions) {
    const ids = [...decision.left_fragment_ids, ...decision.right_fragment_ids];
    const eligible = decision.confidence === 'high' && ['SAME', 'MOVED'].includes(decision.status)
      && decision.left_fragment_ids.length > 0 && decision.right_fragment_ids.length > 0
      && decision.left_fragment_ids.every((id) => byId.get(id)?.side === 'left')
      && decision.right_fragment_ids.every((id) => byId.get(id)?.side === 'right');
    const profiles = new Set(decision.right_fragment_ids.map((id) => byId.get(id)?.profile_id));
    const actual = new Set(decision.actual_right_profile_ids ?? []);
    const movedValid = decision.status !== 'MOVED' || (actual.size === profiles.size && [...profiles].every((id) => id !== undefined && actual.has(id)));
    for (const id of ids) (eligible && movedValid ? accepted : vetoed).add(id);
  }
  return [...accepted].filter((id) => !vetoed.has(id)).sort();
}
