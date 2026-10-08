'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { Account, UpdateMyProfileRequest } from '@/shared/api';
import { queryKeys, updateMyProfile } from '@/shared/api';

export function useEditProfile() {
  const queryClient = useQueryClient();
  return useMutation<Account, unknown, UpdateMyProfileRequest>({
    mutationFn: async (body) => (await updateMyProfile({ body })).data,
    onSuccess: (account) => {
      queryClient.setQueryData(queryKeys.account.me(), account);
      void queryClient.invalidateQueries({ queryKey: queryKeys.account.me() });
    },
  });
}
