'use client';

/**
 * The create-project command.
 *
 * The mutation carries the idempotency key its caller minted for the intent and does not
 * mint one itself: a key minted inside the mutation would be a new key on every retry.
 * React Query's mutation retry stays off, as `_app` configured it — whether to retry a
 * write belongs to the screen that knows what the user asked for.
 *
 * `W46-CLIENT`, `X-6`/`Y6-a`. A new project changes the dashboard's one read — a row in
 * `documents_by_project`, and for the first project, `hasProjects` flips and decides two
 * panels' empty state (`query-keys.ts:165`'s own promise: *"every mutation that changes a
 * number this key answers for invalidates it"*). This used to invalidate `projects.all()`
 * only, which does not reach `dashboard.summary()` — a separate root namespace — so with
 * the app's `staleTime: 30_000` a client-side return to `/dashboard` after creating the
 * first project still read *«Проектов пока нет.»* and made no request to find out.
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
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.summary() });
    },
  });
}
