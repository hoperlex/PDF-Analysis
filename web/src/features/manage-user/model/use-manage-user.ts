'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { QueryClient } from '@tanstack/react-query';

import type { Account, PersonNames, Role } from '@/shared/api';
import { archiveUser, purgeUser, queryKeys, resetUserPassword, restoreUser, updateUser } from '@/shared/api';

export type UserCommand =
  | { readonly kind: 'names'; readonly names: PersonNames }
  | { readonly kind: 'roles'; readonly roles: Role[] }
  | { readonly kind: 'archive' }
  | { readonly kind: 'restore' }
  | { readonly kind: 'purge' }
  | { readonly kind: 'reset-password'; readonly temporaryPassword: string };

export type UserCommandResult =
  | { readonly kind: 'account'; readonly account: Account }
  | { readonly kind: 'purged' };

/** The two router calls the controls make after a command — `next/navigation`'s, narrowed. */
export interface UserCommandRouter {
  refresh(): void;
  push(href: string): void;
}

/**
 * What follows a successful command (`C-20`): a purge leaves the deleted account's screen for
 * the list; a change to the signed-in account re-renders the server components, so the
 * frame's name and menu follow it (the BFF refreshes the session's subject on that write).
 */
export function followUserCommand(
  router: UserCommandRouter,
  result: UserCommandResult,
  isSelf: boolean,
  usersAddress: string,
): void {
  if (result.kind === 'purged') router.push(usersAddress);
  else if (isSelf) router.refresh();
}

export function refreshManagedUser(queryClient: QueryClient, account: Account): void {
  queryClient.setQueryData(queryKeys.users.detail(account.user_uid), account);
  void queryClient.invalidateQueries({ queryKey: queryKeys.users.all() });
  const own = queryClient.getQueryData(queryKeys.account.me());
  if (own !== null && typeof own === 'object' && 'user_uid' in own && own.user_uid === account.user_uid) {
    void queryClient.invalidateQueries({ queryKey: queryKeys.account.me() });
  }
}

export function useManageUser(userUid: string) {
  const queryClient = useQueryClient();
  return useMutation<UserCommandResult, unknown, UserCommand>({
    mutationFn: async (command) => {
      const path = { user_uid: userUid };
      switch (command.kind) {
        case 'names': return { kind: 'account', account: (await updateUser({ path, body: { names: command.names } })).data };
        case 'roles': return { kind: 'account', account: (await updateUser({ path, body: { roles: command.roles } })).data };
        case 'archive': return { kind: 'account', account: (await archiveUser({ path })).data };
        case 'restore': return { kind: 'account', account: (await restoreUser({ path })).data };
        case 'reset-password': return { kind: 'account', account: (await resetUserPassword({ path, body: { temporary_password: command.temporaryPassword } })).data };
        case 'purge': await purgeUser({ path }); return { kind: 'purged' };
      }
    },
    onSuccess: (result) => {
      if (result.kind === 'account') {
        refreshManagedUser(queryClient, result.account);
      } else {
        queryClient.removeQueries({ queryKey: queryKeys.users.detail(userUid) });
        void queryClient.invalidateQueries({ queryKey: queryKeys.users.all() });
      }
    },
  });
}
