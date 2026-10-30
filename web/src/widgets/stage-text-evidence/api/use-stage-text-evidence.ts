'use client';

import { useQuery } from '@tanstack/react-query';

import {
  ApiError, listStageRawDifferences, listStageTextExclusions,
  listStageTextFragments, listStageTextHints,
} from '@/shared/api';
import type { StageTextEvidenceData } from '../model/evidence';

export const STAGE_TEXT_KEYS = {
  evidence: (pairId: string, revisionId: string | undefined) => ['stage-text-evidence', pairId, revisionId ?? 'none'] as const,
};

async function allPages<T>(read: (cursor?: string) => Promise<{
  items: T[]; page: { next_cursor: string | null };
}>): Promise<T[]> {
  const items: T[] = [];
  const seen = new Set<string>();
  let cursor: string | undefined;
  do {
    const page = await read(cursor);
    items.push(...page.items);
    cursor = page.page.next_cursor ?? undefined;
    if (cursor !== undefined) {
      if (seen.has(cursor)) throw new Error('Список свидетельств изменился. Обновите сравнение.');
      seen.add(cursor);
    }
  } while (cursor !== undefined);
  return items;
}

export async function loadStageTextEvidence(pairId: string, revisionId: string): Promise<StageTextEvidenceData> {
  const query = (cursor?: string) => ({ limit: 100, ...(cursor === undefined ? {} : { cursor }) });
  const [fragments, exclusions, differences, hints] = await Promise.all([
    allPages(async (cursor) => (await listStageTextFragments({ path: { stage_pair_id: pairId }, query: query(cursor) })).data),
    allPages(async (cursor) => (await listStageTextExclusions({ path: { stage_link_revision_id: revisionId }, query: query(cursor) })).data),
    allPages(async (cursor) => (await listStageRawDifferences({ path: { stage_link_revision_id: revisionId }, query: query(cursor) })).data),
    allPages(async (cursor) => (await listStageTextHints({ path: { stage_link_revision_id: revisionId }, query: query(cursor) })).data),
  ]);
  return { fragments, exclusions, differences, hints };
}

export function evidenceNeedsRecompute(error: unknown): boolean {
  return error instanceof ApiError && error.status === 503
    && error.envelope.details?.dependency === 'comparison_stage_text_evidence';
}

export function useStageTextEvidence(pairId: string, revisionId: string | undefined) {
  return useQuery({
    queryKey: STAGE_TEXT_KEYS.evidence(pairId, revisionId),
    queryFn: () => loadStageTextEvidence(pairId, revisionId!),
    enabled: revisionId !== undefined, retry: false,
  });
}
