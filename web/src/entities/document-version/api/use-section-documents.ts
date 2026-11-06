'use client';

/**
 * The documents of one section — the one listing the section page and the document page's «n из m» share
 * (`R-151l`, `UI-A-28`).
 *
 * `listDocuments` with `section_code` (contract 1.20.0) keeps the documents whose **current** version an expert
 * confirmed for the section, and `order=audit` (contract 1.34.0, `UI-A-49`) is the order the section page shows.
 * Both are the server's, so the order lives here once: the section page reads one page of it through
 * {@link useSectionDocumentList}, and the document page reads every page through {@link useSectionDocumentWalk},
 * under the very same cache keys, so a reader who came from the section page already holds the first page.
 *
 * `auditFilter` is the section page's `?filter=not_run` (`UI-A-38`); the document page never narrows.
 */

import { useEffect, useState } from 'react';
import { useQueries, useQuery } from '@tanstack/react-query';

import type { DocumentVersion, DocumentVersionPage, ProjectSection, ProjectUid } from '@/shared/api';

import type { SectionAuditFilter } from '../model/audit-state';
import { advanceSectionWalk } from '../model/section-walk';
import type { DocumentListAudit } from './use-document-list';
import { documentListQueryOptions } from './use-document-list';

/** The audit narrowing and order of a section's listing: the server's `order=audit`, and `audit_state` when filtered. */
export function sectionListingAudit(auditFilter: SectionAuditFilter | null): DocumentListAudit {
  return { ...(auditFilter === null ? {} : { state: auditFilter }), order: 'audit' };
}

/**
 * What else narrows the section page's listing: archived documents on request (`R-151a`) and one tag (`R-151e`).
 * The walk of the document page never carries either: a position among the section's documents is counted over
 * the documents the section holds.
 */
export interface SectionListingScope {
  readonly includeArchived?: boolean | undefined;
  readonly tag?: string | undefined;
}

function sectionListQueryOptions(
  projectUid: ProjectUid, sectionCode: ProjectSection, cursor: string | undefined, auditFilter: SectionAuditFilter | null,
  scope: SectionListingScope = {},
) {
  return documentListQueryOptions(
    projectUid, cursor, sectionCode, scope.includeArchived ?? false, scope.tag, sectionListingAudit(auditFilter),
  );
}

/** One page of a section's documents, in the section page's order. */
export function useSectionDocumentList(
  projectUid: ProjectUid, sectionCode: ProjectSection, cursor: string | undefined, auditFilter: SectionAuditFilter | null,
  scope: SectionListingScope = {},
) {
  return useQuery<DocumentVersionPage>(sectionListQueryOptions(projectUid, sectionCode, cursor, auditFilter, scope));
}

/** What a reader of the whole section is told. */
export type SectionWalk =
  | { readonly status: 'pending' }
  /** A page failed, or the listing named a cursor twice. No partial list is offered: a position needs the whole. */
  | { readonly status: 'failed' }
  | { readonly status: 'complete'; readonly items: readonly DocumentVersion[] };

/**
 * Every page of a section's documents, in the server's order, following the cursor to its end.
 *
 * The caller keys this hook by project and section (a different section is a different walk). While a page is
 * loading the answer is `pending`; if any page fails it is `failed`, so a screen shows nothing rather than a
 * position computed from a part of the listing.
 */
export function useSectionDocumentWalk(projectUid: ProjectUid, sectionCode: ProjectSection): SectionWalk {
  const [held, setHeld] = useState<readonly (string | undefined)[]>([undefined]);
  const results = useQueries({
    queries: held.map((cursor) => sectionListQueryOptions(projectUid, sectionCode, cursor, null)),
  });
  const step = advanceSectionWalk(held, results.map((result) => result.data));
  const wanted = step.cursors;
  const changed = wanted.length !== held.length || wanted.some((cursor, index) => cursor !== held[index]);

  // The cursors the walk should hold are adopted here; a render that already holds them changes nothing.
  useEffect(() => {
    if (changed) setHeld(wanted);
  }, [changed, wanted]);

  if (step.kind === 'cycle' || results.some((result, index) => result.isError && held[index] === wanted[index])) {
    return { status: 'failed' };
  }
  if (step.kind === 'complete' && !changed) return { status: 'complete', items: step.items };
  return { status: 'pending' };
}
