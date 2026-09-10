'use client';

/**
 * Fetch the version's PDF bytes and hold an object URL for as long as the viewer is open.
 *
 * The bytes come from `streamDocumentVersionContent` and from nothing else. There is no
 * presigned link and no redirect in this contract — deliberately, per the seam §10: a URL
 * into object storage is the internal address the contract forbids in a response and would
 * outlive the request that authorized it. So the browser never learns a bucket name, an
 * object key or a storage host; it learns a `blob:` URL scoped to this document.
 *
 * Lifetime: `gcTime: 0` drops the cached `Blob` as soon as the last viewer unmounts, and
 * the effect revokes the object URL on the way out. `P3-WEB-02` requires that page bytes
 * are fetched per view and not persisted client-side; nothing here touches
 * `localStorage`, `sessionStorage` or IndexedDB.
 */

import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import type { VersionUid } from '@/shared/api';
import { queryKeys, streamDocumentVersionContent } from '@/shared/api';

export interface EvidenceDocument {
  /** `blob:` URL for the fetched PDF, or null while it is unavailable. */
  readonly objectUrl: string | null;
  readonly isLoading: boolean;
  readonly error: unknown;
  readonly correlationId: string | null;
  readonly refetch: () => void;
}

export function useEvidenceDocument(versionUid: VersionUid | null): EvidenceDocument {
  const query = useQuery({
    queryKey: queryKeys.versions.content(versionUid ?? ''),
    queryFn: ({ signal }) =>
      streamDocumentVersionContent({ path: { version_uid: versionUid as VersionUid } }, { signal }),
    enabled: versionUid !== null,
    // The bytes are immutable for the life of a version, so nothing refetches them while
    // the viewer is open; they are dropped the moment it closes.
    staleTime: Number.POSITIVE_INFINITY,
    gcTime: 0,
  });

  const blob = query.data?.data ?? null;
  const [objectUrl, setObjectUrl] = useState<string | null>(null);

  useEffect(() => {
    if (blob === null) {
      setObjectUrl(null);
      return;
    }
    const url = URL.createObjectURL(blob);
    setObjectUrl(url);
    return () => {
      URL.revokeObjectURL(url);
    };
  }, [blob]);

  return {
    objectUrl,
    isLoading: query.isPending && versionUid !== null,
    error: query.error,
    correlationId: query.data?.correlationId ?? null,
    refetch: () => {
      void query.refetch();
    },
  };
}
