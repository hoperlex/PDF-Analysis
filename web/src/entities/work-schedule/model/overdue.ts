/**
 * «Просрочки» of «Выполнено» (`D-319`): the open assignments of «Диспетчер» whose planned date is before today. The
 * count comes from the reserve read, which carries every open assignment with its `planned_on`; one without a date is
 * «без даты» and is not late, and a task planned for today is not late yet.
 */

import type { WorkScheduleReserveEngineer } from '@/shared/api';

import type { EngineerFilter } from './engineer-filter';
import { narrowEngineers } from './engineer-filter';

/** What the tile can draw: the read is under way, it failed, or it gave a number. */
export type OverdueRead =
  | { readonly kind: 'pending' }
  | { readonly kind: 'failed' }
  | { readonly kind: 'ready'; readonly count: number };

/** Open assignments planned before `today` (`YYYY-MM-DD`, compared as calendar days) for the engineers the filter leaves. */
export function overdueCount(
  engineers: readonly WorkScheduleReserveEngineer[],
  today: string,
  filter: EngineerFilter,
): number {
  let count = 0;
  for (const engineer of narrowEngineers(engineers, filter)) {
    for (const item of engineer.items) {
      if (item.planned_on !== undefined && item.planned_on < today) count += 1;
    }
  }
  return count;
}
