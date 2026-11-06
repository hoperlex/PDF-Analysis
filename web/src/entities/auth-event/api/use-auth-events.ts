'use client';

/**
 * `listAuthEvents` — the access journal, one page at a time, newest first (contract 1.36.0, `UI-A-94`).
 *
 * The server's order and the server's cursor; nothing here sorts or filters. A role the server names that this
 * build does not know is not dropped: it is carried to the row as the code the server sent, so a journal line is
 * never lost to a vocabulary that moved.
 */

import { useQuery } from '@tanstack/react-query';

import type { AuthEventListFilters, AuthEventPage } from '@/shared/api';
import { listAuthEvents, queryKeys } from '@/shared/api';

/** One page of the journal. */
export const AUTH_EVENT_PAGE_LIMIT = 50;

export function useAuthEvents(filters: AuthEventListFilters) {
  return useQuery<AuthEventPage>({
    queryKey: queryKeys.users.authEvents(filters),
    queryFn: async () => (await listAuthEvents({ query: filters })).data,
  });
}
