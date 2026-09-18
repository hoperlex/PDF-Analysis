'use client';

/**
 * The published versions of one document — `listVersions`, on mount.
 *
 * Ordered by `version_ordinal` descending, which is the server's order and not this
 * client's: the ordinal is a display and ordering value, never an identity, and nothing
 * here sorts or renumbers.
 *
 * **This returns exactly one row today, and that is a property of the transport rather
 * than of the aggregate.** `uploadDocument` declares no `document_uid`, so every upload
 * through this surface starts a new document at ordinal 1. `IngestService.upload_single_pdf`
 * does take one and does publish a second version onto an existing document — measured by
 * `W18-SEAL` §2. So this is the read side of an aggregate whose write side can already
 * grow, and it is not written as if one row were the rule.
 */

import { useQuery } from '@tanstack/react-query';

import type { DocumentUid, DocumentVersionPage } from '@/shared/api';
import { listVersions, queryKeys } from '@/shared/api';

/** Page size. A document's version history is short; the bound is the contract's. */
export const VERSION_PAGE_LIMIT = 50;

export function useVersionList(documentUid: DocumentUid, cursor?: string) {
  return useQuery<DocumentVersionPage>({
    queryKey: queryKeys.versions.list(documentUid, cursor, VERSION_PAGE_LIMIT),
    queryFn: async () => {
      const response = await listVersions({
        path: { document_uid: documentUid },
        query: { ...(cursor === undefined ? {} : { cursor }), limit: VERSION_PAGE_LIMIT },
      });
      return response.data;
    },
  });
}
