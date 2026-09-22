/**
 * `D-57`'s write half: filing the transport envelope under a key that holds the model.
 *
 * Before the key carried its value type this compiled, and the disagreement surfaced on
 * screen. `tsc` must reject it now.
 */

import type { QueryClient } from '@tanstack/react-query';

import type { RunId, RunStatus } from '@/shared/api';
import { queryKeys } from '@/shared/api';

declare const client: QueryClient;
declare const runId: RunId;
declare const envelope: { data: RunStatus; status: number; correlationId: string | null };

export function writesTheEnvelope(): void {
  client.setQueryData(queryKeys.runs.detail(runId), envelope);
}
