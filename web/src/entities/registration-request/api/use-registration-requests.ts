'use client';

import { useQuery } from '@tanstack/react-query';

import type { RegistrationRequestPage, RegistrationStatus, RegistrationListFilters } from '@/shared/api';
import { REGISTRATION_STATUS_VALUES, listRegistrations, queryKeys } from '@/shared/api';

export const REGISTRATION_PAGE_LIMIT = 50;

export class UnknownRegistrationStatusError extends Error {
  constructor(readonly value: unknown) {
    super('Заявка содержит неизвестное состояние.');
    this.name = 'UnknownRegistrationStatusError';
  }
}

export function isRegistrationStatus(value: unknown): value is RegistrationStatus {
  return typeof value === 'string' && (REGISTRATION_STATUS_VALUES as readonly string[]).includes(value);
}

export function useRegistrationRequests(filters: RegistrationListFilters) {
  return useQuery<RegistrationRequestPage>({
    queryKey: queryKeys.registrations.list(filters),
    queryFn: async () => {
      const page = (await listRegistrations({ query: filters })).data;
      for (const request of page.items) {
        if (!isRegistrationStatus(request.status)) throw new UnknownRegistrationStatusError(request.status);
      }
      return page;
    },
  });
}
