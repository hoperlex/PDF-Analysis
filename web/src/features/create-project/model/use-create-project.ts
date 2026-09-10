'use client';

/**
 * The create-project command.
 *
 * The mutation carries the idempotency key its caller minted for the intent and does not
 * mint one itself: a key minted inside the mutation would be a new key on every retry.
 * React Query's mutation retry stays off, as `_app` configured it — whether to retry a
 * write belongs to the screen that knows what the user asked for.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { Project } from '@/shared/api';
import { createProject, queryKeys } from '@/shared/api';

export interface CreateProjectCommand {
  readonly name: string;
  /** Minted once per intent by the caller and reused on every retry. */
  readonly idempotencyKey: string;
}

export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation<Project, unknown, CreateProjectCommand>({
    mutationFn: async ({ name, idempotencyKey }) => {
      const response = await createProject({ body: { name }, idempotencyKey });
      return response.data;
    },
    onSuccess: (project) => {
      queryClient.setQueryData(queryKeys.projects.detail(project.project_uid), project);
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all() });
    },
  });
}
