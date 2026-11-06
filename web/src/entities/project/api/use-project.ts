'use client';

/**
 * One project by its identity (`getProject`, contract 1.29.0, `UI-PARITY-P0N`).
 *
 * A screen that names its project reads it here instead of looking for it on the first page of `listProjects`, which
 * named a project «Проект» as soon as the deployment had more projects than a page. Cached under
 * `queryKeys.projects.detail`, the key `createProject` already fills and an upload already invalidates.
 */

import { useQuery } from '@tanstack/react-query';

import type { Project, ProjectUid } from '@/shared/api';
import { getProject, queryKeys } from '@/shared/api';

export function useProject(projectUid: string | null) {
  return useQuery<Project>({
    queryKey: queryKeys.projects.detail((projectUid ?? '') as ProjectUid),
    enabled: projectUid !== null && projectUid !== '',
    queryFn: async () => (await getProject({ path: { project_uid: projectUid as ProjectUid } })).data,
  });
}
