'use client';

import { useQuery } from '@tanstack/react-query';

import type { Account, AccountPage, UserListFilters } from '@/shared/api';
import { getUser, listUsers, queryKeys } from '@/shared/api';
import { UnknownRoleError, isKnownRole } from '@/entities/account';

export const USER_PAGE_LIMIT = 50;

function requireKnownRoles(account: Account): Account {
  const unknown = account.roles.find((role) => !isKnownRole(role));
  if (unknown !== undefined) throw new UnknownRoleError(unknown);
  return account;
}

export function useUsers(filters: UserListFilters) {
  return useQuery<AccountPage>({
    queryKey: queryKeys.users.list(filters),
    queryFn: async () => {
      const page = (await listUsers({ query: filters })).data;
      page.items.forEach(requireKnownRoles);
      return page;
    },
  });
}

export function useUser(userUid: string) {
  return useQuery<Account>({
    queryKey: queryKeys.users.detail(userUid),
    queryFn: async () => requireKnownRoles((await getUser({ path: { user_uid: userUid } })).data),
  });
}
