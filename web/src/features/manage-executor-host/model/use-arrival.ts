'use client';

import { useQuery } from '@tanstack/react-query';

import type { ExecutorHostId, ExecutorHostList } from '@/shared/api';
import { AGENT_STATUS_POLL_MS } from '@/shared/config';
import { executorHostsQueryOptions } from '@/entities/executor-host';

import { arrivalOf, hostOf } from './arrival';
import type { Arrival } from './arrival';

/**
 * The list of servers read faster while one is being connected, and the status of that one. The re-read ends by itself the
 * moment the server has reported (`arrivalOf`), so it is a bounded poll, not a loop that outlives its subject. It is the same
 * cache entry the list reads, so the window and the list never disagree.
 */
export function useArrival(hostId: ExecutorHostId | null): Arrival {
  const read = useQuery<ExecutorHostList>({
    ...executorHostsQueryOptions(hostId !== null),
    refetchInterval: (query) =>
      arrivalOf(hostOf(query.state.data, hostId)).arrived ? false : AGENT_STATUS_POLL_MS,
  });
  return arrivalOf(hostOf(read.data, hostId));
}
