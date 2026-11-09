'use client';

import type { ExecutorHostId } from '@/shared/api';
import { useHostArrivalPoll } from '@/features/connect-remote-agent';

import { arrivalOf, hostOf } from './arrival';
import type { Arrival } from './arrival';

/** The status of the server being connected, over the bounded re-read of the list (`useHostArrivalPoll`). */
export function useArrival(hostId: ExecutorHostId | null): Arrival {
  return arrivalOf(hostOf(useHostArrivalPoll(hostId).data, hostId));
}
