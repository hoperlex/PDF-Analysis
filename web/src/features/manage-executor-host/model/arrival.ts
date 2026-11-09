/**
 * The live status of a server being connected (`HOSTS-WEB-01`, plan 2026-11-09 §7.3): «ждём сервер…» until its agent has
 * reported, then «найдено: Opus 5.5, Sonnet 5.5».
 *
 * The server exists the moment its grant or its install session is created (`enrollment.host_id`, `install.host_id`), so the
 * list already holds it, off line and never seen. It has *arrived* when it has reported (`last_seen_at`) and is not off line.
 * Pure, so a test reads each case without a window.
 */

import type { ExecutorHost, ExecutorHostId, ExecutorHostList } from '@/shared/api';
import { modelChips } from '@/entities/executor-host';

import { FOUND_NO_MODELS, WAITING_STATUS, foundStatus } from './words';

export interface Arrival {
  readonly arrived: boolean;
  readonly text: string;
}

export function hostOf(list: ExecutorHostList | undefined, hostId: ExecutorHostId | null): ExecutorHost | undefined {
  return hostId === null ? undefined : list?.items.find((host) => host.host_id === hostId);
}

export function arrivalOf(host: ExecutorHost | undefined): Arrival {
  if (host === undefined || host.last_seen_at === undefined || host.state === 'offline') {
    return { arrived: false, text: WAITING_STATUS };
  }
  const chips = modelChips(host.models);
  return {
    arrived: true,
    text: chips.length === 0 ? FOUND_NO_MODELS : foundStatus(chips.map((chip) => chip.label).join(', ')),
  };
}
