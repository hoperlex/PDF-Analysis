'use client';

/**
 * The published versions of one document — `listVersions`, on mount.
 *
 * Ordered by `version_ordinal` descending, which is the server's order and not this
 * client's: the ordinal is a display and ordering value, never an identity, and nothing
 * here sorts or renumbers.
 *
 * **It is not written as if one row were the rule.** Until `W59-VERSION-UPLOAD-01` every
 * upload through this surface started a new document at ordinal 1 (`W18-SEAL` §2); since
 * then `uploadDocumentVersion` publishes further versions onto an existing document, and
 * its success invalidates every page of this list (`queryKeys.versions.lists`).
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
