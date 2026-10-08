'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { QueryClient } from '@tanstack/react-query';

import type { RegistrationRequest, Role } from '@/shared/api';
import { approveRegistration, queryKeys, rejectRegistration } from '@/shared/api';

export type RegistrationDecision =
  | { readonly kind: 'approve'; readonly requestId: string; readonly roles: Role[]; readonly idempotencyKey: string }
  | { readonly kind: 'reject'; readonly requestId: string; readonly reason: string };

export function refreshDecisionCache(queryClient: QueryClient, kind: RegistrationDecision['kind']): void {
  void queryClient.invalidateQueries({ queryKey: queryKeys.registrations.all() });
  if (kind === 'approve') void queryClient.invalidateQueries({ queryKey: queryKeys.users.all() });
}

export function useDecideRegistration() {
  const queryClient = useQueryClient();
  return useMutation<RegistrationRequest, unknown, RegistrationDecision>({
    mutationFn: async (decision) => {
      const path = { request_id: decision.requestId };
      if (decision.kind === 'approve') {
        return (await approveRegistration({ path, body: { roles: decision.roles }, idempotencyKey: decision.idempotencyKey })).data;
      }
      return (await rejectRegistration({ path, body: { reason: decision.reason } })).data;
    },
    onSuccess: (_request, decision) => refreshDecisionCache(queryClient, decision.kind),
  });
}
