'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRef } from 'react';

import type { DocumentUid, ProjectUid, StagePair, StagePairPage, StagePairSuggestionPage } from '@/shared/api';
import {
  confirmStagePair, listStagePairSuggestions, listStagePairs, newIdempotencyKey,
  setStagePairCompleteness,
} from '@/shared/api';
import type { IntentRecord } from '@/shared/lib';
import { resolveIntentKey } from '@/shared/lib';

const ROOT = ['comparison', 'stage-pairs'] as const;
export const STAGE_PAIR_KEYS = {
  projectPairs: (projectUid: string) => [...ROOT, 'pairs', projectUid] as const,
  projectSuggestions: (projectUid: string) => [...ROOT, 'suggestions', projectUid] as const,
  pairs: (projectUid: string, cursor?: string) => [...ROOT, 'pairs', projectUid, cursor ?? ''] as const,
  suggestions: (projectUid: string, cursor?: string) => [...ROOT, 'suggestions', projectUid, cursor ?? ''] as const,
};

export function useStagePairs(projectUid: ProjectUid | null, cursor?: string) {
  return useQuery<StagePairPage>({
    queryKey: STAGE_PAIR_KEYS.pairs(projectUid ?? '', cursor),
    queryFn: async () => (await listStagePairs({ path: { project_uid: projectUid! }, query: { limit: 100, ...(cursor === undefined ? {} : { cursor }) } })).data,
    enabled: projectUid !== null,
    retry: false,
  });
}

export function useStagePairSuggestions(projectUid: ProjectUid | null, cursor?: string) {
  return useQuery<StagePairSuggestionPage>({
    queryKey: STAGE_PAIR_KEYS.suggestions(projectUid ?? '', cursor),
    queryFn: async () => (await listStagePairSuggestions({ path: { project_uid: projectUid! }, query: { limit: 100, ...(cursor === undefined ? {} : { cursor }) } })).data,
    enabled: projectUid !== null,
    retry: false,
  });
}

interface ConfirmIntent {
  projectUid: ProjectUid;
  leftDocumentUid: DocumentUid;
  rightDocumentUid: DocumentUid;
}

/** A failed request keeps its key, so a retry cannot create a second expert decision. */
export function useConfirmStagePair() {
  const cache = useQueryClient();
  const held = useRef<IntentRecord | null>(null);
  return useMutation<StagePair, unknown, ConfirmIntent>({
    mutationFn: async (intent) => {
      const signature = `${intent.projectUid}|${intent.leftDocumentUid}|${intent.rightDocumentUid}`;
      const record = resolveIntentKey(held.current, signature, newIdempotencyKey);
      held.current = record;
      return (await confirmStagePair({
        path: { project_uid: intent.projectUid },
        body: { left_document_uid: intent.leftDocumentUid, right_document_uid: intent.rightDocumentUid },
        idempotencyKey: record.idempotencyKey,
      })).data;
    },
    retry: false,
    onSuccess: (_pair, intent) => {
      held.current = null;
      void cache.invalidateQueries({ queryKey: STAGE_PAIR_KEYS.projectPairs(intent.projectUid) });
      void cache.invalidateQueries({ queryKey: STAGE_PAIR_KEYS.projectSuggestions(intent.projectUid) });
    },
    onError: (_error, intent) => {
      void cache.invalidateQueries({ queryKey: STAGE_PAIR_KEYS.projectPairs(intent.projectUid) });
      void cache.invalidateQueries({ queryKey: STAGE_PAIR_KEYS.projectSuggestions(intent.projectUid) });
    },
  });
}

interface CompletenessIntent {
  pair: StagePair;
  completeness: 'full' | 'partial';
}

export function useSetStagePairCompleteness() {
  const cache = useQueryClient();
  const held = useRef<IntentRecord | null>(null);
  return useMutation<StagePair, unknown, CompletenessIntent>({
    mutationFn: async ({ pair, completeness }) => {
      const signature = `${pair.pair_id}|${completeness}`;
      const record = resolveIntentKey(held.current, signature, newIdempotencyKey);
      held.current = record;
      return (await setStagePairCompleteness({
        path: { stage_pair_id: pair.pair_id }, body: { completeness },
        idempotencyKey: record.idempotencyKey,
      })).data;
    },
    retry: false,
    onSuccess: (_pair, intent) => {
      held.current = null;
      void cache.invalidateQueries({ queryKey: STAGE_PAIR_KEYS.projectPairs(intent.pair.project_uid) });
    },
    onError: (_error, intent) => {
      void cache.invalidateQueries({ queryKey: STAGE_PAIR_KEYS.projectPairs(intent.pair.project_uid) });
    },
  });
}
