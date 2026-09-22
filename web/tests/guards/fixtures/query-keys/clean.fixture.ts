/**
 * The control. Every use here is the shape `queryKeys.runs.detail` declares, so `tsc`
 * must report nothing against this file.
 *
 * Without it, the two red fixtures beside it would prove only that this directory does
 * not compile.
 */

import type { QueryClient } from '@tanstack/react-query';

import type { RunId, RunState, RunStatus } from '@/shared/api';
import { queryKeys } from '@/shared/api';

declare const client: QueryClient;
declare const runId: RunId;
declare const reading: RunStatus;

export function writesTheModel(): void {
  client.setQueryData(queryKeys.runs.detail(runId), reading);
}

/** No type argument, and `.state` resolves: the key supplied the type. */
export function readsTheModel(): RunState | undefined {
  return client.getQueryData(queryKeys.runs.detail(runId))?.state;
}
