'use client';

/**
 * `getMe` — the signed-in account, as the API describes it, under `queryKeys.account.me`.
 *
 * The one consumer of the operation in the browser. The session's subject, which the server
 * components read, comes from the same operation at sign-in; this is for a client component
 * that needs the account's current answer rather than the one recorded then.
 *
 * The roles are checked on the way in: a value outside the contract set is an
 * `UnknownRoleError` from the query, never an account with a role nobody can name.
 */

import { useQuery } from '@tanstack/react-query';

import type { Account } from '@/shared/api';
import { getMe, queryKeys } from '@/shared/api';

import { UnknownRoleError, isKnownRole } from '../model/account';

/** The query options, so a server prefetch and the hook share one key and one reading. */
export function meQueryOptions() {
  return {
    queryKey: queryKeys.account.me(),
    queryFn: async (): Promise<Account> => {
      const response = await getMe({});
      const unknown = response.data.roles.find((role) => !isKnownRole(role));
      if (unknown !== undefined) throw new UnknownRoleError(unknown);
      return response.data;
    },
  } as const;
}

export function useMe() {
  return useQuery<Account>(meQueryOptions());
}
