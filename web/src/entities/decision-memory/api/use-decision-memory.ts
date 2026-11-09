'use client';

/**
 * The decision memory's three reads (`D-495`): a page of cases, one case, and the administrator's counts and settings.
 *
 * The memory is a copy of what an expert saw and decided, kept after its project and document are gone (`ADR-0027`). It is
 * HISTORY, not a verdict in force: while the source finding exists the ledger decides. These hooks window the server's
 * answer and derive nothing from it. The cursor is opaque and is handed back as received.
 *
 * `staleTime: 0`: a decision taken a moment ago is captured in the same transaction and must be on the list the next time
 * it is opened, not after the application's 30 seconds.
 */

import { useQuery } from '@tanstack/react-query';

import type {
  DecisionMemoryCase,
  DecisionMemoryCaseId,
  DecisionMemoryCasePage,
  DecisionMemoryListFilters,
  DecisionMemoryStatus,
} from '@/shared/api';
import { getDecisionMemoryCase, getDecisionMemoryStatus, listDecisionMemoryCases, queryKeys } from '@/shared/api';

/** Page size: inside the contract's bound, and the journal's own. */
export const MEMORY_PAGE_LIMIT = 50;

export function useDecisionMemoryCases(filters: DecisionMemoryListFilters, enabled = true) {
  const query = { ...filters, limit: MEMORY_PAGE_LIMIT };
  return useQuery<DecisionMemoryCasePage>({
    queryKey: queryKeys.findings.memoryCases(query),
    queryFn: async () => (await listDecisionMemoryCases({ query })).data,
    enabled,
    staleTime: 0,
  });
}

export function useDecisionMemoryCase(caseId: DecisionMemoryCaseId | null) {
  return useQuery<DecisionMemoryCase>({
    queryKey: queryKeys.findings.memoryCase(caseId ?? ''),
    queryFn: async () => (await getDecisionMemoryCase({ path: { case_id: caseId ?? '' } })).data,
    enabled: caseId !== null,
    staleTime: 0,
  });
}

export function useDecisionMemoryStatus(enabled = true) {
  return useQuery<DecisionMemoryStatus>({
    queryKey: queryKeys.findings.memoryStatus(),
    queryFn: async () => (await getDecisionMemoryStatus({})).data,
    enabled,
    staleTime: 0,
  });
}
