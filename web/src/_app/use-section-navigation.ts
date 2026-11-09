'use client';

/**
 * The read behind the «Разделы» group (`UI-A-04`): `getDashboardSummary` for the current project, the very read and
 * cache entry the dashboard's section panel uses (`queryKeys.dashboard.summary(projectUid)`), so the menu's counts
 * and the panel's are one answer, and every mutation that already invalidates the summary refreshes the menu too.
 *
 * It is a hook of its own rather than `useDashboardSummary` because the frame wraps every screen: importing the
 * dashboard widget here would put its panels in the first-load bundle of all of them, which `W50-LAZY-01` split off.
 * The query function is the same call, and the entry holds the same model, so nothing is read twice.
 *
 * Mounted only where the group is offered and the address names a well-formed project: a render of the frame without
 * a project, or without a query client, makes no request (`app-frame.tsx`).
 */

import { useQuery } from '@tanstack/react-query';

import type { DashboardSummary, ProjectUid } from '@/shared/api';
import { getDashboardSummary, queryKeys } from '@/shared/api';

import type { SectionNavigation } from './section-navigation';
import { sectionNavigationOf } from './section-navigation';

export function useSectionNavigation(projectUid: string, pathname: string | null): SectionNavigation {
  const summary = useQuery<DashboardSummary>({
    queryKey: queryKeys.dashboard.summary(projectUid as ProjectUid),
    queryFn: async () => (await getDashboardSummary({ query: { project_uid: projectUid as ProjectUid } })).data,
  });
  if (summary.data !== undefined) return sectionNavigationOf(summary.data.section_breakdown, projectUid, pathname);
  return summary.isError ? { status: 'failed' } : { status: 'loading' };
}
