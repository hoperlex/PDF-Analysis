/**
 * The worker registry as the screens read it (`W54-WORKERS-WEB`, plan §3.7).
 *
 * `listWorkers` answers one row per registered worker process, newest start first. Its
 * `state` is derived by the server from the last heartbeat (`online`, `stale` after 90 s,
 * `offline` after 600 s); nothing here recomputes it from `heartbeat_at`, because the
 * client's clock is not the server's.
 */

import type { ExecutionWorker, ExecutionWorkerPage, RunId, WorkerId } from '@/shared/api';
import { WORKER_STATE_VALUES } from '@/shared/api';

const WORKER_STATE_LABELS: Readonly<Record<(typeof WORKER_STATE_VALUES)[number], string>> = {
  online: 'На связи',
  stale: 'Не отвечает',
  offline: 'Отключён',
};

/** The Russian word for a worker's state, or `null` for a value outside the sealed set. */
export function workerStateLabel(state: string): string | null {
  return (WORKER_STATE_VALUES as readonly string[]).includes(state)
    ? WORKER_STATE_LABELS[state as (typeof WORKER_STATE_VALUES)[number]]
    : null;
}

export function workerIntakeLabel(enabled: boolean): string {
  return enabled ? 'Берёт новые прогоны' : 'Не берёт новые прогоны';
}

export interface WorkerGroups {
  /** `online` and `stale`, in the server's order: these still hold or may take runs. */
  readonly active: readonly ExecutionWorker[];
  /** `offline`: shown collapsed below the active ones. */
  readonly offline: readonly ExecutionWorker[];
}

/**
 * Online and stale workers first, offline ones apart (plan §3.7). The server's order —
 * newest start first — is kept inside each group. A row whose state is outside the sealed
 * set is not placed in either group; {@link hasUnknownWorkerState} is how a screen refuses it.
 */
export function groupWorkers(items: readonly ExecutionWorker[]): WorkerGroups {
  return {
    active: items.filter((worker) => worker.state === 'online' || worker.state === 'stale'),
    offline: items.filter((worker) => worker.state === 'offline'),
  };
}

export function hasUnknownWorkerState(items: readonly ExecutionWorker[]): boolean {
  return items.some((worker) => workerStateLabel(worker.state) === null);
}

/**
 * Who holds a run, as far as one page of `listWorkers` can say.
 *
 *   - `held`: a listed worker's `current_run_ids` names the run;
 *   - `unheld`: the page is the whole registry and no worker names it. A run executed by
 *     the application process itself (`EXECUTION_ROLE=all`) is held by no registered
 *     worker, so this is a fact about the registry, not a claim that nothing runs it;
 *   - `beyond`: the registry has more pages than was read, so the holder may be on one of
 *     them;
 *   - `unreadable` / `pending`: the read failed or has not answered.
 */
export type RunWorker =
  | { readonly kind: 'held'; readonly workerId: WorkerId }
  | { readonly kind: 'unheld' }
  | { readonly kind: 'beyond' }
  | { readonly kind: 'unreadable' }
  | { readonly kind: 'pending' };

export function runWorker(
  page: ExecutionWorkerPage | undefined,
  failed: boolean,
  runId: RunId,
): RunWorker {
  if (failed) return { kind: 'unreadable' };
  if (page === undefined) return { kind: 'pending' };
  const holder = page.items.find((worker) => worker.current_run_ids.includes(runId));
  if (holder !== undefined) return { kind: 'held', workerId: holder.worker_id };
  return page.page.next_cursor === null ? { kind: 'unheld' } : { kind: 'beyond' };
}

/** Job states in which a Lease is held, so a worker can be named. */
export function jobHoldsLease(state: string): boolean {
  return state === 'leased' || state === 'running';
}

/** Run states during which the run's Job holds a Lease, so a worker can be named. */
export function runHoldsLease(state: string): boolean {
  return state === 'running' || state === 'validating';
}
