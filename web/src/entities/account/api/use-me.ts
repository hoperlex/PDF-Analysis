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

/**
 * What `getMe` says of the object the account chose last (`UIP-G-06`, owner ruling Г7-B): the object the screens that
 * follow the object open on when their address names none.
 */
export interface LastProject {
  /** `getMe` has answered. */
  readonly known: boolean;
  /** `getMe` is on its way: the screens that follow the object cannot yet say which object they open on. */
  readonly pending: boolean;
  /** `last_project_uid`: the object's uid, or `null` — chosen none, its object gone, or not known (`known` says which). */
  readonly projectUid: string | null;
}

/**
 * The account's last object, from the one `getMe` query (`queryKeys.account.me()`: every reader of the account shares it, so
 * this asks for nothing a screen did not already ask). `enabled: false` only reads the cache and never fetches, for a screen
 * whose address already names its object. A read that failed leaves the object unknown (`known: false`, not `pending`): the
 * screens then show «Все объекты», and the failure itself is said wherever the account is shown.
 */
export function useLastProject(options: { readonly enabled?: boolean } = {}): LastProject {
  const enabled = options.enabled ?? true;
  const me = useQuery<Account>({ ...meQueryOptions(), enabled });
  if (me.data !== undefined) return { known: true, pending: false, projectUid: me.data.last_project_uid ?? null };
  return { known: false, pending: enabled && me.isPending, projectUid: null };
}
