import type { CreateStageReviewCardRequest } from '@/shared/api';

export const REVIEW_SOURCE_LIMIT = 400;
export function reviewRequest(sourceIds: readonly string[], reason: string): CreateStageReviewCardRequest | null {
  const sources = [...new Set(sourceIds)];
  const text = reason.trim();
  if (sources.length === 0 || sources.length > REVIEW_SOURCE_LIMIT || text === '' || text.length > 2000) return null;
  return { source_ids: sources, reason: text };
}
