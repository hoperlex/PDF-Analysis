'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { markReleaseNotesRead, queryKeys } from '@/shared/api';

export function useMarkReleaseNotesRead() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (readThrough: string) => {
      await markReleaseNotesRead({ body: { read_through: readThrough } });
    },
    onSuccess: () => void client.invalidateQueries({ queryKey: queryKeys.releases.all() }),
  });
}
