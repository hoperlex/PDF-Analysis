/**
 * The projects the home page lists: the first five of `listProjects`' answer, in the order
 * the API gave them (`W50-PLAN.md` §3.6).
 *
 * The contract's order is read and never re-sorted: `listProjects` answers newest first. The
 * tile asks for five and slices to five as well, so an entry holding more than five — whoever
 * filled it — still shows exactly five.
 */

import type { ProjectPage } from '@/shared/api';

/** How many projects the home page lists. */
export const RECENT_PROJECT_LIMIT = 5;

export function recentProjects(page: ProjectPage): ProjectPage['items'] {
  return page.items.slice(0, RECENT_PROJECT_LIMIT);
}
