'use client';

/**
 * The project list query.
 *
 * One page, newest first, under the frozen `queryKeys.projects.list` namespace. The
 * cursor is opaque: it is handed back exactly as received and never parsed or built.
 *
 * `options.enabled` (`UI-PARITY-01` wave 1) lets a reader that sits on every screen, the
 * frame's project selector, ask for the first page only when it is needed. It is the same
 * query under the same key, so a list another screen already loaded is read from the cache.
 */

import { useQuery } from '@tanstack/react-query';

import type { ProjectPage } from '@/shared/api';
import { listProjects, queryKeys } from '@/shared/api';

/** Page size. Inside the contract's 1..200 bound and equal to the contract default. */
export const PROJECT_PAGE_LIMIT = 50;

export interface ProjectListOptions {
  /** `false` reads the cache only and starts no request. Absent means `true`. */
  readonly enabled?: boolean;
}

export function useProjectList(cursor?: string, options: ProjectListOptions = {}) {
  return useQuery<ProjectPage>({
    queryKey: queryKeys.projects.list(cursor, PROJECT_PAGE_LIMIT),
    enabled: options.enabled ?? true,
    queryFn: async () => {
      const response = await listProjects({
        query: { ...(cursor === undefined ? {} : { cursor }), limit: PROJECT_PAGE_LIMIT },
      });
      return response.data;
    },
  });
}
