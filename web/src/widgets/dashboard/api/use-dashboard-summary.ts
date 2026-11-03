'use client';

/**
 * `getDashboardSummary` — the one read behind all four dashboard panels.
 *
 * `R-44`, wired at `W46-WIRE`. Before this, the dashboard walked the surface client-side:
 * `useProjectList` for documents per project, `useDecisionJournal` for findings by
 * verdict, and a bespoke `useRunActivityWalk` — a fan-out over projects, then their
 * documents, then those versions' runs — for run activity and spend. `F-3b`
 * (`docs/program/reviews/W46-JUDGE-A.md` §5) measured that the aggregate this hook reads
 * had landed with no consumer: the walks were still the live path. This hook, and the
 * panels built on it, are the join.
 *
 * The three entity hooks above are unchanged and stay exported: `/projects`,
 * `/knowledge-base` and the run screen still read them directly, and a page total from a
 * paged listing is a different question from a deployment-wide count.
 */

import { useQuery } from '@tanstack/react-query';

import type { DashboardSummary, ProjectUid } from '@/shared/api';
import { getDashboardSummary, queryKeys } from '@/shared/api';

/**
 * `projectUid` is the project the address names (`?project=`, `UI-PARITY-P0A`), or `null` for
 * «Все проекты». With one, the server restricts all four panels to that project and answers
 * `404 not_found` for a project it does not know; without one it answers the whole deployment,
 * exactly as before. The project is in the cache key, so two projects are two entries and a
 * switch never shows the other project's numbers while the new ones load.
 */
export function useDashboardSummary(projectUid: ProjectUid | null = null) {
  return useQuery<DashboardSummary>({
    queryKey: queryKeys.dashboard.summary(projectUid),
    queryFn: async () => {
      const response = await getDashboardSummary(
        projectUid === null ? {} : { query: { project_uid: projectUid } },
      );
      return response.data;
    },
  });
}
