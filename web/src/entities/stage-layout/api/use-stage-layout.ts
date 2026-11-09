'use client';

import { useQuery } from '@tanstack/react-query';

import type { ModelCatalogue, StageModelLayout } from '@/shared/api';
import { getStageModelLayout, listModelCatalogue, queryKeys } from '@/shared/api';

/**
 * The reads of «Модели по этапам» (`HOSTS-WEB-01`). Filed under `execution`, so a command on a server, which can change which
 * cells have no server, and a command on the layout refresh them. The layout is read on tab return and after a command; the
 * catalogue is a frozen file of the contract and is read once. **The viewer reads neither** (`R-150w`): the screen enables a
 * read only for an expert or an administrator.
 */

export const stageLayoutKey = (): readonly unknown[] => [...queryKeys.execution.all(), 'stage-layout'];
export const modelCatalogueKey = (): readonly unknown[] => ['model-catalogue'];

export function stageLayoutQueryOptions(enabled = true) {
  return {
    queryKey: stageLayoutKey(),
    queryFn: async () => (await getStageModelLayout({})).data,
    refetchOnWindowFocus: 'always',
    staleTime: 0,
    enabled,
  } as const;
}

export function useStageModelLayout(enabled = true) {
  return useQuery<StageModelLayout>(stageLayoutQueryOptions(enabled));
}

export function modelCatalogueQueryOptions(enabled = true) {
  return {
    queryKey: modelCatalogueKey(),
    queryFn: async () => (await listModelCatalogue({})).data,
    staleTime: Infinity,
    enabled,
  } as const;
}

export function useModelCatalogue(enabled = true) {
  return useQuery<ModelCatalogue>(modelCatalogueQueryOptions(enabled));
}
