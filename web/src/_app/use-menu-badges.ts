'use client';

/**
 * The reads behind the side menu's badges (`UI-A-06`, `UI-A-91`; `menu-badges.ts` says what each number is).
 *
 * Four reads, each of an operation the generated client already has, each only for a session whose menu holds the item
 * it feeds (`badgeSourcesOf`); a source not asked for is `enabled: false` and asks the server nothing.
 *
 *   «Очередь»              `listExecutionQueue` with `limit: 1` (`D-350`): the figures are the page's `overview` (the jobs still
 *                          open, whenever they were accepted) and its `live_failure_count` (`D-395`, contract 1.43.0: the failed
 *                          jobs nothing has answered yet, which make the red badge), so one row is the least a page can carry.
 *                          One read, where the window of `D-331` needed two. A key of its own (`queryKeys.execution.queueCount`),
 *                          not the queue screen's page of 25 rows with their ETA, which a counter read on every screen does not need.
 *   «База знаний»          `listKnowledgeBaseEntries` with `limit: 1`: the answer carries `total` whatever the page, so
 *                          one entry is the cheapest question. A key of its own (`knowledgeBase({ limit: 1 })`), which
 *                          every decision still refreshes, because it invalidates the knowledge base by prefix. It counts
 *                          both journals (the screen's «Все»); `menu-badges.ts` says why it keeps doing so (`D-362`).
 *                          The screen follows the header's project (`R-150c`, class `optional`), so the read does too:
 *                          the address's project is sent as `project_uid` and is in the key, as on the screen, and
 *                          the menu never shows another project's total while the new one loads. A project the address
 *                          spells as no uid is not asked about: it has no figure.
 *   «Заявки на регистрацию» `listRegistrations` with `{ status: 'pending', limit: 1 }`: **the key and the call of the
 *                          home page's `PendingRegistrationsTile`**, so the tile and the menu share one cache entry and
 *                          a decision on a request refreshes both.
 *
 * All of them follow the operational-list cadence (`OPERATIONAL_LIST_POLLING`, `shared/config/polling.ts`): every ten
 * seconds while the tab is visible, backing off after a failed read, and again on the tab's return. They are the only
 * reads of the frame besides the pause state that run on every screen.
 *
 * **A failed read is no badge.** A re-read that failed keeps the earlier answer beside its error in React Query, and
 * that earlier number is not what the server says now; a badge is drawn from a read that last succeeded, or not at all.
 * Loading is no badge either, so a cold frame draws nothing and never a zero.
 *
 * Needs a query client: {@link FrameNavigation} mounts it only where there is one.
 */

import { useQuery } from '@tanstack/react-query';

import type { ExecutionQueuePage, KnowledgeBaseEntryPage, RegistrationRequestPage } from '@/shared/api';
import { listExecutionQueue, listKnowledgeBaseEntries, listRegistrations, queryKeys } from '@/shared/api';
import { OPERATIONAL_LIST_POLL } from '@/entities/execution';
import { looksLikeProjectUid } from '@/entities/project';

import type { MenuBadgeSource, MenuBadges } from './menu-badges';
import { menuBadgesOf } from './menu-badges';

/** The one entry that tells the knowledge base's total. */
const KNOWLEDGE_BASE_PROBE = { limit: 1 } as const;
/** The one row that carries the queue's overview. */
const QUEUE_PROBE = { limit: 1 } as const;

/** One read of the queue for its counts: the overview and the live failures, both over the whole history. */
function queueCountOptions(enabled: boolean) {
  return {
    queryKey: queryKeys.execution.queueCount(),
    queryFn: async () => (await listExecutionQueue({ query: QUEUE_PROBE })).data,
    ...OPERATIONAL_LIST_POLL,
    refetchOnWindowFocus: 'always',
    staleTime: 0,
    enabled,
  } as const;
}

/** The page whose `pending_total` the administrator's tile and the menu both show. */
const PENDING_REGISTRATIONS = { status: 'pending', limit: 1 } as const;

/**
 * `projectUid` is the project the address names (`R-150c`), or `null`: the installation. The frame reads it from the address
 * and keeps no copy, so a project change in the address is a new key here.
 */
export function useMenuBadges(sources: ReadonlySet<MenuBadgeSource>, projectUid: string | null = null): MenuBadges {
  const queue = useQuery<ExecutionQueuePage>(queueCountOptions(sources.has('queue')));
  // A uid that is not spelled as one names no project; asking the server about it would be asking for an error.
  const badProject = projectUid !== null && !looksLikeProjectUid(projectUid);
  const knowledgeBaseProbe = projectUid === null || badProject ? KNOWLEDGE_BASE_PROBE : { project_uid: projectUid, ...KNOWLEDGE_BASE_PROBE };
  const knowledgeBase = useQuery<KnowledgeBaseEntryPage>({
    queryKey: queryKeys.findings.knowledgeBase(knowledgeBaseProbe),
    queryFn: async () => (await listKnowledgeBaseEntries({ query: knowledgeBaseProbe })).data,
    ...OPERATIONAL_LIST_POLL,
    refetchOnWindowFocus: 'always',
    enabled: sources.has('knowledge-base') && !badProject,
  });
  const registrations = useQuery<RegistrationRequestPage>({
    queryKey: queryKeys.registrations.list(PENDING_REGISTRATIONS),
    queryFn: async () => (await listRegistrations({ query: PENDING_REGISTRATIONS })).data,
    ...OPERATIONAL_LIST_POLL,
    refetchOnWindowFocus: 'always',
    enabled: sources.has('registrations'),
  });
  // A source the menu does not hold is read as nothing even if another screen left its entry in the cache.
  const held = (source: MenuBadgeSource, failed: boolean): boolean => sources.has(source) && !failed;
  return menuBadgesOf({
    queueOverview: held('queue', queue.isError) ? queue.data?.overview : undefined,
    queueLiveFailures: held('queue', queue.isError) ? queue.data?.live_failure_count : undefined,
    knowledgeBaseTotal: held('knowledge-base', knowledgeBase.isError || badProject) ? knowledgeBase.data?.total : undefined,
    knowledgeBaseOfProject: projectUid !== null && !badProject,
    pendingRegistrations: held('registrations', registrations.isError) ? registrations.data?.pending_total : undefined,
  });
}
