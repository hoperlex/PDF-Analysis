'use client';

/**
 * Every page of the listing the section page shows, followed to its end (`UI-A-35`, «Выбрать все»).
 *
 * «Выбрать все» and «Выбрать не запускавшиеся» chose the cards of the page in view — up to fifty, silently. The original's
 * section page has every document of the section on one screen, so its «выбрать все» is the whole section. Here the
 * listing is paged by the server's cursor, and the same rule the document page's «N из M» uses
 * (`useSectionDocumentWalk`, `advanceSectionWalk`) reads it through: page after page under the cursor each page names, until the
 * server names none, never a cap and never a part of the listing offered as the whole.
 *
 * The walk is the **listing in view**, not the section unfiltered: it carries the page's own narrowing — the audit state
 * (`?filter=not_run`), archived documents and the tag — through `documentListQueryOptions`, the one source of the listing's
 * request and cache key. With no narrowing its pages are the very ones `useSectionDocumentWalk` reads for the document page, so a
 * reader who walks on to a document already holds them. It is read only when asked for (`enabled`): a section that fits one
 * page, or a session that cannot start an audit, reads nothing more than the page.
 */

import { useState } from 'react';
import { useQueries } from '@tanstack/react-query';

import type { DocumentVersion, ProjectSection, ProjectUid } from '@/shared/api';
import { advanceSectionWalk, documentListQueryOptions, sectionListingAudit } from '@/entities/document-version';
import type { SectionAuditFilter } from '@/entities/document-version';

export type ListingWalk =
  /** Not asked for: the page in view is the whole listing, or nothing here needs the whole. */
  | { readonly status: 'idle' }
  | { readonly status: 'pending' }
  /** A page failed, or the listing named a cursor twice. No partial list is offered. */
  | { readonly status: 'failed'; readonly retry: () => void }
  | { readonly status: 'complete'; readonly items: readonly DocumentVersion[] };

export interface ListingScope {
  readonly projectUid: ProjectUid;
  readonly sectionCode: ProjectSection;
  readonly auditFilter: SectionAuditFilter | null;
  readonly includeArchived: boolean;
  readonly tag: string | null;
}

export function useListingWalk(enabled: boolean, scope: ListingScope): ListingWalk {
  const { projectUid, sectionCode, auditFilter, includeArchived, tag } = scope;
  // Cursors belong to the listing they were issued under (the server refuses one under another narrowing), so a walk begun
  // under one narrowing is dropped, not continued, when the narrowing changes.
  const signature = `${projectUid}|${sectionCode}|${auditFilter ?? ''}|${includeArchived ? 'a' : ''}|${tag ?? ''}`;
  const [held, setHeld] = useState<{ readonly signature: string; readonly cursors: readonly (string | undefined)[] }>({
    signature,
    cursors: [undefined],
  });
  const cursors = held.signature === signature ? held.cursors : [undefined];
  const results = useQueries({
    queries: cursors.map((cursor) => ({
      ...documentListQueryOptions(
        projectUid, cursor, sectionCode, includeArchived, tag ?? undefined, sectionListingAudit(auditFilter),
      ),
      enabled,
    })),
  });
  const step = advanceSectionWalk(cursors, results.map((result) => result.data));
  const wanted = step.cursors;
  const changed = held.signature !== signature || wanted.length !== cursors.length || wanted.some((cursor, index) => cursor !== cursors[index]);

  // The cursors the walk should hold are adopted in the render that learns them; a render that already holds them changes nothing.
  if (enabled && changed) setHeld({ signature, cursors: wanted });

  if (!enabled) return { status: 'idle' };
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
