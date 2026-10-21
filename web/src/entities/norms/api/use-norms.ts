'use client';

/**
 * The reads of the «Нормы» screens (`W55A-WEB-NORMS`, plan §A3.6–§A3.7), over SEAL's
 * generated client. Until `W55A-SEARCH-01` fills them, every one of these answers the sealed
 * `503 dependency_unavailable`, and the screens render that as a failed read.
 *
 * Freshness: the snapshot list and its history are what an administrator opens the screen to
 * see now, so they are stale the moment they settle and refresh on tab return (the same rule
 * as the execution reads, `C-26`). A search page and a document are answers about one
 * snapshot's immutable rows and keep the application's default freshness.
 */

import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import type {
  NormCatalogueEntryPage, NormDocument, NormDocumentId, NormParagraphPage, NormSearchPage,
  NormSnapshotEventPage, NormSnapshotPage,
} from '@/shared/api';
import {
  getNormDocument, listNormDocuments, listNormParagraphs, listNormSnapshotEvents, listNormSnapshots,
  queryKeys, searchNorms, streamNormDocumentContent,
} from '@/shared/api';

/**
 * The snapshot list is read in one page of the contract's largest size. A deployment holds a
 * handful of snapshots; the page answers which one is current, and past it the screens say
 * the current one is not among those read rather than guessing (`currentSnapshotOf`).
 */
export const NORM_SNAPSHOT_LIMIT = 200;
export const NORM_EVENT_PAGE_LIMIT = 50;
export const NORM_SEARCH_PAGE_LIMIT = 20;
export const NORM_PARAGRAPH_PAGE_LIMIT = 200;
export const NORM_CATALOGUE_PAGE_LIMIT = 50;

/** The catalogue's two filters as the address carries them; `null` for none. */
export interface NormCatalogueFilter {
  readonly q: string | null;
  readonly kind: string | null;
}

/**
 * One page of `listNormDocuments` (`W57B-NORMS-CATALOGUE-XLSX-01`): the current snapshot's
 * documents with display names, filtered and paged. An answer about one snapshot's immutable
 * rows, so it keeps the application's default freshness, like a search page.
 */
export function normCatalogueQueryOptions(filter: NormCatalogueFilter, cursor: string | undefined, enabled: boolean) {
  const q = filter.q ?? undefined;
  const kind = filter.kind ?? undefined;
  return {
    queryKey: queryKeys.norms.catalogue(q, kind, cursor, NORM_CATALOGUE_PAGE_LIMIT),
    queryFn: async () => (await listNormDocuments({
      query: {
        limit: NORM_CATALOGUE_PAGE_LIMIT,
        ...(q === undefined ? {} : { q }),
        ...(kind === undefined ? {} : { kind }),
        ...(cursor === undefined ? {} : { cursor }),
      },
    })).data,
    enabled,
  } as const;
}

export function useNormCatalogue(filter: NormCatalogueFilter, cursor: string | undefined, enabled: boolean) {
  return useQuery<NormCatalogueEntryPage>(normCatalogueQueryOptions(filter, cursor, enabled));
}

export function normSnapshotsQueryOptions() {
  return {
    queryKey: queryKeys.norms.snapshots(undefined, NORM_SNAPSHOT_LIMIT),
    queryFn: async () => (await listNormSnapshots({ query: { limit: NORM_SNAPSHOT_LIMIT } })).data,
    refetchOnWindowFocus: 'always',
    staleTime: 0,
  } as const;
}

export function useNormSnapshots() {
  return useQuery<NormSnapshotPage>(normSnapshotsQueryOptions());
}

/** The designation history (`listNormSnapshotEvents`, `admin`): read only when `enabled`. */
export function normSnapshotEventsQueryOptions(cursor: string | undefined, enabled: boolean) {
  return {
    queryKey: queryKeys.norms.events(cursor, NORM_EVENT_PAGE_LIMIT),
    queryFn: async () => (await listNormSnapshotEvents({
      query: { limit: NORM_EVENT_PAGE_LIMIT, ...(cursor === undefined ? {} : { cursor }) },
    })).data,
    refetchOnWindowFocus: 'always',
    staleTime: 0,
    enabled,
  } as const;
}

export function useNormSnapshotEvents(cursor: string | undefined, enabled: boolean) {
  return useQuery<NormSnapshotEventPage>(normSnapshotEventsQueryOptions(cursor, enabled));
}

/** One page of `searchNorms` over the current snapshot. */
export function normSearchQueryOptions(q: string, cursor: string | undefined, enabled: boolean) {
  return {
    queryKey: queryKeys.norms.search(q, cursor, NORM_SEARCH_PAGE_LIMIT),
    queryFn: async () => (await searchNorms({
      query: { q, limit: NORM_SEARCH_PAGE_LIMIT, ...(cursor === undefined ? {} : { cursor }) },
    })).data,
    enabled,
  } as const;
}

export function useNormSearch(q: string, cursor: string | undefined, enabled: boolean) {
  return useQuery<NormSearchPage>(normSearchQueryOptions(q, cursor, enabled));
}

export function normDocumentQueryOptions(normDocumentId: NormDocumentId) {
  return {
    queryKey: queryKeys.norms.document(normDocumentId),
    queryFn: async () => (await getNormDocument({ path: { norm_document_id: normDocumentId } })).data,
  } as const;
}

export function useNormDocument(normDocumentId: NormDocumentId) {
  return useQuery<NormDocument>(normDocumentQueryOptions(normDocumentId));
}

export function normParagraphsQueryOptions(normDocumentId: NormDocumentId, cursor: string | undefined) {
  return {
    queryKey: queryKeys.norms.paragraphs(normDocumentId, cursor, NORM_PARAGRAPH_PAGE_LIMIT),
    queryFn: async () => (await listNormParagraphs({
      path: { norm_document_id: normDocumentId },
      query: { limit: NORM_PARAGRAPH_PAGE_LIMIT, ...(cursor === undefined ? {} : { cursor }) },
    })).data,
  } as const;
}

export function useNormParagraphs(normDocumentId: NormDocumentId, cursor: string | undefined) {
  return useQuery<NormParagraphPage>(normParagraphsQueryOptions(normDocumentId, cursor));
}

export interface NormContent {
  /** `blob:` URL of the fetched PDF, or null while it is unavailable. */
  readonly objectUrl: string | null;
  readonly isLoading: boolean;
  readonly error: unknown;
  readonly refetch: () => void;
}

/**
 * The norm document's source PDF, held as an object URL while the viewer is open — the same
 * rule as the evidence viewer's: the bytes come from the content operation and nothing else,
 * no storage link reaches the browser, and nothing is persisted. Mounted only when the PDF is
 * wanted (`wantsNormPdf`), so opening a document without a page reads no bytes at all.
 */
export function useNormContent(normDocumentId: NormDocumentId): NormContent {
  const query = useQuery({
    queryKey: queryKeys.norms.content(normDocumentId),
    queryFn: ({ signal }) =>
      streamNormDocumentContent({ path: { norm_document_id: normDocumentId } }, { signal }),
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
    // Loading until the object URL exists, not only until the bytes arrive: the effect that
    // makes the URL runs after the render that received them.
    isLoading: query.error === null && (query.isPending || objectUrl === null),
    error: query.error,
    refetch: () => {
      void query.refetch();
    },
  };
}
