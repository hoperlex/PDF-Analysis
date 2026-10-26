import type { ArV3RunGroupId } from '@/shared/api';

/** Validate only the opaque address shape; it conveys no group semantics. */
export function looksLikeArV3GroupId(value: unknown): value is ArV3RunGroupId {
  return typeof value === 'string' && /^arg_[0-9A-HJKMNP-TV-Z]{26}$/.test(value);
}

/**
 * Where «Настройки анализа» reads one group's review: the settings screen with the group in
 * its address (`app/analysis-settings/page.tsx` reads `group_id` and refuses a malformed one).
 * Built here, beside the shape guard it is checked against, because the address is the only
 * thing a started group is handed to the reader as.
 */
export function arV3GroupReviewAddress(groupId: ArV3RunGroupId): string {
  return `/analysis-settings?group_id=${encodeURIComponent(groupId)}`;
}
