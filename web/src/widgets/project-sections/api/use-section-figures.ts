'use client';

/**
 * The server's count of each section's documents by audit state, for one project (`UI-A-35`).
 *
 * It is `getDashboardSummary` with `project_uid`, filed under the key the dashboard and the menu already use for the
 * project, so a project whose dashboard was open costs no request; the screens ask only for the section rows
 * (`select`), and the cache holds the whole answer. Every mutation that moves a count already invalidates that key.
 */

import { useQuery } from '@tanstack/react-query';

import type { DashboardSummary, ProjectUid } from '@/shared/api';
import { getDashboardSummary, queryKeys } from '@/shared/api';

import type { SectionFigures } from '../model/section-figures';
import { sectionFigures } from '../model/section-figures';

export function useSectionFigures(projectUid: ProjectUid) {
  return useQuery<DashboardSummary, Error, SectionFigures>({
    queryKey: queryKeys.dashboard.summary(projectUid),
    queryFn: async () => (await getDashboardSummary({ query: { project_uid: projectUid } })).data,
    select: (summary) => sectionFigures(summary.section_breakdown),
  });
}
