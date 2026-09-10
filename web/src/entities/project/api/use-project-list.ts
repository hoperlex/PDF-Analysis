'use client';

/**
 * The project list query.
 *
 * One page, newest first, under the frozen `queryKeys.projects.list` namespace. The
 * cursor is opaque: it is handed back exactly as received and never parsed or built.
 */

import { useQuery } from '@tanstack/react-query';

import type { ProjectPage } from '@/shared/api';
import { listProjects, queryKeys } from '@/shared/api';

/** Page size. Inside the contract's 1..200 bound and equal to the contract default. */
export const PROJECT_PAGE_LIMIT = 50;

export function useProjectList(cursor?: string) {
  return useQuery<ProjectPage>({
    queryKey: queryKeys.projects.list(cursor, PROJECT_PAGE_LIMIT),
    queryFn: async () => {
      const response = await listProjects({
        query: { ...(cursor === undefined ? {} : { cursor }), limit: PROJECT_PAGE_LIMIT },
      });
      return response.data;
    },
  });
}
