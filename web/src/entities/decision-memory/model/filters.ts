/**
 * The filters of the memory's list (`D-495`): the five the operation offers besides the project, which the screen takes from its
 * address (`?project=` is `origin_project_uid`, an identity that may resolve nowhere any more). `'all'` is the absence of the
 * filter and is never sent to the server.
 */

import type { DecisionMemoryListFilters, ProjectUid } from '@/shared/api';

import type { MemoryDataClass, MemoryStatus, MemoryVerdict } from './labels';

export type MemoryStatusChoice = MemoryStatus | 'all';
export type MemoryVerdictChoice = MemoryVerdict | 'all';
export type MemoryDataClassChoice = MemoryDataClass | 'all';

export const MEMORY_STATUS_CHOICES: readonly MemoryStatusChoice[] = ['all', 'active', 'withdrawn', 'forgotten'];
export const MEMORY_VERDICT_CHOICES: readonly MemoryVerdictChoice[] = ['all', 'accepted', 'rejected'];
export const MEMORY_DATA_CLASS_CHOICES: readonly MemoryDataClassChoice[] = ['all', 'test', 'real'];

export interface MemoryFilters {
  readonly status: MemoryStatusChoice;
  readonly verdict: MemoryVerdictChoice;
  /** A finding category of the journal (`CATEGORY_LABELS`), or `'all'`. */
  readonly category: string;
  /** A section code (`PROJECT_SECTIONS`), or `'all'`. */
  readonly section: string;
  readonly dataClass: MemoryDataClassChoice;
}

export const NO_MEMORY_FILTERS: MemoryFilters = { status: 'all', verdict: 'all', category: 'all', section: 'all', dataClass: 'all' };

/** True when any of the five narrows the list. */
export function memoryFiltersNarrow(filters: MemoryFilters): boolean {
  return (Object.keys(NO_MEMORY_FILTERS) as (keyof MemoryFilters)[]).some((name) => filters[name] !== NO_MEMORY_FILTERS[name]);
}

/** The operation's query for these filters under this project and cursor: what is `'all'` is left out. */
export function memoryListQuery(
  filters: MemoryFilters,
  projectUid: ProjectUid | null,
  cursor?: string | undefined,
): DecisionMemoryListFilters {
  return {
    ...(filters.status === 'all' ? {} : { status: filters.status }),
    ...(filters.verdict === 'all' ? {} : { verdict: filters.verdict }),
    ...(filters.category === 'all' ? {} : { category: filters.category }),
    ...(filters.section === 'all' ? {} : { section_code: filters.section }),
    ...(filters.dataClass === 'all' ? {} : { data_class: filters.dataClass }),
    ...(projectUid === null ? {} : { origin_project_uid: projectUid }),
    ...(cursor === undefined ? {} : { cursor }),
  };
}
