'use client';

/**
 * The reads of «График работ» (`UI-PARITY-P0P`): one month of «Выполнено» and a run of days of «Календарь запаса», under
 * `queryKeys.workSchedule`.
 *
 * The server decides what a viewer reads: an administrator every active expert, an expert their own row. Nothing here
 * filters by role.
 */

import { useQuery } from '@tanstack/react-query';

import type { WorkScheduleMonth, WorkScheduleReserve } from '@/shared/api';
import { getWorkSchedule, getWorkScheduleReserve, queryKeys } from '@/shared/api';

export function useWorkSchedule(month: string) {
  return useQuery<WorkScheduleMonth>({
    queryKey: queryKeys.workSchedule.month(month),
    queryFn: async () => (await getWorkSchedule({ query: { month } })).data,
  });
}

export function useWorkScheduleReserve(start: string, days: number) {
  return useQuery<WorkScheduleReserve>({
    queryKey: queryKeys.workSchedule.reserve(start, days),
    queryFn: async () => (await getWorkScheduleReserve({ query: { start, days } })).data,
  });
}
