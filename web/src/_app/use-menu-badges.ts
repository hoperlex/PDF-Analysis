'use client';

/**
 * The reads behind the side menu's badges (`UI-A-06`, `UI-A-91`; `menu-badges.ts` says what each number is).
 *
 * Three reads, each of an operation the generated client already has, each only for a session whose menu holds the item
 * it feeds (`badgeSourcesOf`); a source not asked for is `enabled: false` and asks the server nothing.
 *
 *   «Очередь»              `listExecutionQueue`, the entity's own `queueQueryOptions()`: the very entry and cadence of
 *                          the first, unfiltered page the queue screen reads, so the screen and the menu are one answer.
 *   «База знаний»          `listKnowledgeBaseEntries` with `limit: 1`: the answer carries `total` whatever the page, so
 *                          one entry is the cheapest question. A key of its own (`knowledgeBase({ limit: 1 })`), which
 *                          every decision still refreshes, because it invalidates the knowledge base by prefix.
 *   «Заявки на регистрацию» `listRegistrations` with `{ status: 'pending', limit: 1 }`: **the key and the call of the
 *                          home page's `PendingRegistrationsTile`**, so the tile and the menu share one cache entry and
 *                          a decision on a request refreshes both.
 *
 * All three follow the operational-list cadence (`OPERATIONAL_LIST_POLLING`, `shared/config/polling.ts`): every ten
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
import { listKnowledgeBaseEntries, listRegistrations, queryKeys } from '@/shared/api';
import { OPERATIONAL_LIST_POLL, queueQueryOptions } from '@/entities/execution';

import type { MenuBadgeSource, MenuBadges } from './menu-badges';
import { menuBadgesOf } from './menu-badges';

/** The one entry that tells the knowledge base's total. */
const KNOWLEDGE_BASE_PROBE = { limit: 1 } as const;
/** The page whose `pending_total` the administrator's tile and the menu both show. */
const PENDING_REGISTRATIONS = { status: 'pending', limit: 1 } as const;

export function useMenuBadges(sources: ReadonlySet<MenuBadgeSource>): MenuBadges {
  const queue = useQuery<ExecutionQueuePage>({ ...queueQueryOptions(), enabled: sources.has('queue') });
  const knowledgeBase = useQuery<KnowledgeBaseEntryPage>({
    queryKey: queryKeys.findings.knowledgeBase(KNOWLEDGE_BASE_PROBE),
    queryFn: async () => (await listKnowledgeBaseEntries({ query: KNOWLEDGE_BASE_PROBE })).data,
    ...OPERATIONAL_LIST_POLL,
    refetchOnWindowFocus: 'always',
    enabled: sources.has('knowledge-base'),
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
    knowledgeBaseTotal: held('knowledge-base', knowledgeBase.isError) ? knowledgeBase.data?.total : undefined,
    pendingRegistrations: held('registrations', registrations.isError) ? registrations.data?.pending_total : undefined,
  });
}
