'use client';

/**
 * The reads of the «Прецеденты» (`PREC-WEB`, contract 1.51.0): the labels of a run, the card of a finding, the night window, and the
 * administrator's settings.
 *
 * The three reads of the expert are `role:admin|expert`; the viewer is denied, so a screen passes `enabled: false` for him and NO request is
 * made (the options carry the switch, and `tests/unit/review/precedents-access.test.ts` shows that a disabled read asks nothing). They are
 * references and never block a screen: a failed read draws nothing (`retry: false`, no error state), and the findings go on as they were.
 */

import { queryOptions, useQuery } from '@tanstack/react-query';

import type { FindingPrecedents, PrecedentSettingList, RunPrecedents, VectorControl } from '@/shared/api';
import { getFindingPrecedents, getRunPrecedents, getVectorControl, listPrecedentSettings } from '@/shared/api';

/** One namespace for the four reads, so a later invalidation can name it. */
export const precedentKeys = {
  all: () => ['precedents'] as const,
  run: (runId: string) => ['precedents', 'run', runId] as const,
  finding: (findingUid: string) => ['precedents', 'finding', findingUid] as const,
  vectorControl: () => ['precedents', 'vector-control'] as const,
  settings: () => ['precedents', 'settings'] as const,
};

const MINUTE_MS = 60_000;

export function runPrecedentsQueryOptions(runId: string, enabled: boolean) {
  return queryOptions<RunPrecedents>({
    queryKey: precedentKeys.run(runId),
    queryFn: async ({ signal }) => (await getRunPrecedents({ path: { run_id: runId } }, { signal })).data,
    enabled,
    retry: false,
    staleTime: MINUTE_MS,
  });
}

export function findingPrecedentsQueryOptions(findingUid: string, enabled: boolean) {
  return queryOptions<FindingPrecedents>({
    queryKey: precedentKeys.finding(findingUid),
    queryFn: async ({ signal }) => (await getFindingPrecedents({ path: { finding_uid: findingUid } }, { signal })).data,
    enabled,
    retry: false,
    staleTime: MINUTE_MS,
  });
}

export function vectorControlQueryOptions(enabled: boolean) {
  return queryOptions<VectorControl>({
    queryKey: precedentKeys.vectorControl(),
    queryFn: async ({ signal }) => (await getVectorControl({}, { signal })).data,
    enabled,
    retry: false,
    staleTime: MINUTE_MS,
  });
}

export function precedentSettingsQueryOptions(enabled: boolean) {
  return queryOptions<PrecedentSettingList>({
    queryKey: precedentKeys.settings(),
    queryFn: async ({ signal }) => (await listPrecedentSettings({}, { signal })).data,
    enabled,
    retry: false,
    staleTime: 0,
  });
}

export const useRunPrecedents = (runId: string, enabled: boolean) => useQuery(runPrecedentsQueryOptions(runId, enabled));
export const useFindingPrecedents = (findingUid: string | null, enabled: boolean) =>
  useQuery(findingPrecedentsQueryOptions(findingUid ?? '', enabled && findingUid !== null));
export const useVectorControl = (enabled: boolean) => useQuery(vectorControlQueryOptions(enabled));
export const usePrecedentSettings = (enabled: boolean) => useQuery(precedentSettingsQueryOptions(enabled));
