'use client';

/**
 * The three reads the home page makes (`W50-PLAN.md` §3.6), each under a key of
 * `query-keys.ts` and each holding exactly what the generated client answered — the model,
 * never the transport envelope — so a key another screen also fills holds one shape.
 *
 *   `listProjects`         `projects.list(undefined, 5)`: the first page of five, in the
 *                          contract's order (newest first). Its own entry beside the projects
 *                          screen's page of fifty; `createProject` invalidates both through
 *                          `projects.all()`.
 *   `getDashboardSummary`  `dashboard.summary()`: the same entry, the same `queryFn` answer
 *                          and the same shape as the dashboard's own read, so the two screens
 *                          share one cache entry and every mutation that already invalidates
 *                          it reaches the home page too.
 *   `listRegistrations`    `registrations.list({ status: 'pending', limit: 1 })`, and only for
 *                          a session holding `admin` (`R-60`): the caller decides by mounting
 *                          the tile, and nothing here reads the session. The page is cached as
 *                          the API answered it; the tile selects `pending_total` and nothing
 *                          else, so no applicant's name, e-mail or reason reaches the screen.
 *                          `limit` is the contract's minimum, 1 — the contract has no
 *                          count-only read, so the answer still carries at most one request,
 *                          which nothing renders.
 */

import { useQuery } from '@tanstack/react-query';

import type { DashboardSummary, ProjectPage, RegistrationRequestPage } from '@/shared/api';
import {
  getDashboardSummary,
  listProjects,
  listRegistrations,
  queryKeys,
} from '@/shared/api';

import { RECENT_PROJECT_LIMIT } from '../model/recent-projects';

/** The one page of `listRegistrations` whose `pending_total` the administrator's tile shows. */
const PENDING_REGISTRATIONS = { status: 'pending', limit: 1 } as const;

export function useRecentProjects() {
  return useQuery<ProjectPage>({
    queryKey: queryKeys.projects.list(undefined, RECENT_PROJECT_LIMIT),
    queryFn: async () => {
      const response = await listProjects({ query: { limit: RECENT_PROJECT_LIMIT } });
      return response.data;
    },
  });
}

export function useHomeSummary() {
  return useQuery<DashboardSummary>({
    queryKey: queryKeys.dashboard.summary(),
    queryFn: async () => {
      const response = await getDashboardSummary({});
      return response.data;
    },
  });
}

export function usePendingRegistrationTotal() {
  return useQuery({
    queryKey: queryKeys.registrations.list(PENDING_REGISTRATIONS),
    queryFn: async (): Promise<RegistrationRequestPage> => {
      const response = await listRegistrations({ query: PENDING_REGISTRATIONS });
      return response.data;
    },
    select: (page) => page.pending_total,
  });
}
