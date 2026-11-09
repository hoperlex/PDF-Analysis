'use client';

/**
 * The two re-reads of the agent wizard (`EXEC2-WEB-WIZARD-01`). Both are bounded: each ends by
 * itself the moment the thing it waits for has happened, and neither starts a timer of its own.
 *
 * **The install session** (path A). A session moves on the worker's clock — requested, scanning,
 * installing — so while it moves it is read every few seconds and the person watches it progress
 * instead of pressing «Обновить». It stops at `awaiting_host_key` (the next move is the person's:
 * confirming the fingerprint refreshes the read), and at `succeeded` and `failed`.
 *
 * **The connection's detail** (both paths). A grant that waits to be used, and an agent that
 * registered a short while ago and is not yet ready, move without anyone pressing anything: the
 * agent enrolls, reports its health, answers a probe. While `agentIsMoving` the detail is read
 * every few seconds; an offline agent registered yesterday, a ready one and an archived connection
 * schedule nothing. It reads the same cache entry the list reads, so the card and the wizard never
 * disagree, and it is enabled only while something moves so a quiet card adds no request.
 *
 * Neither read touches the run endpoint, and neither is a run poll.
 */

import { useQuery } from '@tanstack/react-query';

import type {
  ExecutorAgentInstall,
  ExecutorAgentInstallId,
  ExecutorConnectionDetail,
  ExecutorConnectionId,
  ExecutorHost,
  ExecutorHostId,
  ExecutorHostList,
} from '@/shared/api';
import { getExecutorAgentInstall, getExecutorHostAgentInstall, queryKeys } from '@/shared/api';
import { AGENT_INSTALL_POLL_MS, AGENT_STATUS_POLL_MS } from '@/shared/config';
import { connectionDetailQueryOptions } from '@/entities/executor-connection';
import { executorHostsQueryOptions } from '@/entities/executor-host';

import { agentIsMoving } from './lifecycle';

/** An install the worker is still working on: the person has nothing to do, so the page re-reads. */
export function installIsMoving(install: ExecutorAgentInstall | undefined): boolean {
  return install !== undefined &&
    (install.state === 'requested' || install.state === 'scanning' || install.state === 'installing');
}

/** The install session's read, filed under `execution` so every command on a connection refreshes it. */
export function agentInstallQueryKey(installId: ExecutorAgentInstallId): readonly unknown[] {
  return [...queryKeys.execution.all(), 'agent-install', installId];
}

/**
 * One install session. `initial` is the answer of the command that created it, so the first
 * paint needs no round trip; the read takes over from there.
 */
export function useAgentInstall(
  connectionId: ExecutorConnectionId,
  installId: ExecutorAgentInstallId,
  initial: ExecutorAgentInstall,
) {
  return useQuery<ExecutorAgentInstall>({
    queryKey: agentInstallQueryKey(installId),
    queryFn: async () =>
      (await getExecutorAgentInstall({ path: { connection_id: connectionId, install_id: installId } })).data,
    initialData: initial,
    staleTime: 0,
    refetchInterval: (query) => (installIsMoving(query.state.data) ? AGENT_INSTALL_POLL_MS : false),
  });
}

/**
 * Keep an agent connection's detail fresh while it moves. The card and the wizard read the detail
 * through the entity's own hook; this one schedules the re-read, and its result is the same entry.
 */
export function useAgentStatusPoll(connectionId: ExecutorConnectionId, enabled: boolean) {
  return useQuery<ExecutorConnectionDetail>({
    ...connectionDetailQueryOptions(connectionId, enabled),
    refetchInterval: (query) => (agentIsMoving(query.state.data, Date.now()) ? AGENT_STATUS_POLL_MS : false),
  });
}

/*
 * `HOSTS-WEB-01`: the same two bounded re-reads for a server connected as a host (ADR-0028), in the one file the polling seam
 * names for the agent lifecycle. They live here and not in `features/manage-executor-host` so that the seam's closed list does not
 * grow: each ends by itself, on the same constants.
 */

/** The server has arrived when its agent has reported (`last_seen_at`) and it is not off line. */
export function hostHasReported(host: ExecutorHost | undefined): boolean {
  return host !== undefined && host.last_seen_at !== undefined && host.state !== 'offline';
}

/**
 * The list of servers read faster while one is being connected, until that server has reported. The same cache entry the list
 * reads, so the window and the list never disagree.
 */
export function useHostArrivalPoll(hostId: ExecutorHostId | null) {
  return useQuery<ExecutorHostList>({
    ...executorHostsQueryOptions(hostId !== null),
    refetchInterval: (query) =>
      hostHasReported(query.state.data?.items.find((host) => host.host_id === hostId)) ? false : AGENT_STATUS_POLL_MS,
  });
}

/** The install session of a server (path A), read from the answer of the command that made it, while the worker moves. */
export function useHostInstall(hostId: ExecutorHostId, installId: ExecutorAgentInstallId, initial: ExecutorAgentInstall) {
  return useQuery<ExecutorAgentInstall>({
    queryKey: [...queryKeys.execution.all(), 'host-install', installId],
    queryFn: async () => (await getExecutorHostAgentInstall({ path: { host_id: hostId, install_id: installId } })).data,
    initialData: initial,
    staleTime: 0,
    refetchInterval: (query) => (installIsMoving(query.state.data) ? AGENT_INSTALL_POLL_MS : false),
  });
}
