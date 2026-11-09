'use client';

/**
 * The state and the reads of the «Память решений» tab (`D-495`): its filters and open case from the address, the cursors of the
 * pages walked past, and the three reads -- the page of cases, the open case, the administrator's counts.
 *
 * Each read is made only where it is drawn: nothing while the tab is not the one on screen, the list only while no case is open,
 * the case only while one is, the counts only for the administrator. A filter or project change returns to the first page (a
 * cursor belongs to the filters it was issued under, `useCursorWalk`), and leaves the case. Opening a case is a step of the
 * history, so Back returns to the list with its filters; a filter is not a place to go Back to and replaces the entry.
 */

import type { DecisionMemoryCaseId, ProjectUid } from '@/shared/api';
import { useAddressState } from '@/shared/lib';
import { NO_MEMORY_FILTERS, memoryListQuery, useDecisionMemoryCase, useDecisionMemoryCases, useDecisionMemoryStatus } from '@/entities/decision-memory';
import type { MemoryAccess, MemoryFilters } from '@/entities/decision-memory';

import { readMemoryAddress, writeMemoryAddress } from './memory-address';
import { useCursorWalk } from './use-cursor-walk';

export function useMemoryTab(projectUid: ProjectUid | null, active: boolean, access: MemoryAccess) {
  const [address, setAddress] = useAddressState(readMemoryAddress, writeMemoryAddress);
  const { filters, caseId } = address;
  const filterKey = [filters.status, filters.verdict, filters.category, filters.section, filters.dataClass].join('|');
  const [cursors, setCursors] = useCursorWalk(`${projectUid ?? ''}|${filterKey}`);
  const cursor = cursors.at(-1);

  const list = useDecisionMemoryCases(memoryListQuery(filters, projectUid, cursor), active && access.read && caseId === null);
  const detail = useDecisionMemoryCase(active && access.read ? caseId : null);
  const status = useDecisionMemoryStatus(active && access.manage);

  return {
    filters,
    caseId,
    cursors,
    setCursors,
    list,
    detail,
    status,
    /** A filter changes: replace the entry, back to the list and its first page. */
    setFilters: (patch: Partial<MemoryFilters>) => setAddress({ filters: { ...filters, ...patch }, caseId: null }, 'replace'),
    resetFilters: () => setAddress({ filters: NO_MEMORY_FILTERS, caseId: null }, 'replace'),
    openCase: (next: DecisionMemoryCaseId) => setAddress({ filters, caseId: next }, 'push'),
    closeCase: () => setAddress({ filters, caseId: null }, 'push'),
  };
}

export type MemoryTab = ReturnType<typeof useMemoryTab>;
