'use client';

/**
 * Every page of one object's documents, followed to its end (`UIP-S13-03`): the panel «Добавить документы» offers the whole object, not
 * the first fifty, and says so while it is still reading and when a page could not be read (no part of the listing is offered as the
 * whole). The listing is the object's own, the very request and cache key the object's page makes (`documentListQueryOptions`), so a
 * reader who has just seen the object's documents holds them already.
 */

import { useState } from 'react';
import { useQueries } from '@tanstack/react-query';

import type { DocumentVersion, ProjectUid } from '@/shared/api';
import { advanceSectionWalk, documentListQueryOptions } from '@/entities/document-version';

export type ObjectDocuments =
  | { readonly status: 'idle' }
  | { readonly status: 'pending' }
  /** A page failed, or the listing named a cursor twice. No partial list is offered. */
  | { readonly status: 'failed'; readonly retry: () => void }
  | { readonly status: 'complete'; readonly items: readonly DocumentVersion[] };

/** `projectUid` `null` reads nothing (`idle`). */
export function useObjectDocuments(projectUid: string | null): ObjectDocuments {
  // Cursors belong to the listing they were issued under, so a walk begun on one object is dropped, not continued, on another.
  const [held, setHeld] = useState<{ readonly projectUid: string | null; readonly cursors: readonly (string | undefined)[] }>({
    projectUid, cursors: [undefined],
  });
  const cursors = held.projectUid === projectUid ? held.cursors : [undefined];
  const results = useQueries({
    queries: cursors.map((cursor) => ({
      ...documentListQueryOptions((projectUid ?? '') as ProjectUid, cursor),
      enabled: projectUid !== null,
    })),
  });
  const step = advanceSectionWalk(cursors, results.map((result) => result.data));
  const wanted = step.cursors;
  const changed = held.projectUid !== projectUid || wanted.length !== cursors.length
    || wanted.some((cursor, index) => cursor !== cursors[index]);

  // The cursors the walk should hold are adopted in the render that learns them; a render that already holds them changes nothing.
  if (projectUid !== null && changed) setHeld({ projectUid, cursors: wanted });

  if (projectUid === null) return { status: 'idle' };
  if (step.kind === 'cycle' || results.some((result, index) => result.isError && cursors[index] === wanted[index])) {
    return {
      status: 'failed',
      retry: () => {
        for (const result of results) if (result.isError) void result.refetch();
      },
    };
  }
  if (step.kind === 'complete' && !changed) return { status: 'complete', items: step.items };
  return { status: 'pending' };
}
