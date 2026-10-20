'use client';

import { useQuery } from '@tanstack/react-query';

import type { DocumentUid, ProjectUid, SpecificationPrices } from '@/shared/api';
import { getSpecificationPrices, queryKeys } from '@/shared/api';

/** Rows per page. Inside the contract's bound (1..200). */
export const SPECIFICATION_ROW_LIMIT = 50;

/**
 * `getSpecificationPrices` (`W60-OPT-MATCH-01`): one page of a document set's AR specification
 * priced from the project's current price list, or the state that stops it.
 *
 * The answer is always a `SpecificationPrices`: an unclassified or non-AR version, a project
 * without a price list, a version without a published run or saved text is its `state`, not
 * a failure. A failure is what the transport refuses (`404` for a set outside the project).
 */
export function specificationPricesQueryOptions(
  projectUid: ProjectUid,
  documentUid: DocumentUid,
  offset = 0,
  limit = SPECIFICATION_ROW_LIMIT,
) {
  return {
    queryKey: queryKeys.optimisation.specificationPrices(projectUid, documentUid, offset, limit),
    queryFn: async (): Promise<SpecificationPrices> =>
      (
        await getSpecificationPrices({
          path: { project_uid: projectUid, document_uid: documentUid },
          query: { offset, limit },
        })
      ).data,
  } as const;
}

/**
 * Disabled until a set is chosen. The previous page of the **same** set stays on screen while
 * the next loads; another set's answer never stands in for this one's.
 */
export function useSpecificationPrices(
  projectUid: ProjectUid,
  documentUid: DocumentUid | null,
  offset = 0,
) {
  return useQuery<SpecificationPrices>({
    ...specificationPricesQueryOptions(projectUid, (documentUid ?? '') as DocumentUid, offset),
    enabled: documentUid !== null,
    placeholderData: (previous, previousQuery) =>
      previousQuery?.queryKey[3] === documentUid ? previous : undefined,
  });
}
